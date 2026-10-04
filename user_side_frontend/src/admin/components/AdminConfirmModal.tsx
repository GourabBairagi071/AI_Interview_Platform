import React from "react"

interface AdminConfirmModalProps {
  isOpen: boolean
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  isDestructive?: boolean
  loading?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export const AdminConfirmModal: React.FC<AdminConfirmModalProps> = ({
  isOpen,
  title,
  message,
  confirmText = "Confirm",
  cancelText = "Cancel",
  isDestructive = false,
  loading = false,
  onConfirm,
  onCancel,
}) => {
  if (!isOpen) return null

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: "rgba(0, 0, 0, 0.75)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        padding: "1rem",
      }}
    >
      <div
        style={{
          background: "#1e293b",
          border: "1px solid rgba(255, 255, 255, 0.1)",
          borderRadius: "14px",
          width: "100%",
          maxWidth: "460px",
          padding: "1.75rem",
          boxShadow: "0 20px 25px -5px rgba(0,0,0,0.5)",
          color: "#f8fafc",
        }}
      >
        <h3 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "0.75rem" }}>
          {title}
        </h3>
        <p style={{ color: "#94a3b8", fontSize: "0.95rem", lineHeight: 1.5, marginBottom: "1.5rem" }}>
          {message}
        </p>
        <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem" }}>
          <button
            onClick={onCancel}
            disabled={loading}
            style={{
              padding: "0.55rem 1.1rem",
              borderRadius: "8px",
              background: "rgba(255, 255, 255, 0.08)",
              border: "1px solid rgba(255, 255, 255, 0.1)",
              color: "#e2e8f0",
              cursor: "pointer",
            }}
          >
            {cancelText}
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            style={{
              padding: "0.55rem 1.25rem",
              borderRadius: "8px",
              background: isDestructive ? "#ef4444" : "#6366f1",
              border: "none",
              color: "#ffffff",
              fontWeight: 600,
              cursor: loading ? "wait" : "pointer",
            }}
          >
            {loading ? "Processing..." : confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}
