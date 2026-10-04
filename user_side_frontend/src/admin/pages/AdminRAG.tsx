import React, { useEffect, useState } from "react"
import { adminApi } from "../services/adminApi"
import { DatabaseIcon } from "../components/AdminIcons"

export const AdminRAG: React.FC = () => {
  const [status, setStatus] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadRAGStatus()
  }, [])

  const loadRAGStatus = async () => {
    try {
      setLoading(true)
      const data = await adminApi.getRAGStatus()
      setStatus(data)
    } catch (err) {
      console.error("Failed to load RAG status:", err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem", maxWidth: "900px" }}>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">RAG Architecture & Vector Indexing</h1>
          <p className="admin-page-subtitle">
            Monitor high-dimensional semantic search indexes and question retrieval embeddings
          </p>
        </div>
      </div>

      {loading ? (
        <div style={{ padding: "3rem", textAlign: "center", color: "#94a3b8" }}>
          Inspecting vector index health...
        </div>
      ) : !status ? (
        <div className="admin-card" style={{ padding: "3rem", textAlign: "center", color: "#64748b" }}>
          Unable to connect to vector indexer.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          {/* Top Status Card */}
          <div
            className="admin-card"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "1.75rem",
              background: "linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
              <div style={{ padding: "1rem", borderRadius: "12px", background: "rgba(99, 102, 241, 0.15)", color: "#818cf8" }}>
                <DatabaseIcon size={32} />
              </div>
              <div>
                <span style={{ fontSize: "0.8rem", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  Indexed Embeddings
                </span>
                <div style={{ fontSize: "2rem", fontWeight: 800, color: "#f8fafc" }}>
                  {(status.total_vectors || 0).toLocaleString()} Vectors
                </div>
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "0.35rem" }}>
              <span className="admin-badge admin-badge-success">Operational</span>
              <span style={{ fontSize: "0.75rem", color: "#64748b" }}>Model: all-MiniLM-L6-v2 (384-d)</span>
            </div>
          </div>

          {/* Collection Status Grid */}
          <div className="admin-card">
            <h3 style={{ fontSize: "1rem", fontWeight: 600, color: "#f8fafc", marginBottom: "1rem" }}>
              Active Semantic Collections
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              {(status.collections || []).map((col: any, idx: number) => (
                <div
                  key={idx}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "0.85rem 1rem",
                    background: "rgba(255,255,255,0.03)",
                    borderRadius: "8px",
                  }}
                >
                  <div>
                    <span style={{ fontFamily: "monospace", fontWeight: 600, color: "#6366f1" }}>
                      {col.name}
                    </span>
                    <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
                      Adaptive Question Matching Index
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                    <span style={{ fontSize: "0.85rem", color: "#f8fafc", fontWeight: 600 }}>
                      {col.count} documents
                    </span>
                    <span className="admin-badge admin-badge-success">{col.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
export default AdminRAG
