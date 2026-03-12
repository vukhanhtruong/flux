import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  CONTAINER_NAME,
  IMAGE_NAME,
  buildEnvVars,
  buildContainerConfig,
  createDockerClient,
  isDockerRunning,
  pullImage,
  getContainer,
  getContainerStatus,
  startContainer,
  stopContainer,
  removeContainer,
  containerLogs,
} from "../src/docker.js";

// Helper: create a mock Docker client
function createMockDocker(overrides = {}) {
  return {
    ping: overrides.ping || (async () => "OK"),
    pull: overrides.pull || (async () => "stream"),
    listContainers: overrides.listContainers || (async () => []),
    getContainer: overrides.getContainer || (() => createMockContainer()),
    createContainer: overrides.createContainer || (async () => createMockContainer()),
    modem: {
      followProgress: overrides.followProgress || ((stream, onFinished) => {
        onFinished(null, [{ status: "done" }]);
      }),
    },
  };
}

function createMockContainer(overrides = {}) {
  return {
    start: overrides.start || (async () => {}),
    stop: overrides.stop || (async () => {}),
    remove: overrides.remove || (async () => {}),
    inspect: overrides.inspect || (async () => ({
      State: { Running: true, Status: "running" },
      NetworkSettings: { Ports: { "80/tcp": [{ HostPort: "5173" }] } },
    })),
    logs: overrides.logs || (async () => "log stream"),
  };
}

describe("docker", () => {
  it("exports correct container name", () => {
    assert.equal(CONTAINER_NAME, "flux-finance");
  });

  it("exports correct image name", () => {
    assert.equal(IMAGE_NAME, "vukhanhtruong/flux:latest");
  });

  it("buildEnvVars combines .env config with fixed vars", () => {
    const config = {
      TELEGRAM_BOT_TOKEN: "123:ABC",
      PORT: "5173",
    };
    const envVars = buildEnvVars(config);
    assert.ok(envVars.includes("TELEGRAM_BOT_TOKEN=123:ABC"));
    assert.ok(envVars.includes("DATABASE_PATH=/data/sqlite/flux.db"));
    assert.ok(envVars.includes("ZVEC_PATH=/data/zvec"));
    assert.ok(envVars.includes("BACKUP_LOCAL_DIR=/data/backups"));
    assert.ok(envVars.includes("MCP_CONFIG_PATH=/app/mcp-config.json"));
    // PORT should NOT be in container env — it's the host port
    assert.ok(!envVars.some((v) => v.startsWith("PORT=")));
  });

  it("buildEnvVars skips empty/falsy values", () => {
    const config = { TELEGRAM_BOT_TOKEN: "", EMPTY: null };
    const envVars = buildEnvVars(config);
    assert.ok(!envVars.some((v) => v.startsWith("TELEGRAM_BOT_TOKEN=")));
    assert.ok(!envVars.some((v) => v.startsWith("EMPTY=")));
  });

  it("buildEnvVars does not override user-provided fixed keys", () => {
    const config = { DATABASE_PATH: "/custom/path" };
    const envVars = buildEnvVars(config);
    assert.ok(envVars.includes("DATABASE_PATH=/custom/path"));
    assert.ok(!envVars.includes("DATABASE_PATH=/data/sqlite/flux.db"));
  });

  it("buildContainerConfig creates correct docker config", () => {
    const config = { PORT: "8080" };
    const dataDir = "/tmp/test-data";
    const containerConfig = buildContainerConfig(config, dataDir);
    assert.equal(containerConfig.name, "flux-finance");
    assert.equal(containerConfig.Image, "vukhanhtruong/flux:latest");
    assert.deepEqual(containerConfig.HostConfig.PortBindings["80/tcp"], [
      { HostPort: "8080" },
    ]);
    assert.ok(
      containerConfig.HostConfig.Binds[0].endsWith(":/data")
    );
    assert.deepEqual(containerConfig.HostConfig.RestartPolicy, {
      Name: "unless-stopped",
    });
  });

  it("buildContainerConfig defaults to port 5173", () => {
    const containerConfig = buildContainerConfig({}, "/tmp/data");
    assert.deepEqual(containerConfig.HostConfig.PortBindings["80/tcp"], [
      { HostPort: "5173" },
    ]);
  });

  it("createDockerClient returns a Dockerode instance", () => {
    const client = createDockerClient();
    assert.ok(client);
    assert.ok(typeof client.ping === "function");
  });

  // --- Async function tests with mock Docker client ---

  it("isDockerRunning returns true when Docker responds", async () => {
    const docker = createMockDocker();
    const result = await isDockerRunning(docker);
    assert.equal(result, true);
  });

  it("isDockerRunning returns false when Docker fails", async () => {
    const docker = createMockDocker({
      ping: async () => { throw new Error("not running"); },
    });
    const result = await isDockerRunning(docker);
    assert.equal(result, false);
  });

  it("pullImage resolves on success", async () => {
    const progressCalls = [];
    const docker = createMockDocker({
      pull: async () => "stream",
      followProgress: (stream, onFinished, onProgress) => {
        if (onProgress) onProgress({ status: "pulling" });
        onFinished(null, [{ status: "complete" }]);
      },
    });
    const result = await pullImage((p) => progressCalls.push(p), docker);
    assert.deepEqual(result, [{ status: "complete" }]);
    assert.equal(progressCalls.length, 1);
  });

  it("pullImage rejects on error", async () => {
    const docker = createMockDocker({
      pull: async () => "stream",
      followProgress: (stream, onFinished) => {
        onFinished(new Error("pull failed"));
      },
    });
    await assert.rejects(() => pullImage(undefined, docker), { message: "pull failed" });
  });

  it("getContainer returns null when no containers exist", async () => {
    const docker = createMockDocker({ listContainers: async () => [] });
    const result = await getContainer(docker);
    assert.equal(result, null);
  });

  it("getContainer returns container when found", async () => {
    const mockContainer = createMockContainer();
    const docker = createMockDocker({
      listContainers: async () => [{ Id: "abc123" }],
      getContainer: () => mockContainer,
    });
    const result = await getContainer(docker);
    assert.equal(result, mockContainer);
  });

  it("getContainerStatus returns not-exists when no container", async () => {
    const docker = createMockDocker({ listContainers: async () => [] });
    const result = await getContainerStatus(docker);
    assert.deepEqual(result, { exists: false, running: false });
  });

  it("getContainerStatus returns running status", async () => {
    const mockContainer = createMockContainer();
    const docker = createMockDocker({
      listContainers: async () => [{ Id: "abc123" }],
      getContainer: () => mockContainer,
    });
    const result = await getContainerStatus(docker);
    assert.equal(result.exists, true);
    assert.equal(result.running, true);
    assert.equal(result.status, "running");
  });

  it("startContainer creates and starts a new container", async () => {
    let created = false;
    let started = false;
    const newContainer = createMockContainer({
      start: async () => { started = true; },
    });
    const docker = createMockDocker({
      listContainers: async () => [],
      createContainer: async () => { created = true; return newContainer; },
    });
    const result = await startContainer({ PORT: "8080" }, "/tmp/data", docker);
    assert.ok(created);
    assert.ok(started);
    assert.equal(result, newContainer);
  });

  it("startContainer removes existing container before creating", async () => {
    let stopped = false;
    let removed = false;
    const existingContainer = createMockContainer({
      stop: async () => { stopped = true; },
      remove: async () => { removed = true; },
    });
    const newContainer = createMockContainer();
    const docker = createMockDocker({
      listContainers: async () => [{ Id: "old123" }],
      getContainer: () => existingContainer,
      createContainer: async () => newContainer,
    });
    await startContainer({}, "/tmp/data", docker);
    assert.ok(stopped);
    assert.ok(removed);
  });

  it("startContainer handles stop error on existing container gracefully", async () => {
    const existingContainer = createMockContainer({
      stop: async () => { throw new Error("already stopped"); },
      remove: async () => {},
    });
    const newContainer = createMockContainer();
    const docker = createMockDocker({
      listContainers: async () => [{ Id: "old123" }],
      getContainer: () => existingContainer,
      createContainer: async () => newContainer,
    });
    // Should not throw
    await startContainer({}, "/tmp/data", docker);
  });

  it("stopContainer returns false when no container exists", async () => {
    const docker = createMockDocker({ listContainers: async () => [] });
    const result = await stopContainer(docker);
    assert.equal(result, false);
  });

  it("stopContainer stops container and returns true", async () => {
    let stopped = false;
    const mockContainer = createMockContainer({
      stop: async () => { stopped = true; },
    });
    const docker = createMockDocker({
      listContainers: async () => [{ Id: "abc123" }],
      getContainer: () => mockContainer,
    });
    const result = await stopContainer(docker);
    assert.equal(result, true);
    assert.ok(stopped);
  });

  it("removeContainer returns false when no container exists", async () => {
    const docker = createMockDocker({ listContainers: async () => [] });
    const result = await removeContainer(docker);
    assert.equal(result, false);
  });

  it("removeContainer stops and removes container", async () => {
    let stopped = false;
    let removed = false;
    const mockContainer = createMockContainer({
      stop: async () => { stopped = true; },
      remove: async () => { removed = true; },
    });
    const docker = createMockDocker({
      listContainers: async () => [{ Id: "abc123" }],
      getContainer: () => mockContainer,
    });
    const result = await removeContainer(docker);
    assert.equal(result, true);
    assert.ok(stopped);
    assert.ok(removed);
  });

  it("removeContainer handles stop error gracefully", async () => {
    const mockContainer = createMockContainer({
      stop: async () => { throw new Error("already stopped"); },
      remove: async () => {},
    });
    const docker = createMockDocker({
      listContainers: async () => [{ Id: "abc123" }],
      getContainer: () => mockContainer,
    });
    const result = await removeContainer(docker);
    assert.equal(result, true);
  });

  it("containerLogs returns null when no container exists", async () => {
    const docker = createMockDocker({ listContainers: async () => [] });
    const result = await containerLogs(true, docker);
    assert.equal(result, null);
  });

  it("containerLogs returns log stream", async () => {
    const mockContainer = createMockContainer({
      logs: async (opts) => {
        assert.equal(opts.stdout, true);
        assert.equal(opts.stderr, true);
        assert.equal(opts.follow, true);
        assert.equal(opts.tail, 50);
        return "log data";
      },
    });
    const docker = createMockDocker({
      listContainers: async () => [{ Id: "abc123" }],
      getContainer: () => mockContainer,
    });
    const result = await containerLogs(true, docker);
    assert.equal(result, "log data");
  });

  it("containerLogs passes follow=false", async () => {
    const mockContainer = createMockContainer({
      logs: async (opts) => {
        assert.equal(opts.follow, false);
        return "log data";
      },
    });
    const docker = createMockDocker({
      listContainers: async () => [{ Id: "abc123" }],
      getContainer: () => mockContainer,
    });
    await containerLogs(false, docker);
  });
});
