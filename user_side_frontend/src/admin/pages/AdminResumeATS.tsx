import React, { useEffect, useState } from "react"
import { adminApi } from "../services/adminApi"
import { AdminTable, type Column } from "../components/AdminTable"
import { SearchIcon, ResumeIcon } from "../components/AdminIcons"

export const AdminResumeATS: React.FC = () => {
  const [resumes, setResumes] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(15)
  const [search, setSearch] = useState("")
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadResumes()
  }, [page])

  const loadResumes = async () => {
    try {
      setLoading(true)
      const res = await adminApi.getResumes({
        page,
        page_size: pageSize,
        search: search.trim() || undefined,
      })
      setResumes(res.resumes || [])
      setTotal(res.total || 0)
    } catch (err) {
      console.error("Failed to load resumes:", err)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    loadResumes()
  }

  const columns: Column<any>[] = [
    {
      key: "candidate",
      header: "Candidate",
      render: (r) => (
        <div>
          <span style={{ fontWeight: 600, color: "#f8fafc" }}>{r.user_name || "Candidate"}</span>
          <div style={{ fontSize: "0.75rem", color: "#64748b" }}>{r.user_email}</div>
        </div>
      ),
    },
    {
      key: "filename",
      header: "Resume File",
      render: (r) => (
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <ResumeIcon size={16} className="text-slate-400" />
          <span style={{ color: "#cbd5e1" }}>{r.filename}</span>
        </div>
      ),
    },
    {
      key: "uploaded_at",
      header: "Uploaded At",
      render: (r) => (
        <span style={{ color: "#94a3b8", fontSize: "0.825rem" }}>
          {new Date(r.uploaded_at).toLocaleString()}
        </span>
      ),
    },
    {
      key: "file_url",
      header: "Document URL",
      render: (r) => (
        <a
          href={r.file_url}
          target="_blank"
          rel="noreferrer"
          className="admin-btn admin-btn-secondary"
          style={{ padding: "0.25rem 0.6rem", fontSize: "0.75rem", textDecoration: "none" }}
        >
          Open Document
        </a>
      ),
    },
  ]

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Resume & ATS Intelligence</h1>
          <p className="admin-page-subtitle">
            Inspect uploaded candidate resumes, parsed tech stacks, and ATS compatibility pipelines
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
              placeholder="Search by candidate email or filename..."
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
      </div>

      <AdminTable
        columns={columns}
        data={resumes}
        loading={loading}
        total={total}
        page={page}
        pageSize={pageSize}
        onPageChange={(p) => setPage(p)}
      />
    </div>
  )
}
export default AdminResumeATS
