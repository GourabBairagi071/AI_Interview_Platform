import React, { useEffect, useState } from "react"
import { adminApi } from "../services/adminApi"
import { AdminTable, type Column } from "../components/AdminTable"
import { ContestIcon } from "../components/AdminIcons"

export const AdminContests: React.FC = () => {
  const [contests, setContests] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(15)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadContests()
  }, [page])

  const loadContests = async () => {
    try {
      setLoading(true)
      const res = await adminApi.getContests({ page, page_size: pageSize })
      setContests(res.contests || [])
      setTotal(res.total || 0)
    } catch (err) {
      console.error("Failed to load contests:", err)
    } finally {
      setLoading(false)
    }
  }

  const columns: Column<any>[] = [
    {
      key: "title",
      header: "Contest Tournament",
      render: (c) => (
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <ContestIcon size={18} className="text-yellow-400" />
          <div>
            <span style={{ fontWeight: 600, color: "#f8fafc" }}>{c.title}</span>
            <div style={{ fontSize: "0.75rem", color: "#64748b" }}>Slug: {c.slug}</div>
          </div>
        </div>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (c) => {
        const s = (c.status || "").toLowerCase()
        return (
          <span
            className={`admin-badge ${
              s === "active" || s === "ongoing"
                ? "admin-badge-success"
                : s === "upcoming"
                ? "admin-badge-info"
                : "admin-badge-secondary"
            }`}
          >
            {c.status}
          </span>
        )
      },
      width: "130px",
    },
    {
      key: "duration_minutes",
      header: "Duration",
      render: (c) => (
        <span style={{ color: "#cbd5e1", fontSize: "0.85rem" }}>
          {c.duration_minutes} mins
        </span>
      ),
      width: "120px",
    },
    {
      key: "participant_count",
      header: "Participants",
      render: (c) => (
        <span style={{ fontWeight: 600, color: "#38bdf8" }}>
          {c.participant_count || 0} enrolled
        </span>
      ),
      width: "140px",
    },
    {
      key: "start_time",
      header: "Start Schedule",
      render: (c) => (
        <span style={{ color: "#94a3b8", fontSize: "0.825rem" }}>
          {new Date(c.start_time).toLocaleString()}
        </span>
      ),
      width: "180px",
    },
  ]

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Competitive Contests & Tournaments</h1>
          <p className="admin-page-subtitle">
            Oversee competitive coding arenas, live leaderboards, and scheduled tournaments
          </p>
        </div>
      </div>

      <AdminTable
        columns={columns}
        data={contests}
        loading={loading}
        total={total}
        page={page}
        pageSize={pageSize}
        onPageChange={(p) => setPage(p)}
      />
    </div>
  )
}
export default AdminContests
