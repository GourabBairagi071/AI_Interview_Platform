import React, { type ReactNode } from "react"

interface AdminStatCardProps {
  title: string
  value: string | number
  icon: ReactNode
  subtitle?: string
  trend?: {
    value: number | string
    isPositive?: boolean
    label?: string
  }
  colorVariant?: "indigo" | "emerald" | "amber" | "rose" | "purple" | "cyan"
}

export const AdminStatCard: React.FC<AdminStatCardProps> = ({
  title,
  value,
  icon,
  subtitle,
  trend,
  colorVariant = "indigo",
}) => {
  const colorMap = {
    indigo: {
      border: "rgba(99, 102, 241, 0.25)",
      bg: "rgba(99, 102, 241, 0.1)",
      text: "#818cf8",
    },
    emerald: {
      border: "rgba(16, 185, 129, 0.25)",
      bg: "rgba(16, 185, 129, 0.1)",
      text: "#34d399",
    },
    amber: {
      border: "rgba(245, 158, 11, 0.25)",
      bg: "rgba(245, 158, 11, 0.1)",
      text: "#fbbf24",
    },
    rose: {
      border: "rgba(244, 63, 94, 0.25)",
      bg: "rgba(244, 63, 94, 0.1)",
      text: "#fb7185",
    },
    purple: {
      border: "rgba(168, 85, 247, 0.25)",
      bg: "rgba(168, 85, 247, 0.1)",
      text: "#c084fc",
    },
    cyan: {
      border: "rgba(6, 182, 212, 0.25)",
      bg: "rgba(6, 182, 212, 0.1)",
      text: "#22d3ee",
    },
  }

  const activeColor = colorMap[colorVariant] || colorMap.indigo

  return (
    <div
      style={{
        background: "rgba(17, 24, 39, 0.8)",
        backdropFilter: "blur(12px)",
        border: `1px solid ${activeColor.border}`,
        borderRadius: "14px",
        padding: "1.25rem",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        transition: "all 0.2s ease-in-out",
        boxShadow: "0 4px 20px -2px rgba(0, 0, 0, 0.3)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <span style={{ fontSize: "0.825rem", fontWeight: 500, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em" }}>
            {title}
          </span>
          <div style={{ fontSize: "1.75rem", fontWeight: 700, color: "#f8fafc", marginTop: "0.35rem" }}>
            {value}
          </div>
        </div>
        <div
          style={{
            padding: "0.6rem",
            borderRadius: "10px",
            background: activeColor.bg,
            color: activeColor.text,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {icon}
        </div>
      </div>

      {(subtitle || trend) && (
        <div style={{ marginTop: "0.75rem", display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.825rem" }}>
          {trend && (
            <span
              style={{
                color: trend.isPositive !== false ? "#34d399" : "#f87171",
                fontWeight: 600,
              }}
            >
              {trend.isPositive !== false ? "↑" : "↓"} {trend.value}
            </span>
          )}
          {subtitle && <span style={{ color: "#64748b" }}>{subtitle}</span>}
        </div>
      )}
    </div>
  )
}
