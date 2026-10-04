import React from "react"
import { useAdminAuth } from "../hooks/useAdminAuth"
import { LogoutIcon } from "./AdminIcons"
import RealtimeStatusBadge from "../../components/RealtimeStatusBadge"

interface AdminHeaderProps {
  collapsed: boolean
  onToggleSidebar: () => void
}

export const AdminHeader: React.FC<AdminHeaderProps> = ({
  collapsed,
  onToggleSidebar,
}) => {
  const { admin, logout } = useAdminAuth()

  return (
    <header
      style={{
        height: "64px",
        background: "rgba(11, 16, 30, 0.8)",
        backdropFilter: "blur(12px)",
        borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 1.5rem",
        position: "sticky",
        top: 0,
        zIndex: 40,
      }}
    >
      {/* Left side: Toggle button and search */}
      <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
        <button
          onClick={onToggleSidebar}
          style={{
            background: "rgba(255, 255, 255, 0.04)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            color: "#94a3b8",
            width: "36px",
            height: "36px",
            borderRadius: "8px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
          }}
          title={collapsed ? "Expand Sidebar" : "Collapse Sidebar"}
        >
          {collapsed ? "→" : "←"}
        </button>

        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <span style={{ fontSize: "0.85rem", color: "#64748b", fontWeight: 500 }}>
            Session ID:
          </span>
          <span
            style={{
              fontSize: "0.75rem",
              background: "rgba(99, 102, 241, 0.1)",
              border: "1px solid rgba(99, 102, 241, 0.3)",
              color: "#a5b4fc",
              padding: "0.15rem 0.5rem",
              borderRadius: "4px",
              fontFamily: "monospace",
            }}
          >
            LIVE-ADMIN
          </span>
        </div>
      </div>

      {/* Right side: Realtime badge, Admin identity, Logout */}
      <div style={{ display: "flex", alignItems: "center", gap: "1.25rem" }}>
        {/* Realtime WebSocket indicator from Phase 16 */}
        <RealtimeStatusBadge />

        {/* User Identity Pill */}
        {admin && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.75rem",
              background: "rgba(30, 41, 59, 0.6)",
              border: "1px solid rgba(255, 255, 255, 0.06)",
              padding: "0.35rem 0.75rem 0.35rem 0.5rem",
              borderRadius: "999px",
            }}
          >
            <div
              style={{
                width: "28px",
                height: "28px",
                borderRadius: "50%",
                background: "#6366f1",
                color: "#ffffff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "0.8rem",
                fontWeight: 700,
              }}
            >
              {admin.full_name?.charAt(0).toUpperCase() || "A"}
            </div>
            <div style={{ display: "flex", flexDirection: "column" }}>
              <span style={{ fontSize: "0.825rem", fontWeight: 600, color: "#f8fafc" }}>
                {admin.full_name}
              </span>
              <span
                style={{
                  fontSize: "0.68rem",
                  color: admin.role === "SUPER_ADMIN" ? "#fbbf24" : "#38bdf8",
                  fontWeight: 600,
                }}
              >
                {admin.role}
              </span>
            </div>
          </div>
        )}

        {/* Logout */}
        <button
          onClick={logout}
          style={{
            background: "rgba(239, 68, 68, 0.1)",
            border: "1px solid rgba(239, 68, 68, 0.2)",
            color: "#f87171",
            padding: "0.45rem 0.85rem",
            borderRadius: "8px",
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            fontSize: "0.825rem",
            fontWeight: 500,
            cursor: "pointer",
          }}
          title="Sign Out"
        >
          <LogoutIcon size={16} />
          <span>Exit</span>
        </button>
      </div>
    </header>
  )
}
