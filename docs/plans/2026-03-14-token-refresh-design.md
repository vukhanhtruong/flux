# Token Refresh Without Manual Edit

## Problem

When a user's Claude OAuth token expires, the bot stops working silently. The only fix is to manually edit `~/.flux-finance/.env` and restart Docker — poor UX for a tool meant to "just work."

## Background

- `claude setup-token` opens a browser, user authorizes, and the CLI **prints a ~1-year token to stdout** (does NOT write to `~/.claude/.credentials.json`)
- `claude login` writes short-lived tokens (~10-15 min) to `.credentials.json` — unreliable in headless/Docker environments
- API keys (`sk-ant-api...`) never expire — already supported via `_setup_env()`
- The current wizard already calls `claude setup-token` but then reads from `.credentials.json` (broken — token is only printed to stdout)

## Solution — Three Parts

### Part 1: Fix wizard to capture `setup-token` stdout

**Current (broken):** Wizard runs `execSync("claude setup-token", { stdio: "inherit" })` then calls `readClaudeToken()` from `.credentials.json`. Since `setup-token` only prints to stdout, this fails silently and falls through to manual paste.

**New behavior:**
1. When Claude CLI is installed, auto-run `claude setup-token` (skip the "auto vs manual" choice prompt)
2. Capture stdout and parse the token via regex `/sk-ant-oat\S+/`
3. If capture fails (e.g., user cancels browser auth), fall back to manual paste
4. If Claude CLI is not installed, go straight to manual paste

**Files:**
- `packages/cli/src/claude-auth.js` — add `runSetupToken()` function
- `packages/cli/src/wizard.js` — simplify Step 2 auth flow

### Part 2: `refresh-token` CLI command

New command: `npx @flux-finance/cli refresh-token`

**Flow:**
1. Verify existing config exists (must have run setup first)
2. Check Claude CLI is installed — if not, fall back to manual prompt
3. Run `claude setup-token` → capture token from stdout
4. If capture fails, prompt user to paste token manually
5. Validate token format (`sk-ant-` prefix)
6. Update `~/.flux-finance/.env` via `writeConfig()`
7. Restart container via `startContainer()` with new config
8. Print success message

**Files:**
- `packages/cli/src/index.js` — add `refresh-token` command
- `packages/cli/src/claude-auth.js` — `runSetupToken()` (shared with wizard)

### Part 3: Auth error detection + admin notification

When the agent bot encounters an authentication error from the Claude SDK:

1. **Detect** auth errors in `handler.py` — match patterns: `"authentication_error"`, `"unauthorized"`, `"401"`, `"token expired"`, `"invalid.*token"`
2. **Notify admin** via Telegram — send to `TELEGRAM_ALLOW_FROM` chat ID: "Your Claude token has expired. Run `npx @flux-finance/cli refresh-token` to fix."
3. **Notify user** — reply with: "I'm temporarily unavailable. The admin has been notified."
4. **Throttle** — send admin notification at most once per hour to avoid spam

**Files:**
- `packages/agent-bot/src/flux_bot/orchestrator/handler.py` — add auth error detection, admin notification, throttle logic
- `packages/agent-bot/src/flux_bot/config.py` — add `admin_chat_id` from `TELEGRAM_ALLOW_FROM` env var

## Approach: Dropped

**Mounting `~/.claude/.credentials.json` into Docker** — rejected because `setup-token` doesn't write there, `login` tokens are short-lived and don't auto-refresh in headless mode, and it adds Docker config complexity for no benefit.

## Test Plan

### CLI Tests (`packages/cli/tests/`)

#### claude-auth.test.js — `runSetupToken()`

| # | Test case | Expected |
|---|-----------|----------|
| 1 | `claude setup-token` succeeds, stdout contains `sk-ant-oat...` token | Returns parsed token string |
| 2 | `claude setup-token` fails (throws/exit code non-zero) | Returns `null` |
| 3 | `claude setup-token` succeeds but stdout has no token pattern | Returns `null` |
| 4 | Token in stdout has leading/trailing whitespace | Returns trimmed token |

#### index.test.js — `refresh-token` command

| # | Test case | Expected |
|---|-----------|----------|
| 5 | Happy path: setup-token succeeds, config updated, container restarted | `writeConfig` called with new token, `startContainer` called, success message |
| 6 | No existing config (first-time user) | Exits with error: "Run setup first" |
| 7 | Claude CLI not installed, user pastes token manually | Token saved, container restarted |
| 8 | Claude CLI not installed, user provides no token | Exits with error |
| 9 | `setup-token` fails, falls back to manual paste, user provides token | Token saved, container restarted |
| 10 | `setup-token` fails, manual paste empty | Exits with error |
| 11 | Container restart fails after config update | Shows error (config already saved) |

#### wizard.test.js — updated wizard auth flow

| # | Test case | Expected |
|---|-----------|----------|
| 12 | Claude CLI installed: auto-runs `setup-token`, captures token | Token used, no method choice prompt |
| 13 | Claude CLI installed, `setup-token` fails: falls back to manual paste | User prompted for token |
| 14 | Claude CLI not installed: goes straight to manual paste | No `setup-token` attempt |

### Agent Bot Tests (`packages/agent-bot/tests/`)

#### test_handler.py — auth error detection + notification

| # | Test case | Expected |
|---|-----------|----------|
| 15 | Auth error (e.g., "authentication_error") sends admin notification and user-facing message | Admin gets "token expired" message, user gets "temporarily unavailable" |
| 16 | Auth error without admin channel configured | Logs warning, no crash, user still gets "unavailable" message |
| 17 | Second auth error within 1 hour: admin notification throttled | Admin NOT notified again, user still gets "unavailable" |
| 18 | Auth error after throttle window (1 hour) expires | Admin notified again |
| 19 | Non-auth errors (timeout, rate limit, etc.) | Do NOT trigger admin notification (existing behavior preserved) |
| 20 | Admin notification delivery fails (network error) | Logged, no crash, user still gets "unavailable" message |
| 21 | Auth error for user without platform_id | Message marked failed, no send attempted, no crash |
