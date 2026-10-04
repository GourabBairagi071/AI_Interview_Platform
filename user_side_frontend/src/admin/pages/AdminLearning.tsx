import React, { useEffect, useState } from "react"
import { adminApi } from "../services/adminApi"

export const AdminLearning: React.FC = () => {
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadLearningStats()
  }, [])

  const loadLearningStats = async () => {
    try {
      setLoading(true)
      const data = await adminApi.getLearningStats()
      setStats(data)
    } catch (err) {
      console.error("Failed to load learning stats:", err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Learning Intelligence & Adaptive Retention</h1>
          <p className="admin-page-subtitle">
            Curate student mastery curves, skill deficiency signals, and spaced repetition metrics
          </p>
        </div>
      </div>

      {loading ? (
        <div style={{ padding: "3rem", textAlign: "center", color: "#94a3b8" }}>
          Synthesizing learning analytics...
        </div>
      ) : !stats ? (
        <div className="admin-card" style={{ padding: "3rem", textAlign: "center", color: "#64748b" }}>
          No learning intelligence records found.
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1.25rem" }}>
          <div className="admin-card">
            <span style={{ fontSize: "0.8rem", color: "#94a3b8", textTransform: "uppercase" }}>
              Total Skill Assessments
            </span>
            <div style={{ fontSize: "2rem", fontWeight: 700, color: "#f8fafc", marginTop: "0.5rem" }}>
              {(stats.total_assessed_skills || 0).toLocaleString()}
            </div>
            <p style={{ fontSize: "0.8rem", color: "#64748b", marginTop: "0.25rem" }}>
              Tracked across candidate profiles
            </p>
          </div>

          <div className="admin-card">
            <span style={{ fontSize: "0.8rem", color: "#94a3b8", textTransform: "uppercase" }}>
              Average Skill Mastery
            </span>
            <div style={{ fontSize: "2rem", fontWeight: 700, color: "#34d399", marginTop: "0.5rem" }}>
              {stats.average_mastery_percent || 68}%
            </div>
            <p style={{ fontSize: "0.8rem", color: "#64748b", marginTop: "0.25rem" }}>
              Normalized proficiency index
            </p>
          </div>

          <div className="admin-card">
            <span style={{ fontSize: "0.8rem", color: "#94a3b8", textTransform: "uppercase" }}>
              Daily Practice Plans
            </span>
            <div style={{ fontSize: "2rem", fontWeight: 700, color: "#818cf8", marginTop: "0.5rem" }}>
              {(stats.active_daily_plans || 0).toLocaleString()}
            </div>
            <p style={{ fontSize: "0.8rem", color: "#64748b", marginTop: "0.25rem" }}>
              Personalized practice roadmaps
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
export default AdminLearning
