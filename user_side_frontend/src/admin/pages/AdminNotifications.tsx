import React, { useState } from "react"
import { adminApi } from "../services/adminApi"
import { NotificationIcon } from "../components/AdminIcons"

export const AdminNotifications: React.FC = () => {
  const [formData, setFormData] = useState({
    title: "",
    message: "",
    target_role: "",
    priority: "medium",
  })
  const [broadcasting, setBroadcasting] = useState(false)
  const [resultMessage, setResultMessage] = useState<string | null>(null)

  const handleBroadcast = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.title.trim() || !formData.message.trim()) {
      alert("Title and message body are required.")
      return
    }

    try {
      setBroadcasting(true)
      setResultMessage(null)
      const res = await adminApi.broadcastNotification({
        title: formData.title,
        message: formData.message,
        target_role: formData.target_role || undefined,
        priority: formData.priority,
      })
      setResultMessage(`Announcement transmitted successfully to ${res.recipients_count} candidate accounts via WebSocket and Database persistence.`)
      setFormData({
        title: "",
        message: "",
        target_role: "",
        priority: "medium",
      })
    } catch (err: any) {
      alert(err.message || "Failed to broadcast notification")
    } finally {
      setBroadcasting(false)
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem", maxWidth: "800px" }}>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Broadcast Announcements</h1>
          <p className="admin-page-subtitle">
            Push real-time WebSocket toast alerts and in-app notifications directly to candidate dashboards
          </p>
        </div>
      </div>

      {resultMessage && (
        <div style={{ padding: "1rem 1.25rem", background: "rgba(16, 185, 129, 0.15)", border: "1px solid rgba(16, 185, 129, 0.3)", borderRadius: "10px", color: "#34d399", fontSize: "0.9rem" }}>
          ✓ {resultMessage}
        </div>
      )}

      <div className="admin-card">
        <form onSubmit={handleBroadcast} style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
            <NotificationIcon className="text-indigo-400" />
            <h3 style={{ fontSize: "1.1rem", fontWeight: 600, color: "#f8fafc" }}>
              Compose Platform Transmission
            </h3>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.825rem", color: "#94a3b8", marginBottom: "0.4rem" }}>
              Announcement Subject
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Scheduled Maintenance or New FAANG Interview Set Available"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              className="admin-input"
              style={{ width: "100%" }}
            />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.825rem", color: "#94a3b8", marginBottom: "0.4rem" }}>
                Target Audience Cohort
              </label>
              <select
                value={formData.target_role}
                onChange={(e) => setFormData({ ...formData, target_role: e.target.value })}
                className="admin-select"
                style={{ width: "100%" }}
              >
                <option value="">All Platform Users (Global Broadcast)</option>
                <option value="CANDIDATE">Candidates Only</option>
                <option value="ADMIN">Administrative Staff Only</option>
              </select>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.825rem", color: "#94a3b8", marginBottom: "0.4rem" }}>
                Priority Level
              </label>
              <select
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                className="admin-select"
                style={{ width: "100%" }}
              >
                <option value="low">Low (General Update)</option>
                <option value="medium">Medium (Standard)</option>
                <option value="high">High (Important)</option>
                <option value="urgent">Urgent (Immediate Banner)</option>
              </select>
            </div>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.825rem", color: "#94a3b8", marginBottom: "0.4rem" }}>
              Notification Body
            </label>
            <textarea
              required
              rows={5}
              placeholder="Full announcement content displayed to candidates..."
              value={formData.message}
              onChange={(e) => setFormData({ ...formData, message: e.target.value })}
              className="admin-input"
              style={{ width: "100%", resize: "vertical" }}
            />
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button
              type="submit"
              disabled={broadcasting}
              className="admin-btn admin-btn-primary"
              style={{ padding: "0.65rem 1.5rem", fontSize: "0.9rem" }}
            >
              {broadcasting ? "Broadcasting..." : "Broadcast Real-time Announcement"}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
export default AdminNotifications
