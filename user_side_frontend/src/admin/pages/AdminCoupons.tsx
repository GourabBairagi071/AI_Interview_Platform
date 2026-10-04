import React, { useEffect, useState } from "react"
import { adminApi } from "../services/adminApi"
import { AdminTable, type Column } from "../components/AdminTable"
import { PlusIcon } from "../components/AdminIcons"

export const AdminCoupons: React.FC = () => {
  const [coupons, setCoupons] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(15)
  const [loading, setLoading] = useState(true)

  // Create Modal
  const [formOpen, setFormOpen] = useState(false)
  const [formData, setFormData] = useState({
    code: "",
    discount_percent: 20,
    usage_limit: 100,
  })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadCoupons()
  }, [page])

  const loadCoupons = async () => {
    try {
      setLoading(true)
      const res = await adminApi.getCoupons({ page, page_size: pageSize })
      setCoupons(res.coupons || [])
      setTotal(res.total || 0)
    } catch (err) {
      console.error("Failed to load coupons:", err)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateCoupon = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.code.trim()) {
      alert("Coupon code is required.")
      return
    }

    try {
      setSaving(true)
      await adminApi.createCoupon({
        ...formData,
        code: formData.code.toUpperCase().trim(),
      })
      setFormOpen(false)
      loadCoupons()
    } catch (err: any) {
      alert(err.message || "Failed to create coupon")
    } finally {
      setSaving(false)
    }
  }

  const handleToggle = async (couponId: string) => {
    try {
      await adminApi.toggleCoupon(couponId)
      loadCoupons()
    } catch (err: any) {
      alert(err.message || "Failed to toggle status")
    }
  }

  const columns: Column<any>[] = [
    {
      key: "code",
      header: "Promo Code",
      render: (c) => (
        <span style={{ fontFamily: "monospace", fontWeight: 700, color: "#6366f1", fontSize: "0.95rem" }}>
          {c.code}
        </span>
      ),
    },
    {
      key: "discount_percent",
      header: "Discount",
      render: (c) => (
        <span style={{ fontWeight: 700, color: "#34d399" }}>
          {c.discount_percent}% OFF
        </span>
      ),
      width: "140px",
    },
    {
      key: "usage",
      header: "Usage / Quota",
      render: (c) => (
        <span style={{ color: "#cbd5e1", fontSize: "0.85rem" }}>
          {c.times_used || 0} / {c.usage_limit || "∞"}
        </span>
      ),
      width: "160px",
    },
    {
      key: "is_active",
      header: "Status",
      render: (c) => (
        <span className={`admin-badge ${c.is_active ? "admin-badge-success" : "admin-badge-danger"}`}>
          {c.is_active ? "Active" : "Disabled"}
        </span>
      ),
      width: "120px",
    },
    {
      key: "actions",
      header: "Action",
      render: (c) => (
        <button
          onClick={() => handleToggle(c.id)}
          className={`admin-btn ${c.is_active ? "admin-btn-danger" : "admin-btn-secondary"}`}
          style={{ padding: "0.3rem 0.65rem", fontSize: "0.75rem" }}
        >
          {c.is_active ? "Disable" : "Enable"}
        </button>
      ),
      width: "130px",
    },
  ]

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Discount Coupons & Promotions</h1>
          <p className="admin-page-subtitle">
            Create promotional codes, percent-off incentives, and redemption thresholds
          </p>
        </div>
        <button onClick={() => setFormOpen(true)} className="admin-btn admin-btn-primary">
          <PlusIcon /> Create Coupon
        </button>
      </div>

      <AdminTable
        columns={columns}
        data={coupons}
        loading={loading}
        total={total}
        page={page}
        pageSize={pageSize}
        onPageChange={(p) => setPage(p)}
      />

      {/* Create Modal */}
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
            onSubmit={handleCreateCoupon}
            style={{
              background: "#1e293b",
              border: "1px solid rgba(255, 255, 255, 0.12)",
              borderRadius: "16px",
              width: "100%",
              maxWidth: "460px",
              padding: "2rem",
              color: "#f8fafc",
            }}
          >
            <h3 style={{ fontSize: "1.25rem", fontWeight: 700, marginBottom: "1.25rem" }}>
              Issue Promotional Coupon
            </h3>

            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                Promo Code
              </label>
              <input
                type="text"
                required
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                className="admin-input"
                style={{ width: "100%", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 700 }}
                placeholder="SAVE50"
              />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                  Discount (%)
                </label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  required
                  value={formData.discount_percent}
                  onChange={(e) => setFormData({ ...formData, discount_percent: parseInt(e.target.value) })}
                  className="admin-input"
                  style={{ width: "100%" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                  Max Redemptions
                </label>
                <input
                  type="number"
                  min="1"
                  required
                  value={formData.usage_limit}
                  onChange={(e) => setFormData({ ...formData, usage_limit: parseInt(e.target.value) })}
                  className="admin-input"
                  style={{ width: "100%" }}
                />
              </div>
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
                {saving ? "Creating..." : "Issue Coupon"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
export default AdminCoupons
