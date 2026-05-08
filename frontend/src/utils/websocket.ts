import type { TaskUpdateEvent } from '../types'

type MessageHandler = (payload: TaskUpdateEvent) => void

class TaskWebSocketClient {
  private ws: WebSocket | null = null
  private handler: MessageHandler | null = null
  private reconnectTimer: number | null = null
  private manualClose = false

  private getUrl() {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
const host = import.meta.env.DEV ? '10.138.50.58:8000' : window.location.host
    return `${protocol}://${host}/ws/tasks`
  }

  connect(handler: MessageHandler) {
    this.handler = handler
    this.manualClose = false

    if (this.ws && this.ws.readyState <= WebSocket.OPEN) {
      return
    }

    this.ws = new WebSocket(this.getUrl())

    this.ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as TaskUpdateEvent
        this.handler?.(payload)
      } catch {
        // Ignore malformed messages to keep the dashboard alive.
      }
    }

    this.ws.onclose = () => {
      this.ws = null
      if (!this.manualClose) {
        this.scheduleReconnect()
      }
    }
  }

  disconnect() {
    this.manualClose = true
    if (this.reconnectTimer) {
      window.clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.ws?.close()
    this.ws = null
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) {
      return
    }

    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null
      if (this.handler) {
        this.connect(this.handler)
      }
    }, 3000)
  }
}

export const taskWebSocket = new TaskWebSocketClient()
