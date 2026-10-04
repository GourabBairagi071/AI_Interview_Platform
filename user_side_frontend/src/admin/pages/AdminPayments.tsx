import React, { useEffect, useState } from "react"
import { adminApi } from "../services/adminApi"
import { AdminTable, type Column } from "../components/AdminTable"
import { SearchIcon } from "../components/AdminIcons"
import type { AdminPaymentItem } from "../types"

export const AdminPayments: React.FC = () => {
  const [payments, setPayments] = useState<AdminPaymentItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(15)
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState("")
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadPayments()
  }, [page, statusFilter])

  const loadPayments = async () => {
    try {
      setLoading(true)
      const res = await adminApi.getPayments({
        page,
        page_size: pageSize,
        search: search.trim() || undefined,
        status: statusFilter || undefined,
      })
      setPayments(res.payments || [])
      setTotal(res.total || 0)
    } catch (err) {
      console.error("Failed to load payments:", err)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    loadPayments()
  }

  const columns: Column<AdminPaymentItem>[] = [
    {
      key: "provider_order_id",
      header: "Razorpay Order ID",
      render: (p) => (
        <span style={{ fontFamily: "monospace", color: "#6366f1", fontSize: "0.85rem" }}>
          {p.provider_order_id}
        </span>
      ),
    },
    {
      key: "candidate",
      header: "Candidate Account",
      render: (p) => (
        <span style={{ color: "#f8fafc", fontSize: "0.85rem" }}>
          {p.user_email || p.user_id}
        </span>
      ),
    },
    {
      key: "amount_inr",
      header: "Amount",
      render: (p) => (
        <span style={{ fontWeight: 700, color: "#34d399", fontSize: "0.95rem" }}>
          ₹{p.amount_inr.toLocaleString("en-IN")}
        </span>
      ),
      width: "130px",
    },
    {
      key: "status",
      header: "Payment Status",
      render: (p) => {
        const isPaid = p.status.toLowerCase() === "paid"
        return (
          <span className={`admin-badge ${isPaid ? "admin-badge-success" : "admin-badge-warning"}`}>
            {p.status}
          </span>
        )
      },
      width: "130px",
    },
    {
      key: "created_at",
      header: "Transaction Timestamp",
      render: (p) => (
        <span style={{ color: "#94a3b8", fontSize: "0.825rem" }}>
          {new Date(p.created_at).toLocaleString()}
        </span>
      ),
      width: "180px",
    },
  ]

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Payment & Revenue Audit</h1>
          <p className="admin-page-subtitle">
            Inspect live Razorpay checkouts, payment signatures, and billing transaction ledgers
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
              placeholder="Search by order ID or customer..."
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

        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value)
            setPage(1)
          }}
          className="admin-select"
        >
          <option value="">All Statuses</option>
          <option value="paid">Paid</option>
          <option value="created">Created</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      <AdminTable
        columns={columns}
        data={payments}
        loading={loading}
        total={total}
        page={page}
        pageSize={pageSize}
        onPageChange={(p) => setPage(p)}
      />
    </div>
  )
}
export default AdminPayments
