import qrcode from "qrcode-terminal";

export const BOTFATHER_URL = "https://t.me/botfather";
export const RAW_DATA_BOT_URL = "https://t.me/raw_data_bot";
export const TOKEN_EXAMPLE = "7123456789:AAHBx5K-example-token-here";
export const USER_ID_EXAMPLE = "123456789";

export const BOTFATHER_INSTRUCTIONS = `How to create your Telegram bot:

  Option 1: Scan the QR code above to open @BotFather

  Option 2: Open Telegram manually
    1. Open Telegram
    2. Search "BotFather" (look for the blue checkmark)
    3. Send /newbot
    4. Choose a name (e.g., "My Finance Bot")
    5. Choose a username ending in _bot (e.g., "myfinance_bot")
    6. Copy the token BotFather gives you

  The token looks like: ${TOKEN_EXAMPLE}

  Tip: If you already have a bot but the token doesn't work,
  send /revoke to @BotFather, select the bot, and get a fresh token.`;

export const RAW_DATA_BOT_INSTRUCTIONS = `How to get your Telegram User ID:

  Option 1: Scan the QR code above to open @raw_data_bot

  Option 2: Open Telegram manually
    1. Open Telegram
    2. Search "Raw Data Bot" (@raw_data_bot)
    3. Send /start
    4. The bot replies with your user info
    5. Copy the number next to "id"

  Your ID looks like: ${USER_ID_EXAMPLE} (just numbers)`;

export function showQR(url) {
  return new Promise((resolve) => {
    qrcode.generate(url, { small: true }, (code) => {
      console.log(code);
      resolve();
    });
  });
}
