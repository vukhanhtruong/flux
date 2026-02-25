import makeWASocket, {
  DisconnectReason,
  useMultiFileAuthState,
  WASocket,
} from '@whiskeysockets/baileys'
import pino from 'pino'

const logger = pino({ level: 'warn' })

// Track message IDs sent by the bot to avoid infinite loops
const sentMessageIds = new Set<string>()

export interface WhatsAppEvents {
  onMessage: (from: string, text: string) => void
  onQR: (qr: string) => void
  onConnected: () => void
  onDisconnected: () => void
}

export async function createWhatsAppClient(
  authDir: string,
  events: WhatsAppEvents,
): Promise<WASocket> {
  const { state, saveCreds } = await useMultiFileAuthState(authDir)

  const sock = makeWASocket({
    auth: state,
    logger,
  })

  sock.ev.on('creds.update', saveCreds)

  sock.ev.on('connection.update', (update) => {
    const { connection, lastDisconnect, qr } = update

    if (qr) {
      events.onQR(qr)
    }

    if (connection === 'close') {
      const reason = (lastDisconnect?.error as any)?.output?.statusCode
      if (reason !== DisconnectReason.loggedOut) {
        // Reconnect
        createWhatsAppClient(authDir, events)
      } else {
        events.onDisconnected()
      }
    } else if (connection === 'open') {
      events.onConnected()
    }
  })

  sock.ev.on('messages.upsert', async ({ messages }) => {
    for (const msg of messages) {
      // Skip bot's own replies (tracked by sent message IDs)
      const msgId = msg.key.id
      if (msgId && sentMessageIds.has(msgId)) {
        sentMessageIds.delete(msgId)
        continue
      }

      // Only process messages sent from the linked device (fromMe=true)
      // This ensures only the owner can interact with the bot
      if (!msg.key.fromMe) continue

      // Skip group chats and status broadcasts
      const jid = msg.key.remoteJid
      if (!jid || jid.endsWith('@g.us') || jid === 'status@broadcast') continue

      const text = msg.message?.conversation || msg.message?.extendedTextMessage?.text
      if (text) {
        events.onMessage(jid, text)
      }
    }
  })

  return sock
}

export function trackSentMessage(id: string) {
  sentMessageIds.add(id)
  // Clean up old IDs after 60s to prevent memory leak
  setTimeout(() => sentMessageIds.delete(id), 60000)
}
