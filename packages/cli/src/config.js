import fs from "node:fs";
import path from "node:path";
import os from "node:os";

export const CONFIG_DIR_NAME = ".flux-finance";
export const ENV_FILE_NAME = ".env";

export function getFluxDir() {
  return path.join(os.homedir(), CONFIG_DIR_NAME);
}

export function getConfigPath() {
  return path.join(getFluxDir(), ENV_FILE_NAME);
}

export function getDataDir() {
  return path.join(getFluxDir(), "data");
}

export function readConfig() {
  const envPath = getConfigPath();
  if (!fs.existsSync(envPath)) {
    return {};
  }
  const content = fs.readFileSync(envPath, "utf-8");
  const config = {};
  for (const line of content.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eqIndex = trimmed.indexOf("=");
    if (eqIndex === -1) continue;
    const key = trimmed.slice(0, eqIndex).trim();
    const value = trimmed.slice(eqIndex + 1).trim();
    config[key] = value;
  }
  return config;
}

export function writeConfig(config) {
  const fluxDir = getFluxDir();
  const dataDir = getDataDir();

  fs.mkdirSync(fluxDir, { recursive: true });
  fs.mkdirSync(path.join(dataDir, "sqlite"), { recursive: true });
  fs.mkdirSync(path.join(dataDir, "zvec"), { recursive: true });
  fs.mkdirSync(path.join(dataDir, "backups"), { recursive: true });

  const lines = Object.entries(config)
    .map(([key, value]) => `${key}=${value}`)
    .join("\n");
  fs.writeFileSync(path.join(fluxDir, ENV_FILE_NAME), lines + "\n", {
    mode: 0o600,
  });
}
