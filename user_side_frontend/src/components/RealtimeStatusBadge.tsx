import React from "react"
import { useWebSocket } from "../hooks/useWebSocket"
import "./RealtimeStatusBadge.css"

interface RealtimeStatusBadgeProps {
  className?: string
  showText?: boolean
}

export const RealtimeStatusBadge: React.FC<RealtimeStatusBadgeProps> = ({
  className = "",
  showText = true,
}) => {
  const { status } = useWebSocket()

  const getStatusConfig = () => {
    switch (status) {
      case "connected":
        return {
          label: "Live",
          dotClass: "dot-connected",
          tooltip: "Connected to real-time events",
        }
      case "connecting":
        return {
          label: "Connecting...",
          dotClass: "dot-connecting",
          tooltip: "Establishing real-time connection...",
        }
      case "disconnected":
      default:
        return {
          label: "Offline (REST)",
          dotClass: "dot-disconnected",
          tooltip: "Real-time offline. Using background REST sync.",
        }
    }
  }

  const { label, dotClass, tooltip } = getStatusConfig()

  return (
    <div
      className={`realtime-status-badge ${status} ${className}`}
      title={tooltip}
    >
      <span className={`realtime-dot ${dotClass}`} />
      {showText && <span className="realtime-label">{label}</span>}
    </div>
  )
}

export default RealtimeStatusBadge
