import React, { useEffect, useState } from "react"
import { adminApi } from "../services/adminApi"
import { AdminTable, type Column } from "../components/AdminTable"
import type { AdminFeedbackItem } from "../types"

export const AdminFeedback: React.FC = () => {
  const [feedbackList, setFeedbackList] = useState<AdminFeedbackItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(15)
  const [statusFilter, setStatusFilter] = useState("")
  const [loading, setLoading] = useState(true)

  // Status modal
  const [selectedFeedback, setSelectedFeedback] = useState<AdminFeedbackItem | null>(null)
  const [newStatus, setNewStatus] = useState("reviewed")
  const [notes, setNotes] = useState("")
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadFeedback()
  }, [page, statusFilter])

  const loadFeedback = async () => {
    try {
      setLoading(true)
      const res = await adminApi.getFeedback({
        page,
        page_size: pageSize,
        status: statusFilter || undefined,
      })
      setFeedbackList(res.feedback || [])
      setTotal(res.total || 0)
    } catch (err) {
      console.error("Failed to load feedback:", err)
    } finally {
      setLoading(false)
    }
  }

  const handleUpdateStatus = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedFeedback) return

    try {
      setSaving(true)
      await adminApi.updateFeedbackStatus(selectedFeedback.id, newStatus, notes)
      setSelectedFeedback(null)
      loadFeedback()
    } catch (err: any) {
      alert(err.message || "Failed to update feedback status")
    } finally {
      setSaving(false)
    }
  }

  const columns: Column<AdminFeedbackItem>[] = [
    {
      key: "candidate",
      header: "Candidate",
      render: (f) => (
        <span style={{ color: "#cbd5e1", fontSize: "0.85rem" }}>
          {f.user_email || f.user_id}
        </span>
      ),
    },
    {
      key: "category",
      header: "Domain",
      render: (f) => (
        <span className="admin-badge admin-badge-info">{f.category}</span>
      ),
      width: "140px",
    },
    {
      key: "rating",
      header: "Satisfaction",
      render: (f) => (
        <span style={{ fontWeight: 700, color: f.rating >= 4 ? "#34d399" : f.rating === 3 ? "#fbbf24" : "#f87171" }}>
          {"★".repeat(f.rating || 0)} ({f.rating || 0}/5)
        </span>
      ),
      width: "140px",
    },
    {
      key: "feedback_text",
      header: "Candidate Remarks",
      render: (f) => (
        <div style={{ color: "#f8fafc", lineHeight: 1.4, fontSize: "0.85rem" }}>
          {f.feedback_text}
        </div>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (f) => (
        <span
          className={`admin-badge ${
            f.status === "resolved"
              ? "admin-badge-success"
              : f.status === "reviewed"
              ? "admin-badge-info"
              : "admin-badge-warning"
          }`}
        >
          {f.status}
        </span>
      ),
      width: "120px",
    },
    {
      key: "actions",
      header: "Action",
      render: (f) => (
        <button
          onClick={() => {
            setSelectedFeedback(f)
            setNewStatus(f.status || "reviewed")
            setNotes("")
          }}
          className="admin-btn admin-btn-secondary"
          style={{ padding: "0.3rem 0.65rem", fontSize: "0.75rem" }}
        >
          Acknowledge
        </button>
      ),
      width: "130px",
    },
  ]

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Candidate Sentiment & Bug Reports</h1>
          <p className="admin-page-subtitle">
            Analyze feedback ratings, user complaints, and reported platform glitches
          </p>
        </div>
      </div>

      <div
        className="admin-card"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "1rem",
        }}
      >
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value)
            setPage(1)
          }}
          className="admin-select"
        >
          <option value="">All Feedback Statuses</option>
          <option value="pending">Pending</option>
          <option value="reviewed">Reviewed</option>
          <option value="resolved">Resolved</option>
        </select>
      </div>

      <AdminTable
        columns={columns}
        data={feedbackList}
        loading={loading}
        total={total}
        page={page}
        pageSize={pageSize}
        onPageChange={(p) => setPage(p)}
      />

      {/* Modal */}
      {selectedFeedback && (
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
            padding: "1rem",
          }}
        >
          <form
            onSubmit={handleUpdateStatus}
            style={{
              background: "#1e293b",
              border: "1px solid rgba(255, 255, 255, 0.12)",
              borderRadius: "16px",
              width: "100%",
              maxWidth: "520px",
              padding: "2rem",
              color: "#f8fafc",
            }}
          >
            <h3 style={{ fontSize: "1.25rem", fontWeight: 700, marginBottom: "0.5rem" }}>
              Acknowledge Candidate Feedback
            </h3>
            <p style={{ color: "#94a3b8", fontSize: "0.85rem", marginBottom: "1.25rem" }}>
              Update resolution status and internal notes for this item.
            </p>

            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                Resolution State
              </label>
              <select
                value={newStatus}
                onChange={(e) => setNewStatus(e.target.value)}
                className="admin-select"
                style={{ width: "100%" }}
              >
                <option value="pending">Pending</option>
                <option value="reviewed">Reviewed</option>
                <option value="resolved">Resolved</option>
              </select>
            </div>

            <div style={{ marginBottom: "1.5rem" }}>
              <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                Resolution Notes
              </label>
              <textarea
                rows={3}
                placeholder="Action taken or bug ticket reference..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="admin-input"
                style={{ width: "100%", resize: "vertical" }}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem" }}>
              <button
                type="button"
                onClick={() => setSelectedFeedback(null)}
                className="admin-btn admin-btn-secondary"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="admin-btn admin-btn-primary"
              >
                {saving ? "Saving..." : "Commit Update"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
export default AdminFeedback
