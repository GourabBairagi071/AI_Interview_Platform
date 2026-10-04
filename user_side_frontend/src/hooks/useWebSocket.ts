import { useEffect, useState, useCallback, useRef } from "react"
import {
  realtimeService,
  type RealtimeStatus,
  type RealtimeEventHandler,
} from "../services/websocket"

/**
 * Hook providing access to global WebSocket status and manual connect/reconnect triggers.
 */
export function useWebSocket() {
  const [status, setStatus] = useState<RealtimeStatus>(realtimeService.getStatus())

  useEffect(() => {
    const unsubscribe = realtimeService.onStatusChange((newStatus) => {
      setStatus(newStatus)
    })
    return unsubscribe
  }, [])

  const connect = useCallback(() => {
    realtimeService.connect()
  }, [])

  const disconnect = useCallback(() => {
    realtimeService.disconnect()
  }, [])

  const send = useCallback((data: any) => {
    return realtimeService.send(data)
  }, [])

  return {
    status,
    isConnected: status === "connected",
    isConnecting: status === "connecting",
    connect,
    disconnect,
    send,
  }
}

/**
 * Convenient React hook to subscribe to a specific real-time event.
 * Automatically handles subscription lifecycle and unmount cleanup.
 */
export function useWebSocketEvent<T = any>(
  eventName: string,
  handler: RealtimeEventHandler<T>
) {
  const handlerRef = useRef(handler)
  handlerRef.current = handler

  useEffect(() => {
    const listener: RealtimeEventHandler<T> = (data, envelope) => {
      if (handlerRef.current) {
        handlerRef.current(data, envelope)
      }
    }

    const unsubscribe = realtimeService.subscribe<T>(eventName, listener)
    return () => {
      unsubscribe()
    }
  }, [eventName])
}
