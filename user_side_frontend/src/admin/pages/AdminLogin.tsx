import React, { useState } from "react"
import { useNavigate, Link } from "react-router-dom"
import { ShieldIcon } from "../components/AdminIcons"

const API_BASE_URL = "http://127.0.0.1:8000/api/v1"

export const AdminLogin: React.FC = () => {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          email: email.trim(),
          password,
        }),
      })

      let data: any = {}
      try {
        data = await response.json()
      } catch {
        data = {}
      }

      if (!response.ok) {
        throw new Error(data.detail || data.message || "Invalid email or password")
      }

      if (!data.access_token) {
        throw new Error("Login succeeded but access token was not returned.")
      }

      const user = data.user || {}
      const normalizedRole = (user.role || "").trim().toUpperCase().replace(/[\s-]/g, "_")
      const isExplicitAdmin = user.is_admin === true || normalizedRole === "SUPER_ADMIN"
      const hasAdminRole = normalizedRole !== "" && normalizedRole !== "CANDIDATE"
      const isAdmin = isExplicitAdmin || hasAdminRole

      if (!isAdmin) {
        throw new Error("Access Denied: This account does not possess administrative privileges.")
      }

      localStorage.setItem("access_token", data.access_token)
      navigate("/admin/dashboard", { replace: true })
    } catch (err: any) {
      setError(err?.message || "Authentication failed")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        background: "#0b0f19",
        color: "#f8fafc",
        fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        padding: "1rem",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "420px",
          background: "rgba(17, 24, 39, 0.8)",
          backdropFilter: "blur(16px)",
          border: "1px solid rgba(255, 255, 255, 0.1)",
          borderRadius: "16px",
          padding: "2rem",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.5)",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: "1.75rem" }}>
          <div
            style={{
              width: "48px",
              height: "48px",
              borderRadius: "12px",
              background: "linear-gradient(135deg, #6366f1 0%, #a855f7 100%)",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              marginBottom: "1rem",
              color: "#ffffff",
              boxShadow: "0 4px 14px rgba(99, 102, 241, 0.4)",
            }}
          >
            <ShieldIcon size={24} />
          </div>
          <h1 style={{ fontSize: "1.35rem", fontWeight: 700, letterSpacing: "-0.02em" }}>
            Admin Control Center
          </h1>
          <p style={{ fontSize: "0.85rem", color: "#94a3b8", marginTop: "0.25rem" }}>
            Sign in with administrative privileges to manage platform operations
          </p>
        </div>

        {error && (
          <div
            style={{
              padding: "0.75rem 1rem",
              background: "rgba(239, 68, 68, 0.15)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              borderRadius: "8px",
              color: "#fca5a5",
              fontSize: "0.85rem",
              marginBottom: "1.25rem",
              lineHeight: 1.4,
            }}
          >
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div>
            <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.35rem", fontWeight: 500 }}>
              Admin Email
            </label>
            <input
              type="email"
              required
              placeholder="admin@interviewplatform.ai"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="admin-input"
              style={{ width: "100%" }}
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.35rem", fontWeight: 500 }}>
              Password
            </label>
            <input
              type="password"
              required
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="admin-input"
              style={{ width: "100%" }}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="admin-btn admin-btn-primary"
            style={{
              width: "100%",
              justifyContent: "center",
              padding: "0.7rem",
              marginTop: "0.5rem",
              fontSize: "0.9rem",
              fontWeight: 600,
            }}
          >
            {loading ? "Authenticating..." : "Sign In to Admin Console"}
          </button>
        </form>

        <div style={{ marginTop: "1.5rem", textAlign: "center", borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: "1rem" }}>
          <Link to="/login" style={{ fontSize: "0.8rem", color: "#94a3b8", textDecoration: "none" }}>
            Candidate? <span style={{ color: "#6366f1", fontWeight: 500 }}>Sign in to Candidate Portal</span>
          </Link>
        </div>
      </div>
    </div>
  )
}
export default AdminLogin
