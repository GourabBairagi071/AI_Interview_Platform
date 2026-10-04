import React, { useEffect, useState } from "react"
import { useParams, Link } from "react-router-dom"
import { adminApi } from "../services/adminApi"

export const AdminUserDetails: React.FC = () => {
  const { userId, id } = useParams<{ userId?: string; id?: string }>()
  const effectiveUserId = userId || id
  const [user, setUser] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (effectiveUserId) {
      loadUserDetail()
    }
  }, [effectiveUserId])

  const loadUserDetail = async () => {
    try {
      setLoading(true)
      const res = await adminApi.getUserDetail(effectiveUserId!)
      setUser(res)
    } catch (err: any) {
      setError(err?.message || "Failed to load candidate details")
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div style={{ padding: "3rem", textAlign: "center", color: "#94a3b8" }}>
        Loading user dossier...
      </div>
    )
  }

  if (error || !user) {
    return (
      <div style={{ padding: "2rem", color: "#f87171" }}>
        <h3>Error Loading User</h3>
        <p>{error || "Candidate not found."}</p>
        <Link to="/admin/users" className="admin-btn admin-btn-secondary" style={{ marginTop: "1rem" }}>
          ← Back to Users
        </Link>
      </div>
    )
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Header */}
      <div className="admin-page-header">
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <h1 className="admin-page-title">{user.full_name}</h1>
            <span
              className={`admin-badge ${user.is_active ? "admin-badge-success" : "admin-badge-danger"}`}
            >
              {user.is_active ? "Active" : "Suspended"}
            </span>
            <span className="admin-badge admin-badge-info">{user.role}</span>
          </div>
          <p className="admin-page-subtitle">{user.email} • ID: {user.id}</p>
        </div>
        <Link to="/admin/users" className="admin-btn admin-btn-secondary">
          ← Back to Users
        </Link>
      </div>

      {/* Profile Overview Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1rem" }}>
        <div className="admin-card">
          <h3 style={{ fontSize: "0.95rem", fontWeight: 600, color: "#94a3b8", marginBottom: "0.75rem" }}>
            Account Metadata
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", fontSize: "0.85rem" }}>
            <div><strong style={{ color: "#cbd5e1" }}>Verified:</strong> {user.is_verified ? "Yes" : "No"}</div>
            <div><strong style={{ color: "#cbd5e1" }}>Admin Privileges:</strong> {user.is_admin ? "Yes" : "No"}</div>
            <div><strong style={{ color: "#cbd5e1" }}>Registered Date:</strong> {new Date(user.created_at).toLocaleString()}</div>
          </div>
        </div>

        <div className="admin-card">
          <h3 style={{ fontSize: "0.95rem", fontWeight: 600, color: "#94a3b8", marginBottom: "0.75rem" }}>
            Coding Performance
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", fontSize: "0.85rem" }}>
            <div><strong style={{ color: "#cbd5e1" }}>Submissions:</strong> {user.coding_stats?.total_submissions || 0}</div>
            <div><strong style={{ color: "#cbd5e1" }}>Accepted:</strong> {user.coding_stats?.accepted_submissions || 0}</div>
            <div><strong style={{ color: "#cbd5e1" }}>Solved (E / M / H):</strong> {user.coding_stats?.easy_solved || 0} / {user.coding_stats?.medium_solved || 0} / {user.coding_stats?.hard_solved || 0}</div>
          </div>
        </div>
      </div>

      {/* Candidate Interviews */}
      <div className="admin-card">
        <h3 style={{ fontSize: "1rem", fontWeight: 600, color: "#f8fafc", marginBottom: "1rem" }}>
          Interview Sessions ({user.interviews?.length || 0})
        </h3>
        {(!user.interviews || user.interviews.length === 0) ? (
          <p style={{ color: "#64748b", fontSize: "0.875rem" }}>No interviews completed yet.</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {user.interviews.map((int: any) => (
              <div
                key={int.id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "0.75rem 1rem",
                  background: "rgba(255, 255, 255, 0.02)",
                  borderRadius: "8px",
                  fontSize: "0.875rem",
                }}
              >
                <div>
                  <span style={{ fontWeight: 600, color: "#f8fafc" }}>{int.job_role}</span>
                  <span style={{ color: "#64748b", marginLeft: "0.75rem", fontSize: "0.75rem" }}>
                    {int.difficulty} • {new Date(int.created_at).toLocaleDateString()}
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                  <span style={{ fontWeight: 600, color: int.score >= 7 ? "#34d399" : "#fbbf24" }}>
                    {int.score !== null ? `${int.score}/10` : "Pending"}
                  </span>
                  <span className={`admin-badge ${int.status === "completed" ? "admin-badge-success" : "admin-badge-warning"}`}>
                    {int.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Subscriptions & Payments */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
        <div className="admin-card">
          <h3 style={{ fontSize: "1rem", fontWeight: 600, color: "#f8fafc", marginBottom: "1rem" }}>
            Subscriptions ({user.subscriptions?.length || 0})
          </h3>
          {(!user.subscriptions || user.subscriptions.length === 0) ? (
            <p style={{ color: "#64748b", fontSize: "0.875rem" }}>No active or past subscriptions.</p>
          ) : (
            user.subscriptions.map((sub: any) => (
              <div key={sub.id} style={{ padding: "0.5rem 0", borderBottom: "1px solid rgba(255,255,255,0.05)", fontSize: "0.85rem" }}>
                <span style={{ fontWeight: 600, color: "#f8fafc" }}>{sub.plan_name}</span> - {sub.status}
              </div>
            ))
          )}
        </div>

        <div className="admin-card">
          <h3 style={{ fontSize: "1rem", fontWeight: 600, color: "#f8fafc", marginBottom: "1rem" }}>
            Payment History ({user.payments?.length || 0})
          </h3>
          {(!user.payments || user.payments.length === 0) ? (
            <p style={{ color: "#64748b", fontSize: "0.875rem" }}>No recorded payment transactions.</p>
          ) : (
            user.payments.map((p: any) => (
              <div key={p.id} style={{ display: "flex", justifyContent: "space-between", padding: "0.5rem 0", borderBottom: "1px solid rgba(255,255,255,0.05)", fontSize: "0.85rem" }}>
                <span>₹{p.amount_inr}</span>
                <span style={{ color: "#34d399" }}>{p.status}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
export default AdminUserDetails
