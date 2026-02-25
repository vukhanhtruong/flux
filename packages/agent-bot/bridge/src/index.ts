import WebSocket from 'ws'
import qrcode from 'qrcode-terminal'
import { createWhatsAppClient, trackSentMessage } from './whatsapp.js'

const AGENT_WS_URL = process.env.AGENT_WS_URL || 'ws://localhost:9000'
const AUTH_DIR = process.env.AUTH_DIR || './auth'

let ws: WebSocket | null = null
let waSock: any = null

function connectToAgent(): WebSocket {
  console.log(`Connecting to agent at ${AGENT_WS_URL}...`)
  const socket = new WebSocket(AGENT_WS_URL)

  socket.on('open', () => {
    console.log('Connected to flux agent')
    socket.send(JSON.stringify({ type: 'status', status: 'bridge_connected' }))
  })

  socket.on('message', async (data: WebSocket.Data) => {
    const msg = JSON.parse(data.toString())
    if (msg.type === 'message' && waSock) {
      const sent = await waSock.sendMessage(msg.to, { text: msg.text })
      if (sent?.key?.id) {
        trackSentMessage(sent.key.id)
      }
      console.log(`Sent to WhatsApp ${msg.to}: ${msg.text.substring(0, 50)}...`)
    }
  })

  socket.on('close', () => {
    console.log('Disconnected from agent, reconnecting in 5s...')
    setTimeout(() => { ws = connectToAgent() }, 5000)
  })

  socket.on('error', (err: Error) => {
    console.error('WebSocket error:', err.message)
  })

  return socket
}

async function main() {
  // Connect to flux agent bot
  ws = connectToAgent()

  // Connect to WhatsApp
  waSock = await createWhatsAppClient(AUTH_DIR, {
    onMessage: (from: string, text: string) => {
      console.log(`WhatsApp message from ${from}: ${text.substring(0, 50)}`)
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'message', from, text }))
      }
    },
    onQR: (qr: string) => {
      console.log('\nScan QR code with WhatsApp → Settings → Linked Devices\n')
      qrcode.generate(qr, { small: true })
    },
    onConnected: () => {
      console.log('WhatsApp connected!')
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'status', status: 'whatsapp_connected' }))
      }
    },
    onDisconnected: () => {
      console.log('WhatsApp disconnected')
    },
  })
}

main().catch(console.error)
