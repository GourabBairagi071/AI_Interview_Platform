import React, { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { adminApi } from "../services/adminApi"
import { AdminTable, type Column } from "../components/AdminTable"
import { AdminConfirmModal } from "../components/AdminConfirmModal"
import { SearchIcon } from "../components/AdminIcons"
import type { AdminUserListItem } from "../types"

export const AdminUsers: React.FC = () => {
  const [users, setUsers] = useState<AdminUserListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(15)
  const [search, setSearch] = useState("")
  const [roleFilter, setRoleFilter] = useState("")
  const [loading, setLoading] = useState(true)

  // Status toggle modal state
  const [selectedUser, setSelectedUser] = useState<AdminUserListItem | null>(null)
  const [statusModalOpen, setStatusModalOpen] = useState(false)
  const [roleModalOpen, setRoleModalOpen] = useState(false)
  const [newRole, setNewRole] = useState("")
  const [actionLoading, setActionLoading] = useState(false)

  useEffect(() => {
    loadUsers()
  }, [page, roleFilter])

  const loadUsers = async () => {
    try {
      setLoading(true)
      const res = await adminApi.getUsers({
        page,
        page_size: pageSize,
        search: search.trim() || undefined,
        role: roleFilter || undefined,
      })
      setUsers(res.users || [])
      setTotal(res.total || 0)
    } catch (err) {
      console.error("Failed to load users:", err)
    } finally {
      setLoading(false)
    }
  }

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    loadUsers()
  }

  const handleConfirmToggleStatus = async () => {
    if (!selectedUser) return
    try {
      setActionLoading(true)
      await adminApi.updateUserStatus(selectedUser.id, !selectedUser.is_active)
      setStatusModalOpen(false)
      loadUsers()
    } catch (err: any) {
      alert(err.message || "Failed to update status")
    } finally {
      setActionLoading(false)
    }
  }

  const handleConfirmChangeRole = async () => {
    if (!selectedUser || !newRole) return
    try {
      setActionLoading(true)
      await adminApi.updateUserRole(selectedUser.id, newRole)
      setRoleModalOpen(false)
      loadUsers()
    } catch (err: any) {
      alert(err.message || "Failed to update role")
    } finally {
      setActionLoading(false)
    }
  }

  const columns: Column<AdminUserListItem>[] = [
    {
      key: "full_name",
      header: "Candidate / Name",
      render: (u) => (
        <div style={{ display: "flex", flexDirection: "column" }}>
          <span style={{ fontWeight: 600, color: "#f8fafc" }}>{u.full_name}</span>
          <span style={{ fontSize: "0.75rem", color: "#64748b" }}>{u.email}</span>
        </div>
      ),
    },
    {
      key: "role",
      header: "Access Role",
      render: (u) => {
        const isSuper = u.role === "SUPER_ADMIN"
        const isAdmin = u.is_admin || u.role === "ADMIN"
        return (
          <span
            className={`admin-badge ${
              isSuper
                ? "admin-badge-warning"
                : isAdmin
                ? "admin-badge-info"
                : "admin-badge-secondary"
            }`}
            style={{
              background: isSuper
                ? "rgba(245, 158, 11, 0.15)"
                : isAdmin
                ? "rgba(99, 102, 241, 0.15)"
                : "rgba(255, 255, 255, 0.05)",
              color: isSuper ? "#fbbf24" : isAdmin ? "#a5b4fc" : "#94a3b8",
            }}
          >
            {u.role}
          </span>
        )
      },
    },
    {
      key: "is_active",
      header: "Status",
      render: (u) => (
        <span
          className={`admin-badge ${
            u.is_active ? "admin-badge-success" : "admin-badge-danger"
          }`}
        >
          {u.is_active ? "Active" : "Suspended"}
        </span>
      ),
    },
    {
      key: "interview_count",
      header: "Interviews",
      render: (u) => (
        <span style={{ color: "#cbd5e1", fontWeight: 500 }}>
          {u.interview_count || 0} sessions
        </span>
      ),
    },
    {
      key: "created_at",
      header: "Registered",
      render: (u) => (
        <span style={{ color: "#94a3b8", fontSize: "0.8rem" }}>
          {new Date(u.created_at).toLocaleDateString()}
        </span>
      ),
    },
    {
      key: "actions",
      header: "Actions",
      render: (u) => (
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <Link
            to={`/admin/users/${u.id}`}
            className="admin-btn admin-btn-secondary"
            style={{ padding: "0.3rem 0.6rem", fontSize: "0.75rem" }}
          >
            Details
          </Link>
          <button
            onClick={() => {
              setSelectedUser(u)
              setNewRole(u.role)
              setRoleModalOpen(true)
            }}
            className="admin-btn admin-btn-secondary"
            style={{ padding: "0.3rem 0.6rem", fontSize: "0.75rem" }}
          >
            Role
          </button>
          <button
            onClick={() => {
              setSelectedUser(u)
              setStatusModalOpen(true)
            }}
            className={`admin-btn ${u.is_active ? "admin-btn-danger" : "admin-btn-secondary"}`}
            style={{ padding: "0.3rem 0.6rem", fontSize: "0.75rem" }}
          >
            {u.is_active ? "Suspend" : "Activate"}
          </button>
        </div>
      ),
    },
  ]

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Candidate Directory & Access</h1>
          <p className="admin-page-subtitle">
            Manage platform accounts, security clearance, and access roles
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div
        className="admin-card"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "1rem",
          padding: "1rem",
        }}
      >
        <form onSubmit={handleSearchSubmit} style={{ display: "flex", gap: "0.5rem", flex: "1 1 300px" }}>
          <div style={{ position: "relative", width: "100%", maxWidth: "380px" }}>
            <input
              type="text"
              placeholder="Search by candidate name or email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="admin-input"
              style={{ width: "100%", paddingLeft: "2.25rem" }}
            />
            <span
              style={{
                position: "absolute",
                left: "0.75rem",
                top: "50%",
                transform: "translateY(-50%)",
                color: "#64748b",
              }}
            >
              <SearchIcon />
            </span>
          </div>
          <button type="submit" className="admin-btn admin-btn-primary">
            Search
          </button>
        </form>

        <div style={{ display: "flex", gap: "0.75rem" }}>
          <select
            value={roleFilter}
            onChange={(e) => {
              setRoleFilter(e.target.value)
              setPage(1)
            }}
            className="admin-select"
          >
            <option value="">All Roles</option>
            <option value="CANDIDATE">Candidate</option>
            <option value="ADMIN">Admin</option>
            <option value="SUPER_ADMIN">Super Admin</option>
            <option value="SUPPORT_AGENT">Support Agent</option>
            <option value="CONTENT_ADMIN">Content Admin</option>
          </select>
        </div>
      </div>

      {/* User Table */}
      <AdminTable
        columns={columns}
        data={users}
        loading={loading}
        total={total}
        page={page}
        pageSize={pageSize}
        onPageChange={(p) => setPage(p)}
      />

      {/* Confirm Status Modal */}
      <AdminConfirmModal
        isOpen={statusModalOpen}
        title={selectedUser?.is_active ? "Suspend User Account" : "Activate User Account"}
        message={
          selectedUser?.is_active
            ? `Are you sure you want to suspend ${selectedUser?.email}? They will be blocked from logging into the platform.`
            : `Are you sure you want to restore access for ${selectedUser?.email}?`
        }
        confirmText={selectedUser?.is_active ? "Suspend Account" : "Restore Access"}
        isDestructive={selectedUser?.is_active}
        loading={actionLoading}
        onConfirm={handleConfirmToggleStatus}
        onCancel={() => setStatusModalOpen(false)}
      />

      {/* Change Role Modal */}
      {roleModalOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
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
              maxWidth: "420px",
              padding: "1.75rem",
              color: "#f8fafc",
            }}
          >
            <h3 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "0.5rem" }}>
              Assign Access Role
            </h3>
            <p style={{ color: "#94a3b8", fontSize: "0.875rem", marginBottom: "1.25rem" }}>
              Update privileges for <strong>{selectedUser?.email}</strong>.
            </p>

            <div style={{ marginBottom: "1.5rem" }}>
              <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.4rem" }}>
                Select Role
              </label>
              <select
                value={newRole}
                onChange={(e) => setNewRole(e.target.value)}
                className="admin-select"
                style={{ width: "100%" }}
              >
                <option value="CANDIDATE">CANDIDATE</option>
                <option value="ADMIN">ADMIN</option>
                <option value="SUPER_ADMIN">SUPER_ADMIN</option>
                <option value="SUPPORT_AGENT">SUPPORT_AGENT</option>
                <option value="CONTENT_ADMIN">CONTENT_ADMIN</option>
                <option value="INTERVIEW_ADMIN">INTERVIEW_ADMIN</option>
                <option value="FINANCE_ADMIN">FINANCE_ADMIN</option>
                <option value="AI_ENGINEER">AI_ENGINEER</option>
              </select>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem" }}>
              <button
                onClick={() => setRoleModalOpen(false)}
                className="admin-btn admin-btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmChangeRole}
                disabled={actionLoading}
                className="admin-btn admin-btn-primary"
              >
                {actionLoading ? "Updating..." : "Save Role"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
export default AdminUsers
