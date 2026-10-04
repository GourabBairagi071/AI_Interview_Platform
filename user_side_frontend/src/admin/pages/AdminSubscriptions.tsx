import React, { useEffect, useState } from "react"
import { adminApi } from "../services/adminApi"
import { AdminTable, type Column } from "../components/AdminTable"
import { PlusIcon } from "../components/AdminIcons"

export const AdminSubscriptions: React.FC = () => {
  const [plans, setPlans] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  // Create Plan Modal
  const [formOpen, setFormOpen] = useState(false)
  const [formData, setFormData] = useState({
    name: "",
    slug: "",
    price_inr: 999,
    interval: "month",
    description: "",
  })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadPlans()
  }, [])

  const loadPlans = async () => {
    try {
      setLoading(true)
      const data = await adminApi.getSubscriptionPlans()
      setPlans(data || [])
    } catch (err) {
      console.error("Failed to load subscription plans:", err)
    } finally {
      setLoading(false)
    }
  }

  const handleSavePlan = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.name.trim() || !formData.slug.trim()) {
      alert("Name and slug are required.")
      return
    }

    try {
      setSaving(true)
      await adminApi.createSubscriptionPlan(formData)
      setFormOpen(false)
      loadPlans()
    } catch (err: any) {
      alert(err.message || "Failed to create subscription plan")
    } finally {
      setSaving(false)
    }
  }

  const columns: Column<any>[] = [
    {
      key: "name",
      header: "Plan Name",
      render: (p) => (
        <div>
          <span style={{ fontWeight: 600, color: "#f8fafc" }}>{p.name}</span>
          <span style={{ fontSize: "0.75rem", color: "#64748b", marginLeft: "0.5rem" }}>
            ({p.slug})
          </span>
        </div>
      ),
    },
    {
      key: "price_inr",
      header: "Price",
      render: (p) => (
        <span style={{ fontWeight: 700, color: "#34d399" }}>
          ₹{p.price_inr} / {p.interval}
        </span>
      ),
      width: "160px",
    },
    {
      key: "subscribers_count",
      header: "Active Subscribers",
      render: (p) => (
        <span className="admin-badge admin-badge-info">
          {p.subscribers_count || 0} active
        </span>
      ),
      width: "180px",
    },
    {
      key: "is_active",
      header: "Status",
      render: (p) => (
        <span className={`admin-badge ${p.is_active ? "admin-badge-success" : "admin-badge-danger"}`}>
          {p.is_active ? "Available" : "Disabled"}
        </span>
      ),
      width: "130px",
    },
  ]

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Subscription Plans & Tiers</h1>
          <p className="admin-page-subtitle">
            Configure candidate subscription billing tiers, pricing thresholds, and feature entitlements
          </p>
        </div>
        <button onClick={() => setFormOpen(true)} className="admin-btn admin-btn-primary">
          <PlusIcon /> Add Plan Tier
        </button>
      </div>

      <AdminTable columns={columns} data={plans} loading={loading} />

      {/* Create Plan Modal */}
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
            onSubmit={handleSavePlan}
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
            <h3 style={{ fontSize: "1.25rem", fontWeight: 700, marginBottom: "1.25rem" }}>
              Add New Subscription Tier
            </h3>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                  Plan Name
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      name: e.target.value,
                      slug: e.target.value.toLowerCase().replace(/[^a-z0-9]/g, "-"),
                    })
                  }
                  className="admin-input"
                  style={{ width: "100%" }}
                  placeholder="Pro Monthly"
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                  Slug (Identifier)
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
                  Price (INR)
                </label>
                <input
                  type="number"
                  required
                  min="0"
                  value={formData.price_inr}
                  onChange={(e) => setFormData({ ...formData, price_inr: parseInt(e.target.value) })}
                  className="admin-input"
                  style={{ width: "100%" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                  Billing Interval
                </label>
                <select
                  value={formData.interval}
                  onChange={(e) => setFormData({ ...formData, interval: e.target.value })}
                  className="admin-select"
                  style={{ width: "100%" }}
                >
                  <option value="month">Monthly</option>
                  <option value="year">Yearly</option>
                </select>
              </div>
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
                {saving ? "Creating..." : "Create Plan"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
export default AdminSubscriptions
