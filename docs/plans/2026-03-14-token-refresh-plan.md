# Token Refresh Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Let users refresh an expired Claude OAuth token with one CLI command, and proactively notify admins via Telegram when the token expires.

**Architecture:** Three independent parts: (1) add `runSetupToken()` to `claude-auth.js` that captures stdout from `claude setup-token`, (2) add `refresh-token` CLI command that calls `runSetupToken()` + updates config + restarts container, (3) add auth error detection in agent bot handler that notifies admin via Telegram with throttling. The wizard is also updated to use `runSetupToken()` instead of the broken `.credentials.json` read.

**Tech Stack:** Node.js (CLI — node:test, c8), Python (agent bot — pytest, pytest-asyncio)

---

### Task 1: Add `runSetupToken()` to claude-auth.js — tests

**Files:**
- Modify: `packages/cli/tests/claude-auth.test.js`
- Modify: `packages/cli/src/claude-auth.js`

**Context:** `claude setup-token` opens a browser, user authorizes, and the CLI prints a ~1-year OAuth token to stdout. It does NOT write to `.credentials.json`. We need a function that runs the command, captures stdout, and parses the token via regex.

The existing test file uses real filesystem with `tmpHome` and `process.env.HOME` override. `runSetupToken()` calls `execSync` which is already imported in `claude-auth.js`. The tests must mock `execSync` — but the current test file imports directly from `../src/claude-auth.js` without mocking. We need to add a new `describe` block that mocks `execSync`.

**Step 1: Write the failing tests**

Add a new `describe("runSetupToken", ...)` block at the end of `packages/cli/tests/claude-auth.test.js`. Since the existing tests import directly without mocking, and `runSetupToken` needs `execSync` mocked, create a separate test file `packages/cli/tests/claude-auth-setup-token.test.js` that uses `mock.module`:

```js
import { describe, it, mock } from "node:test";
import assert from "node:assert/strict";

const mockExecSync = mock.fn();

mock.module("node:child_process", {
  namedExports: { execSync: mockExecSync },
  defaultExport: { execSync: mockExecSync },
});

const { runSetupToken } = await import("../src/claude-auth.js");

describe("runSetupToken", () => {
  beforeEach(() => {
    mockExecSync.mock.resetCalls();
  });

  it("parses token from setup-token stdout", () => {
    mockExecSync.mock.mockImplementation(() =>
      "✓ Long-lived authentication token created successfully!\n\n" +
      "Your OAuth token (valid for 1 year):\n\n" +
      "sk-ant-oat01-4yF8Ije4abc123\n\n" +
      "Store this token securely."
    );
    const token = runSetupToken();
    assert.equal(token, "sk-ant-oat01-4yF8Ije4abc123");
    assert.equal(mockExecSync.mock.callCount(), 1);
  });

  it("returns null when command throws", () => {
    mockExecSync.mock.mockImplementation(() => {
      throw new Error("command failed");
    });
    const token = runSetupToken();
    assert.equal(token, null);
  });

  it("returns null when stdout has no token pattern", () => {
    mockExecSync.mock.mockImplementation(() => "No token here");
    const token = runSetupToken();
    assert.equal(token, null);
  });

  it("trims whitespace from captured token", () => {
    mockExecSync.mock.mockImplementation(() =>
      "Your OAuth token:\n\n  sk-ant-oat01-trimMe  \n\nDone."
    );
    const token = runSetupToken();
    assert.equal(token, "sk-ant-oat01-trimMe");
  });
});
```

Also add the new test file to the `test` script in `packages/cli/package.json` — append `tests/claude-auth-setup-token.test.js` to the test command.

**Step 2: Run tests to verify they fail**

Run: `cd packages/cli && npm test 2>&1 | tail -20`
Expected: FAIL — `runSetupToken` is not exported from `claude-auth.js`

**Step 3: Implement `runSetupToken()`**

Add to the end of `packages/cli/src/claude-auth.js`:

```js
export function runSetupToken() {
  try {
    const output = execSync("claude setup-token", {
      encoding: "utf-8",
      stdio: ["inherit", "pipe", "inherit"],
    });
    const match = output.match(/sk-ant-oat\S+/);
    return match ? match[0].trim() : null;
  } catch {
    return null;
  }
}
```

Key details:
- `stdio: ["inherit", "pipe", "inherit"]` — stdin inherited (for browser auth interaction), stdout captured, stderr inherited (for progress messages)
- Regex `/sk-ant-oat\S+/` matches the token line
- Returns `null` on any failure

**Step 4: Run tests to verify they pass**

Run: `cd packages/cli && npm test`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add -f packages/cli/src/claude-auth.js packages/cli/tests/claude-auth-setup-token.test.js packages/cli/package.json
git commit -m "feat(cli): add runSetupToken() to capture token from stdout"
```

---

### Task 2: Update wizard to use `runSetupToken()` — tests

**Files:**
- Modify: `packages/cli/src/wizard.js:85-138` (Step 2: Claude Authentication)
- Modify: `packages/cli/tests/wizard.test.js`

**Context:** The wizard currently offers a choice between "Auto-setup" and "Paste manually" when Claude CLI is installed, then reads from `.credentials.json` (broken). New behavior: when CLI is installed, auto-run `runSetupToken()` (no choice prompt). If it fails, fall back to manual paste.

The test file mocks `../src/claude-auth.js` at the top. We need to add `runSetupToken` to that mock and add a mock for `runSetupToken`.

**Step 1: Update mock setup and write new tests**

In `packages/cli/tests/wizard.test.js`, add `mockRunSetupToken` to the existing mock declarations (near line 14):

```js
const mockRunSetupToken = mock.fn();
```

Update the `mock.module("../src/claude-auth.js", ...)` block (around line 52-57) to include `runSetupToken`:

```js
mock.module("../src/claude-auth.js", {
  namedExports: {
    readClaudeToken: mockReadClaudeToken,
    isClaudeCliInstalled: mockIsClaudeCliInstalled,
    runSetupToken: mockRunSetupToken,
  },
});
```

Add `mockRunSetupToken.mock.resetCalls();` to the `beforeEach` block (around line 230).

Update the existing test `"handles auto-setup success path"` (line 471) to use `mockRunSetupToken` instead of `mockExecSync` + `mockReadClaudeToken`:

```js
it("auto-runs setup-token when CLI is installed and captures token", async () => {
    mockIsDockerRunning.mock.mockImplementation(async () => true);
    mockReadClaudeToken.mock.mockImplementation(() => null);
    mockIsClaudeCliInstalled.mock.mockImplementation(() => true);
    mockRunSetupToken.mock.mockImplementation(() => "sk-ant-oat01-new-token");
    mockPullImage.mock.mockImplementation(async () => {});
    mockStartContainer.mock.mockImplementation(async () => {});
    mockWriteConfig.mock.mockImplementation(() => {});
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");
    mockShowQR.mock.mockImplementation(async () => {});

    let callCount = 0;
    mockPrompts.mock.mockImplementation(async () => {
      callCount++;
      // No method choice prompt — goes straight to bot token
      if (callCount === 1) return { botToken: "123:ABC" };
      if (callCount === 2) return { userId: "456" };
      if (callCount === 3) return { port: "5173" };
      if (callCount === 4) return { setupNgrok: false };
      return {};
    });

    await runWizard();
    assert.equal(mockRunSetupToken.mock.callCount(), 1);
    // writeConfig should have been called with the captured token
    assert.equal(mockWriteConfig.mock.callCount(), 1);
});
```

Update the existing test `"handles auto-setup failure falling back to manual"` (line 504):

```js
it("falls back to manual paste when setup-token fails", async () => {
    mockIsDockerRunning.mock.mockImplementation(async () => true);
    mockReadClaudeToken.mock.mockImplementation(() => null);
    mockIsClaudeCliInstalled.mock.mockImplementation(() => true);
    mockRunSetupToken.mock.mockImplementation(() => null); // setup-token fails
    mockPullImage.mock.mockImplementation(async () => {});
    mockStartContainer.mock.mockImplementation(async () => {});
    mockWriteConfig.mock.mockImplementation(() => {});
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");
    mockShowQR.mock.mockImplementation(async () => {});

    let callCount = 0;
    mockPrompts.mock.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return { token: "sk-ant-oat01-manual" }; // manual paste
      if (callCount === 2) return { botToken: "123:ABC" };
      if (callCount === 3) return { userId: "456" };
      if (callCount === 4) return { port: "5173" };
      if (callCount === 5) return { setupNgrok: false };
      return {};
    });

    await runWizard();
    assert.equal(mockRunSetupToken.mock.callCount(), 1);
});
```

The existing test `"handles choosing not to use existing Claude token"` (line 386) should still work — it tests the path where `readClaudeToken` returns an existing token but user declines, then `isClaudeCliInstalled` returns false, so it goes to manual paste. No change needed.

The existing test `"handles auto-setup with Claude CLI installed"` (line 417) needs updating — it currently tests the "manual" method choice. Since we're removing the method choice, update it to test "CLI not installed → manual paste":

```js
it("goes to manual paste when Claude CLI is not installed", async () => {
    mockIsDockerRunning.mock.mockImplementation(async () => true);
    mockReadClaudeToken.mock.mockImplementation(() => null);
    mockIsClaudeCliInstalled.mock.mockImplementation(() => false);
    mockPullImage.mock.mockImplementation(async () => {});
    mockStartContainer.mock.mockImplementation(async () => {});
    mockWriteConfig.mock.mockImplementation(() => {});
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");
    mockShowQR.mock.mockImplementation(async () => {});

    let callCount = 0;
    mockPrompts.mock.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return { token: "sk-ant-oat01-pasted" };
      if (callCount === 2) return { botToken: "123:ABC" };
      if (callCount === 3) return { userId: "456" };
      if (callCount === 4) return { port: "5173" };
      if (callCount === 5) return { setupNgrok: false };
      return {};
    });

    await runWizard();
    assert.equal(mockRunSetupToken.mock.callCount(), 0); // never called
});
```

**Step 2: Run tests to verify they fail**

Run: `cd packages/cli && npm test 2>&1 | tail -30`
Expected: FAIL — wizard still has old flow with method choice prompt

**Step 3: Update wizard Step 2 (Claude Authentication)**

Replace `packages/cli/src/wizard.js` lines 85-138 (the entire Step 2 Claude Authentication block) with:

```js
  // Step 2: Claude Authentication
  console.log(chalk.bold("Step 2: Claude Authentication\n"));
  let claudeToken = readClaudeToken();

  if (claudeToken) {
    console.log(chalk.green("  Found existing Claude token.\n"));
    const { useExisting } = await prompts({
      type: "confirm",
      name: "useExisting",
      message: "Use the existing Claude token from Claude CLI?",
      initial: true,
    });
    if (!useExisting) claudeToken = null;
  }

  if (!claudeToken) {
    if (isClaudeCliInstalled()) {
      console.log(chalk.dim("  Running: claude setup-token\n"));
      claudeToken = runSetupToken();
      if (claudeToken) {
        console.log(chalk.green("  Token captured successfully.\n"));
      } else {
        console.log(
          chalk.yellow("  Auto-setup failed. Please paste token manually.\n")
        );
      }
    }

    if (!claudeToken) {
      const { token } = await prompts({
        type: "password",
        name: "token",
        message: "Paste your Claude auth token (sk-ant-...)",
      });
      claudeToken = token;
    }
  }

  if (!claudeToken) {
    console.log(chalk.red("\n  Claude token is required. Exiting.\n"));
    process.exit(1);
  }
```

Also add `runSetupToken` to the import at the top of `wizard.js` (line 7):

```js
import { readClaudeToken, isClaudeCliInstalled, runSetupToken } from "./claude-auth.js";
```

**Step 4: Run tests to verify they pass**

Run: `cd packages/cli && npm test`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add -f packages/cli/src/wizard.js packages/cli/tests/wizard.test.js
git commit -m "feat(cli): wizard auto-runs setup-token and captures stdout"
```

---

### Task 3: Add `refresh-token` CLI command — tests

**Files:**
- Modify: `packages/cli/src/index.js`
- Modify: `packages/cli/tests/index.test.js`

**Context:** The `refresh-token` command lets users get a new Claude token without manually editing `.env`. It reuses `runSetupToken()` from Task 1, updates config via `writeConfig()`, and restarts via `startContainer()` — all existing infrastructure. The pattern follows the existing `ngrok` command closely.

The test file `index.test.js` already mocks `config.js`, `docker.js`, `wizard.js`, and `prompts`. We need to add `runSetupToken` and `isClaudeCliInstalled` to the mock for `claude-auth.js`. Currently `claude-auth.js` is NOT mocked in `index.test.js` (only in `wizard.test.js`) — we need to add it.

**Step 1: Add mock setup and write tests**

In `packages/cli/tests/index.test.js`, add mock declarations near the top (after line 17):

```js
const mockRunSetupToken = mock.fn();
const mockIsClaudeCliInstalled = mock.fn();
```

Add mock module for `claude-auth.js` (after the `mock.module("../src/wizard.js", ...)` block around line 60):

```js
mock.module("../src/claude-auth.js", {
  namedExports: {
    readClaudeToken: () => null,
    isClaudeCliInstalled: mockIsClaudeCliInstalled,
    runSetupToken: mockRunSetupToken,
  },
});
```

Add resets in `beforeEach` (around line 121):

```js
    mockRunSetupToken.mock.resetCalls();
    mockIsClaudeCliInstalled.mock.resetCalls();
```

Add tests at the end of the `describe("cli commands", ...)` block (before the closing `});`):

```js
  it("refresh-token runs setup-token, updates config, and restarts", async () => {
    mockReadConfig.mock.mockImplementation(() => ({
      PORT: "5173",
      TELEGRAM_BOT_TOKEN: "123:ABC",
      CLAUDE_AUTH_TOKEN: "sk-ant-oat01-old",
    }));
    mockIsClaudeCliInstalled.mock.mockImplementation(() => true);
    mockRunSetupToken.mock.mockImplementation(() => "sk-ant-oat01-new-token");
    mockWriteConfig.mock.mockImplementation(() => {});
    mockStartContainer.mock.mockImplementation(async () => {});
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");

    await program.parseAsync(["node", "flux-finance", "refresh-token"]);
    assert.equal(mockRunSetupToken.mock.callCount(), 1);
    assert.equal(mockWriteConfig.mock.callCount(), 1);
    // Verify the new token was written
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
    assert.equal(mockRunSetupToken.mock.callCount(), 0);
  });

  it("refresh-token falls back to manual paste when CLI not installed", async () => {
    mockReadConfig.mock.mockImplementation(() => ({
      PORT: "5173",
      CLAUDE_AUTH_TOKEN: "sk-ant-oat01-old",
    }));
    mockIsClaudeCliInstalled.mock.mockImplementation(() => false);
    mockPrompts.mock.mockImplementation(async () => ({
      token: "sk-ant-oat01-manual",
    }));
    mockWriteConfig.mock.mockImplementation(() => {});
    mockStartContainer.mock.mockImplementation(async () => {});
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");

    await program.parseAsync(["node", "flux-finance", "refresh-token"]);
    assert.equal(mockRunSetupToken.mock.callCount(), 0);
    assert.equal(mockWriteConfig.mock.callCount(), 1);
    const writtenConfig = mockWriteConfig.mock.calls[0].arguments[0];
    assert.equal(writtenConfig.CLAUDE_AUTH_TOKEN, "sk-ant-oat01-manual");
  });

  it("refresh-token exits when CLI not installed and no token pasted", async () => {
    mockReadConfig.mock.mockImplementation(() => ({
      PORT: "5173",
      CLAUDE_AUTH_TOKEN: "sk-ant-oat01-old",
    }));
    mockIsClaudeCliInstalled.mock.mockImplementation(() => false);
    mockPrompts.mock.mockImplementation(async () => ({ token: undefined }));

    await assert.rejects(
      () => program.parseAsync(["node", "flux-finance", "refresh-token"]),
      { message: "EXIT_1" }
    );
    assert.equal(mockWriteConfig.mock.callCount(), 0);
  });

  it("refresh-token falls back to manual when setup-token fails", async () => {
    mockReadConfig.mock.mockImplementation(() => ({
      PORT: "5173",
      CLAUDE_AUTH_TOKEN: "sk-ant-oat01-old",
    }));
    mockIsClaudeCliInstalled.mock.mockImplementation(() => true);
    mockRunSetupToken.mock.mockImplementation(() => null); // fails
    mockPrompts.mock.mockImplementation(async () => ({
      token: "sk-ant-oat01-fallback",
    }));
    mockWriteConfig.mock.mockImplementation(() => {});
    mockStartContainer.mock.mockImplementation(async () => {});
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");

    await program.parseAsync(["node", "flux-finance", "refresh-token"]);
    assert.equal(mockWriteConfig.mock.callCount(), 1);
    const writtenConfig = mockWriteConfig.mock.calls[0].arguments[0];
    assert.equal(writtenConfig.CLAUDE_AUTH_TOKEN, "sk-ant-oat01-fallback");
  });

  it("refresh-token exits when setup-token fails and no manual token", async () => {
    mockReadConfig.mock.mockImplementation(() => ({
      PORT: "5173",
      CLAUDE_AUTH_TOKEN: "sk-ant-oat01-old",
    }));
    mockIsClaudeCliInstalled.mock.mockImplementation(() => true);
    mockRunSetupToken.mock.mockImplementation(() => null);
    mockPrompts.mock.mockImplementation(async () => ({ token: undefined }));

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
    mockIsClaudeCliInstalled.mock.mockImplementation(() => true);
    mockRunSetupToken.mock.mockImplementation(() => "sk-ant-oat01-new");
    mockWriteConfig.mock.mockImplementation(() => {});
    mockStartContainer.mock.mockImplementation(async () => {
      throw new Error("restart failed");
    });
    mockGetDataDir.mock.mockImplementation(() => "/tmp/data");

    await assert.rejects(
      () => program.parseAsync(["node", "flux-finance", "refresh-token"]),
      { message: "EXIT_1" }
    );
    // Config should still have been saved
    assert.equal(mockWriteConfig.mock.callCount(), 1);
  });
```

**Step 2: Run tests to verify they fail**

Run: `cd packages/cli && npm test 2>&1 | tail -20`
Expected: FAIL — `refresh-token` command doesn't exist yet

**Step 3: Implement `refresh-token` command**

Add to `packages/cli/src/index.js`, after the `config` command (before the `isDirectRun` check at the bottom). Also add `isClaudeCliInstalled` and `runSetupToken` to the import from `./claude-auth.js` — but since `index.js` doesn't currently import from `claude-auth.js`, add a new import:

At the top of `index.js`, add after line 6:

```js
import { isClaudeCliInstalled, runSetupToken } from "./claude-auth.js";
```

Then add the command:

```js
program
  .command("refresh-token")
  .description("Refresh Claude authentication token")
  .action(async () => {
    const config = readConfig();
    if (Object.keys(config).length === 0) {
      console.log(
        chalk.yellow("  No configuration found. Run setup first.\n")
      );
      process.exit(1);
    }

    let newToken = null;

    if (isClaudeCliInstalled()) {
      console.log(chalk.dim("\n  Running: claude setup-token\n"));
      newToken = runSetupToken();
      if (newToken) {
        console.log(chalk.green("  Token captured successfully.\n"));
      } else {
        console.log(
          chalk.yellow("  Auto-setup failed. Please paste token manually.\n")
        );
      }
    }

    if (!newToken) {
      const prompts = (await import("prompts")).default;
      const { token } = await prompts({
        type: "password",
        name: "token",
        message: "Paste your Claude auth token (sk-ant-...)",
      });
      newToken = token;
    }

    if (!newToken) {
      console.log(chalk.red("\n  No token provided. Aborting.\n"));
      process.exit(1);
    }

    config.CLAUDE_AUTH_TOKEN = newToken;
    writeConfig(config);
    console.log(chalk.green("  Token saved.\n"));

    const spinner = ora("Restarting FluxFinance...").start();
    try {
      await startContainer(config, getDataDir());
      spinner.succeed("FluxFinance restarted with new token!");
    } catch (err) {
      spinner.fail(`Failed to restart: ${err.message}`);
      console.log(
        chalk.yellow("  Token was saved. Try restarting manually with:"),
      );
      console.log(chalk.cyan("    npx @flux-finance/cli start\n"));
      process.exit(1);
    }
  });
```

**Step 4: Run tests to verify they pass**

Run: `cd packages/cli && npm test`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add -f packages/cli/src/index.js packages/cli/tests/index.test.js
git commit -m "feat(cli): add refresh-token command"
```

---

### Task 4: Add auth error detection + admin notification — tests

**Files:**
- Modify: `packages/agent-bot/src/flux_bot/orchestrator/handler.py`
- Modify: `packages/agent-bot/tests/test_orchestrator/test_handler.py`

**Context:** When the Claude SDK returns an auth error (401, "authentication_error", "unauthorized", "token expired"), the handler should: (1) send a Telegram notification to the admin, (2) reply to the user with "I'm temporarily unavailable", (3) throttle admin notifications to at most once per hour. The admin chat ID comes from the `TELEGRAM_ALLOW_FROM` env var (already parsed in `config.py`). We pass it as `admin_chat_id` to `make_handle_message`.

The existing `make_handle_message` signature is:
```python
def make_handle_message(*, runner, msg_repo, session_repo, profile_repo, channels):
```

We add an optional `admin_chat_id` parameter. This keeps all existing callers (especially tests) working without changes.

**Step 1: Write the failing tests**

Add to the end of `packages/agent-bot/tests/test_orchestrator/test_handler.py`:

```python
_AUTH_ERROR = "API Error: 401 authentication_error: Invalid token"
_AUTH_TOKEN_EXPIRED_MSG = (
    "⚠️ I'm temporarily unavailable due to an authentication issue. "
    "The admin has been notified."
)


async def test_auth_error_notifies_admin_and_user():
    """Auth errors send admin notification and user-facing message."""
    channel = AsyncMock()
    deps = _make_deps(channels={"telegram": channel})
    deps["runner"].run.return_value = ClaudeResult(
        text=None, session_id=None, error=_AUTH_ERROR
    )

    handler = make_handle_message(**deps, admin_chat_id="admin-42")
    await handler(_MSG)

    # Two sends: one to admin, one to user
    assert channel.send_message.call_count == 2
    admin_call = channel.send_message.call_args_list[0]
    assert admin_call.args[0] == "admin-42"
    assert "refresh-token" in admin_call.args[1]
    user_call = channel.send_message.call_args_list[1]
    assert user_call.args[0] == "42"
    assert "temporarily unavailable" in user_call.args[1].lower()
    deps["msg_repo"].mark_failed.assert_awaited_once()


async def test_auth_error_without_admin_chat_id_still_notifies_user():
    """Auth error without admin_chat_id configured still sends user message."""
    channel = AsyncMock()
    deps = _make_deps(channels={"telegram": channel})
    deps["runner"].run.return_value = ClaudeResult(
        text=None, session_id=None, error=_AUTH_ERROR
    )

    handler = make_handle_message(**deps)  # no admin_chat_id
    await handler(_MSG)

    assert channel.send_message.call_count == 1
    user_call = channel.send_message.call_args_list[0]
    assert user_call.args[0] == "42"
    assert "temporarily unavailable" in user_call.args[1].lower()


async def test_auth_error_admin_notification_throttled():
    """Second auth error within throttle window does not re-notify admin."""
    channel = AsyncMock()
    deps = _make_deps(channels={"telegram": channel})
    deps["runner"].run.return_value = ClaudeResult(
        text=None, session_id=None, error=_AUTH_ERROR
    )

    handler = make_handle_message(**deps, admin_chat_id="admin-42")
    await handler(_MSG)
    channel.send_message.reset_mock()

    # Second call — admin should NOT be notified again
    deps["msg_repo"].mark_failed.reset_mock()
    await handler(_MSG)

    assert channel.send_message.call_count == 1  # only user notification
    user_call = channel.send_message.call_args_list[0]
    assert user_call.args[0] == "42"


async def test_auth_error_admin_notification_after_throttle_expires():
    """Auth error after throttle window expires re-notifies admin."""
    from unittest.mock import patch
    import time

    channel = AsyncMock()
    deps = _make_deps(channels={"telegram": channel})
    deps["runner"].run.return_value = ClaudeResult(
        text=None, session_id=None, error=_AUTH_ERROR
    )

    handler = make_handle_message(**deps, admin_chat_id="admin-42")
    await handler(_MSG)
    channel.send_message.reset_mock()

    # Simulate time passing beyond throttle window (1 hour)
    with patch("flux_bot.orchestrator.handler.time") as mock_time:
        mock_time.monotonic.return_value = time.monotonic() + 3601
        await handler(_MSG)

    # Admin should be notified again
    assert channel.send_message.call_count == 2  # admin + user
    admin_call = channel.send_message.call_args_list[0]
    assert admin_call.args[0] == "admin-42"


async def test_non_auth_error_does_not_trigger_admin_notification():
    """Non-auth errors like timeout should not trigger admin notification."""
    channel = AsyncMock()
    deps = _make_deps(channels={"telegram": channel})
    deps["runner"].run.return_value = ClaudeResult(
        text=None, session_id=None, error="Timeout"
    )

    handler = make_handle_message(**deps, admin_chat_id="admin-42")
    await handler(_MSG)

    # No notification sent (timeout is not an auth error, and it's not a usage limit)
    channel.send_message.assert_not_awaited()


async def test_auth_error_admin_notification_delivery_fails_gracefully():
    """If admin notification delivery fails, user still gets notified."""
    channel = AsyncMock()
    # First call (admin notification) fails, second call (user notification) succeeds
    channel.send_message.side_effect = [
        Exception("Network error"),
        None,
    ]
    deps = _make_deps(channels={"telegram": channel})
    deps["runner"].run.return_value = ClaudeResult(
        text=None, session_id=None, error=_AUTH_ERROR
    )

    handler = make_handle_message(**deps, admin_chat_id="admin-42")
    await handler(_MSG)  # must not raise

    assert channel.send_message.call_count == 2
    deps["msg_repo"].mark_failed.assert_awaited_once()


async def test_auth_error_without_platform_id():
    """Auth error for message without platform_id marks failed, no crash."""
    deps = _make_deps()
    deps["runner"].run.return_value = ClaudeResult(
        text=None, session_id=None, error=_AUTH_ERROR
    )

    msg_no_platform = {**_MSG, "platform_id": ""}
    handler = make_handle_message(**deps, admin_chat_id="admin-42")
    await handler(msg_no_platform)  # must not raise

    deps["msg_repo"].mark_failed.assert_awaited_once()
```

**Step 2: Run tests to verify they fail**

Run: `cd packages/agent-bot && python -m pytest tests/test_orchestrator/test_handler.py -v 2>&1 | tail -20`
Expected: FAIL — `make_handle_message` doesn't accept `admin_chat_id`

**Step 3: Implement auth error detection + notification**

Modify `packages/agent-bot/src/flux_bot/orchestrator/handler.py`:

Add `import time` at the top (after `import asyncio`).

Add auth error patterns and messages after the existing `_SESSION_RETRY_PATTERNS` (around line 34):

```python
_AUTH_ERROR_PATTERNS = (
    "authentication_error",
    "unauthorized",
    "401",
    "token expired",
    "invalid token",
    "invalid_token",
)

_AUTH_ERROR_USER_MSG = (
    "⚠️ I'm temporarily unavailable due to an authentication issue. "
    "The admin has been notified."
)

_AUTH_ERROR_ADMIN_MSG = (
    "⚠️ Claude authentication token has expired.\n"
    "Run this command to refresh:\n\n"
    "npx @flux-finance/cli refresh-token"
)

_AUTH_NOTIFY_THROTTLE_SECS = 3600  # 1 hour
```

Add auth error detection function:

```python
def _is_auth_error(error: str) -> bool:
    """Check if the error is an authentication/token error."""
    err = error.lower()
    return any(pattern in err for pattern in _AUTH_ERROR_PATTERNS)
```

Update `make_handle_message` signature to accept optional `admin_chat_id`:

```python
def make_handle_message(*, runner, msg_repo, session_repo, profile_repo, channels, admin_chat_id=None):
```

Add throttle state inside `make_handle_message` (before the `handle_message` inner function):

```python
    last_admin_notify = [0.0]  # mutable container for closure
```

Add auth error handling inside `handle_message`, right after the `if result.error is not None:` block (line 109). Replace the entire block from line 109 to line 118 with:

```python
        if result.error is not None:
            await msg_repo.mark_failed(msg["id"], result.error)
            logger.error(f"Message {msg['id']} failed: {result.error}")

            if _is_auth_error(result.error):
                # Notify admin (throttled)
                if admin_chat_id and channel:
                    now = time.monotonic()
                    if now - last_admin_notify[0] >= _AUTH_NOTIFY_THROTTLE_SECS:
                        last_admin_notify[0] = now
                        try:
                            await channel.send_message(admin_chat_id, _AUTH_ERROR_ADMIN_MSG)
                        except Exception as e:
                            logger.error(f"Could not notify admin: {e}")
                # Notify user
                if channel and platform_id:
                    try:
                        await channel.send_message(platform_id, _AUTH_ERROR_USER_MSG)
                    except Exception as e:
                        logger.error(f"Could not notify user {user_id}: {e}")
            else:
                user_msg = _error_notification_for_user(result.error)
                if channel and platform_id and user_msg:
                    try:
                        await channel.send_message(platform_id, user_msg)
                    except Exception as e:
                        logger.error(f"Could not deliver usage-limit notification to {user_id}: {e}")
            return
```

**Step 4: Run tests to verify they pass**

Run: `cd packages/agent-bot && python -m pytest tests/test_orchestrator/test_handler.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add packages/agent-bot/src/flux_bot/orchestrator/handler.py packages/agent-bot/tests/test_orchestrator/test_handler.py
git commit -m "feat(agent-bot): detect auth errors and notify admin via Telegram"
```

---

### Task 5: Wire admin_chat_id in main.py + update management commands display

**Files:**
- Modify: `packages/agent-bot/src/flux_bot/main.py:73-78`
- Modify: `packages/cli/src/wizard.js:331-339` (management commands display)

**Step 1: Wire admin_chat_id**

In `packages/agent-bot/src/flux_bot/main.py`, update the `make_handle_message` call (around line 73) to pass `admin_chat_id`:

```python
    # Use the first allowed Telegram user as admin for notifications
    admin_chat_id = config.telegram.allow_from[0] if config.telegram.allow_from else None

    handle_message = make_handle_message(
        runner=runner,
        msg_repo=msg_repo,
        session_repo=session_repo,
        profile_repo=profile_repo,
        channels=channels,
        admin_chat_id=admin_chat_id,
    )
```

**Step 2: Add `refresh-token` to wizard's management commands display**

In `packages/cli/src/wizard.js`, find the management commands section (around line 332) and add `refresh-token` after the `config` line:

```js
  console.log(`    ${chalk.cyan("npx @flux-finance/cli refresh-token")} Refresh Claude token`);
```

**Step 3: Run full test suites**

Run CLI tests:
```bash
cd packages/cli && npm test
```

Run agent-bot tests:
```bash
cd packages/agent-bot && python -m pytest tests/ -v
```

Expected: All tests PASS in both packages

**Step 4: Commit**

```bash
git add packages/agent-bot/src/flux_bot/main.py packages/cli/src/wizard.js
git commit -m "feat: wire admin_chat_id and add refresh-token to help output"
```

---

### Task 6: Final verification + full test suite

**Step 1: Run all tests across both packages**

```bash
cd packages/cli && npm test
cd packages/agent-bot && python -m pytest tests/ -v --tb=short
```

**Step 2: Run ruff linter on agent-bot**

```bash
cd packages/agent-bot && ruff check src/ tests/
```

**Step 3: Verify coverage meets 90% threshold**

CLI:
```bash
cd packages/cli && npm test
```
(c8 coverage is built into the test command)

Agent-bot:
```bash
cd packages/agent-bot && python -m pytest tests/ --cov=flux_bot --cov-report=term-missing
```

**Step 4: Commit any fixes**

If ruff or coverage surface issues, fix them and commit:
```bash
git commit -m "fix: address lint/coverage issues from token refresh feature"
```
