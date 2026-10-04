import React, { useEffect, useState } from "react"
import { adminApi } from "../services/adminApi"
import { AdminTable, type Column } from "../components/AdminTable"
import { InvoiceIcon } from "../components/AdminIcons"

export const AdminInvoices: React.FC = () => {
  const [invoices, setInvoices] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(15)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadInvoices()
  }, [page])

  const loadInvoices = async () => {
    try {
      setLoading(true)
      const res = await adminApi.getInvoices({ page, page_size: pageSize })
      setInvoices(res.invoices || [])
      setTotal(res.total || 0)
    } catch (err) {
      console.error("Failed to load invoices:", err)
    } finally {
      setLoading(false)
    }
  }

  const columns: Column<any>[] = [
    {
      key: "invoice_number",
      header: "Invoice Reference",
      render: (inv) => (
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <InvoiceIcon size={16} className="text-slate-400" />
          <span style={{ fontFamily: "monospace", fontWeight: 600, color: "#f8fafc" }}>
            {inv.invoice_number}
          </span>
        </div>
      ),
    },
    {
      key: "candidate",
      header: "Billed Customer",
      render: (inv) => (
        <span style={{ color: "#cbd5e1", fontSize: "0.85rem" }}>
          {inv.user_email || inv.user_id}
        </span>
      ),
    },
    {
      key: "amount_inr",
      header: "Taxable Total",
      render: (inv) => (
        <span style={{ fontWeight: 700, color: "#34d399" }}>
          ₹{inv.amount_inr.toLocaleString("en-IN")}
        </span>
      ),
      width: "140px",
    },
    {
      key: "status",
      header: "Invoice State",
      render: () => (
        <span className="admin-badge admin-badge-success">Settled</span>
      ),
      width: "120px",
    },
    {
      key: "issued_at",
      header: "Issued Date",
      render: (inv) => (
        <span style={{ color: "#94a3b8", fontSize: "0.825rem" }}>
          {new Date(inv.issued_at).toLocaleDateString()}
        </span>
      ),
      width: "150px",
    },
  ]

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Tax Invoices & Billing Records</h1>
          <p className="admin-page-subtitle">
            Immutable fiscal audit records, generated customer tax receipts, and ledger statements
          </p>
        </div>
      </div>

      <AdminTable
        columns={columns}
        data={invoices}
        loading={loading}
        total={total}
        page={page}
        pageSize={pageSize}
        onPageChange={(p) => setPage(p)}
      />
    </div>
  )
}
export default AdminInvoices
