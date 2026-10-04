import React, { useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import { adminApi } from "../services/adminApi"
import { AdminTable, type Column } from "../components/AdminTable"
import type { AdminSupportTicketItem } from "../types"

export const AdminSupport: React.FC = () => {
  const { ticketId } = useParams<{ ticketId?: string }>()
  const [tickets, setTickets] = useState<AdminSupportTicketItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(15)
  const [statusFilter, setStatusFilter] = useState("")
  const [priorityFilter, setPriorityFilter] = useState("")
  const [loading, setLoading] = useState(true)

  // Ticket inspection & response modal
  const [selectedTicket, setSelectedTicket] = useState<any>(null)
  const [replyMessage, setReplyMessage] = useState("")
  const [isInternal, setIsInternal] = useState(false)
  const [submittingReply, setSubmittingReply] = useState(false)

  useEffect(() => {
    loadTickets()
    if (ticketId) {
      handleOpenTicket(ticketId)
    }
  }, [page, statusFilter, priorityFilter, ticketId])

  const loadTickets = async () => {
    try {
      setLoading(true)
      const res = await adminApi.getSupportTickets({
        page,
        page_size: pageSize,
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
      })
      setTickets(res.tickets || [])
      setTotal(res.total || 0)
    } catch (err) {
      console.error("Failed to load support tickets:", err)
    } finally {
      setLoading(false)
    }
  }

  const handleOpenTicket = async (ticketId: string) => {
    try {
      const detail = await adminApi.getSupportTicketDetail(ticketId)
      setSelectedTicket(detail)
      setReplyMessage("")
    } catch (err: any) {
      alert(err.message || "Failed to load ticket details")
    }
  }

  const handleSendReply = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedTicket || !replyMessage.trim()) return

    try {
      setSubmittingReply(true)
      const updated = await adminApi.replySupportTicket(selectedTicket.id, replyMessage, isInternal)
      setSelectedTicket(updated)
      setReplyMessage("")
      loadTickets()
    } catch (err: any) {
      alert(err.message || "Failed to post agent reply")
    } finally {
      setSubmittingReply(false)
    }
  }

  const handleUpdateStatus = async (status: string) => {
    if (!selectedTicket) return
    try {
      const updated = await adminApi.updateSupportTicketStatus(selectedTicket.id, status)
      setSelectedTicket(updated)
      loadTickets()
    } catch (err: any) {
      alert(err.message || "Failed to update ticket status")
    }
  }

  const columns: Column<AdminSupportTicketItem>[] = [
    {
      key: "ticket_number",
      header: "Ticket #",
      render: (t) => (
        <span style={{ fontFamily: "monospace", fontWeight: 700, color: "#6366f1" }}>
          {t.ticket_number}
        </span>
      ),
      width: "140px",
    },
    {
      key: "subject",
      header: "Subject / Query",
      render: (t) => (
        <div>
          <span style={{ fontWeight: 600, color: "#f8fafc" }}>{t.subject}</span>
          <div style={{ fontSize: "0.75rem", color: "#64748b" }}>Category: {t.category}</div>
        </div>
      ),
    },
    {
      key: "priority",
      header: "Priority",
      render: (t) => {
        const p = (t.priority || "").toLowerCase()
        return (
          <span
            className={`admin-badge ${
              p === "urgent" || p === "high"
                ? "admin-badge-danger"
                : p === "medium"
                ? "admin-badge-warning"
                : "admin-badge-info"
            }`}
          >
            {t.priority}
          </span>
        )
      },
      width: "120px",
    },
    {
      key: "status",
      header: "Status",
      render: (t) => {
        const s = (t.status || "").toLowerCase()
        return (
          <span
            className={`admin-badge ${
              s === "resolved" || s === "closed"
                ? "admin-badge-success"
                : s === "in_progress"
                ? "admin-badge-info"
                : "admin-badge-warning"
            }`}
          >
            {t.status.replace("_", " ")}
          </span>
        )
      },
      width: "130px",
    },
    {
      key: "created_at",
      header: "Opened",
      render: (t) => (
        <span style={{ color: "#94a3b8", fontSize: "0.825rem" }}>
          {new Date(t.created_at).toLocaleDateString()}
        </span>
      ),
      width: "130px",
    },
    {
      key: "actions",
      header: "Action",
      render: (t) => (
        <button
          onClick={() => handleOpenTicket(t.id)}
          className="admin-btn admin-btn-secondary"
          style={{ padding: "0.3rem 0.65rem", fontSize: "0.75rem" }}
        >
          Open Case
        </button>
      ),
      width: "120px",
    },
  ]

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Candidate Support & Help Desk</h1>
          <p className="admin-page-subtitle">
            Manage incoming assistance requests, SLA adherence, and internal support dialogue
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
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value)
              setPage(1)
            }}
            className="admin-select"
          >
            <option value="">All Statuses</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="waiting_user">Waiting on Candidate</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </select>

          <select
            value={priorityFilter}
            onChange={(e) => {
              setPriorityFilter(e.target.value)
              setPage(1)
            }}
            className="admin-select"
          >
            <option value="">All Priorities</option>
            <option value="urgent">Urgent</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>

      <AdminTable
        columns={columns}
        data={tickets}
        loading={loading}
        total={total}
        page={page}
        pageSize={pageSize}
        onPageChange={(p) => setPage(p)}
      />

      {/* Case Resolver Modal */}
      {selectedTicket && (
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
              maxWidth: "760px",
              maxHeight: "85vh",
              overflowY: "auto",
              padding: "2rem",
              color: "#f8fafc",
              display: "flex",
              flexDirection: "column",
              gap: "1.25rem",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <span style={{ fontFamily: "monospace", color: "#6366f1", fontWeight: 700 }}>
                  {selectedTicket.ticket_number}
                </span>
                <h3 style={{ fontSize: "1.25rem", fontWeight: 700, marginTop: "0.25rem" }}>
                  {selectedTicket.subject}
                </h3>
              </div>
              <button
                onClick={() => setSelectedTicket(null)}
                className="admin-btn admin-btn-secondary"
                style={{ padding: "0.3rem 0.6rem" }}
              >
                ✕
              </button>
            </div>

            {/* Status change toolbar */}
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", background: "rgba(0,0,0,0.25)", padding: "0.75rem", borderRadius: "8px" }}>
              <span style={{ fontSize: "0.8rem", color: "#94a3b8" }}>Change Ticket Status:</span>
              {["open", "in_progress", "waiting_user", "resolved", "closed"].map((st) => (
                <button
                  key={st}
                  onClick={() => handleUpdateStatus(st)}
                  className="admin-btn"
                  style={{
                    padding: "0.25rem 0.6rem",
                    fontSize: "0.75rem",
                    background: selectedTicket.status === st ? "#6366f1" : "rgba(255,255,255,0.05)",
                    color: selectedTicket.status === st ? "#ffffff" : "#94a3b8",
                    border: "1px solid rgba(255,255,255,0.1)",
                  }}
                >
                  {st.replace("_", " ")}
                </button>
              ))}
            </div>

            {/* Conversation thread */}
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", maxHeight: "280px", overflowY: "auto", padding: "0.5rem" }}>
              {(selectedTicket.messages || []).map((m: any) => {
                const isAdmin = m.sender_type === "admin"
                const isInternalNote = m.is_internal

                return (
                  <div
                    key={m.id}
                    style={{
                      padding: "0.75rem 1rem",
                      borderRadius: "10px",
                      background: isInternalNote
                        ? "rgba(245, 158, 11, 0.15)"
                        : isAdmin
                        ? "rgba(99, 102, 241, 0.15)"
                        : "rgba(255, 255, 255, 0.04)",
                      border: isInternalNote
                        ? "1px solid rgba(245, 158, 11, 0.3)"
                        : "1px solid rgba(255, 255, 255, 0.06)",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                      <span style={{ fontWeight: 600, color: isInternalNote ? "#fbbf24" : isAdmin ? "#818cf8" : "#f8fafc" }}>
                        {isInternalNote ? "🔒 Internal Staff Note" : isAdmin ? "Staff Specialist" : "Candidate"}
                      </span>
                      <span>{new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                    </div>
                    <p style={{ fontSize: "0.85rem", lineHeight: 1.5, color: "#cbd5e1" }}>
                      {m.message}
                    </p>
                  </div>
                )
              })}
            </div>

            {/* Reply Input Form */}
            <form onSubmit={handleSendReply} style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <textarea
                required
                rows={3}
                placeholder="Type your official reply or internal note..."
                value={replyMessage}
                onChange={(e) => setReplyMessage(e.target.value)}
                className="admin-input"
                style={{ width: "100%", resize: "vertical" }}
              />
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.825rem", color: "#fbbf24", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={isInternal}
                    onChange={(e) => setIsInternal(e.target.checked)}
                  />
                  Internal Note (Visible to Admins only)
                </label>
                <button
                  type="submit"
                  disabled={submittingReply}
                  className="admin-btn admin-btn-primary"
                >
                  {submittingReply ? "Posting..." : isInternal ? "Post Internal Note" : "Send Candidate Reply"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
export default AdminSupport
