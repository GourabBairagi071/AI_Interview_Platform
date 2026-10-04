/**
 * PHASE 16 — REAL-TIME WEBSOCKET SERVICE
 * Production-ready singleton managing authenticated WebSocket connections,
 * heartbeat keep-alive, exponential backoff reconnection, and event dispatch.
 */

export type RealtimeStatus = "connected" | "connecting" | "disconnected"

export interface RealtimeEnvelope<T = any> {
  event: string
  timestamp: string
  data: T
  id?: string
  version?: string
}

export type RealtimeEventHandler<T = any> = (data: T, envelope: RealtimeEnvelope<T>) => void

class WebSocketService {
  private ws: WebSocket | null = null
  private status: RealtimeStatus = "disconnected"
  private statusListeners = new Set<(status: RealtimeStatus) => void>()
  private eventHandlers = new Map<string, Set<RealtimeEventHandler>>()

  // Reconnection properties
  private reconnectAttempts = 0
  private maxReconnectAttempts = 10
  private baseReconnectDelay = 1500
  private maxReconnectDelay = 15000
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private intentionallyClosed = false

  // Heartbeat properties
  private pingInterval: ReturnType<typeof setInterval> | null = null
  private readonly pingFrequencyMs = 25000

  constructor() {
    // Automatically recheck on online/offline window events
    if (typeof window !== "undefined") {
      window.addEventListener("online", () => {
        if (this.status === "disconnected" && this.hasToken()) {
          this.reconnectAttempts = 0
          this.connect()
        }
      })
      window.addEventListener("offline", () => {
        this.setStatus("disconnected")
      })
    }
  }

  private hasToken(): boolean {
    return Boolean(
      localStorage.getItem("access_token") || localStorage.getItem("token")
    )
  }

  private getToken(): string | null {
    return (
      localStorage.getItem("access_token") ||
      localStorage.getItem("token") ||
      null
    )
  }

  private getWebSocketUrl(): string | null {
    const token = this.getToken()
    if (!token) return null

    // Determine backend host from current host or default backend port 8000
    const isHttps = window.location.protocol === "https:"
    const protocol = isHttps ? "wss:" : "ws:"
    const hostname = window.location.hostname || "127.0.0.1"
    const port = "8000" // Backend default port in development

    return `${protocol}//${hostname}:${port}/api/v1/ws?token=${encodeURIComponent(token)}`
  }

  public getStatus(): RealtimeStatus {
    return this.status
  }

  public isConnected(): boolean {
    return this.status === "connected" && this.ws?.readyState === WebSocket.OPEN
  }

  private setStatus(newStatus: RealtimeStatus) {
    if (this.status !== newStatus) {
      this.status = newStatus
      this.statusListeners.forEach((listener) => {
        try {
          listener(newStatus)
        } catch (err) {
          console.error("Error in realtime status listener:", err)
        }
      })
    }
  }

  public onStatusChange(callback: (status: RealtimeStatus) => void): () => void {
    this.statusListeners.add(callback)
    callback(this.status)
    return () => {
      this.statusListeners.delete(callback)
    }
  }

  public connect(): void {
    if (typeof window === "undefined") return

    // If already connected or open, no need to reconnect
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return
    }

    const wsUrl = this.getWebSocketUrl()
    if (!wsUrl) {
      this.setStatus("disconnected")
      return
    }

    this.intentionallyClosed = false
    this.setStatus("connecting")

    try {
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        this.reconnectAttempts = 0
        this.setStatus("connected")
        this.startHeartbeat()
      }

      this.ws.onmessage = (event: MessageEvent) => {
        this.handleMessage(event.data)
      }

      this.ws.onerror = (err) => {
        console.warn("WebSocket connection warning:", err)
      }

      this.ws.onclose = (event: CloseEvent) => {
        this.stopHeartbeat()
        this.setStatus("disconnected")

        // 1008 = Policy violation (e.g. invalid/expired token) -> Do not spam reconnect
        if (event.code === 1008 || event.code === 4401) {
          console.warn("WebSocket closed due to auth rejection. Token may be expired.")
          return
        }

        if (!this.intentionallyClosed) {
          this.scheduleReconnect()
        }
      }
    } catch (err) {
      console.warn("Failed to initiate WebSocket connection:", err)
      this.setStatus("disconnected")
      this.scheduleReconnect()
    }
  }

  public disconnect(): void {
    this.intentionallyClosed = true
    this.stopHeartbeat()
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.ws) {
      try {
        this.ws.close()
      } catch (err) {
        // Ignored
      }
      this.ws = null
    }
    this.setStatus("disconnected")
  }

  private scheduleReconnect(): void {
    if (this.intentionallyClosed || !this.hasToken()) return
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.info("Max WebSocket reconnect attempts reached. Falling back to REST.")
      return
    }

    const delay = Math.min(
      this.baseReconnectDelay * Math.pow(1.5, this.reconnectAttempts),
      this.maxReconnectDelay
    )
    this.reconnectAttempts++

    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.reconnectTimer = setTimeout(() => {
      this.connect()
    }, delay)
  }

  private startHeartbeat(): void {
    this.stopHeartbeat()
    this.pingInterval = setInterval(() => {
      if (this.isConnected()) {
        this.send({ type: "ping" })
      }
    }, this.pingFrequencyMs)
  }

  private stopHeartbeat(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }
  }

  public send(data: any): boolean {
    if (this.isConnected() && this.ws) {
      try {
        this.ws.send(typeof data === "string" ? data : JSON.stringify(data))
        return true
      } catch (err) {
        console.warn("Failed to send WebSocket payload:", err)
      }
    }
    return false
  }

  private handleMessage(raw: string): void {
    try {
      const envelope: RealtimeEnvelope = JSON.parse(raw)
      const eventName = envelope.event

      // Handle pong
      if (eventName === "pong" || envelope.data?.reply_to === "ping") {
        return
      }

      // Dispatch to subscribed handlers
      const handlers = this.eventHandlers.get(eventName)
      if (handlers) {
        handlers.forEach((handler) => {
          try {
            handler(envelope.data, envelope)
          } catch (err) {
            console.error(`Error in event handler for '${eventName}':`, err)
          }
        })
      }

      // Also dispatch to wildcard listeners if any
      const wildcardHandlers = this.eventHandlers.get("*")
      if (wildcardHandlers) {
        wildcardHandlers.forEach((handler) => {
          try {
            handler(envelope.data, envelope)
          } catch (err) {
            console.error("Error in wildcard event handler:", err)
          }
        })
      }
    } catch {
      // Non-JSON message or ping response
    }
  }

  public subscribe<T = any>(eventName: string, handler: RealtimeEventHandler<T>): () => void {
    if (!this.eventHandlers.has(eventName)) {
      this.eventHandlers.set(eventName, new Set())
    }
    this.eventHandlers.get(eventName)!.add(handler as RealtimeEventHandler)

    // Ensure connection is established if authenticated
    if (this.status === "disconnected" && this.hasToken()) {
      this.connect()
    }

    return () => {
      this.unsubscribe(eventName, handler)
    }
  }

  public unsubscribe<T = any>(eventName: string, handler: RealtimeEventHandler<T>): void {
    const handlers = this.eventHandlers.get(eventName)
    if (handlers) {
      handlers.delete(handler as RealtimeEventHandler)
      if (handlers.size === 0) {
        this.eventHandlers.delete(eventName)
      }
    }
  }
}

// Global Singleton Instance
export const realtimeService = new WebSocketService()
