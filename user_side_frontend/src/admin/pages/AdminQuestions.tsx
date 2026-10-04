import React, { useEffect, useState } from "react"
import { adminApi } from "../services/adminApi"
import { AdminTable, type Column } from "../components/AdminTable"
import { AdminConfirmModal } from "../components/AdminConfirmModal"
import { SearchIcon, PlusIcon } from "../components/AdminIcons"
import type { AdminQuestionItem } from "../types"

export const AdminQuestions: React.FC = () => {
  const [questions, setQuestions] = useState<AdminQuestionItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(15)
  const [search, setSearch] = useState("")
  const [techFilter, setTechFilter] = useState("")
  const [diffFilter, setDiffFilter] = useState("")
  const [loading, setLoading] = useState(true)

  // Create / Edit Modal
  const [formOpen, setFormOpen] = useState(false)
  const [editingItem, setEditingItem] = useState<AdminQuestionItem | null>(null)
  const [formData, setFormData] = useState({
    technology: "Python",
    category: "Data Structures",
    difficulty: "Medium",
    question_text: "",
    expected_answer: "",
    evaluation_criteria: "",
  })
  const [saving, setSaving] = useState(false)

  // Delete modal
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [questionToDelete, setQuestionToDelete] = useState<AdminQuestionItem | null>(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    loadQuestions()
  }, [page, techFilter, diffFilter])

  const loadQuestions = async () => {
    try {
      setLoading(true)
      const res = await adminApi.getQuestions({
        page,
        page_size: pageSize,
        technology: techFilter || undefined,
        difficulty: diffFilter || undefined,
        search: search.trim() || undefined,
      })
      setQuestions(res.questions || [])
      setTotal(res.total || 0)
    } catch (err) {
      console.error("Failed to load questions:", err)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    loadQuestions()
  }

  const handleOpenCreate = () => {
    setEditingItem(null)
    setFormData({
      technology: "Python",
      category: "Data Structures",
      difficulty: "Medium",
      question_text: "",
      expected_answer: "",
      evaluation_criteria: "",
    })
    setFormOpen(true)
  }

  const handleOpenEdit = (q: AdminQuestionItem) => {
    setEditingItem(q)
    setFormData({
      technology: q.technology,
      category: q.category,
      difficulty: q.difficulty,
      question_text: q.question_text,
      expected_answer: q.expected_answer || "",
      evaluation_criteria: q.evaluation_criteria || "",
    })
    setFormOpen(true)
  }

  const handleSaveQuestion = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.question_text.trim()) {
      alert("Question text is required.")
      return
    }

    try {
      setSaving(true)
      if (editingItem) {
        await adminApi.updateQuestion(editingItem.id, formData)
      } else {
        await adminApi.createQuestion(formData)
      }
      setFormOpen(false)
      loadQuestions()
    } catch (err: any) {
      alert(err.message || "Failed to save question")
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!questionToDelete) return
    try {
      setDeleting(true)
      await adminApi.deleteQuestion(questionToDelete.id)
      setDeleteModalOpen(false)
      loadQuestions()
    } catch (err: any) {
      alert(err.message || "Failed to delete question")
    } finally {
      setDeleting(false)
    }
  }

  const columns: Column<AdminQuestionItem>[] = [
    {
      key: "technology",
      header: "Technology",
      render: (q) => (
        <span className="admin-badge admin-badge-info">{q.technology}</span>
      ),
      width: "120px",
    },
    {
      key: "difficulty",
      header: "Difficulty",
      render: (q) => {
        const d = (q.difficulty || "").toLowerCase()
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
            {q.difficulty}
          </span>
        )
      },
      width: "110px",
    },
    {
      key: "category",
      header: "Category",
      render: (q) => (
        <span style={{ color: "#94a3b8", fontSize: "0.825rem" }}>{q.category}</span>
      ),
      width: "160px",
    },
    {
      key: "question_text",
      header: "Question Prompt",
      render: (q) => (
        <div style={{ color: "#f8fafc", fontWeight: 500, lineHeight: 1.4 }}>
          {q.question_text.length > 100
            ? `${q.question_text.substring(0, 100)}...`
            : q.question_text}
        </div>
      ),
    },
    {
      key: "actions",
      header: "Actions",
      render: (q) => (
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button
            onClick={() => handleOpenEdit(q)}
            className="admin-btn admin-btn-secondary"
            style={{ padding: "0.3rem 0.6rem", fontSize: "0.75rem" }}
          >
            Edit
          </button>
          <button
            onClick={() => {
              setQuestionToDelete(q)
              setDeleteModalOpen(true)
            }}
            className="admin-btn admin-btn-danger"
            style={{ padding: "0.3rem 0.6rem", fontSize: "0.75rem" }}
          >
            Delete
          </button>
        </div>
      ),
      width: "160px",
    },
  ]

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Technical Question Bank</h1>
          <p className="admin-page-subtitle">
            Curate practice, domain, and behavioral interview questions
          </p>
        </div>
        <button onClick={handleOpenCreate} className="admin-btn admin-btn-primary">
          <PlusIcon /> Add Question
        </button>
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
              placeholder="Search question text or keywords..."
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
            Search
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
        data={questions}
        loading={loading}
        total={total}
        page={page}
        pageSize={pageSize}
        onPageChange={(p) => setPage(p)}
      />

      {/* Create / Edit Modal */}
      {formOpen && (
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
            onSubmit={handleSaveQuestion}
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
            <h3 style={{ fontSize: "1.25rem", fontWeight: 700, marginBottom: "1.25rem" }}>
              {editingItem ? "Edit Technical Question" : "Create Technical Question"}
            </h3>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                  Technology
                </label>
                <input
                  type="text"
                  required
                  value={formData.technology}
                  onChange={(e) => setFormData({ ...formData, technology: e.target.value })}
                  className="admin-input"
                  style={{ width: "100%" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                  Category
                </label>
                <input
                  type="text"
                  required
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="admin-input"
                  style={{ width: "100%" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                  Difficulty
                </label>
                <select
                  value={formData.difficulty}
                  onChange={(e) => setFormData({ ...formData, difficulty: e.target.value })}
                  className="admin-select"
                  style={{ width: "100%" }}
                >
                  <option value="Easy">Easy</option>
                  <option value="Medium">Medium</option>
                  <option value="Hard">Hard</option>
                </select>
              </div>
            </div>

            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                Question Statement
              </label>
              <textarea
                required
                rows={4}
                value={formData.question_text}
                onChange={(e) => setFormData({ ...formData, question_text: e.target.value })}
                className="admin-input"
                style={{ width: "100%", resize: "vertical" }}
              />
            </div>

            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                Sample Solution / Expected Answer
              </label>
              <textarea
                rows={3}
                value={formData.expected_answer}
                onChange={(e) => setFormData({ ...formData, expected_answer: e.target.value })}
                className="admin-input"
                style={{ width: "100%", resize: "vertical" }}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "1.5rem" }}>
              <button
                type="button"
                onClick={() => setFormOpen(false)}
                className="admin-btn admin-btn-secondary"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="admin-btn admin-btn-primary"
              >
                {saving ? "Saving..." : "Save Question"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <AdminConfirmModal
        isOpen={deleteModalOpen}
        title="Delete Question"
        message="Are you sure you want to delete this technical interview question from the bank?"
        confirmText="Delete"
        isDestructive
        loading={deleting}
        onConfirm={handleDelete}
        onCancel={() => setDeleteModalOpen(false)}
      />
    </div>
  )
}
export default AdminQuestions
