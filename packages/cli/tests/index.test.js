import { describe, it, mock, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import realFs from "node:fs";

// Mock all dependencies before importing index.js
const mockReadConfig = mock.fn();
const mockWriteConfig = mock.fn();
const mockGetDataDir = mock.fn();
const mockGetFluxDir = mock.fn();
const mockIsDockerRunning = mock.fn();
const mockPullImage = mock.fn();
const mockStartContainer = mock.fn();
const mockStopContainer = mock.fn();
const mockRemoveContainer = mock.fn();
const mockGetContainerStatus = mock.fn();
const mockContainerLogs = mock.fn();
const mockRunWizard = mock.fn();
const mockAcquireClaudeToken = mock.fn();
const mockPrompts = mock.fn();
const mockExistsSync = mock.fn();
const mockUnlinkSync = mock.fn();

mock.module("../src/config.js", {
  namedExports: {
    readConfig: mockReadConfig,
    writeConfig: mockWriteConfig,
    getDataDir: mockGetDataDir,
    getFluxDir: mockGetFluxDir,
    getConfigPath: () => "/tmp/.flux-finance/.env",
    CONFIG_DIR_NAME: ".flux-finance",
    ENV_FILE_NAME: ".env",
  },
});

mock.module("../src/docker.js", {
  namedExports: {
    isDockerRunning: mockIsDockerRunning,
    pullImage: mockPullImage,
    startContainer: mockStartContainer,
    stopContainer: mockStopContainer,
    removeContainer: mockRemoveContainer,
    getContainerStatus: mockGetContainerStatus,
    containerLogs: mockContainerLogs,
    CONTAINER_NAME: "flux-finance",
    IMAGE_NAME: "vukhanhtruong/flux:latest",
    buildEnvVars: () => [],
    buildContainerConfig: () => ({}),
    createDockerClient: () => ({}),
    getContainer: async () => null,
  },
});

mock.module("../src/wizard.js", {
  namedExports: {
    runWizard: mockRunWizard,
    validateBotToken: () => true,
    validateUserId: () => true,
    validatePort: () => true,
    generateSecretKey: () => "test-uuid",
  },
});

mock.module("../src/claude-auth.js", {
  namedExports: {
    readClaudeToken: () => null,
    acquireClaudeToken: mockAcquireClaudeToken,
  },
});

mock.module("prompts", {
  defaultExport: mockPrompts,
});

mock.module("node:fs", {
  defaultExport: {
    ...realFs,
    existsSync: mockExistsSync,
    unlinkSync: mockUnlinkSync,
    readFileSync: realFs.readFileSync,
    writeFileSync: realFs.writeFileSync,
    mkdirSync: realFs.mkdirSync,
    rmSync: realFs.rmSync,
    mkdtempSync: realFs.mkdtempSync,
  },
  namedExports: {
    existsSync: mockExistsSync,
    unlinkSync: mockUnlinkSync,
    readFileSync: realFs.readFileSync,
    writeFileSync: realFs.writeFileSync,
    mkdirSync: realFs.mkdirSync,
    rmSync: realFs.rmSync,
    mkdtempSync: realFs.mkdtempSync,
  },
});

// Must import after mocking
const { program } = await import("../src/index.js");

describe("cli commands", () => {
  let originalLog;
  let originalError;
  let originalExit;
  let exitCode;
  let logs;

  beforeEach(() => {
    originalLog = console.log;
    originalError = console.error;
    originalExit = process.exit;
    exitCode = null;
    logs = [];

    console.log = (...args) => logs.push(args.join(" "));
    console.error = () => {};
    process.exit = (code) => { exitCode = code; throw new Error(`EXIT_${code}`); };

    // Reset mocks
    mockReadConfig.mock.resetCalls();
    mockWriteConfig.mock.resetCalls();
    mockGetDataDir.mock.resetCalls();
    mockGetFluxDir.mock.resetCalls();
    mockPullImage.mock.resetCalls();
    mockStartContainer.mock.resetCalls();
    mockStopContainer.mock.resetCalls();
    mockRemoveContainer.mock.resetCalls();
    mockGetContainerStatus.mock.resetCalls();
    mockContainerLogs.mock.resetCalls();
    mockRunWizard.mock.resetCalls();
    mockPrompts.mock.resetCalls();
    mockAcquireClaudeToken.mock.resetCalls();
    mockExistsSync.mock.resetCalls();
    mockUnlinkSync.mock.resetCalls();
  });

  afterEach(() => {
    console.log = originalLog;
    console.error = originalError;
    process.exit = originalExit;
  });

  it("default action runs wizard when no config exists", async () => {
    mockReadConfig.mock.mockImplementation(() => ({}));
    mockRunWizard.mock.mockImplementation(async () => {});

    await program.parseAsync(["node", "flux-finance"]);
    assert.equal(mockRunWizard.mock.callCount(), 1);
  });

  it("default action shows running message when container is running", async () => {
    mockReadConfig.mock.mockImplementation(() => ({ PORT: "8080", TELEGRAM_BOT_TOKEN: "t" }));
    mockGetContainerStatus.mock.mockImplementation(async () => ({ exists: true, running: true }));

    await program.parseAsync(["node", "flux-finance"]);
    assert.ok(logs.some((l) => l.includes("already running")));
  });

  it("default action starts container when not running", async () => {
    mockReadConfig.mock.mockImplementation(() => ({ PORT: "5173", TELEGRAM_BOT_TOKEN: "t" }));
    mockGetContainerStatus.mock.mockImplementation(async () => ({ exists: true, running: false }));
    mockStartContainer.mock.mockImplementation(async () => {});
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");

    await program.parseAsync(["node", "flux-finance"]);
    assert.equal(mockStartContainer.mock.callCount(), 1);
  });

  it("default action handles start failure", async () => {
    mockReadConfig.mock.mockImplementation(() => ({ PORT: "5173", TELEGRAM_BOT_TOKEN: "t" }));
    mockGetContainerStatus.mock.mockImplementation(async () => ({ exists: true, running: false }));
    mockStartContainer.mock.mockImplementation(async () => { throw new Error("failed"); });
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");

    await assert.rejects(() => program.parseAsync(["node", "flux-finance"]), { message: "EXIT_1" });
  });

  it("start command runs wizard when no config", async () => {
    mockReadConfig.mock.mockImplementation(() => ({}));
    mockRunWizard.mock.mockImplementation(async () => {});

    await program.parseAsync(["node", "flux-finance", "start"]);
    assert.equal(mockRunWizard.mock.callCount(), 1);
  });

  it("start command starts container with config", async () => {
    mockReadConfig.mock.mockImplementation(() => ({ PORT: "5173", TELEGRAM_BOT_TOKEN: "t" }));
    mockStartContainer.mock.mockImplementation(async () => {});
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");

    await program.parseAsync(["node", "flux-finance", "start"]);
    assert.equal(mockStartContainer.mock.callCount(), 1);
  });

  it("start command handles failure", async () => {
    mockReadConfig.mock.mockImplementation(() => ({ TELEGRAM_BOT_TOKEN: "t" }));
    mockStartContainer.mock.mockImplementation(async () => { throw new Error("fail"); });
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");

    await assert.rejects(() => program.parseAsync(["node", "flux-finance", "start"]), { message: "EXIT_1" });
  });

  it("stop command stops running container", async () => {
    mockStopContainer.mock.mockImplementation(async () => true);

    await program.parseAsync(["node", "flux-finance", "stop"]);
    assert.equal(mockStopContainer.mock.callCount(), 1);
  });

  it("stop command handles not running", async () => {
    mockStopContainer.mock.mockImplementation(async () => false);

    await program.parseAsync(["node", "flux-finance", "stop"]);
    assert.equal(mockStopContainer.mock.callCount(), 1);
  });

  it("stop command handles failure", async () => {
    mockStopContainer.mock.mockImplementation(async () => { throw new Error("fail"); });

    await assert.rejects(() => program.parseAsync(["node", "flux-finance", "stop"]), { message: "EXIT_1" });
  });

  it("status command shows not installed", async () => {
    mockGetContainerStatus.mock.mockImplementation(async () => ({ exists: false, running: false }));
    mockReadConfig.mock.mockImplementation(() => ({}));

    await program.parseAsync(["node", "flux-finance", "status"]);
    assert.ok(logs.some((l) => l.includes("not installed")));
  });

  it("status command shows running", async () => {
    mockGetContainerStatus.mock.mockImplementation(async () => ({
      exists: true, running: true, status: "running",
      ports: { "80/tcp": [{ HostPort: "5173" }] },
    }));
    mockReadConfig.mock.mockImplementation(() => ({ PORT: "5173" }));

    await program.parseAsync(["node", "flux-finance", "status"]);
    assert.ok(logs.some((l) => l.includes("running")));
  });

  it("status command shows stopped", async () => {
    mockGetContainerStatus.mock.mockImplementation(async () => ({ exists: true, running: false }));
    mockReadConfig.mock.mockImplementation(() => ({}));

    await program.parseAsync(["node", "flux-finance", "status"]);
    assert.ok(logs.some((l) => l.includes("stopped")));
  });

  it("logs command streams logs", async () => {
    const mockStream = { pipe: mock.fn() };
    mockContainerLogs.mock.mockImplementation(async () => mockStream);

    await program.parseAsync(["node", "flux-finance", "logs"]);
    assert.equal(mockStream.pipe.mock.callCount(), 1);
  });

  it("logs command handles no container", async () => {
    mockContainerLogs.mock.mockImplementation(async () => null);

    await assert.rejects(() => program.parseAsync(["node", "flux-finance", "logs"]), { message: "EXIT_1" });
  });

  it("update command pulls and restarts", async () => {
    mockReadConfig.mock.mockImplementation(() => ({ PORT: "5173", TELEGRAM_BOT_TOKEN: "t" }));
    mockPullImage.mock.mockImplementation(async () => {});
    mockStartContainer.mock.mockImplementation(async () => {});
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");

    await program.parseAsync(["node", "flux-finance", "update"]);
    assert.equal(mockPullImage.mock.callCount(), 1);
    assert.equal(mockStartContainer.mock.callCount(), 1);
  });

  it("update command handles no config", async () => {
    mockReadConfig.mock.mockImplementation(() => ({}));

    await assert.rejects(() => program.parseAsync(["node", "flux-finance", "update"]), { message: "EXIT_1" });
  });

  it("update command handles pull failure", async () => {
    mockReadConfig.mock.mockImplementation(() => ({ TELEGRAM_BOT_TOKEN: "t" }));
    mockPullImage.mock.mockImplementation(async () => { throw new Error("pull failed"); });

    await assert.rejects(() => program.parseAsync(["node", "flux-finance", "update"]), { message: "EXIT_1" });
  });

  it("update command handles restart failure", async () => {
    mockReadConfig.mock.mockImplementation(() => ({ TELEGRAM_BOT_TOKEN: "t" }));
    mockPullImage.mock.mockImplementation(async () => {});
    mockStartContainer.mock.mockImplementation(async () => { throw new Error("restart failed"); });
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");

    await assert.rejects(() => program.parseAsync(["node", "flux-finance", "update"]), { message: "EXIT_1" });
  });

  it("config command shows empty config", async () => {
    mockReadConfig.mock.mockImplementation(() => ({}));

    await program.parseAsync(["node", "flux-finance", "config"]);
    assert.ok(logs.some((l) => l.includes("No configuration found")));
  });

  it("config command shows config with masked secrets", async () => {
    mockReadConfig.mock.mockImplementation(() => ({
      PORT: "5173",
      TELEGRAM_BOT_TOKEN: "7123456789:AAHBx5K-very-long-token",
      FLUX_SECRET_KEY: "some-uuid-value",
    }));

    await program.parseAsync(["node", "flux-finance", "config"]);
    // PORT should be shown in full
    assert.ok(logs.some((l) => l.includes("5173")));
    // TOKEN should be masked
    assert.ok(logs.some((l) => l.includes("...")));
  });

  it("ngrok command saves token and restarts if running", async () => {
    mockReadConfig.mock.mockImplementation(() => ({ PORT: "5173" }));
    mockWriteConfig.mock.mockImplementation(() => {});
    mockGetContainerStatus.mock.mockImplementation(async () => ({ exists: true, running: true }));
    mockStartContainer.mock.mockImplementation(async () => {});
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");
    mockPrompts.mock.mockImplementation(async () => ({ ngrokToken: "ngrok-test-token" }));

    await program.parseAsync(["node", "flux-finance", "ngrok"]);
    assert.equal(mockWriteConfig.mock.callCount(), 1);
    assert.equal(mockStartContainer.mock.callCount(), 1);
  });

  it("ngrok command saves token without restart if not running", async () => {
    mockReadConfig.mock.mockImplementation(() => ({ PORT: "5173" }));
    mockWriteConfig.mock.mockImplementation(() => {});
    mockGetContainerStatus.mock.mockImplementation(async () => ({ exists: false, running: false }));
    mockPrompts.mock.mockImplementation(async () => ({ ngrokToken: "ngrok-test-token" }));

    await program.parseAsync(["node", "flux-finance", "ngrok"]);
    assert.equal(mockWriteConfig.mock.callCount(), 1);
    assert.equal(mockStartContainer.mock.callCount(), 0);
  });

  it("ngrok command does nothing with empty token", async () => {
    mockReadConfig.mock.mockImplementation(() => ({}));
    mockPrompts.mock.mockImplementation(async () => ({ ngrokToken: undefined }));

    await program.parseAsync(["node", "flux-finance", "ngrok"]);
    assert.equal(mockWriteConfig.mock.callCount(), 0);
  });

  it("ngrok command handles restart failure", async () => {
    mockReadConfig.mock.mockImplementation(() => ({ PORT: "5173" }));
    mockWriteConfig.mock.mockImplementation(() => {});
    mockGetContainerStatus.mock.mockImplementation(async () => ({ exists: true, running: true }));
    mockStartContainer.mock.mockImplementation(async () => { throw new Error("fail"); });
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");
    mockPrompts.mock.mockImplementation(async () => ({ ngrokToken: "ngrok-test" }));

    // Should not throw — ngrok restart failure is non-fatal
    await program.parseAsync(["node", "flux-finance", "ngrok"]);
  });

  it("reset command removes config and container", async () => {
    mockRemoveContainer.mock.mockImplementation(async () => true);
    mockGetFluxDir.mock.mockImplementation(() => "/tmp/.flux-finance");
    mockPrompts.mock.mockImplementation(async () => ({ confirm: true }));
    mockExistsSync.mock.mockImplementation(() => true);
    mockUnlinkSync.mock.mockImplementation(() => {});

    await program.parseAsync(["node", "flux-finance", "reset"]);
    assert.equal(mockRemoveContainer.mock.callCount(), 1);
    assert.equal(mockUnlinkSync.mock.callCount(), 1);
  });

  it("reset command handles cancel", async () => {
    mockPrompts.mock.mockImplementation(async () => ({ confirm: false }));

    await program.parseAsync(["node", "flux-finance", "reset"]);
    assert.equal(mockRemoveContainer.mock.callCount(), 0);
  });

  it("reset command handles no env file", async () => {
    mockRemoveContainer.mock.mockImplementation(async () => true);
    mockGetFluxDir.mock.mockImplementation(() => "/tmp/.flux-finance");
    mockPrompts.mock.mockImplementation(async () => ({ confirm: true }));
    mockExistsSync.mock.mockImplementation(() => false);

    await program.parseAsync(["node", "flux-finance", "reset"]);
    assert.equal(mockRemoveContainer.mock.callCount(), 1);
    assert.equal(mockUnlinkSync.mock.callCount(), 0);
  });

  it("refresh-token acquires token, updates config, and restarts", async () => {
    mockReadConfig.mock.mockImplementation(() => ({
      PORT: "5173",
      TELEGRAM_BOT_TOKEN: "123:ABC",
      CLAUDE_AUTH_TOKEN: "sk-ant-oat01-old",
    }));
    mockAcquireClaudeToken.mock.mockImplementation(async () => "sk-ant-oat01-new-token");
    mockWriteConfig.mock.mockImplementation(() => {});
    mockStartContainer.mock.mockImplementation(async () => {});
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");

    await program.parseAsync(["node", "flux-finance", "refresh-token"]);
    assert.equal(mockAcquireClaudeToken.mock.callCount(), 1);
    assert.equal(mockWriteConfig.mock.callCount(), 1);
    const writtenConfig = mockWriteConfig.mock.calls[0].arguments[0];
    assert.equal(writtenConfig.CLAUDE_AUTH_TOKEN, "sk-ant-oat01-new-token");
    assert.equal(mockStartContainer.mock.callCount(), 1);
  });

  it("refresh-token exits when no config exists", async () => {
    mockReadConfig.mock.mockImplementation(() => ({}));

    await assert.rejects(
      () => program.parseAsync(["node", "flux-finance", "refresh-token"]),
      { message: "EXIT_1" }
    );
    assert.equal(mockAcquireClaudeToken.mock.callCount(), 0);
  });

  it("refresh-token exits when no token acquired", async () => {
    mockReadConfig.mock.mockImplementation(() => ({
      PORT: "5173",
      CLAUDE_AUTH_TOKEN: "sk-ant-oat01-old",
    }));
    mockAcquireClaudeToken.mock.mockImplementation(async () => null);

    await assert.rejects(
      () => program.parseAsync(["node", "flux-finance", "refresh-token"]),
      { message: "EXIT_1" }
    );
    assert.equal(mockWriteConfig.mock.callCount(), 0);
  });

  it("refresh-token handles restart failure after config update", async () => {
    mockReadConfig.mock.mockImplementation(() => ({
      PORT: "5173",
      CLAUDE_AUTH_TOKEN: "sk-ant-oat01-old",
    }));
    mockAcquireClaudeToken.mock.mockImplementation(async () => "sk-ant-oat01-new");
    mockWriteConfig.mock.mockImplementation(() => {});
    mockStartContainer.mock.mockImplementation(async () => {
      throw new Error("restart failed");
    });
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");

    await assert.rejects(
      () => program.parseAsync(["node", "flux-finance", "refresh-token"]),
      { message: "EXIT_1" }
    );
    assert.equal(mockWriteConfig.mock.callCount(), 1);
  });
});
