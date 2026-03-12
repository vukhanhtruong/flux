import Dockerode from "dockerode";

export const CONTAINER_NAME = "flux-finance";
export const IMAGE_NAME = "vukhanhtruong/flux:latest";

const FIXED_ENV_VARS = {
  DATABASE_PATH: "/data/sqlite/flux.db",
  ZVEC_PATH: "/data/zvec",
  BACKUP_LOCAL_DIR: "/data/backups",
  CORS_ORIGINS: "http://localhost",
  MCP_CONFIG_PATH: "/app/mcp-config.json",
};

const HOST_ONLY_KEYS = new Set(["PORT"]);

export function buildEnvVars(config) {
  const env = [];
  for (const [key, value] of Object.entries(config)) {
    if (!HOST_ONLY_KEYS.has(key) && value) {
      env.push(`${key}=${value}`);
    }
  }
  const userKeys = new Set(env.map((e) => e.split("=")[0]));
  for (const [key, value] of Object.entries(FIXED_ENV_VARS)) {
    if (!userKeys.has(key)) {
      env.push(`${key}=${value}`);
    }
  }
  return env;
}

export function buildContainerConfig(config, dataDir) {
  const port = config.PORT || "5173";
  return {
    name: CONTAINER_NAME,
    Image: IMAGE_NAME,
    Env: buildEnvVars(config),
    ExposedPorts: { "80/tcp": {} },
    HostConfig: {
      PortBindings: {
        "80/tcp": [{ HostPort: port }],
      },
      Binds: [`${dataDir}:/data`],
      RestartPolicy: { Name: "unless-stopped" },
    },
  };
}

export function createDockerClient() {
  return new Dockerode();
}

export async function isDockerRunning(docker) {
  try {
    const client = docker || createDockerClient();
    await client.ping();
    return true;
  } catch {
    return false;
  }
}

export async function pullImage(onProgress, docker) {
  const client = docker || createDockerClient();
  const stream = await client.pull(IMAGE_NAME);
  return new Promise((resolve, reject) => {
    client.modem.followProgress(stream, (err, output) => {
      if (err) reject(err);
      else resolve(output);
    }, onProgress);
  });
}

export async function getContainer(docker) {
  const client = docker || createDockerClient();
  const containers = await client.listContainers({
    all: true,
    filters: { name: [CONTAINER_NAME] },
  });
  if (containers.length === 0) return null;
  return client.getContainer(containers[0].Id);
}

export async function getContainerStatus(docker) {
  const container = await getContainer(docker);
  if (!container) return { exists: false, running: false };
  const info = await container.inspect();
  return {
    exists: true,
    running: info.State.Running,
    status: info.State.Status,
    ports: info.NetworkSettings.Ports,
  };
}

export async function startContainer(config, dataDir, docker) {
  const client = docker || createDockerClient();
  const existing = await getContainer(client);
  if (existing) {
    try { await existing.stop(); } catch { /* already stopped */ }
    await existing.remove();
  }
  const containerConfig = buildContainerConfig(config, dataDir);
  const container = await client.createContainer(containerConfig);
  await container.start();
  return container;
}

export async function stopContainer(docker) {
  const container = await getContainer(docker);
  if (!container) return false;
  await container.stop();
  return true;
}

export async function removeContainer(docker) {
  const container = await getContainer(docker);
  if (!container) return false;
  try { await container.stop(); } catch { /* already stopped */ }
  await container.remove();
  return true;
}

export async function containerLogs(follow = true, docker) {
  const container = await getContainer(docker);
  if (!container) return null;
  return container.logs({
    stdout: true,
    stderr: true,
    follow,
    tail: 50,
  });
}
