import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { BOTFATHER_URL, RAW_DATA_BOT_URL, BOTFATHER_INSTRUCTIONS, RAW_DATA_BOT_INSTRUCTIONS, TOKEN_EXAMPLE, USER_ID_EXAMPLE } from "../src/qr.js";

describe("qr", () => {
  it("exports correct BotFather URL", () => {
    assert.equal(BOTFATHER_URL, "https://t.me/botfather");
  });

  it("exports correct Raw Data Bot URL", () => {
    assert.equal(RAW_DATA_BOT_URL, "https://t.me/raw_data_bot");
  });

  it("exports BotFather instructions as non-empty string", () => {
    assert.ok(BOTFATHER_INSTRUCTIONS.length > 0);
    assert.ok(BOTFATHER_INSTRUCTIONS.includes("/newbot"));
  });

  it("exports Raw Data Bot instructions as non-empty string", () => {
    assert.ok(RAW_DATA_BOT_INSTRUCTIONS.length > 0);
    assert.ok(RAW_DATA_BOT_INSTRUCTIONS.includes("/start"));
  });

  it("exports token example matching Telegram format", () => {
    assert.match(TOKEN_EXAMPLE, /^\d+:.+$/);
  });

  it("exports user ID example as numeric string", () => {
    assert.match(USER_ID_EXAMPLE, /^\d+$/);
  });
});
