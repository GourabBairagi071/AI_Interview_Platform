import React, { useEffect, useState } from "react"
import { adminApi } from "../services/adminApi"
import { AdminTable, type Column } from "../components/AdminTable"
import { AdminConfirmModal } from "../components/AdminConfirmModal"
import { PlusIcon, SearchIcon } from "../components/AdminIcons"

export const AdminAssignments: React.FC = () => {
  const [assignments, setAssignments] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(15)
  const [loading, setLoading] = useState(true)

  // Filters
  const [search, setSearch] = useState("")
  const [typeFilter, setTypeFilter] = useState("")
  const [statusFilter, setStatusFilter] = useState("")

  // Analytics summary
  const [analytics, setAnalytics] = useState<any>(null)

  // Create Assignment Modal
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [formData, setFormData] = useState({
    title: "",
    description: "",
    assignment_type: "CODING_PROBLEM",
    content_id: "",
    instructions: "",
    priority: "MEDIUM",
    target_type: "INDIVIDUAL",
    target_candidate_email: "",
    target_skill: "Python",
    target_role: "CANDIDATE",
    target_tier: "PRO",
    due_date: "",
    time_limit_mins: 60,
    attempt_limit: 1,
  })

  // Candidate options for autocomplete
  const [candidates, setCandidates] = useState<any[]>([])

  // Recipient Drawer Modal
  const [detailModalOpen, setDetailModalOpen] = useState(false)
  const [activeDetail, setActiveDetail] = useState<any>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)

  // Status Action Modal
  const [statusModalOpen, setStatusModalOpen] = useState(false)
  const [selectedAssignment, setSelectedAssignment] = useState<any>(null)
  const [newStatusToApply, setNewStatusToApply] = useState("")
  const [updatingStatus, setUpdatingStatus] = useState(false)

  useEffect(() => {
    loadAssignments()
    loadAnalytics()
    loadCandidatesList()
  }, [page, typeFilter, statusFilter])

  const loadAssignments = async () => {
    try {
      setLoading(true)
      const res = await adminApi.getAssignments({
        page,
        page_size: pageSize,
        assignment_type: typeFilter || undefined,
        status: statusFilter || undefined,
        search: search.trim() || undefined,
      })
      setAssignments(res.assignments || [])
      setTotal(res.total || 0)
    } catch (err) {
      console.error("Failed to load assignments:", err)
    } finally {
      setLoading(false)
    }
  }

  const loadAnalytics = async () => {
    try {
      const data = await adminApi.getAssignmentAnalytics()
      setAnalytics(data)
    } catch (err) {
      console.error("Failed to load analytics:", err)
    }
  }

  const loadCandidatesList = async () => {
    try {
      const res = await adminApi.getUsers({ page: 1, page_size: 50, role: "CANDIDATE" })
      setCandidates(res.users || [])
    } catch (err) {
      console.error("Failed to load candidate list:", err)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    loadAssignments()
  }

  const handleOpenDetail = async (item: any) => {
    try {
      setDetailModalOpen(true)
      setLoadingDetail(true)
      const detail = await adminApi.getAssignmentDetail(item.id)
      setActiveDetail(detail)
    } catch (err: any) {
      alert(err.message || "Failed to load assignment telemetry")
      setDetailModalOpen(false)
    } finally {
      setLoadingDetail(false)
    }
  }

  const handleOpenStatusAction = (item: any, status: string) => {
    setSelectedAssignment(item)
    setNewStatusToApply(status)
    setStatusModalOpen(true)
  }

  const handleConfirmStatusChange = async () => {
    if (!selectedAssignment) return
    try {
      setUpdatingStatus(true)
      await adminApi.updateAssignmentStatus(selectedAssignment.id, newStatusToApply)
      setStatusModalOpen(false)
      loadAssignments()
      loadAnalytics()
    } catch (err: any) {
      alert(err.message || "Failed to update assignment status")
    } finally {
      setUpdatingStatus(false)
    }
  }

  const handleCreateAssignment = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.title.trim()) {
      alert("Assignment title is required.")
      return
    }

    try {
      setSaving(true)

      // Build target filter based on target_type
      const targetFilter: Record<string, any> = {}
      if (formData.target_type === "INDIVIDUAL") {
        const found = candidates.find(
          (c) => c.email.toLowerCase() === formData.target_candidate_email.trim().toLowerCase()
        )
        if (found) {
          targetFilter.candidate_id = found.id
        } else if (formData.target_candidate_email) {
          targetFilter.candidate_email = formData.target_candidate_email.trim()
        }
      } else if (formData.target_type === "SKILL") {
        targetFilter.skill = formData.target_skill.trim()
      } else if (formData.target_type === "ROLE") {
        targetFilter.role = formData.target_role
      } else if (formData.target_type === "SUBSCRIPTION_TIER") {
        targetFilter.tier = formData.target_tier
      }

      const payload = {
        title: formData.title.trim(),
        description: formData.description.trim() || undefined,
        assignment_type: formData.assignment_type,
        content_id: formData.content_id.trim() || undefined,
        instructions: formData.instructions.trim() || undefined,
        priority: formData.priority,
        target_type: formData.target_type,
        target_filter: targetFilter,
        due_date: formData.due_date ? new Date(formData.due_date).toISOString() : undefined,
        time_limit_mins: formData.time_limit_mins ? Number(formData.time_limit_mins) : undefined,
        attempt_limit: Number(formData.attempt_limit || 1),
      }

      await adminApi.createAssignment(payload)
      setCreateModalOpen(false)
      setFormData({
        title: "",
        description: "",
        assignment_type: "CODING_PROBLEM",
        content_id: "",
        instructions: "",
        priority: "MEDIUM",
        target_type: "INDIVIDUAL",
        target_candidate_email: "",
        target_skill: "Python",
        target_role: "CANDIDATE",
        target_tier: "PRO",
        due_date: "",
        time_limit_mins: 60,
        attempt_limit: 1,
      })
      loadAssignments()
      loadAnalytics()
    } catch (err: any) {
      alert(err.message || "Failed to create assignment")
    } finally {
      setSaving(false)
    }
  }

  const columns: Column<any>[] = [
    {
      key: "title",
      header: "Assignment & Description",
      render: (a) => (
        <div>
          <div style={{ fontWeight: 600, color: "#f8fafc", fontSize: "0.95rem" }}>
            {a.title}
          </div>
          {a.description && (
            <div style={{ fontSize: "0.8rem", color: "#94a3b8", marginTop: "0.2rem", maxWidth: "320px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {a.description}
            </div>
          )}
        </div>
      ),
    },
    {
      key: "assignment_type",
      header: "Type",
      render: (a) => {
        const typeColors: Record<string, string> = {
          QUESTION: "admin-badge-info",
          CODING_PROBLEM: "admin-badge-success",
          AI_INTERVIEW: "admin-badge-primary",
          INTERVIEW_TEMPLATE: "admin-badge-primary",
          RESOURCE: "admin-badge-warning",
          ROADMAP: "admin-badge-info",
          CONTEST: "admin-badge-danger",
          MOCK_TEST: "admin-badge-warning",
        }
        return (
          <span className={`admin-badge ${typeColors[a.assignment_type] || "admin-badge-secondary"}`}>
            {a.assignment_type.replace(/_/g, " ")}
          </span>
        )
      },
      width: "140px",
    },
    {
      key: "priority",
      header: "Priority",
      render: (a) => {
        const p = a.priority || "MEDIUM"
        return (
          <span
            className={`admin-badge ${
              p === "URGENT"
                ? "admin-badge-danger"
                : p === "HIGH"
                ? "admin-badge-warning"
                : p === "LOW"
                ? "admin-badge-secondary"
                : "admin-badge-info"
            }`}
          >
            {p}
          </span>
        )
      },
      width: "100px",
    },
    {
      key: "target_type",
      header: "Targeting",
      render: (a) => (
        <span style={{ fontSize: "0.825rem", color: "#cbd5e1" }}>
          {a.target_type} ({a.total_assigned || 0})
        </span>
      ),
      width: "120px",
    },
    {
      key: "progress",
      header: "Turnaround & Completion",
      render: (a) => (
        <div style={{ minWidth: "140px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", marginBottom: "0.25rem", color: "#cbd5e1" }}>
            <span>{a.total_completed} / {a.total_assigned} done</span>
            <span style={{ fontWeight: 600, color: a.completion_rate > 50 ? "#34d399" : "#fbbf24" }}>
              {a.completion_rate}%
            </span>
          </div>
          <div style={{ width: "100%", height: "6px", background: "rgba(255,255,255,0.1)", borderRadius: "3px", overflow: "hidden" }}>
            <div
              style={{
                width: `${a.completion_rate || 0}%`,
                height: "100%",
                background: a.completion_rate > 75 ? "#34d399" : a.completion_rate > 35 ? "#38bdf8" : "#fbbf24",
                borderRadius: "3px",
              }}
            />
          </div>
        </div>
      ),
      width: "180px",
    },
    {
      key: "due_date",
      header: "Due Date",
      render: (a) => (
        <span style={{ fontSize: "0.8rem", color: a.due_date ? "#94a3b8" : "#64748b" }}>
          {a.due_date ? new Date(a.due_date).toLocaleDateString() : "No deadline"}
        </span>
      ),
      width: "120px",
    },
    {
      key: "status",
      header: "Status",
      render: (a) => (
        <span
          className={`admin-badge ${
            a.status === "COMPLETED"
              ? "admin-badge-success"
              : a.status === "EXPIRED" || a.status === "ARCHIVED"
              ? "admin-badge-secondary"
              : a.status === "SCHEDULED"
              ? "admin-badge-warning"
              : "admin-badge-info"
          }`}
        >
          {a.status}
        </span>
      ),
      width: "110px",
    },
    {
      key: "actions",
      header: "Actions",
      render: (a) => (
        <div style={{ display: "flex", gap: "0.4rem" }}>
          <button
            onClick={() => handleOpenDetail(a)}
            className="admin-btn admin-btn-secondary"
            style={{ padding: "0.25rem 0.5rem", fontSize: "0.75rem" }}
          >
            Telemetry
          </button>
          {a.status === "ASSIGNED" && (
            <button
              onClick={() => handleOpenStatusAction(a, "ARCHIVED")}
              className="admin-btn admin-btn-secondary"
              style={{ padding: "0.25rem 0.5rem", fontSize: "0.75rem", color: "#f87171" }}
            >
              Archive
            </button>
          )}
        </div>
      ),
      width: "150px",
    },
  ]

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Header */}
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Candidate Assignments & Directed Tasks</h1>
          <p className="admin-page-subtitle">
            Target and dispatch coding problems, AI interviews, roadmaps, and practice sets to individual candidates or cohorts with due dates and progress tracking
          </p>
        </div>
        <button onClick={() => setCreateModalOpen(true)} className="admin-btn admin-btn-primary">
          <PlusIcon /> Create Assignment
        </button>
      </div>

      {/* KPI Summary Tiles */}
      {analytics && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "1rem" }}>
          <div className="admin-card" style={{ padding: "1.25rem" }}>
            <div style={{ fontSize: "0.8rem", color: "#94a3b8" }}>Total Assignments</div>
            <div style={{ fontSize: "1.75rem", fontWeight: 700, color: "#f8fafc", marginTop: "0.25rem" }}>
              {analytics.total_assignments}
            </div>
          </div>
          <div className="admin-card" style={{ padding: "1.25rem" }}>
            <div style={{ fontSize: "0.8rem", color: "#94a3b8" }}>Task Dispatches</div>
            <div style={{ fontSize: "1.75rem", fontWeight: 700, color: "#38bdf8", marginTop: "0.25rem" }}>
              {analytics.total_task_dispatches}
            </div>
          </div>
          <div className="admin-card" style={{ padding: "1.25rem" }}>
            <div style={{ fontSize: "0.8rem", color: "#94a3b8" }}>Completion Rate</div>
            <div style={{ fontSize: "1.75rem", fontWeight: 700, color: "#34d399", marginTop: "0.25rem" }}>
              {analytics.overall_completion_rate}%
            </div>
          </div>
          <div className="admin-card" style={{ padding: "1.25rem" }}>
            <div style={{ fontSize: "0.8rem", color: "#94a3b8" }}>Avg Score</div>
            <div style={{ fontSize: "1.75rem", fontWeight: 700, color: "#a855f7", marginTop: "0.25rem" }}>
              {analytics.avg_assignment_score !== null ? `${analytics.avg_assignment_score}%` : "—"}
            </div>
          </div>
        </div>
      )}

      {/* Filter Bar */}
      <div className="admin-card" style={{ padding: "1rem", display: "flex", gap: "1rem", alignItems: "center", flexWrap: "wrap" }}>
        <form onSubmit={handleSearch} style={{ display: "flex", gap: "0.5rem", flex: "1 1 250px" }}>
          <input
            type="text"
            placeholder="Search assignments by title..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="admin-input"
            style={{ width: "100%" }}
          />
          <button type="submit" className="admin-btn admin-btn-secondary">
            <SearchIcon />
          </button>
        </form>

        <select
          value={typeFilter}
          onChange={(e) => {
            setTypeFilter(e.target.value)
            setPage(1)
          }}
          className="admin-select"
          style={{ width: "180px" }}
        >
          <option value="">All Types</option>
          <option value="CODING_PROBLEM">Coding Problem</option>
          <option value="AI_INTERVIEW">AI Interview</option>
          <option value="INTERVIEW_TEMPLATE">Interview Template</option>
          <option value="QUESTION">Practice Question</option>
          <option value="RESOURCE">Learning Resource</option>
          <option value="ROADMAP">Roadmap</option>
          <option value="CONTEST">Contest</option>
          <option value="CUSTOM_TASK">Custom Task</option>
        </select>

        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value)
            setPage(1)
          }}
          className="admin-select"
          style={{ width: "150px" }}
        >
          <option value="">All Statuses</option>
          <option value="ASSIGNED">Assigned</option>
          <option value="SCHEDULED">Scheduled</option>
          <option value="COMPLETED">Completed</option>
          <option value="ARCHIVED">Archived</option>
        </select>
      </div>

      {/* Table */}
      <AdminTable
        columns={columns}
        data={assignments}
        loading={loading}
        total={total}
        page={page}
        pageSize={pageSize}
        onPageChange={(p) => setPage(p)}
      />

      {/* CREATE ASSIGNMENT MODAL */}
      {createModalOpen && (
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
            overflowY: "auto",
          }}
        >
          <form
            onSubmit={handleCreateAssignment}
            style={{
              background: "#1e293b",
              border: "1px solid rgba(255, 255, 255, 0.12)",
              borderRadius: "16px",
              width: "100%",
              maxWidth: "680px",
              padding: "2rem",
              color: "#f8fafc",
              maxHeight: "90vh",
              overflowY: "auto",
            }}
          >
            <h3 style={{ fontSize: "1.3rem", fontWeight: 700, marginBottom: "1.25rem" }}>
              Dispatch Candidate Assignment
            </h3>

            <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                  Assignment Title
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g., Week 2: Dynamic Programming & Binary Search"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="admin-input"
                  style={{ width: "100%" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                  Priority
                </label>
                <select
                  value={formData.priority}
                  onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                  className="admin-select"
                  style={{ width: "100%" }}
                >
                  <option value="LOW">Low</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="HIGH">High</option>
                  <option value="URGENT">Urgent</option>
                </select>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                  Assignment Type
                </label>
                <select
                  value={formData.assignment_type}
                  onChange={(e) => setFormData({ ...formData, assignment_type: e.target.value })}
                  className="admin-select"
                  style={{ width: "100%" }}
                >
                  <option value="CODING_PROBLEM">Coding Problem</option>
                  <option value="AI_INTERVIEW">AI Interview</option>
                  <option value="INTERVIEW_TEMPLATE">Interview Template</option>
                  <option value="QUESTION">Practice Question</option>
                  <option value="RESOURCE">Learning Resource</option>
                  <option value="ROADMAP">Roadmap Track</option>
                  <option value="CONTEST">Contest Assessment</option>
                  <option value="CUSTOM_TASK">Custom Task</option>
                </select>
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                  Content Reference ID / Slug
                </label>
                <input
                  type="text"
                  placeholder="e.g. two-sum or UUID"
                  value={formData.content_id}
                  onChange={(e) => setFormData({ ...formData, content_id: e.target.value })}
                  className="admin-input"
                  style={{ width: "100%" }}
                />
              </div>
            </div>

            {/* Targeting Selection */}
            <div style={{ background: "rgba(15, 23, 42, 0.6)", padding: "1rem", borderRadius: "10px", marginBottom: "1rem", border: "1px solid rgba(255,255,255,0.08)" }}>
              <div style={{ fontSize: "0.85rem", fontWeight: 600, color: "#38bdf8", marginBottom: "0.75rem" }}>
                Target Audience Resolution
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1.5fr", gap: "1rem" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                    Target Audience
                  </label>
                  <select
                    value={formData.target_type}
                    onChange={(e) => setFormData({ ...formData, target_type: e.target.value })}
                    className="admin-select"
                    style={{ width: "100%" }}
                  >
                    <option value="INDIVIDUAL">One Individual Candidate</option>
                    <option value="ROLE">All Candidates (Role)</option>
                    <option value="SKILL">By Skill Topic</option>
                    <option value="SUBSCRIPTION_TIER">By Subscription Tier</option>
                    <option value="ALL">All Eligible Candidates</option>
                  </select>
                </div>

                <div>
                  {formData.target_type === "INDIVIDUAL" && (
                    <div>
                      <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                        Candidate Email
                      </label>
                      <input
                        type="email"
                        required
                        placeholder="candidate@example.com"
                        value={formData.target_candidate_email}
                        onChange={(e) => setFormData({ ...formData, target_candidate_email: e.target.value })}
                        className="admin-input"
                        style={{ width: "100%" }}
                      />
                    </div>
                  )}

                  {formData.target_type === "SKILL" && (
                    <div>
                      <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                        Target Skill
                      </label>
                      <input
                        type="text"
                        placeholder="e.g., React, Python, System Design"
                        value={formData.target_skill}
                        onChange={(e) => setFormData({ ...formData, target_skill: e.target.value })}
                        className="admin-input"
                        style={{ width: "100%" }}
                      />
                    </div>
                  )}

                  {formData.target_type === "SUBSCRIPTION_TIER" && (
                    <div>
                      <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                        Subscription Plan Tier
                      </label>
                      <select
                        value={formData.target_tier}
                        onChange={(e) => setFormData({ ...formData, target_tier: e.target.value })}
                        className="admin-select"
                        style={{ width: "100%" }}
                      >
                        <option value="FREE">Free Tier</option>
                        <option value="PRO">Pro Tier</option>
                        <option value="ENTERPRISE">Enterprise Tier</option>
                      </select>
                    </div>
                  )}

                  {formData.target_type === "ROLE" && (
                    <div style={{ fontSize: "0.8rem", color: "#94a3b8", paddingTop: "1.5rem" }}>
                      Targeting all active candidates in the system.
                    </div>
                  )}

                  {formData.target_type === "ALL" && (
                    <div style={{ fontSize: "0.8rem", color: "#94a3b8", paddingTop: "1.5rem" }}>
                      Broadcasting to all eligible platform candidates.
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Dates & Constraints */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                  Due Date
                </label>
                <input
                  type="datetime-local"
                  value={formData.due_date}
                  onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                  className="admin-input"
                  style={{ width: "100%" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                  Time Limit (Mins)
                </label>
                <input
                  type="number"
                  min="5"
                  value={formData.time_limit_mins}
                  onChange={(e) => setFormData({ ...formData, time_limit_mins: parseInt(e.target.value) || 0 })}
                  className="admin-input"
                  style={{ width: "100%" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                  Attempt Limit
                </label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={formData.attempt_limit}
                  onChange={(e) => setFormData({ ...formData, attempt_limit: parseInt(e.target.value) || 1 })}
                  className="admin-input"
                  style={{ width: "100%" }}
                />
              </div>
            </div>

            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                Instructions / Mentor Guidance
              </label>
              <textarea
                rows={3}
                placeholder="Specific guidance, requirements, or focus areas for the candidate..."
                value={formData.instructions}
                onChange={(e) => setFormData({ ...formData, instructions: e.target.value })}
                className="admin-input"
                style={{ width: "100%", resize: "vertical" }}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "1.5rem" }}>
              <button
                type="button"
                onClick={() => setCreateModalOpen(false)}
                className="admin-btn admin-btn-secondary"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="admin-btn admin-btn-primary"
              >
                {saving ? "Dispatching..." : "Publish & Dispatch"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* RECIPIENT TELEMETRY DRAWER MODAL */}
      {detailModalOpen && (
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
          <div
            style={{
              background: "#1e293b",
              border: "1px solid rgba(255, 255, 255, 0.12)",
              borderRadius: "16px",
              width: "100%",
              maxWidth: "800px",
              padding: "2rem",
              color: "#f8fafc",
              maxHeight: "85vh",
              overflowY: "auto",
            }}
          >
            {loadingDetail || !activeDetail ? (
              <div style={{ textAlign: "center", padding: "3rem", color: "#94a3b8" }}>
                Loading recipient telemetry...
              </div>
            ) : (
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1.25rem" }}>
                  <div>
                    <h3 style={{ fontSize: "1.25rem", fontWeight: 700 }}>{activeDetail.title}</h3>
                    <div style={{ fontSize: "0.85rem", color: "#94a3b8", marginTop: "0.2rem" }}>
                      Type: <span style={{ color: "#38bdf8" }}>{activeDetail.assignment_type}</span> | Priority: <span style={{ color: "#f8fafc" }}>{activeDetail.priority}</span>
                    </div>
                  </div>
                  <button
                    onClick={() => setDetailModalOpen(false)}
                    className="admin-btn admin-btn-secondary"
                    style={{ padding: "0.3rem 0.6rem", fontSize: "0.8rem" }}
                  >
                    Close
                  </button>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0.75rem", marginBottom: "1.5rem" }}>
                  <div style={{ background: "rgba(15,23,42,0.6)", padding: "0.75rem", borderRadius: "8px" }}>
                    <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Assigned</div>
                    <div style={{ fontSize: "1.2rem", fontWeight: 700 }}>{activeDetail.total_assigned}</div>
                  </div>
                  <div style={{ background: "rgba(15,23,42,0.6)", padding: "0.75rem", borderRadius: "8px" }}>
                    <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Completed</div>
                    <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#34d399" }}>{activeDetail.total_completed}</div>
                  </div>
                  <div style={{ background: "rgba(15,23,42,0.6)", padding: "0.75rem", borderRadius: "8px" }}>
                    <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>In Progress</div>
                    <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#38bdf8" }}>{activeDetail.total_started}</div>
                  </div>
                  <div style={{ background: "rgba(15,23,42,0.6)", padding: "0.75rem", borderRadius: "8px" }}>
                    <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Avg Score</div>
                    <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#a855f7" }}>
                      {activeDetail.avg_score !== null ? `${activeDetail.avg_score}%` : "—"}
                    </div>
                  </div>
                </div>

                <h4 style={{ fontSize: "0.95rem", fontWeight: 600, marginBottom: "0.75rem", color: "#cbd5e1" }}>
                  Recipient Candidate Status
                </h4>

                <div style={{ maxHeight: "300px", overflowY: "auto", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "8px" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.825rem" }}>
                    <thead>
                      <tr style={{ background: "rgba(15,23,42,0.8)", borderBottom: "1px solid rgba(255,255,255,0.08)", textAlign: "left" }}>
                        <th style={{ padding: "0.6rem 0.75rem", color: "#94a3b8" }}>Candidate</th>
                        <th style={{ padding: "0.6rem 0.75rem", color: "#94a3b8" }}>Status</th>
                        <th style={{ padding: "0.6rem 0.75rem", color: "#94a3b8" }}>Attempts</th>
                        <th style={{ padding: "0.6rem 0.75rem", color: "#94a3b8" }}>Score</th>
                        <th style={{ padding: "0.6rem 0.75rem", color: "#94a3b8" }}>Completed At</th>
                      </tr>
                    </thead>
                    <tbody>
                      {activeDetail.recipients.length === 0 ? (
                        <tr>
                          <td colSpan={5} style={{ padding: "1.5rem", textAlign: "center", color: "#64748b" }}>
                            No recipients resolved for this task
                          </td>
                        </tr>
                      ) : (
                        activeDetail.recipients.map((r: any) => (
                          <tr key={r.id} style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                            <td style={{ padding: "0.6rem 0.75rem" }}>
                              <div style={{ fontWeight: 600, color: "#f8fafc" }}>{r.candidate_name}</div>
                              <div style={{ fontSize: "0.75rem", color: "#64748b" }}>{r.candidate_email}</div>
                            </td>
                            <td style={{ padding: "0.6rem 0.75rem" }}>
                              <span
                                className={`admin-badge ${
                                  r.status === "COMPLETED"
                                    ? "admin-badge-success"
                                    : r.status === "IN_PROGRESS"
                                    ? "admin-badge-info"
                                    : r.status === "EXPIRED"
                                    ? "admin-badge-danger"
                                    : "admin-badge-secondary"
                                }`}
                              >
                                {r.status}
                              </span>
                            </td>
                            <td style={{ padding: "0.6rem 0.75rem", color: "#cbd5e1" }}>
                              {r.attempt_count}
                            </td>
                            <td style={{ padding: "0.6rem 0.75rem", fontWeight: 600, color: r.score !== null ? "#34d399" : "#64748b" }}>
                              {r.score !== null ? `${r.score}%` : "—"}
                            </td>
                            <td style={{ padding: "0.6rem 0.75rem", color: "#94a3b8" }}>
                              {r.completed_at ? new Date(r.completed_at).toLocaleDateString() : "Pending"}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* STATUS CHANGE CONFIRMATION MODAL */}
      <AdminConfirmModal
        isOpen={statusModalOpen}
        title="Update Assignment Status"
        message={`Are you sure you want to mark this assignment as ${newStatusToApply}?`}
        confirmText="Confirm"
        onConfirm={handleConfirmStatusChange}
        onCancel={() => setStatusModalOpen(false)}
        loading={updatingStatus}
      />
    </div>
  )
}
