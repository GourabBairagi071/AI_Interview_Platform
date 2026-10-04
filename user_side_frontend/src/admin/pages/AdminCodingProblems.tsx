import React, { useEffect, useState } from "react"
import { adminApi } from "../services/adminApi"
import { AdminTable, type Column } from "../components/AdminTable"
import { SearchIcon } from "../components/AdminIcons"

export const AdminCodingProblems: React.FC = () => {
  const [problems, setProblems] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(15)
  const [search, setSearch] = useState("")
  const [diffFilter, setDiffFilter] = useState("")
  const [topicFilter, setTopicFilter] = useState("")
  const [loading, setLoading] = useState(true)

  // Inspection modal
  const [selectedProblem, setSelectedProblem] = useState<any>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)

  useEffect(() => {
    loadProblems()
  }, [page, diffFilter, topicFilter])

  const loadProblems = async () => {
    try {
      setLoading(true)
      const res = await adminApi.getCodingProblems({
        page,
        page_size: pageSize,
        difficulty: diffFilter || undefined,
        topic: topicFilter || undefined,
        search: search.trim() || undefined,
      })
      setProblems(res.problems || [])
      setTotal(res.total || 0)
    } catch (err) {
      console.error("Failed to load coding problems:", err)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    loadProblems()
  }

  const handleInspectProblem = async (problemId: string) => {
    try {
      setLoadingDetail(true)
      const detail = await adminApi.getCodingProblemDetail(problemId)
      setSelectedProblem(detail)
    } catch (err: any) {
      alert(err.message || "Failed to load problem detail")
    } finally {
      setLoadingDetail(false)
    }
  }

  const columns: Column<any>[] = [
    {
      key: "id",
      header: "ID",
      render: (p) => (
        <span style={{ fontFamily: "monospace", color: "#6366f1", fontSize: "0.8rem" }}>
          {p.id}
        </span>
      ),
      width: "90px",
    },
    {
      key: "title",
      header: "Problem Title",
      render: (p) => (
        <div style={{ color: "#f8fafc", fontWeight: 600 }}>{p.title}</div>
      ),
    },
    {
      key: "difficulty",
      header: "Difficulty",
      render: (p) => {
        const d = (p.difficulty || "").toLowerCase()
        return (
          <span
            className={`admin-badge ${
              d === "easy"
                ? "admin-badge-success"
                : d === "hard"
                ? "admin-badge-danger"
                : "admin-badge-warning"
            }`}
          >
            {p.difficulty}
          </span>
        )
      },
      width: "120px",
    },
    {
      key: "topic",
      header: "Algorithm Domain",
      render: (p) => (
        <span className="admin-badge admin-badge-info">{p.topic}</span>
      ),
      width: "180px",
    },
    {
      key: "acceptance_rate",
      header: "Acceptance",
      render: (p) => (
        <span style={{ color: "#94a3b8", fontSize: "0.85rem" }}>
          {p.acceptance_rate ? `${p.acceptance_rate}%` : "—"}
        </span>
      ),
      width: "110px",
    },
    {
      key: "actions",
      header: "Actions",
      render: (p) => (
        <button
          onClick={() => handleInspectProblem(p.id)}
          className="admin-btn admin-btn-secondary"
          style={{ padding: "0.3rem 0.65rem", fontSize: "0.75rem" }}
        >
          View Specs
        </button>
      ),
      width: "130px",
    },
  ]

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">1,000 Coding Arena Problems</h1>
          <p className="admin-page-subtitle">
            Inspect algorithmic test suites, reference solutions, and acceptance rates
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
              placeholder="Search problem title..."
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

        <div style={{ display: "flex", gap: "0.75rem" }}>
          <select
            value={diffFilter}
            onChange={(e) => {
              setDiffFilter(e.target.value)
              setPage(1)
            }}
            className="admin-select"
          >
            <option value="">All Difficulties</option>
            <option value="Easy">Easy</option>
            <option value="Medium">Medium</option>
            <option value="Hard">Hard</option>
          </select>
        </div>
      </div>

      <AdminTable
        columns={columns}
        data={problems}
        loading={loading}
        total={total}
        page={page}
        pageSize={pageSize}
        onPageChange={(p) => setPage(p)}
      />

      {/* Detail Modal */}
      {selectedProblem && (
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
              maxWidth: "800px",
              maxHeight: "85vh",
              overflowY: "auto",
              padding: "2rem",
              color: "#f8fafc",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1.5rem" }}>
              <div>
                <h3 style={{ fontSize: "1.35rem", fontWeight: 700 }}>
                  {selectedProblem.title}
                </h3>
                <span className="admin-badge admin-badge-info" style={{ marginTop: "0.25rem" }}>
                  {selectedProblem.difficulty} • {selectedProblem.topic}
                </span>
              </div>
              <button
                onClick={() => setSelectedProblem(null)}
                className="admin-btn admin-btn-secondary"
                style={{ padding: "0.3rem 0.6rem" }}
              >
                ✕
              </button>
            </div>

            <div style={{ marginBottom: "1.5rem" }}>
              <h4 style={{ fontSize: "0.95rem", color: "#a5b4fc", marginBottom: "0.5rem" }}>
                Problem Description
              </h4>
              <div style={{ padding: "1rem", background: "rgba(0,0,0,0.3)", borderRadius: "8px", fontSize: "0.875rem", lineHeight: 1.6, color: "#cbd5e1" }}>
                {selectedProblem.description}
              </div>
            </div>

            {selectedProblem.starter_code && (
              <div style={{ marginBottom: "1.5rem" }}>
                <h4 style={{ fontSize: "0.95rem", color: "#a5b4fc", marginBottom: "0.5rem" }}>
                  Starter Code
                </h4>
                <pre style={{ padding: "1rem", background: "rgba(0,0,0,0.4)", borderRadius: "8px", fontSize: "0.8rem", color: "#38bdf8", overflowX: "auto" }}>
                  {selectedProblem.starter_code}
                </pre>
              </div>
            )}

            {selectedProblem.solution && (
              <div>
                <h4 style={{ fontSize: "0.95rem", color: "#34d399", marginBottom: "0.5rem" }}>
                  Canonical Reference Solution
                </h4>
                <pre style={{ padding: "1rem", background: "rgba(0,0,0,0.4)", borderRadius: "8px", fontSize: "0.8rem", color: "#34d399", overflowX: "auto" }}>
                  {selectedProblem.solution}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
export default AdminCodingProblems
