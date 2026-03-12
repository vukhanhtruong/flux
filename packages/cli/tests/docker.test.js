import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  CONTAINER_NAME,
  IMAGE_NAME,
  buildEnvVars,
  buildContainerConfig,
} from "../src/docker.js";

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
});
