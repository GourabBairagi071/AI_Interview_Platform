import { useState } from "react"
import type { FormEvent } from "react"
import { useNavigate } from "react-router-dom"

import "./InterviewSetup.css"

const API_BASE_URL = "http://127.0.0.1:8000/api/v1"

function InterviewSetup() {
  const navigate = useNavigate()

  const [jobRole, setJobRole] = useState("Software Engineer")
  const [difficulty, setDifficulty] = useState("medium")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    const token = localStorage.getItem("access_token")

    if (!token) {
      navigate("/login")
      return
    }

    setLoading(true)
    setError("")

    try {
      const response = await fetch(
        `${API_BASE_URL}/interview`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            job_role: jobRole,
            difficulty: difficulty,
          }),
        },
      )

      if (response.status === 401) {
        localStorage.removeItem("access_token")
        navigate("/login")
        return
      }

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          data.detail || "Failed to create interview",
        )
      }

      const interviewId = data.interview?.id

      if (!interviewId) {
        throw new Error(
          "Interview created but ID was not returned",
        )
      }

      navigate(`/interview/${interviewId}`)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong",
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="setup-page">

      {/* BACK */}

      <button
        className="back-button"
        onClick={() => navigate("/dashboard")}
      >
        ← Back to Dashboard
      </button>

      <div className="setup-container">

        {/* HEADER */}

        <div className="setup-header">

          <div className="setup-logo">
            AI
          </div>

          <h1>
            Setup Your Interview
          </h1>

          <p>
            Customize your AI-powered interview
            experience before you begin.
          </p>

        </div>

        {/* CARD */}

        <form
          className="setup-card"
          onSubmit={handleSubmit}
        >

          {/* JOB ROLE */}

          <div className="setup-section">

            <label>
              What role are you preparing for?
            </label>

            <p className="section-description">
              Choose the role that best matches
              your target position.
            </p>

            <div className="role-grid">

              {[
                "Software Engineer",
                "Data Scientist",
                "ML Engineer",
                "AI Engineer",
                "Backend Developer",
                "Frontend Developer",
              ].map((role) => (

                <button
                  type="button"
                  key={role}
                  className={`role-option ${
                    jobRole === role
                      ? "selected"
                      : ""
                  }`}
                  onClick={() =>
                    setJobRole(role)
                  }
                >

                  <span className="role-icon">
                    {role === "Software Engineer"
                      ? "</>"
                      : role === "Data Scientist"
                      ? "◈"
                      : role === "ML Engineer"
                      ? "✦"
                      : role === "AI Engineer"
                      ? "AI"
                      : role === "Backend Developer"
                      ? "⌘"
                      : "◆"}
                  </span>

                  <span>
                    {role}
                  </span>

                </button>

              ))}

            </div>

          </div>

          {/* DIFFICULTY */}

          <div className="setup-section">

            <label>
              Select difficulty
            </label>

            <p className="section-description">
              Choose the level that matches your
              current preparation.
            </p>

            <div className="difficulty-grid">

              <button
                type="button"
                className={`difficulty-option easy ${
                  difficulty === "easy"
                    ? "selected"
                    : ""
                }`}
                onClick={() =>
                  setDifficulty("easy")
                }
              >
                <span className="difficulty-dot" />
                <span>
                  <strong>Easy</strong>
                  <small>
                    Fundamental questions
                  </small>
                </span>
              </button>

              <button
                type="button"
                className={`difficulty-option medium ${
                  difficulty === "medium"
                    ? "selected"
                    : ""
                }`}
                onClick={() =>
                  setDifficulty("medium")
                }
              >
                <span className="difficulty-dot" />
                <span>
                  <strong>Medium</strong>
                  <small>
                    Interview-level questions
                  </small>
                </span>
              </button>

              <button
                type="button"
                className={`difficulty-option hard ${
                  difficulty === "hard"
                    ? "selected"
                    : ""
                }`}
                onClick={() =>
                  setDifficulty("hard")
                }
              >
                <span className="difficulty-dot" />
                <span>
                  <strong>Hard</strong>
                  <small>
                    Advanced questions
                  </small>
                </span>
              </button>

            </div>

          </div>

          {/* SUMMARY */}

          <div className="interview-summary">

            <div className="summary-item">
              <span>Role</span>
              <strong>{jobRole}</strong>
            </div>

            <div className="summary-divider" />

            <div className="summary-item">
              <span>Difficulty</span>
              <strong>
                {difficulty.charAt(0).toUpperCase() +
                  difficulty.slice(1)}
              </strong>
            </div>

            <div className="summary-divider" />

            <div className="summary-item">
              <span>Powered by</span>
              <strong>AI Interviewer</strong>
            </div>

          </div>

          {/* ERROR */}

          {error && (
            <div className="setup-error">
              {error}
            </div>
          )}

          {/* SUBMIT */}

          <button
            type="submit"
            className="start-interview-button"
            disabled={loading}
          >
            {loading
              ? "Creating Interview..."
              : "Start AI Interview"}

            {!loading && (
              <span>→</span>
            )}
          </button>

        </form>

        {/* FOOTER */}

        <p className="setup-footer">
          You can leave the interview anytime and
          continue later.
        </p>

      </div>

    </div>
  )
}

export default InterviewSetup