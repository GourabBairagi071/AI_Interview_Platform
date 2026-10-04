import React, { useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import { adminApi } from "../services/adminApi"
import { AdminTable, type Column } from "../components/AdminTable"
import { SearchIcon } from "../components/AdminIcons"
import type { AdminInterviewItem } from "../types"

export const AdminInterviews: React.FC = () => {
  const { interviewId, id } = useParams<{ interviewId?: string; id?: string }>()
  const targetInterviewId = interviewId || id
  const [interviews, setInterviews] = useState<AdminInterviewItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(15)
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState("")
  const [loading, setLoading] = useState(true)

  // Inspection modal
  const [selectedInterview, setSelectedInterview] = useState<any>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  useEffect(() => {
    loadInterviews()
    if (targetInterviewId) {
      handleInspect(targetInterviewId)
    }
  }, [page, statusFilter, targetInterviewId])

  const loadInterviews = async () => {
    try {
      setLoading(true)
      const res = await adminApi.getInterviews({
        page,
        page_size: pageSize,
        search: search.trim() || undefined,
        status: statusFilter || undefined,
      })
      setInterviews(res.interviews || [])
      setTotal(res.total || 0)
    } catch (err) {
      console.error("Failed to load interviews:", err)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    loadInterviews()
  }

  const handleInspect = async (interviewId: string) => {
    try {
      setDetailLoading(true)
      const detail = await adminApi.getInterviewDetail(interviewId)
      setSelectedInterview(detail)
    } catch (err: any) {
      alert(err.message || "Failed to load interview details")
    } finally {
      setDetailLoading(false)
    }
  }

  const columns: Column<AdminInterviewItem>[] = [
    {
      key: "candidate",
      header: "Candidate",
      render: (i) => (
        <div style={{ display: "flex", flexDirection: "column" }}>
          <span style={{ fontWeight: 600, color: "#f8fafc" }}>{i.user_name || "Anonymous Candidate"}</span>
          <span style={{ fontSize: "0.75rem", color: "#64748b" }}>{i.user_email || i.user_id}</span>
        </div>
      ),
    },
    {
      key: "job_role",
      header: "Target Role",
      render: (i) => (
        <div>
          <span style={{ fontWeight: 500, color: "#cbd5e1" }}>{i.job_role}</span>
          <span style={{ marginLeft: "0.5rem", fontSize: "0.72rem", color: "#94a3b8" }}>
            ({i.difficulty})
          </span>
        </div>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (i) => (
        <span
          className={`admin-badge ${
            i.status === "completed"
              ? "admin-badge-success"
              : i.status === "in_progress"
              ? "admin-badge-warning"
              : "admin-badge-info"
          }`}
        >
          {i.status}
        </span>
      ),
    },
    {
      key: "score",
      header: "Score",
      render: (i) => (
        <span
          style={{
            fontWeight: 700,
            color: i.score === null ? "#64748b" : i.score >= 7 ? "#34d399" : i.score >= 5 ? "#fbbf24" : "#f87171",
          }}
        >
          {i.score !== null ? `${i.score}/10` : "Pending"}
        </span>
      ),
    },
    {
      key: "created_at",
      header: "Date",
      render: (i) => (
        <span style={{ color: "#94a3b8", fontSize: "0.8rem" }}>
          {new Date(i.created_at).toLocaleDateString()}
        </span>
      ),
    },
    {
      key: "actions",
      header: "Audit",
      render: (i) => (
        <button
          onClick={() => handleInspect(i.id)}
          className="admin-btn admin-btn-secondary"
          style={{ padding: "0.3rem 0.65rem", fontSize: "0.75rem" }}
        >
          Inspect Session
        </button>
      ),
    },
  ]

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Adaptive AI Interviews</h1>
          <p className="admin-page-subtitle">
            Audit live, completed, and evaluated candidate interview sessions
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
        <form onSubmit={handleSearch} style={{ display: "flex", gap: "0.5rem", flex: "1 1 300px" }}>
          <div style={{ position: "relative", width: "100%", maxWidth: "380px" }}>
            <input
              type="text"
              placeholder="Search by job role or candidate email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
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
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value)
            setPage(1)
          }}
          className="admin-select"
        >
          <option value="">All Statuses</option>
          <option value="completed">Completed</option>
          <option value="in_progress">In Progress</option>
          <option value="pending">Pending</option>
        </select>
      </div>

      <AdminTable
        columns={columns}
        data={interviews}
        loading={loading}
        total={total}
        page={page}
        pageSize={pageSize}
        onPageChange={(p) => setPage(p)}
      />

      {/* Inspection Modal */}
      {selectedInterview && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.8)",
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
              maxWidth: "750px",
              maxHeight: "85vh",
              overflowY: "auto",
              padding: "2rem",
              color: "#f8fafc",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1.5rem" }}>
              <div>
                <h3 style={{ fontSize: "1.35rem", fontWeight: 700 }}>
                  {selectedInterview.job_role} Interview Audit
                </h3>
                <p style={{ color: "#94a3b8", fontSize: "0.85rem" }}>
                  ID: {selectedInterview.id} • Candidate: {selectedInterview.user_email || selectedInterview.user_id}
                </p>
              </div>
              <button
                onClick={() => setSelectedInterview(null)}
                className="admin-btn admin-btn-secondary"
                style={{ padding: "0.3rem 0.6rem" }}
              >
                ✕
              </button>
            </div>

            <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem" }}>
              <div style={{ padding: "0.75rem", background: "rgba(255,255,255,0.03)", borderRadius: "8px", flex: 1 }}>
                <span style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Final Score</span>
                <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "#34d399" }}>
                  {selectedInterview.score !== null ? `${selectedInterview.score} / 10` : "N/A"}
                </div>
              </div>
              <div style={{ padding: "0.75rem", background: "rgba(255,255,255,0.03)", borderRadius: "8px", flex: 1 }}>
                <span style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Difficulty</span>
                <div style={{ fontSize: "1.1rem", fontWeight: 600 }}>{selectedInterview.difficulty}</div>
              </div>
              <div style={{ padding: "0.75rem", background: "rgba(255,255,255,0.03)", borderRadius: "8px", flex: 1 }}>
                <span style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Status</span>
                <div style={{ fontSize: "1.1rem", fontWeight: 600, color: "#6366f1" }}>{selectedInterview.status}</div>
              </div>
            </div>

            {selectedInterview.feedback && (
              <div style={{ marginBottom: "1.5rem" }}>
                <h4 style={{ fontSize: "0.95rem", color: "#a5b4fc", marginBottom: "0.5rem" }}>
                  AI Synthesized Feedback & Evaluation
                </h4>
                <div style={{ padding: "1rem", background: "rgba(0,0,0,0.3)", borderRadius: "8px", fontSize: "0.875rem", lineHeight: 1.6, color: "#cbd5e1" }}>
                  {selectedInterview.feedback}
                </div>
              </div>
            )}

            {selectedInterview.transcript && (
              <div>
                <h4 style={{ fontSize: "0.95rem", color: "#a5b4fc", marginBottom: "0.5rem" }}>
                  Live Dialogue Transcript
                </h4>
                <pre
                  style={{
                    padding: "1rem",
                    background: "rgba(0,0,0,0.4)",
                    borderRadius: "8px",
                    fontSize: "0.8rem",
                    color: "#94a3b8",
                    whiteSpace: "pre-wrap",
                    maxHeight: "220px",
                    overflowY: "auto",
                  }}
                >
                  {selectedInterview.transcript}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
export default AdminInterviews
