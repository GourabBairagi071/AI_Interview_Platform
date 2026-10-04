import React, { useEffect, useState } from "react"
import { adminApi } from "../services/adminApi"
import { ShieldIcon } from "../components/AdminIcons"
import type { AdminRoleItem } from "../types"

export const AdminRBAC: React.FC = () => {
  const [roles, setRoles] = useState<AdminRoleItem[]>([])
  const [loading, setLoading] = useState(true)

  // Edit Role Permissions Modal
  const [selectedRole, setSelectedRole] = useState<AdminRoleItem | null>(null)
  const [rolePermissions, setRolePermissions] = useState<string[]>([])
  const [saving, setSaving] = useState(false)

  // Quick Role Assignment form
  const [assignEmailOrId, setAssignEmailOrId] = useState("")
  const [assignRoleName, setAssignRoleName] = useState("ADMIN")
  const [assigning, setAssigning] = useState(false)
  const [assignResult, setAssignResult] = useState<string | null>(null)

  useEffect(() => {
    loadRoles()
  }, [])

  const loadRoles = async () => {
    try {
      setLoading(true)
      const data = await adminApi.getRBACRoles()
      setRoles(data || [])
    } catch (err) {
      console.error("Failed to load roles:", err)
    } finally {
      setLoading(false)
    }
  }

  const handleOpenEdit = (role: AdminRoleItem) => {
    setSelectedRole(role)
    setRolePermissions([...role.permissions])
  }

  const togglePermission = (perm: string) => {
    if (rolePermissions.includes(perm)) {
      setRolePermissions(rolePermissions.filter((p) => p !== perm))
    } else {
      setRolePermissions([...rolePermissions, perm])
    }
  }

  const handleSavePermissions = async () => {
    if (!selectedRole) return
    try {
      setSaving(true)
      await adminApi.updateRBACRole(selectedRole.name, rolePermissions)
      setSelectedRole(null)
      loadRoles()
    } catch (err: any) {
      alert(err.message || "Failed to update role permissions")
    } finally {
      setSaving(false)
    }
  }

  const handleAssignRole = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!assignEmailOrId.trim()) return

    try {
      setAssigning(true)
      setAssignResult(null)
      // Check if it's an email or UUID
      const usersRes = await adminApi.getUsers({ search: assignEmailOrId.trim(), page_size: 1 })
      const matchedUser = (usersRes.users || [])[0]
      if (!matchedUser) {
        throw new Error(`User not found with search term: ${assignEmailOrId}`)
      }

      await adminApi.assignUserRole(matchedUser.id, assignRoleName)
      setAssignResult(`Successfully assigned role ${assignRoleName} to ${matchedUser.email}`)
      setAssignEmailOrId("")
    } catch (err: any) {
      alert(err.message || "Failed to assign role")
    } finally {
      setAssigning(false)
    }
  }

  const allKnownPermissions = [
    "users.view",
    "users.manage",
    "interviews.view",
    "interviews.manage",
    "questions.view",
    "questions.create",
    "questions.update",
    "questions.delete",
    "companies.view",
    "companies.manage",
    "resources.view",
    "resources.manage",
    "ai_agents.view",
    "ai_agents.manage",
    "analytics.view",
    "subscriptions.view",
    "subscriptions.manage",
    "payments.view",
    "coupons.manage",
    "invoices.view",
    "support.view",
    "support.manage",
    "feedback.view",
    "feedback.manage",
    "notifications.manage",
    "achievements.manage",
    "audit_logs.view",
    "settings.view",
    "settings.manage",
    "rag.view",
    "rag.manage",
    "contests.view",
    "contests.manage",
    "rbac.view",
    "rbac.manage",
  ]

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Role-Based Access Control (RBAC)</h1>
          <p className="admin-page-subtitle">
            Configure system roles, fine-grained permission matrices, and security clearances
          </p>
        </div>
      </div>

      {/* Role Assignment Card */}
      <div className="admin-card">
        <h3 style={{ fontSize: "1rem", fontWeight: 600, color: "#f8fafc", marginBottom: "0.75rem" }}>
          Direct User Role Assignment
        </h3>
        {assignResult && (
          <div style={{ padding: "0.75rem 1rem", background: "rgba(16,185,129,0.15)", border: "1px solid rgba(16,185,129,0.3)", borderRadius: "8px", color: "#34d399", fontSize: "0.85rem", marginBottom: "1rem" }}>
            ✓ {assignResult}
          </div>
        )}
        <form onSubmit={handleAssignRole} style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", alignItems: "center" }}>
          <input
            type="text"
            required
            placeholder="Candidate email (e.g. user@example.com)"
            value={assignEmailOrId}
            onChange={(e) => setAssignEmailOrId(e.target.value)}
            className="admin-input"
            style={{ width: "320px" }}
          />
          <select
            value={assignRoleName}
            onChange={(e) => setAssignRoleName(e.target.value)}
            className="admin-select"
            style={{ width: "200px" }}
          >
            {roles.map((r) => (
              <option key={r.name} value={r.name}>
                {r.name}
              </option>
            ))}
          </select>
          <button type="submit" disabled={assigning} className="admin-btn admin-btn-primary">
            {assigning ? "Assigning..." : "Assign Role"}
          </button>
        </form>
      </div>

      {/* Roles Grid */}
      {loading ? (
        <div style={{ padding: "3rem", textAlign: "center", color: "#94a3b8" }}>
          Loading RBAC matrix...
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1.25rem" }}>
          {roles.map((role) => (
            <div
              key={role.id}
              className="admin-card"
              style={{
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                gap: "1rem",
              }}
            >
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <ShieldIcon className="text-indigo-400" />
                    <h3 style={{ fontSize: "1.1rem", fontWeight: 700, color: "#f8fafc" }}>
                      {role.name}
                    </h3>
                  </div>
                  <span className="admin-badge admin-badge-info">
                    {role.permissions?.length || 0} permissions
                  </span>
                </div>

                <p style={{ fontSize: "0.85rem", color: "#94a3b8", marginBottom: "1rem" }}>
                  {role.description || "System RBAC access policy"}
                </p>

                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem", maxHeight: "160px", overflowY: "auto" }}>
                  {(role.permissions || []).map((p) => (
                    <span
                      key={p}
                      style={{
                        padding: "0.2rem 0.45rem",
                        borderRadius: "4px",
                        background: "rgba(255,255,255,0.05)",
                        color: "#cbd5e1",
                        fontSize: "0.72rem",
                        fontFamily: "monospace",
                      }}
                    >
                      {p}
                    </span>
                  ))}
                </div>
              </div>

              {role.name !== "SUPER_ADMIN" && (
                <div style={{ borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: "0.75rem", display: "flex", justifyContent: "flex-end" }}>
                  <button
                    onClick={() => handleOpenEdit(role)}
                    className="admin-btn admin-btn-secondary"
                    style={{ padding: "0.35rem 0.8rem", fontSize: "0.8rem" }}
                  >
                    Edit Capabilities
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Permissions Editor Modal */}
      {selectedRole && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.8)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
            padding: "1.5rem",
          }}
        >
          <div
            style={{
              background: "#1e293b",
              border: "1px solid rgba(255, 255, 255, 0.12)",
              borderRadius: "16px",
              width: "100%",
              maxWidth: "700px",
              maxHeight: "85vh",
              overflowY: "auto",
              padding: "2rem",
              color: "#f8fafc",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1.5rem" }}>
              <div>
                <h3 style={{ fontSize: "1.25rem", fontWeight: 700 }}>
                  Edit Capabilities: {selectedRole.name}
                </h3>
                <p style={{ color: "#94a3b8", fontSize: "0.85rem" }}>
                  Toggle fine-grained permissions enabled for this role.
                </p>
              </div>
              <button
                onClick={() => setSelectedRole(null)}
                className="admin-btn admin-btn-secondary"
                style={{ padding: "0.3rem 0.6rem" }}
              >
                ✕
              </button>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", marginBottom: "1.5rem" }}>
              {allKnownPermissions.map((perm) => {
                const checked = rolePermissions.includes(perm)
                return (
                  <label
                    key={perm}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "0.6rem",
                      padding: "0.5rem 0.75rem",
                      background: checked ? "rgba(99, 102, 241, 0.15)" : "rgba(255,255,255,0.03)",
                      border: checked ? "1px solid rgba(99, 102, 241, 0.3)" : "1px solid rgba(255,255,255,0.05)",
                      borderRadius: "8px",
                      cursor: "pointer",
                      fontSize: "0.8rem",
                      fontFamily: "monospace",
                      color: checked ? "#ffffff" : "#94a3b8",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => togglePermission(perm)}
                    />
                    {perm}
                  </label>
                )
              })}
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem" }}>
              <button
                onClick={() => setSelectedRole(null)}
                className="admin-btn admin-btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleSavePermissions}
                disabled={saving}
                className="admin-btn admin-btn-primary"
              >
                {saving ? "Saving..." : "Save Capabilities"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
export default AdminRBAC
