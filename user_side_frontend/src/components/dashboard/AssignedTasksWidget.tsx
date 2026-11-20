import React, { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  getCandidateAssignments,
  startCandidateAssignment,
  submitCandidateAssignment,
} from "../../services/api"

export const AssignedTasksWidget: React.FC = () => {
  const navigate = useNavigate()
  const [tasks, setTasks] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  // Custom Task / Submission Modal
  const [activeTaskModal, setActiveTaskModal] = useState<any | null>(null)
  const [submissionNotes, setSubmissionNotes] = useState("")
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    loadAssignedTasks()
  }, [])

  const loadAssignedTasks = async () => {
    try {
      setLoading(true)
      const data = await getCandidateAssignments()
      setTasks(data || [])
    } catch (err) {
      console.error("Failed to load assigned tasks:", err)
    } finally {
      setLoading(false)
    }
  }

  const handleLaunchTask = async (task: any) => {
    try {
      setActionLoading(task.id)

      // If assigned and not started yet, trigger start endpoint
      if (task.status === "ASSIGNED") {
        await startCandidateAssignment(task.assignment_id)
      }

      // Route according to assignment_type
      const type = (task.assignment_type || "").toUpperCase()
      const contentId = task.content_id

      if (type === "CODING_PROBLEM") {
        if (contentId) {
          navigate(`/coding/${contentId}`)
        } else {
          navigate("/coding")
        }
      } else if (type === "AI_INTERVIEW" || type === "INTERVIEW_TEMPLATE") {
        navigate("/interview-setup")
      } else if (type === "QUESTION" || type === "PRACTICE_SET") {
        navigate("/practice")
      } else if (type === "CONTEST") {
        if (contentId) {
          navigate(`/contests/${contentId}`)
        } else {
          navigate("/contests")
        }
      } else if (type === "ROADMAP") {
        navigate("/learning")
      } else if (type === "RESOURCE") {
        if (task.content_payload?.url) {
          window.open(task.content_payload.url, "_blank")
        } else {
          navigate("/learning")
        }
      } else {
        // Custom Task / Assessment -> Open in-app execution modal
        setActiveTaskModal(task)
      }
    } catch (err: any) {
      alert(err.message || "Failed to launch task")
    } finally {
      setActionLoading(null)
    }
  }

  const handleSubmitModalTask = async () => {
    if (!activeTaskModal) return
    try {
      setSubmitting(true)
      await submitCandidateAssignment(activeTaskModal.assignment_id, {
        score: 100.0,
        submission_data: { notes: submissionNotes, submitted_at: new Date().toISOString() },
      })
      setActiveTaskModal(null)
      setSubmissionNotes("")
      loadAssignedTasks()
    } catch (err: any) {
      alert(err.message || "Failed to submit assignment")
    } finally {
      setSubmitting(false)
    }
  }

  // If no tasks assigned, return null or empty state
  if (!loading && tasks.length === 0) {
    return null
  }

  return (
    <div
      style={{
        background: "linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%)",
        border: "1px solid rgba(56, 189, 248, 0.25)",
        borderRadius: "16px",
        padding: "1.5rem",
        marginBottom: "2rem",
        boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 0 15px rgba(56, 189, 248, 0.1)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <div
            style={{
              width: "36px",
              height: "36px",
              borderRadius: "10px",
              background: "linear-gradient(135deg, #0284c7 0%, #38bdf8 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
              fontSize: "1.1rem",
            }}
          >
            📋
          </div>
          <div>
            <h3 style={{ fontSize: "1.15rem", fontWeight: 700, color: "#f8fafc", margin: 0 }}>
              My Assigned Tasks & Challenges
            </h3>
            <p style={{ fontSize: "0.8rem", color: "#94a3b8", margin: 0, marginTop: "0.15rem" }}>
              Direct assignments and milestone goals assigned to you
            </p>
          </div>
        </div>

        <button
          onClick={loadAssignedTasks}
          style={{
            background: "transparent",
            border: "1px solid rgba(255, 255, 255, 0.1)",
            borderRadius: "8px",
            color: "#94a3b8",
            fontSize: "0.75rem",
            padding: "0.35rem 0.75rem",
            cursor: "pointer",
          }}
        >
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
        {tasks.map((task) => {
          const isCompleted = task.status === "COMPLETED"
          const isExpired = task.status === "EXPIRED"
          const isInProgress = task.status === "IN_PROGRESS"
          const priority = task.priority || "MEDIUM"

          return (
            <div
              key={task.id}
              style={{
                background: "rgba(15, 23, 42, 0.6)",
                border: "1px solid rgba(255, 255, 255, 0.08)",
                borderRadius: "12px",
                padding: "1rem 1.25rem",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                flexWrap: "wrap",
                gap: "1rem",
              }}
            >
              <div style={{ flex: "1 1 300px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.35rem" }}>
                  <span
                    style={{
                      fontSize: "0.7rem",
                      fontWeight: 700,
                      padding: "0.15rem 0.5rem",
                      borderRadius: "6px",
                      background:
                        priority === "URGENT"
                          ? "rgba(239, 68, 68, 0.2)"
                          : priority === "HIGH"
                          ? "rgba(245, 158, 11, 0.2)"
                          : "rgba(56, 189, 248, 0.15)",
                      color:
                        priority === "URGENT"
                          ? "#f87171"
                          : priority === "HIGH"
                          ? "#fbbf24"
                          : "#38bdf8",
                    }}
                  >
                    {priority}
                  </span>
                  <span
                    style={{
                      fontSize: "0.7rem",
                      padding: "0.15rem 0.5rem",
                      borderRadius: "6px",
                      background: "rgba(255, 255, 255, 0.06)",
                      color: "#cbd5e1",
                    }}
                  >
                    {task.assignment_type.replace(/_/g, " ")}
                  </span>
                  {task.due_date && (
                    <span style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
                      • Due: {new Date(task.due_date).toLocaleDateString()}
                    </span>
                  )}
                </div>

                <div style={{ fontSize: "0.95rem", fontWeight: 600, color: "#f8fafc" }}>
                  {task.title}
                </div>
                {task.description && (
                  <div style={{ fontSize: "0.8rem", color: "#94a3b8", marginTop: "0.2rem" }}>
                    {task.description}
                  </div>
                )}
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "1.25rem" }}>
                {isCompleted ? (
                  <div style={{ textAlign: "right" }}>
                    <span
                      style={{
                        background: "rgba(52, 211, 153, 0.15)",
                        color: "#34d399",
                        padding: "0.25rem 0.6rem",
                        borderRadius: "8px",
                        fontSize: "0.75rem",
                        fontWeight: 700,
                      }}
                    >
                      ✓ Completed ({task.score}%)
                    </span>
                  </div>
                ) : isExpired ? (
                  <div>
                    <span
                      style={{
                        background: "rgba(239, 68, 68, 0.15)",
                        color: "#f87171",
                        padding: "0.25rem 0.6rem",
                        borderRadius: "8px",
                        fontSize: "0.75rem",
                        fontWeight: 600,
                      }}
                    >
                      Expired
                    </span>
                  </div>
                ) : (
                  <button
                    onClick={() => handleLaunchTask(task)}
                    disabled={actionLoading === task.id}
                    style={{
                      background: isInProgress
                        ? "linear-gradient(135deg, #0284c7 0%, #38bdf8 100%)"
                        : "linear-gradient(135deg, #4f46e5 0%, #6366f1 100%)",
                      color: "#fff",
                      border: "none",
                      borderRadius: "8px",
                      padding: "0.5rem 1.1rem",
                      fontSize: "0.825rem",
                      fontWeight: 600,
                      cursor: "pointer",
                      boxShadow: "0 4px 12px rgba(99, 102, 241, 0.3)",
                    }}
                  >
                    {actionLoading === task.id
                      ? "Launching..."
                      : isInProgress
                      ? "Continue Task"
                      : "Start Task"}
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* MODAL FOR DIRECT TASK VIEW / SUBMISSION */}
      {activeTaskModal && (
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
          <div
            style={{
              background: "#1e293b",
              border: "1px solid rgba(255, 255, 255, 0.12)",
              borderRadius: "16px",
              width: "100%",
              maxWidth: "560px",
              padding: "2rem",
              color: "#f8fafc",
            }}
          >
            <h3 style={{ fontSize: "1.25rem", fontWeight: 700, marginBottom: "0.5rem" }}>
              {activeTaskModal.title}
            </h3>
            <div style={{ fontSize: "0.85rem", color: "#38bdf8", marginBottom: "1rem" }}>
              Task Type: {activeTaskModal.assignment_type.replace(/_/g, " ")}
            </div>

            {activeTaskModal.instructions && (
              <div
                style={{
                  background: "rgba(15, 23, 42, 0.6)",
                  padding: "1rem",
                  borderRadius: "10px",
                  fontSize: "0.85rem",
                  color: "#cbd5e1",
                  marginBottom: "1.25rem",
                  lineHeight: 1.5,
                }}
              >
                <strong style={{ color: "#f8fafc", display: "block", marginBottom: "0.3rem" }}>
                  Instructions:
                </strong>
                {activeTaskModal.instructions}
              </div>
            )}

            <div style={{ marginBottom: "1.25rem" }}>
              <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.3rem" }}>
                Submission Notes / Completion Summary
              </label>
              <textarea
                rows={3}
                placeholder="Describe what you completed or provide links/answers..."
                value={submissionNotes}
                onChange={(e) => setSubmissionNotes(e.target.value)}
                style={{
                  width: "100%",
                  background: "rgba(15, 23, 42, 0.8)",
                  border: "1px solid rgba(255, 255, 255, 0.12)",
                  borderRadius: "8px",
                  padding: "0.75rem",
                  color: "#f8fafc",
                  fontSize: "0.85rem",
                }}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem" }}>
              <button
                type="button"
                onClick={() => setActiveTaskModal(null)}
                style={{
                  background: "transparent",
                  border: "1px solid rgba(255, 255, 255, 0.2)",
                  borderRadius: "8px",
                  padding: "0.5rem 1rem",
                  color: "#94a3b8",
                  cursor: "pointer",
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={submitting}
                onClick={handleSubmitModalTask}
                style={{
                  background: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
                  border: "none",
                  borderRadius: "8px",
                  padding: "0.5rem 1.25rem",
                  color: "#fff",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                {submitting ? "Submitting..." : "Submit Task"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
