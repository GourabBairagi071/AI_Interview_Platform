import React, { useEffect, useState } from "react"
import { adminApi } from "../services/adminApi"

export const AdminSettings: React.FC = () => {
  const [settings, setSettings] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [editingKey, setEditingKey] = useState<string | null>(null)
  const [editValue, setEditValue] = useState<any>("")
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      setLoading(true)
      const data = await adminApi.getSettings()
      setSettings(data || [])
    } catch (err) {
      console.error("Failed to load settings:", err)
    } finally {
      setLoading(false)
    }
  }

  const handleStartEdit = (s: any) => {
    setEditingKey(s.key)
    setEditValue(typeof s.value === "object" ? JSON.stringify(s.value) : s.value)
  }

  const handleSave = async (key: string) => {
    try {
      setSaving(true)
      let parsed = editValue
      if (typeof editValue === "string") {
        if (editValue.toLowerCase() === "true") parsed = true
        else if (editValue.toLowerCase() === "false") parsed = false
        else if (!isNaN(Number(editValue)) && editValue.trim() !== "") parsed = Number(editValue)
        else {
          try {
            parsed = JSON.parse(editValue)
          } catch {
            parsed = editValue
          }
        }
      }
      await adminApi.updateSetting(key, parsed)
      setEditingKey(null)
      loadSettings()
    } catch (err: any) {
      alert(err.message || "Failed to update system setting")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem", maxWidth: "900px" }}>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Global System Configurations</h1>
          <p className="admin-page-subtitle">
            Fine-tune operational switches, maintenance toggles, and LLM inference defaults
          </p>
        </div>
      </div>

      {loading ? (
        <div style={{ padding: "3rem", textAlign: "center", color: "#94a3b8" }}>
          Loading system parameters...
        </div>
      ) : settings.length === 0 ? (
        <div className="admin-card" style={{ padding: "3rem", textAlign: "center", color: "#64748b" }}>
          No system settings registered. Ensure default seeds have executed.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {settings.map((s) => (
            <div
              key={s.key}
              className="admin-card"
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                flexWrap: "wrap",
                gap: "1rem",
              }}
            >
              <div style={{ flex: "1 1 300px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span style={{ fontFamily: "monospace", fontWeight: 700, color: "#f8fafc", fontSize: "0.95rem" }}>
                    {s.key}
                  </span>
                  <span className="admin-badge admin-badge-info" style={{ fontSize: "0.65rem" }}>
                    {s.category || "GENERAL"}
                  </span>
                </div>
                <p style={{ color: "#94a3b8", fontSize: "0.825rem", marginTop: "0.25rem" }}>
                  {s.description || "System runtime configuration parameter"}
                </p>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                {editingKey === s.key ? (
                  <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                    <input
                      type="text"
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      className="admin-input"
                      style={{ width: "200px" }}
                    />
                    <button
                      onClick={() => handleSave(s.key)}
                      disabled={saving}
                      className="admin-btn admin-btn-primary"
                      style={{ padding: "0.35rem 0.75rem", fontSize: "0.8rem" }}
                    >
                      {saving ? "Saving..." : "Save"}
                    </button>
                    <button
                      onClick={() => setEditingKey(null)}
                      className="admin-btn admin-btn-secondary"
                      style={{ padding: "0.35rem 0.75rem", fontSize: "0.8rem" }}
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                    <span
                      style={{
                        padding: "0.3rem 0.75rem",
                        background: "rgba(0,0,0,0.3)",
                        borderRadius: "6px",
                        fontFamily: "monospace",
                        color: typeof s.value === "boolean" ? (s.value ? "#34d399" : "#f87171") : "#38bdf8",
                        fontWeight: 600,
                        fontSize: "0.85rem",
                      }}
                    >
                      {String(s.value)}
                    </span>
                    <button
                      onClick={() => handleStartEdit(s)}
                      className="admin-btn admin-btn-secondary"
                      style={{ padding: "0.35rem 0.75rem", fontSize: "0.8rem" }}
                    >
                      Edit
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
export default AdminSettings
