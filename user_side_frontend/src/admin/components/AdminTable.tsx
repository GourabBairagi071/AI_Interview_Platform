import { type ReactNode } from "react"

export interface Column<T> {
  key: string
  header: string
  render?: (row: T) => ReactNode
  width?: string
}

interface AdminTableProps<T> {
  columns: Column<T>[]
  data: T[]
  loading?: boolean
  emptyMessage?: string
  page?: number
  pageSize?: number
  total?: number
  onPageChange?: (newPage: number) => void
}

export function AdminTable<T extends { id?: string | number }>({
  columns,
  data,
  loading = false,
  emptyMessage = "No records found.",
  page = 1,
  pageSize = 20,
  total = 0,
  onPageChange,
}: AdminTableProps<T>) {
  const totalPages = Math.ceil(total / pageSize) || 1

  return (
    <div
      style={{
        background: "rgba(15, 23, 42, 0.75)",
        backdropFilter: "blur(12px)",
        border: "1px solid rgba(255, 255, 255, 0.08)",
        borderRadius: "14px",
        overflow: "hidden",
        boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.3)",
      }}
    >
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
          <thead>
            <tr style={{ background: "rgba(30, 41, 59, 0.7)", borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
              {columns.map((col) => (
                <th
                  key={col.key}
                  style={{
                    padding: "0.85rem 1.25rem",
                    fontSize: "0.785rem",
                    fontWeight: 600,
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                    color: "#94a3b8",
                    width: col.width,
                  }}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={columns.length} style={{ padding: "3rem", textAlign: "center", color: "#94a3b8" }}>
                  <div style={{ display: "inline-block", width: "24px", height: "24px", border: "2px solid #6366f1", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
                  <p style={{ marginTop: "0.5rem", fontSize: "0.875rem" }}>Loading data...</p>
                </td>
              </tr>
            ) : data.length === 0 ? (
              <tr>
                <td colSpan={columns.length} style={{ padding: "3rem", textAlign: "center", color: "#64748b", fontSize: "0.95rem" }}>
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              data.map((row, idx) => (
                <tr
                  key={row.id ? String(row.id) : idx}
                  style={{
                    borderBottom: "1px solid rgba(255, 255, 255, 0.04)",
                    transition: "background 0.15s ease",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255, 255, 255, 0.02)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      style={{
                        padding: "1rem 1.25rem",
                        fontSize: "0.875rem",
                        color: "#cbd5e1",
                      }}
                    >
                      {col.render ? col.render(row) : (row as any)[col.key]}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {total > 0 && onPageChange && (
        <div
          style={{
            padding: "0.85rem 1.25rem",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "rgba(15, 23, 42, 0.9)",
            borderTop: "1px solid rgba(255, 255, 255, 0.06)",
            fontSize: "0.85rem",
            color: "#94a3b8",
          }}
        >
          <div>
            Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, total)} of {total} entries
          </div>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              disabled={page <= 1}
              onClick={() => onPageChange(page - 1)}
              style={{
                padding: "0.4rem 0.8rem",
                borderRadius: "6px",
                border: "1px solid rgba(255,255,255,0.1)",
                background: page <= 1 ? "rgba(255,255,255,0.02)" : "rgba(255,255,255,0.06)",
                color: page <= 1 ? "#475569" : "#e2e8f0",
                cursor: page <= 1 ? "not-allowed" : "pointer",
              }}
            >
              Previous
            </button>
            <span style={{ display: "flex", alignItems: "center", padding: "0 0.5rem", color: "#f8fafc", fontWeight: 600 }}>
              {page} / {totalPages}
            </span>
            <button
              disabled={page >= totalPages}
              onClick={() => onPageChange(page + 1)}
              style={{
                padding: "0.4rem 0.8rem",
                borderRadius: "6px",
                border: "1px solid rgba(255,255,255,0.1)",
                background: page >= totalPages ? "rgba(255,255,255,0.02)" : "rgba(255,255,255,0.06)",
                color: page >= totalPages ? "#475569" : "#e2e8f0",
                cursor: page >= totalPages ? "not-allowed" : "pointer",
              }}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
