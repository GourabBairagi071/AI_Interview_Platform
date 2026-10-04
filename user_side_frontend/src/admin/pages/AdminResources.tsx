import React, { useEffect, useState } from "react"
import { adminApi } from "../services/adminApi"
import { AdminTable, type Column } from "../components/AdminTable"
import { AdminConfirmModal } from "../components/AdminConfirmModal"
import { SearchIcon, PlusIcon } from "../components/AdminIcons"

export const AdminResources: React.FC = () => {
  const [resources, setResources] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(15)
  const [search, setSearch] = useState("")
  const [topicFilter, setTopicFilter] = useState("")
  const [loading, setLoading] = useState(true)

  // Form modal
  const [formOpen, setFormOpen] = useState(false)
  const [editingItem, setEditingItem] = useState<any>(null)
  const [formData, setFormData] = useState({
    title: "",
    topic: "System Design",
    resource_type: "article",
    url: "",
    description: "",
  })
  const [saving, setSaving] = useState(false)

  // Delete modal
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [selectedToDelete, setSelectedToDelete] = useState<any>(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    loadResources()
  }, [page, topicFilter])

  const loadResources = async () => {
    try {
      setLoading(true)
      const res = await adminApi.getResources({
        page,
        page_size: pageSize,
        topic: topicFilter || undefined,
        search: search.trim() || undefined,
      })
      setResources(res.resources || [])
      setTotal(res.total || 0)
    } catch (err) {
      console.error("Failed to load resources:", err)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    loadResources()
  }

  const handleOpenCreate = () => {
    setEditingItem(null)
    setFormData({
      title: "",
      topic: "System Design",
      resource_type: "article",
      url: "",
      description: "",
    })
    setFormOpen(true)
  }

  const handleOpenEdit = (r: any) => {
    setEditingItem(r)
    setFormData({
      title: r.title,
      topic: r.topic || "General",
      resource_type: r.resource_type || "article",
      url: r.url || "",
      description: r.description || "",
    })
    setFormOpen(true)
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.title.trim() || !formData.url.trim()) {
      alert("Title and URL are required.")
      return
    }

    try {
      setSaving(true)
      if (editingItem) {
        await adminApi.updateResource(editingItem.id, formData)
      } else {
        await adminApi.createResource(formData)
      }
      setFormOpen(false)
      loadResources()
    } catch (err: any) {
      alert(err.message || "Failed to save resource")
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!selectedToDelete) return
    try {
      setDeleting(true)
      await adminApi.deleteResource(selectedToDelete.id)
      setDeleteModalOpen(false)
      loadResources()
    } catch (err: any) {
      alert(err.message || "Failed to delete resource")
    } finally {
      setDeleting(false)
    }
  }

  const columns: Column<any>[] = [
    {
      key: "title",
      header: "Resource Title",
      render: (r) => (
        <div>
          <span style={{ fontWeight: 600, color: "#f8fafc" }}>{r.title}</span>
          <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
            <a href={r.url} target="_blank" rel="noreferrer" style={{ color: "#6366f1", textDecoration: "none" }}>
              {r.url.length > 40 ? `${r.url.substring(0, 40)}...` : r.url}
            </a>
          </div>
        </div>
      ),
    },
    {
      key: "topic",
      header: "Topic",
      render: (r) => (
        <span className="admin-badge admin-badge-info">{r.topic}</span>
      ),
      width: "160px",
    },
    {
      key: "resource_type",
      header: "Format",
      render: (r) => (
        <span className="admin-badge admin-badge-warning">{r.resource_type}</span>
      ),
      width: "120px",
    },
    {
      key: "actions",
      header: "Actions",
      render: (r) => (
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button
            onClick={() => handleOpenEdit(r)}
            className="admin-btn admin-btn-secondary"
            style={{ padding: "0.3rem 0.6rem", fontSize: "0.75rem" }}
          >
            Edit
          </button>
          <button
            onClick={() => {
              setSelectedToDelete(r)
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
          <h1 className="admin-page-title">Curated Learning Resources</h1>
          <p className="admin-page-subtitle">
            Manage preparation guides, architectural cheat-sheets, and algorithmic roadmaps
          </p>
        </div>
        <button onClick={handleOpenCreate} className="admin-btn admin-btn-primary">
          <PlusIcon /> Add Resource
        </button>
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
              placeholder="Search resource title or topic..."
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
        data={resources}
        loading={loading}
        total={total}
        page={page}
        pageSize={pageSize}
        onPageChange={(p) => setPage(p)}
      />

      {/* Form Modal */}
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
            onSubmit={handleSave}
            style={{
              background: "#1e293b",
              border: "1px solid rgba(255, 255, 255, 0.12)",
              borderRadius: "16px",
              width: "100%",
              maxWidth: "560px",
              padding: "2rem",
              color: "#f8fafc",
            }}
          >
            <h3 style={{ fontSize: "1.25rem", fontWeight: 700, marginBottom: "1.25rem" }}>
              {editingItem ? "Edit Learning Resource" : "Create Learning Resource"}
            </h3>

            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                Resource Title
              </label>
              <input
                type="text"
                required
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                className="admin-input"
                style={{ width: "100%" }}
              />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                  Topic Domain
                </label>
                <input
                  type="text"
                  required
                  value={formData.topic}
                  onChange={(e) => setFormData({ ...formData, topic: e.target.value })}
                  className="admin-input"
                  style={{ width: "100%" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                  Resource Type
                </label>
                <select
                  value={formData.resource_type}
                  onChange={(e) => setFormData({ ...formData, resource_type: e.target.value })}
                  className="admin-select"
                  style={{ width: "100%" }}
                >
                  <option value="article">Article / Guide</option>
                  <option value="video">Video Course</option>
                  <option value="cheatsheet">Cheat Sheet</option>
                  <option value="book">Reference Book</option>
                </select>
              </div>
            </div>

            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                Destination URL
              </label>
              <input
                type="url"
                required
                value={formData.url}
                onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                className="admin-input"
                style={{ width: "100%" }}
                placeholder="https://..."
              />
            </div>

            <div style={{ marginBottom: "1.5rem" }}>
              <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                Description
              </label>
              <textarea
                rows={3}
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="admin-input"
                style={{ width: "100%", resize: "vertical" }}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem" }}>
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
                {saving ? "Saving..." : "Save Resource"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Delete Modal */}
      <AdminConfirmModal
        isOpen={deleteModalOpen}
        title="Delete Learning Resource"
        message="Are you sure you want to remove this learning resource?"
        confirmText="Delete"
        isDestructive
        loading={deleting}
        onConfirm={handleDelete}
        onCancel={() => setDeleteModalOpen(false)}
      />
    </div>
  )
}
export default AdminResources
