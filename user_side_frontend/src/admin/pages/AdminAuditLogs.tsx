import React, { useEffect, useState } from "react"
import { adminApi } from "../services/adminApi"
import { AdminTable, type Column } from "../components/AdminTable"
import { SearchIcon, AuditIcon } from "../components/AdminIcons"
import type { AdminAuditLogItem } from "../types"

export const AdminAuditLogs: React.FC = () => {
  const [logs, setLogs] = useState<AdminAuditLogItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [actionFilter, setActionFilter] = useState("")
  const [actorEmail, setActorEmail] = useState("")
  const [loading, setLoading] = useState(true)

  // Inspection modal
  const [selectedLog, setSelectedLog] = useState<AdminAuditLogItem | null>(null)

  useEffect(() => {
    loadLogs()
  }, [page, actionFilter])

  const loadLogs = async () => {
    try {
      setLoading(true)
      const res = await adminApi.getAuditLogs({
        page,
        page_size: pageSize,
        action: actionFilter || undefined,
        actor_email: actorEmail.trim() || undefined,
      })
      setLogs(res.logs || [])
      setTotal(res.total || 0)
    } catch (err) {
      console.error("Failed to load audit logs:", err)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    loadLogs()
  }

  const columns: Column<AdminAuditLogItem>[] = [
    {
      key: "action",
      header: "Action Event",
      render: (l) => (
        <span
          style={{
            fontFamily: "monospace",
            fontWeight: 700,
            fontSize: "0.8rem",
            padding: "0.2rem 0.5rem",
            background: "rgba(99, 102, 241, 0.15)",
            color: "#a5b4fc",
            borderRadius: "4px",
          }}
        >
          {l.action}
        </span>
      ),
      width: "180px",
    },
    {
      key: "actor_email",
      header: "Administrator / Actor",
      render: (l) => (
        <span style={{ fontWeight: 600, color: "#f8fafc", fontSize: "0.85rem" }}>
          {l.actor_email}
        </span>
      ),
      width: "220px",
    },
    {
      key: "resource_type",
      header: "Target Resource",
      render: (l) => (
        <div>
          <span style={{ color: "#cbd5e1" }}>{l.resource_type}</span>
          {l.resource_id && (
            <span style={{ fontFamily: "monospace", fontSize: "0.75rem", color: "#64748b", marginLeft: "0.5rem" }}>
              #{String(l.resource_id).substring(0, 8)}
            </span>
          )}
        </div>
      ),
      width: "180px",
    },
    {
      key: "ip_address",
      header: "Origin IP",
      render: (l) => (
        <span style={{ fontFamily: "monospace", fontSize: "0.75rem", color: "#94a3b8" }}>
          {l.ip_address || "127.0.0.1"}
        </span>
      ),
      width: "130px",
    },
    {
      key: "timestamp",
      header: "Event Timestamp",
      render: (l) => (
        <span style={{ color: "#94a3b8", fontSize: "0.825rem" }}>
          {new Date(l.timestamp).toLocaleString()}
        </span>
      ),
      width: "180px",
    },
    {
      key: "actions",
      header: "Diff",
      render: (l) => (
        <button
          onClick={() => setSelectedLog(l)}
          className="admin-btn admin-btn-secondary"
          style={{ padding: "0.25rem 0.6rem", fontSize: "0.75rem" }}
        >
          Inspect Diff
        </button>
      ),
      width: "110px",
    },
  ]

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Administrative Audit Trail</h1>
          <p className="admin-page-subtitle">
            Immutable security ledger tracking every privileged change, role promotion, and system mutation
          </p>
        </div>
      </div>

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
        <form onSubmit={handleSearch} style={{ display: "flex", gap: "0.5rem", flex: "1 1 300px" }}>
          <div style={{ position: "relative", width: "100%", maxWidth: "380px" }}>
            <input
              type="text"
              placeholder="Search by administrator email..."
              value={actorEmail}
              onChange={(e) => setActorEmail(e.target.value)}
              className="admin-input"
              style={{ width: "100%", paddingLeft: "2.25rem" }}
            />
            <span style={{ position: "absolute", left: "0.75rem", top: "50%", transform: "translateY(-50%)", color: "#64748b" }}>
              <SearchIcon />
            </span>
          </div>
          <button type="submit" className="admin-btn admin-btn-primary">
            Filter
          </button>
        </form>

        <select
          value={actionFilter}
          onChange={(e) => {
            setActionFilter(e.target.value)
            setPage(1)
          }}
          className="admin-select"
        >
          <option value="">All Action Types</option>
          <option value="USER_ROLE_UPDATED">USER_ROLE_UPDATED</option>
          <option value="USER_STATUS_UPDATED">USER_STATUS_UPDATED</option>
          <option value="AI_AGENT_CONFIG_UPDATED">AI_AGENT_CONFIG_UPDATED</option>
          <option value="ROLE_PERMISSIONS_UPDATED">ROLE_PERMISSIONS_UPDATED</option>
          <option value="SYSTEM_SETTING_UPDATED">SYSTEM_SETTING_UPDATED</option>
          <option value="NOTIFICATION_BROADCAST">NOTIFICATION_BROADCAST</option>
        </select>
      </div>

      <AdminTable
        columns={columns}
        data={logs}
        loading={loading}
        total={total}
        page={page}
        pageSize={pageSize}
        onPageChange={(p) => setPage(p)}
      />

      {/* Diff Inspector Modal */}
      {selectedLog && (
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
              maxWidth: "600px",
              padding: "2rem",
              color: "#f8fafc",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <AuditIcon className="text-indigo-400" />
                <h3 style={{ fontSize: "1.25rem", fontWeight: 700 }}>
                  Audit Event Details
                </h3>
              </div>
              <button
                onClick={() => setSelectedLog(null)}
                className="admin-btn admin-btn-secondary"
                style={{ padding: "0.3rem 0.6rem" }}
              >
                ✕
              </button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", fontSize: "0.85rem", marginBottom: "1.25rem" }}>
              <div><strong style={{ color: "#94a3b8" }}>Action:</strong> {selectedLog.action}</div>
              <div><strong style={{ color: "#94a3b8" }}>Actor:</strong> {selectedLog.actor_email}</div>
              <div><strong style={{ color: "#94a3b8" }}>Resource:</strong> {selectedLog.resource_type} ({selectedLog.resource_id || "Global"})</div>
              <div><strong style={{ color: "#94a3b8" }}>IP:</strong> {selectedLog.ip_address || "127.0.0.1"}</div>
              <div><strong style={{ color: "#94a3b8" }}>Timestamp:</strong> {new Date(selectedLog.timestamp).toISOString()}</div>
            </div>

            <h4 style={{ fontSize: "0.9rem", color: "#a5b4fc", marginBottom: "0.5rem" }}>
              Payload / Mutation Snapshot
            </h4>
            <pre
              style={{
                background: "rgba(0,0,0,0.4)",
                padding: "1rem",
                borderRadius: "8px",
                fontSize: "0.8rem",
                color: "#38bdf8",
                overflowX: "auto",
                maxHeight: "240px",
              }}
            >
              {JSON.stringify(selectedLog.changes || {}, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}
export default AdminAuditLogs
