import React, { useEffect, useState } from "react"
import { adminApi } from "../services/adminApi"
import { PlusIcon, AchievementIcon } from "../components/AdminIcons"

export const AdminAchievements: React.FC = () => {
  const [achievements, setAchievements] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  // Create Modal
  const [formOpen, setFormOpen] = useState(false)
  const [formData, setFormData] = useState({
    name: "",
    title: "",
    description: "",
    badge_icon: "trophy",
    points: 50,
    category: "INTERVIEW",
  })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadAchievements()
  }, [])

  const loadAchievements = async () => {
    try {
      setLoading(true)
      const data = await adminApi.getAchievements()
      setAchievements(data || [])
    } catch (err) {
      console.error("Failed to load achievements:", err)
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.name.trim() || !formData.title.trim()) {
      alert("Name and Title are required.")
      return
    }

    try {
      setSaving(true)
      await adminApi.createAchievement(formData)
      setFormOpen(false)
      loadAchievements()
    } catch (err: any) {
      alert(err.message || "Failed to create achievement badge")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Candidate Milestones & Badges</h1>
          <p className="admin-page-subtitle">
            Gamification reward thresholds, skill unlock badges, and points allocation
          </p>
        </div>
        <button onClick={() => setFormOpen(true)} className="admin-btn admin-btn-primary">
          <PlusIcon /> Add Badge
        </button>
      </div>

      {loading ? (
        <div style={{ padding: "3rem", textAlign: "center", color: "#94a3b8" }}>
          Loading achievement definitions...
        </div>
      ) : achievements.length === 0 ? (
        <div className="admin-card" style={{ padding: "3rem", textAlign: "center", color: "#64748b" }}>
          No achievement badges defined yet.
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1rem" }}>
          {achievements.map((ach) => (
            <div
              key={ach.id}
              className="admin-card"
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "0.75rem",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                <div style={{ padding: "0.6rem", borderRadius: "10px", background: "rgba(245, 158, 11, 0.15)", color: "#fbbf24" }}>
                  <AchievementIcon size={20} />
                </div>
                <div>
                  <h3 style={{ fontSize: "1rem", fontWeight: 700, color: "#f8fafc" }}>
                    {ach.title}
                  </h3>
                  <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
                    Category: {ach.category}
                  </span>
                </div>
              </div>

              <p style={{ fontSize: "0.85rem", color: "#cbd5e1", lineHeight: 1.4 }}>
                {ach.description}
              </p>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: "0.75rem" }}>
                <span style={{ fontWeight: 700, color: "#fbbf24", fontSize: "0.9rem" }}>
                  +{ach.points} XP
                </span>
                <span className="admin-badge admin-badge-info" style={{ fontFamily: "monospace" }}>
                  {ach.badge_icon}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

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
            onSubmit={handleCreate}
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
              Define Platform Achievement
            </h3>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                  System Key (Unique)
                </label>
                <input
                  type="text"
                  required
                  placeholder="FIRST_INTERVIEW_PASSED"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value.toUpperCase() })}
                  className="admin-input"
                  style={{ width: "100%" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                  Display Title
                </label>
                <input
                  type="text"
                  required
                  placeholder="First Ascent"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="admin-input"
                  style={{ width: "100%" }}
                />
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                  Category
                </label>
                <select
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="admin-select"
                  style={{ width: "100%" }}
                >
                  <option value="INTERVIEW">Interview</option>
                  <option value="CODING">Coding Arena</option>
                  <option value="CONTEST">Contests</option>
                  <option value="STREAK">Daily Streak</option>
                </select>
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                  XP Points Awarded
                </label>
                <input
                  type="number"
                  min="5"
                  required
                  value={formData.points}
                  onChange={(e) => setFormData({ ...formData, points: parseInt(e.target.value) })}
                  className="admin-input"
                  style={{ width: "100%" }}
                />
              </div>
            </div>

            <div style={{ marginBottom: "1.5rem" }}>
              <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                Description / Unlock Condition
              </label>
              <textarea
                rows={3}
                required
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
                {saving ? "Creating..." : "Save Badge"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
export default AdminAchievements
