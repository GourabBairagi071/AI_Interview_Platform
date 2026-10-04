import type { ReactNode } from "react"
import { Navigate } from "react-router-dom"
import { useAdminAuth } from "../hooks/useAdminAuth"

interface AdminProtectedRouteProps {
  children: ReactNode
  requiredPermission?: string
}

export default function AdminProtectedRoute({
  children,
  requiredPermission,
}: AdminProtectedRouteProps) {
  const token = localStorage.getItem("access_token")
  const { admin, loading, error, hasPermission } = useAdminAuth()

  if (!token) {
    return <Navigate to="/admin/login" replace />
  }

  if (loading) {
    return (
      <div className="admin-loading-screen" style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        background: "#0b0f19",
        color: "#94a3b8",
        gap: "1rem",
        fontFamily: "Inter, sans-serif"
      }}>
        <div className="admin-spinner" style={{
          width: "48px",
          height: "48px",
          border: "4px solid rgba(255,255,255,0.1)",
          borderTopColor: "#6366f1",
          borderRadius: "50%",
          animation: "spin 1s linear infinite"
        }} />
        <p style={{ fontSize: "0.95rem" }}>Verifying Administrative Privileges...</p>
        <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
      </div>
    )
  }

  if (error || !admin) {
    return (
      <div style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        background: "#0b0f19",
        color: "#f87171",
        gap: "1rem",
        padding: "2rem",
        textAlign: "center"
      }}>
        <h2 style={{ fontSize: "1.5rem", color: "#fca5a5" }}>Access Restricted</h2>
        <p style={{ maxWidth: "480px", color: "#94a3b8" }}>
          {error || "You do not have administrative clearance to access this control center."}
        </p>
        <div style={{ display: "flex", gap: "1rem", marginTop: "1rem", flexWrap: "wrap", justifyContent: "center" }}>
          <a
            href="/admin/login"
            style={{
              padding: "0.6rem 1.25rem",
              background: "#6366f1",
              color: "#ffffff",
              borderRadius: "8px",
              textDecoration: "none",
              fontWeight: 500,
            }}
          >
            Sign In with Admin Account
          </a>
          <a
            href="/dashboard"
            style={{
              padding: "0.6rem 1.25rem",
              background: "#1e293b",
              color: "#e2e8f0",
              borderRadius: "8px",
              textDecoration: "none",
              border: "1px solid #334155"
            }}
          >
            Return to Candidate Dashboard
          </a>
        </div>
      </div>
    )
  }

  if (requiredPermission && !hasPermission(requiredPermission)) {
    return (
      <div style={{
        padding: "3rem",
        color: "#f87171",
        textAlign: "center",
        background: "#0f172a",
        borderRadius: "12px",
        margin: "2rem"
      }}>
        <h3 style={{ fontSize: "1.25rem", marginBottom: "0.5rem" }}>Permission Denied</h3>
        <p style={{ color: "#94a3b8" }}>
          Your role ({admin.role}) requires the <code>{requiredPermission}</code> capability to view this module.
        </p>
      </div>
    )
  }

  return <>{children}</>
}
