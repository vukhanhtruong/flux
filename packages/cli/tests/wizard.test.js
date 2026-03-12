import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  validateBotToken,
  validateUserId,
  validatePort,
  generateSecretKey,
} from "../src/wizard.js";

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
