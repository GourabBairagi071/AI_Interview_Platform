import React, { useEffect, useState } from "react"
import { adminApi } from "../services/adminApi"
import { AdminTable, type Column } from "../components/AdminTable"
import { AdminConfirmModal } from "../components/AdminConfirmModal"
import { SearchIcon, PlusIcon } from "../components/AdminIcons"

export const AdminCompanies: React.FC = () => {
  const [companies, setCompanies] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(15)
  const [search, setSearch] = useState("")
  const [loading, setLoading] = useState(true)

  // Form modal
  const [formOpen, setFormOpen] = useState(false)
  const [editingItem, setEditingItem] = useState<any>(null)
  const [formData, setFormData] = useState({
    name: "",
    slug: "",
    industry: "Technology",
    website: "",
    description: "",
    difficulty: "Medium",
    hiring_roles: "",
  })
  const [saving, setSaving] = useState(false)

  // Delete modal
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [selectedToDelete, setSelectedToDelete] = useState<any>(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    loadCompanies()
  }, [page])

  const loadCompanies = async () => {
    try {
      setLoading(true)
      const res = await adminApi.getCompanies({
        page,
        page_size: pageSize,
        search: search.trim() || undefined,
      })
      setCompanies(res.companies || [])
      setTotal(res.total || 0)
    } catch (err) {
      console.error("Failed to load companies:", err)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    loadCompanies()
  }

  const handleOpenCreate = () => {
    setEditingItem(null)
    setFormData({
      name: "",
      slug: "",
      industry: "Technology",
      website: "",
      description: "",
      difficulty: "Medium",
      hiring_roles: "Software Engineer, Frontend Developer",
    })
    setFormOpen(true)
  }

  const handleOpenEdit = (c: any) => {
    setEditingItem(c)
    setFormData({
      name: c.name,
      slug: c.slug,
      industry: c.industry || "Technology",
      website: c.website || "",
      description: c.description || "",
      difficulty: c.difficulty || "Medium",
      hiring_roles: Array.isArray(c.hiring_roles) ? c.hiring_roles.join(", ") : c.hiring_roles || "",
    })
    setFormOpen(true)
  }

  const handleSaveCompany = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.name.trim() || !formData.slug.trim()) {
      alert("Name and slug are required.")
      return
    }

    const payload = {
      ...formData,
      hiring_roles: formData.hiring_roles
        .split(",")
        .map((r) => r.trim())
        .filter(Boolean),
    }

    try {
      setSaving(true)
      if (editingItem) {
        await adminApi.updateCompany(editingItem.id, payload)
      } else {
        await adminApi.createCompany(payload)
      }
      setFormOpen(false)
      loadCompanies()
    } catch (err: any) {
      alert(err.message || "Failed to save company")
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!selectedToDelete) return
    try {
      setDeleting(true)
      await adminApi.deleteCompany(selectedToDelete.id)
      setDeleteModalOpen(false)
      loadCompanies()
    } catch (err: any) {
      alert(err.message || "Failed to delete company")
    } finally {
      setDeleting(false)
    }
  }

  const columns: Column<any>[] = [
    {
      key: "name",
      header: "Company",
      render: (c) => (
        <div>
          <span style={{ fontWeight: 600, color: "#f8fafc" }}>{c.name}</span>
          <span style={{ fontSize: "0.75rem", color: "#64748b", marginLeft: "0.5rem" }}>
            ({c.slug})
          </span>
        </div>
      ),
    },
    {
      key: "industry",
      header: "Industry",
      render: (c) => (
        <span className="admin-badge admin-badge-info">{c.industry}</span>
      ),
      width: "150px",
    },
    {
      key: "difficulty",
      header: "Bar Difficulty",
      render: (c) => (
        <span className="admin-badge admin-badge-warning">{c.difficulty}</span>
      ),
      width: "130px",
    },
    {
      key: "hiring_roles",
      header: "Active Roles",
      render: (c) => (
        <div style={{ color: "#94a3b8", fontSize: "0.8rem" }}>
          {Array.isArray(c.hiring_roles) ? c.hiring_roles.slice(0, 3).join(", ") : "Standard Tech Roles"}
        </div>
      ),
    },
    {
      key: "actions",
      header: "Actions",
      render: (c) => (
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button
            onClick={() => handleOpenEdit(c)}
            className="admin-btn admin-btn-secondary"
            style={{ padding: "0.3rem 0.6rem", fontSize: "0.75rem" }}
          >
            Edit
          </button>
          <button
            onClick={() => {
              setSelectedToDelete(c)
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
          <h1 className="admin-page-title">Target Company Profiles</h1>
          <p className="admin-page-subtitle">
            Manage hiring companies, interview rubrics, and target evaluation bars
          </p>
        </div>
        <button onClick={handleOpenCreate} className="admin-btn admin-btn-primary">
          <PlusIcon /> Add Company
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
              placeholder="Search companies by name or industry..."
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
        data={companies}
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
            onSubmit={handleSaveCompany}
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
              {editingItem ? "Edit Company Profile" : "Register Target Company"}
            </h3>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                  Company Name
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value, slug: e.target.value.toLowerCase().replace(/[^a-z0-9]/g, "-") })}
                  className="admin-input"
                  style={{ width: "100%" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                  Slug (URL Key)
                </label>
                <input
                  type="text"
                  required
                  value={formData.slug}
                  onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
                  className="admin-input"
                  style={{ width: "100%" }}
                />
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                  Industry
                </label>
                <input
                  type="text"
                  value={formData.industry}
                  onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
                  className="admin-input"
                  style={{ width: "100%" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                  Difficulty Bar
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
                  <option value="FAANG">FAANG / Ultra-High</option>
                </select>
              </div>
            </div>

            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                Target Hiring Roles (comma-separated)
              </label>
              <input
                type="text"
                value={formData.hiring_roles}
                onChange={(e) => setFormData({ ...formData, hiring_roles: e.target.value })}
                className="admin-input"
                style={{ width: "100%" }}
                placeholder="Software Engineer, Data Scientist, SRE"
              />
            </div>

            <div style={{ marginBottom: "1rem" }}>
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
                {saving ? "Saving..." : "Save Company"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Delete Modal */}
      <AdminConfirmModal
        isOpen={deleteModalOpen}
        title="Delete Company Profile"
        message="Are you sure you want to remove this company profile from the platform?"
        confirmText="Delete"
        isDestructive
        loading={deleting}
        onConfirm={handleDelete}
        onCancel={() => setDeleteModalOpen(false)}
      />
    </div>
  )
}
export default AdminCompanies
