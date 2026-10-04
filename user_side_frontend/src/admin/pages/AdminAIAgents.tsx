import React, { useEffect, useState } from "react"
import { adminApi } from "../services/adminApi"
import { RobotIcon } from "../components/AdminIcons"

export const AdminAIAgents: React.FC = () => {
  const [agents, setAgents] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedAgent, setSelectedAgent] = useState<any>(null)
  const [editFormData, setEditFormData] = useState({
    model_name: "",
    temperature: 0.7,
    max_tokens: 1500,
    system_prompt: "",
    is_active: true,
  })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadAgents()
  }, [])

  const loadAgents = async () => {
    try {
      setLoading(true)
      const data = await adminApi.getAIAgents()
      setAgents(data || [])
    } catch (err) {
      console.error("Failed to load AI agents:", err)
    } finally {
      setLoading(false)
    }
  }

  const handleOpenEdit = (agent: any) => {
    setSelectedAgent(agent)
    setEditFormData({
      model_name: agent.model_name,
      temperature: agent.temperature,
      max_tokens: agent.max_tokens,
      system_prompt: agent.system_prompt,
      is_active: agent.is_active,
    })
  }

  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedAgent) return
    try {
      setSaving(true)
      await adminApi.updateAIAgent(selectedAgent.id, editFormData)
      setSelectedAgent(null)
      loadAgents()
    } catch (err: any) {
      alert(err.message || "Failed to update agent config")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">AI Agents & System Personas</h1>
          <p className="admin-page-subtitle">
            Configure prompt architectures, temperature sampling, and underlying LLM engines
          </p>
        </div>
      </div>

      {loading ? (
        <div style={{ padding: "3rem", textAlign: "center", color: "#94a3b8" }}>
          Loading AI agent architectures...
        </div>
      ) : agents.length === 0 ? (
        <div className="admin-card" style={{ textAlign: "center", padding: "3rem", color: "#64748b" }}>
          No AI Agent configurations found. Ensure backend default seeds have run.
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1.25rem" }}>
          {agents.map((ag) => (
            <div
              key={ag.id}
              className="admin-card"
              style={{
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                gap: "1rem",
              }}
            >
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <div style={{ padding: "0.5rem", borderRadius: "8px", background: "rgba(99, 102, 241, 0.15)", color: "#818cf8" }}>
                      <RobotIcon size={18} />
                    </div>
                    <div>
                      <h3 style={{ fontSize: "1rem", fontWeight: 700, color: "#f8fafc" }}>
                        {ag.agent_name.replace(/_/g, " ").toUpperCase()}
                      </h3>
                      <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
                        Provider: {ag.model_provider}
                      </span>
                    </div>
                  </div>
                  <span className={`admin-badge ${ag.is_active ? "admin-badge-success" : "admin-badge-danger"}`}>
                    {ag.is_active ? "Active" : "Disabled"}
                  </span>
                </div>

                <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.75rem" }}>
                  <span className="admin-badge admin-badge-info" style={{ fontFamily: "monospace" }}>
                    {ag.model_name}
                  </span>
                  <span className="admin-badge admin-badge-secondary">
                    Temp: {ag.temperature}
                  </span>
                  <span className="admin-badge admin-badge-secondary">
                    Max: {ag.max_tokens}
                  </span>
                </div>

                <div style={{ fontSize: "0.8rem", color: "#94a3b8", background: "rgba(0,0,0,0.3)", padding: "0.75rem", borderRadius: "8px", maxHeight: "120px", overflowY: "auto", fontFamily: "monospace" }}>
                  {ag.system_prompt}
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: "0.75rem" }}>
                <button
                  onClick={() => handleOpenEdit(ag)}
                  className="admin-btn admin-btn-secondary"
                  style={{ padding: "0.35rem 0.8rem", fontSize: "0.8rem" }}
                >
                  Tune Persona
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Edit Config Modal */}
      {selectedAgent && (
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
            onSubmit={handleSaveConfig}
            style={{
              background: "#1e293b",
              border: "1px solid rgba(255, 255, 255, 0.12)",
              borderRadius: "16px",
              width: "100%",
              maxWidth: "650px",
              padding: "2rem",
              color: "#f8fafc",
            }}
          >
            <h3 style={{ fontSize: "1.25rem", fontWeight: 700, marginBottom: "0.5rem" }}>
              Tune AI Agent: {selectedAgent.agent_name.replace(/_/g, " ").toUpperCase()}
            </h3>
            <p style={{ color: "#94a3b8", fontSize: "0.85rem", marginBottom: "1.25rem" }}>
              API Keys are securely isolated on the backend. This modal configures generation hyperparameters.
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                  Model Engine
                </label>
                <input
                  type="text"
                  required
                  value={editFormData.model_name}
                  onChange={(e) => setEditFormData({ ...editFormData, model_name: e.target.value })}
                  className="admin-input"
                  style={{ width: "100%" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                  Temperature
                </label>
                <input
                  type="number"
                  step="0.05"
                  min="0"
                  max="1.5"
                  required
                  value={editFormData.temperature}
                  onChange={(e) => setEditFormData({ ...editFormData, temperature: parseFloat(e.target.value) })}
                  className="admin-input"
                  style={{ width: "100%" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                  Max Tokens
                </label>
                <input
                  type="number"
                  step="100"
                  min="100"
                  max="8000"
                  required
                  value={editFormData.max_tokens}
                  onChange={(e) => setEditFormData({ ...editFormData, max_tokens: parseInt(e.target.value) })}
                  className="admin-input"
                  style={{ width: "100%" }}
                />
              </div>
            </div>

            <div style={{ marginBottom: "1.5rem" }}>
              <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                System Persona & Conditioning Prompt
              </label>
              <textarea
                rows={8}
                required
                value={editFormData.system_prompt}
                onChange={(e) => setEditFormData({ ...editFormData, system_prompt: e.target.value })}
                className="admin-input"
                style={{ width: "100%", fontFamily: "monospace", fontSize: "0.85rem", resize: "vertical" }}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem" }}>
              <button
                type="button"
                onClick={() => setSelectedAgent(null)}
                className="admin-btn admin-btn-secondary"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="admin-btn admin-btn-primary"
              >
                {saving ? "Saving Changes..." : "Commit Persona"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
export default AdminAIAgents
