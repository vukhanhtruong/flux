import { describe, it, mock, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import realChildProcess from "node:child_process";

// Mock dependencies before importing wizard
const mockPrompts = mock.fn();
const mockIsDockerRunning = mock.fn();
const mockPullImage = mock.fn();
const mockStartContainer = mock.fn();
const mockReadConfig = mock.fn();
const mockWriteConfig = mock.fn();
const mockExecSync = mock.fn();
const mockGetDataDir = mock.fn();
const mockReadClaudeToken = mock.fn();
const mockIsClaudeCliInstalled = mock.fn();
const mockShowQR = mock.fn();

mock.module("prompts", {
  defaultExport: mockPrompts,
});

mock.module("../src/docker.js", {
  namedExports: {
    isDockerRunning: mockIsDockerRunning,
    pullImage: mockPullImage,
    startContainer: mockStartContainer,
    CONTAINER_NAME: "flux-finance",
    IMAGE_NAME: "vukhanhtruong/flux:latest",
    buildEnvVars: () => [],
    buildContainerConfig: () => ({}),
    createDockerClient: () => ({}),
    getContainer: async () => null,
    getContainerStatus: async () => ({ exists: false, running: false }),
    stopContainer: async () => false,
    removeContainer: async () => false,
    containerLogs: async () => null,
  },
});

mock.module("../src/config.js", {
  namedExports: {
    readConfig: mockReadConfig,
    writeConfig: mockWriteConfig,
    getDataDir: mockGetDataDir,
    getConfigPath: () => "/tmp/.flux-finance/.env",
    getFluxDir: () => "/tmp/.flux-finance",
    CONFIG_DIR_NAME: ".flux-finance",
    ENV_FILE_NAME: ".env",
  },
});

mock.module("../src/claude-auth.js", {
  namedExports: {
    readClaudeToken: mockReadClaudeToken,
    isClaudeCliInstalled: mockIsClaudeCliInstalled,
  },
});

mock.module("node:child_process", {
  namedExports: {
    execSync: mockExecSync,
  },
  defaultExport: {
    ...realChildProcess,
    execSync: mockExecSync,
  },
});

mock.module("../src/qr.js", {
  namedExports: {
    showQR: mockShowQR,
    BOTFATHER_URL: "https://t.me/botfather",
    RAW_DATA_BOT_URL: "https://t.me/raw_data_bot",
    BOTFATHER_INSTRUCTIONS: "instructions",
    RAW_DATA_BOT_INSTRUCTIONS: "instructions",
    TOKEN_EXAMPLE: "7123456789:AAHBx5K-example",
    USER_ID_EXAMPLE: "123456789",
  },
});

const { validateBotToken, validateUserId, validatePort, generateSecretKey, fetchBotUsername, verifyUserId, runWizard } = await import("../src/wizard.js");

describe("wizard validation", () => {
  it("validates correct Telegram bot token", () => {
    assert.equal(validateBotToken("7123456789:AAHBx5K-test"), true);
  });

  it("rejects empty bot token", () => {
    assert.notEqual(validateBotToken(""), true);
  });

  it("rejects bot token without colon", () => {
    assert.notEqual(validateBotToken("noColonHere"), true);
  });

  it("rejects bot token where part before colon is not numeric", () => {
    assert.notEqual(validateBotToken("abc:defghi"), true);
  });

  it("validates correct Telegram user ID (numeric)", () => {
    assert.equal(validateUserId("123456789"), true);
  });

  it("rejects non-numeric user ID", () => {
    assert.notEqual(validateUserId("abc"), true);
  });

  it("rejects empty user ID", () => {
    assert.notEqual(validateUserId(""), true);
  });

  it("validates port in valid range", () => {
    assert.equal(validatePort("5173"), true);
    assert.equal(validatePort("8080"), true);
    assert.equal(validatePort("3000"), true);
  });

  it("rejects invalid port", () => {
    assert.notEqual(validatePort("0"), true);
    assert.notEqual(validatePort("70000"), true);
    assert.notEqual(validatePort("abc"), true);
  });

  it("generates a UUID-format secret key", () => {
    const key = generateSecretKey();
    assert.match(key, /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/);
  });

  it("generates unique keys", () => {
    const key1 = generateSecretKey();
    const key2 = generateSecretKey();
    assert.notEqual(key1, key2);
  });
});

describe("fetchBotUsername", () => {
  it("returns username when API call succeeds", async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () => ({
      json: async () => ({ ok: true, result: { username: "my_test_bot" } }),
    });
    const username = await fetchBotUsername("123:ABC");
    assert.equal(username, "my_test_bot");
    globalThis.fetch = originalFetch;
  });

  it("returns null when API call fails", async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () => ({
      json: async () => ({ ok: false }),
    });
    const username = await fetchBotUsername("invalid");
    assert.equal(username, null);
    globalThis.fetch = originalFetch;
  });

  it("returns null when fetch throws", async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () => { throw new Error("network error"); };
    const username = await fetchBotUsername("123:ABC");
    assert.equal(username, null);
    globalThis.fetch = originalFetch;
  });
});

describe("verifyUserId", () => {
  it("returns chat info when API call succeeds", async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () => ({
      json: async () => ({ ok: true, result: { id: 456, first_name: "John" } }),
    });
    const result = await verifyUserId("123:ABC", "456");
    assert.deepEqual(result, { id: 456, first_name: "John" });
    globalThis.fetch = originalFetch;
  });

  it("returns null when API call fails", async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () => ({
      json: async () => ({ ok: false }),
    });
    const result = await verifyUserId("123:ABC", "999");
    assert.equal(result, null);
    globalThis.fetch = originalFetch;
  });

  it("returns null when fetch throws", async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () => { throw new Error("network error"); };
    const result = await verifyUserId("123:ABC", "456");
    assert.equal(result, null);
    globalThis.fetch = originalFetch;
  });
});

describe("runWizard", () => {
  let originalLog;
  let originalExit;
  let originalFetch;
  let exitCode;

  beforeEach(() => {
    originalLog = console.log;
    originalExit = process.exit;
    originalFetch = globalThis.fetch;
    exitCode = null;

    console.log = () => {};
    console.error = () => {};
    process.exit = (code) => { exitCode = code; throw new Error(`EXIT_${code}`); };
    globalThis.fetch = async (url) => ({
      json: async () => {
        if (url.includes("/getChat")) {
          return { ok: true, result: { id: 456, first_name: "Test User" } };
        }
        return { ok: true, result: { username: "test_bot" } };
      },
    });

    // Reset all mocks
    mockPrompts.mock.resetCalls();
    mockIsDockerRunning.mock.resetCalls();
    mockPullImage.mock.resetCalls();
    mockStartContainer.mock.resetCalls();
    mockWriteConfig.mock.resetCalls();
    mockGetDataDir.mock.resetCalls();
    mockReadClaudeToken.mock.resetCalls();
    mockIsClaudeCliInstalled.mock.resetCalls();
    mockShowQR.mock.resetCalls();
    mockExecSync.mock.resetCalls();
  });

  afterEach(() => {
    console.log = originalLog;
    process.exit = originalExit;
    globalThis.fetch = originalFetch;
  });

  it("exits when Docker is not running", async () => {
    mockIsDockerRunning.mock.mockImplementation(async () => false);

    await assert.rejects(() => runWizard(), { message: "EXIT_1" });
    assert.equal(exitCode, 1);
  });

  it("exits when no Claude token is provided", async () => {
    mockIsDockerRunning.mock.mockImplementation(async () => true);
    mockReadClaudeToken.mock.mockImplementation(() => null);
    mockIsClaudeCliInstalled.mock.mockImplementation(() => false);
    // prompts returns empty token
    mockPrompts.mock.mockImplementation(async () => ({ token: undefined }));

    await assert.rejects(() => runWizard(), { message: "EXIT_1" });
  });

  it("exits when no bot token is provided", async () => {
    mockIsDockerRunning.mock.mockImplementation(async () => true);
    mockReadClaudeToken.mock.mockImplementation(() => "sk-ant-test-token");

    let callCount = 0;
    mockPrompts.mock.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return { useExisting: true }; // use existing claude token
      if (callCount === 2) return { botToken: undefined }; // no bot token
      return {};
    });
    mockShowQR.mock.mockImplementation(async () => {});

    await assert.rejects(() => runWizard(), { message: "EXIT_1" });
  });

  it("exits when no user ID is provided", async () => {
    mockIsDockerRunning.mock.mockImplementation(async () => true);
    mockReadClaudeToken.mock.mockImplementation(() => "sk-ant-test-token");

    let callCount = 0;
    mockPrompts.mock.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return { useExisting: true };
      if (callCount === 2) return { botToken: "123:ABC" };
      if (callCount === 3) return { userId: undefined };
      return {};
    });
    mockShowQR.mock.mockImplementation(async () => {});

    await assert.rejects(() => runWizard(), { message: "EXIT_1" });
  });

  it("completes full wizard flow successfully", async () => {
    mockIsDockerRunning.mock.mockImplementation(async () => true);
    mockReadClaudeToken.mock.mockImplementation(() => "sk-ant-test-token");
    mockPullImage.mock.mockImplementation(async () => {});
    mockStartContainer.mock.mockImplementation(async () => {});
    mockWriteConfig.mock.mockImplementation(() => {});
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");
    mockShowQR.mock.mockImplementation(async () => {});

    let callCount = 0;
    mockPrompts.mock.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return { useExisting: true };    // use existing claude token
      if (callCount === 2) return { botToken: "123:ABC" };   // bot token
      if (callCount === 3) return { userId: "456" };         // user ID
      if (callCount === 4) return { port: "5173" };          // port
      if (callCount === 5) return { setupNgrok: false };     // skip ngrok
      return {};
    });

    await runWizard();
    assert.equal(mockWriteConfig.mock.callCount(), 1);
    assert.equal(mockPullImage.mock.callCount(), 1);
    assert.equal(mockStartContainer.mock.callCount(), 1);
  });

  it("completes wizard with ngrok setup", async () => {
    mockIsDockerRunning.mock.mockImplementation(async () => true);
    mockReadClaudeToken.mock.mockImplementation(() => "sk-ant-test-token");
    mockPullImage.mock.mockImplementation(async () => {});
    mockStartContainer.mock.mockImplementation(async () => {});
    mockWriteConfig.mock.mockImplementation(() => {});
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");
    mockShowQR.mock.mockImplementation(async () => {});

    let callCount = 0;
    mockPrompts.mock.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return { useExisting: true };
      if (callCount === 2) return { botToken: "123:ABC" };
      if (callCount === 3) return { userId: "456" };
      if (callCount === 4) return { port: "5173" };
      if (callCount === 5) return { setupNgrok: true };
      if (callCount === 6) return { ngrokToken: "ngrok-token-123" };
      return {};
    });

    await runWizard();
    // writeConfig called twice: once for initial, once for ngrok
    assert.equal(mockWriteConfig.mock.callCount(), 2);
    // startContainer called twice: once initial, once restart with ngrok
    assert.equal(mockStartContainer.mock.callCount(), 2);
  });

  it("handles pull image failure", async () => {
    mockIsDockerRunning.mock.mockImplementation(async () => true);
    mockReadClaudeToken.mock.mockImplementation(() => "sk-ant-test-token");
    mockPullImage.mock.mockImplementation(async () => { throw new Error("pull failed"); });
    mockWriteConfig.mock.mockImplementation(() => {});
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");
    mockShowQR.mock.mockImplementation(async () => {});

    let callCount = 0;
    mockPrompts.mock.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return { useExisting: true };
      if (callCount === 2) return { botToken: "123:ABC" };
      if (callCount === 3) return { userId: "456" };
      if (callCount === 4) return { port: "5173" };
      return {};
    });

    await assert.rejects(() => runWizard(), { message: "EXIT_1" });
  });

  it("handles start container failure", async () => {
    mockIsDockerRunning.mock.mockImplementation(async () => true);
    mockReadClaudeToken.mock.mockImplementation(() => "sk-ant-test-token");
    mockPullImage.mock.mockImplementation(async () => {});
    mockStartContainer.mock.mockImplementation(async () => { throw new Error("start failed"); });
    mockWriteConfig.mock.mockImplementation(() => {});
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");
    mockShowQR.mock.mockImplementation(async () => {});

    let callCount = 0;
    mockPrompts.mock.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return { useExisting: true };
      if (callCount === 2) return { botToken: "123:ABC" };
      if (callCount === 3) return { userId: "456" };
      if (callCount === 4) return { port: "5173" };
      return {};
    });

    await assert.rejects(() => runWizard(), { message: "EXIT_1" });
  });

  it("handles choosing not to use existing Claude token", async () => {
    mockIsDockerRunning.mock.mockImplementation(async () => true);
    // First call returns a token, but user says no
    let readTokenCalls = 0;
    mockReadClaudeToken.mock.mockImplementation(() => {
      readTokenCalls++;
      if (readTokenCalls === 1) return "existing-token";
      return null;
    });
    mockIsClaudeCliInstalled.mock.mockImplementation(() => false);
    mockPullImage.mock.mockImplementation(async () => {});
    mockStartContainer.mock.mockImplementation(async () => {});
    mockWriteConfig.mock.mockImplementation(() => {});
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");
    mockShowQR.mock.mockImplementation(async () => {});

    let callCount = 0;
    mockPrompts.mock.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return { useExisting: false };    // decline existing token
      if (callCount === 2) return { token: "manual-token" }; // manual token entry
      if (callCount === 3) return { botToken: "123:ABC" };
      if (callCount === 4) return { userId: "456" };
      if (callCount === 5) return { port: "5173" };
      if (callCount === 6) return { setupNgrok: false };
      return {};
    });

    await runWizard();
  });

  it("handles auto-setup with Claude CLI installed", async () => {
    mockIsDockerRunning.mock.mockImplementation(async () => true);
    mockReadClaudeToken.mock.mockImplementation(() => null);
    mockIsClaudeCliInstalled.mock.mockImplementation(() => true);
    mockPullImage.mock.mockImplementation(async () => {});
    mockStartContainer.mock.mockImplementation(async () => {});
    mockWriteConfig.mock.mockImplementation(() => {});
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");
    mockShowQR.mock.mockImplementation(async () => {});

    let callCount = 0;
    mockPrompts.mock.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return { method: "manual" };      // choose manual method
      if (callCount === 2) return { token: "pasted-token" }; // paste token
      if (callCount === 3) return { botToken: "123:ABC" };
      if (callCount === 4) return { userId: "456" };
      if (callCount === 5) return { port: "5173" };
      if (callCount === 6) return { setupNgrok: false };
      return {};
    });

    await runWizard();
  });

  it("handles ngrok restart failure gracefully", async () => {
    mockIsDockerRunning.mock.mockImplementation(async () => true);
    mockReadClaudeToken.mock.mockImplementation(() => "sk-ant-test-token");
    mockPullImage.mock.mockImplementation(async () => {});
    let startCount = 0;
    mockStartContainer.mock.mockImplementation(async () => {
      startCount++;
      if (startCount === 2) throw new Error("restart failed");
    });
    mockWriteConfig.mock.mockImplementation(() => {});
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");
    mockShowQR.mock.mockImplementation(async () => {});

    let callCount = 0;
    mockPrompts.mock.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return { useExisting: true };
      if (callCount === 2) return { botToken: "123:ABC" };
      if (callCount === 3) return { userId: "456" };
      if (callCount === 4) return { port: "5173" };
      if (callCount === 5) return { setupNgrok: true };
      if (callCount === 6) return { ngrokToken: "ngrok-123" };
      return {};
    });

    // Should NOT throw — ngrok restart failure is non-fatal
    await runWizard();
  });

  it("handles auto-setup success path", async () => {
    mockIsDockerRunning.mock.mockImplementation(async () => true);
    mockReadClaudeToken.mock.mockImplementation(() => null);
    mockIsClaudeCliInstalled.mock.mockImplementation(() => true);
    mockExecSync.mock.mockImplementation(() => {});
    mockPullImage.mock.mockImplementation(async () => {});
    mockStartContainer.mock.mockImplementation(async () => {});
    mockWriteConfig.mock.mockImplementation(() => {});
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");
    mockShowQR.mock.mockImplementation(async () => {});

    let callCount = 0;
    let readTokenCalls = 0;
    mockReadClaudeToken.mock.mockImplementation(() => {
      readTokenCalls++;
      if (readTokenCalls >= 2) return "auto-setup-token";
      return null;
    });

    mockPrompts.mock.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return { method: "auto" };        // choose auto method
      if (callCount === 2) return { botToken: "123:ABC" };
      if (callCount === 3) return { userId: "456" };
      if (callCount === 4) return { port: "5173" };
      if (callCount === 5) return { setupNgrok: false };
      return {};
    });

    await runWizard();
    assert.equal(mockExecSync.mock.callCount(), 1);
  });

  it("handles auto-setup failure falling back to manual", async () => {
    mockIsDockerRunning.mock.mockImplementation(async () => true);
    mockIsClaudeCliInstalled.mock.mockImplementation(() => true);
    mockExecSync.mock.mockImplementation(() => { throw new Error("claude not found"); });
    mockPullImage.mock.mockImplementation(async () => {});
    mockStartContainer.mock.mockImplementation(async () => {});
    mockWriteConfig.mock.mockImplementation(() => {});
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");
    mockShowQR.mock.mockImplementation(async () => {});

    let readTokenCalls = 0;
    mockReadClaudeToken.mock.mockImplementation(() => {
      readTokenCalls++;
      return null; // always null — auto-setup failed
    });

    let callCount = 0;
    mockPrompts.mock.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return { method: "auto" };        // choose auto
      if (callCount === 2) return { token: "manual-token" }; // fallback to manual
      if (callCount === 3) return { botToken: "123:ABC" };
      if (callCount === 4) return { userId: "456" };
      if (callCount === 5) return { port: "5173" };
      if (callCount === 6) return { setupNgrok: false };
      return {};
    });

    await runWizard();
    assert.equal(mockExecSync.mock.callCount(), 1);
  });

  it("exits when bot token verification fails and user declines to continue", async () => {
    mockIsDockerRunning.mock.mockImplementation(async () => true);
    mockReadClaudeToken.mock.mockImplementation(() => "sk-ant-test-token");
    mockShowQR.mock.mockImplementation(async () => {});

    // Make fetch return failure so token verification fails
    globalThis.fetch = async () => ({
      json: async () => ({ ok: false }),
    });

    let callCount = 0;
    mockPrompts.mock.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return { useExisting: true };
      if (callCount === 2) return { botToken: "123:INVALID" };
      if (callCount === 3) return { continueAnyway: false }; // decline to continue
      return {};
    });

    await assert.rejects(() => runWizard(), { message: "EXIT_1" });
  });

  it("continues when bot token verification fails but user confirms", async () => {
    mockIsDockerRunning.mock.mockImplementation(async () => true);
    mockReadClaudeToken.mock.mockImplementation(() => "sk-ant-test-token");
    mockPullImage.mock.mockImplementation(async () => {});
    mockStartContainer.mock.mockImplementation(async () => {});
    mockWriteConfig.mock.mockImplementation(() => {});
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");
    mockShowQR.mock.mockImplementation(async () => {});

    // Make fetch return failure for bot token, but success for user ID
    globalThis.fetch = async (url) => ({
      json: async () => {
        if (url.includes("/getChat")) {
          return { ok: true, result: { id: 456, first_name: "Test" } };
        }
        return { ok: false };
      },
    });

    let callCount = 0;
    mockPrompts.mock.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return { useExisting: true };
      if (callCount === 2) return { botToken: "123:UNVERIFIED" };
      if (callCount === 3) return { continueAnyway: true };  // continue anyway
      if (callCount === 4) return { userId: "456" };
      if (callCount === 5) return { port: "5173" };
      if (callCount === 6) return { setupNgrok: false };
      return {};
    });

    await runWizard();
    assert.equal(mockWriteConfig.mock.callCount(), 1);
  });

  it("shows warning when user ID cannot be verified", async () => {
    mockIsDockerRunning.mock.mockImplementation(async () => true);
    mockReadClaudeToken.mock.mockImplementation(() => "sk-ant-test-token");
    mockPullImage.mock.mockImplementation(async () => {});
    mockStartContainer.mock.mockImplementation(async () => {});
    mockWriteConfig.mock.mockImplementation(() => {});
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");
    mockShowQR.mock.mockImplementation(async () => {});

    // getMe succeeds, getChat fails
    globalThis.fetch = async (url) => ({
      json: async () => {
        if (url.includes("/getChat")) {
          return { ok: false };
        }
        return { ok: true, result: { username: "test_bot" } };
      },
    });

    let callCount = 0;
    mockPrompts.mock.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return { useExisting: true };
      if (callCount === 2) return { botToken: "123:ABC" };
      if (callCount === 3) return { userId: "999" };
      if (callCount === 4) return { port: "5173" };
      if (callCount === 5) return { setupNgrok: false };
      return {};
    });

    await runWizard();
    assert.equal(mockWriteConfig.mock.callCount(), 1);
  });

  it("handles ngrok setup with empty token", async () => {
    mockIsDockerRunning.mock.mockImplementation(async () => true);
    mockReadClaudeToken.mock.mockImplementation(() => "sk-ant-test-token");
    mockPullImage.mock.mockImplementation(async () => {});
    mockStartContainer.mock.mockImplementation(async () => {});
    mockWriteConfig.mock.mockImplementation(() => {});
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");
    mockShowQR.mock.mockImplementation(async () => {});

    let callCount = 0;
    mockPrompts.mock.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return { useExisting: true };
      if (callCount === 2) return { botToken: "123:ABC" };
      if (callCount === 3) return { userId: "456" };
      if (callCount === 4) return { port: "5173" };
      if (callCount === 5) return { setupNgrok: true };
      if (callCount === 6) return { ngrokToken: undefined }; // empty ngrok token
      return {};
    });

    await runWizard();
    // writeConfig called only once (no ngrok restart)
    assert.equal(mockWriteConfig.mock.callCount(), 1);
  });
});
