import { useRef, useState } from "react"
import type { FormEvent } from "react"
import { useNavigate } from "react-router-dom"

import "./InterviewSetup.css"

const API_BASE_URL = "http://127.0.0.1:8000/api/v1"

const ROLE_OPTIONS = [
  { role: "Software Engineer", icon: "</>" },
  { role: "Frontend Developer", icon: "◆" },
  { role: "Backend Developer", icon: "⌘" },
  { role: "Full Stack Developer", icon: "⎔" },
  { role: "Data Scientist", icon: "◈" },
  { role: "ML / AI Engineer", icon: "✦" },
  { role: "DevOps Engineer", icon: "⚙" },
  { role: "System Architect", icon: "▦" },
]

const EXPERIENCE_LEVELS = [
  { level: "Junior", label: "Junior / Entry", desc: "0-2 years experience" },
  { level: "Mid-Level", label: "Mid-Level", desc: "3-5 years experience" },
  { level: "Senior", label: "Senior", desc: "5-8 years experience" },
  { level: "Lead", label: "Lead / Principal", desc: "8+ years experience" },
]

const DIFFICULTIES = [
  { key: "easy", label: "Easy", desc: "Fundamental questions" },
  { key: "medium", label: "Medium", desc: "Interview-standard questions" },
  { key: "hard", label: "Hard", desc: "Advanced & edge cases" },
]

const INTERVIEW_TYPES = [
  { type: "Technical", label: "Technical", desc: "Algorithms, coding & core concepts", icon: "💻" },
  { type: "System Design", label: "System Design", desc: "Scalability, architecture & trade-offs", icon: "🏛️" },
  { type: "Behavioral", label: "Behavioral", desc: "STAR method, teamwork & leadership", icon: "🤝" },
  { type: "Mixed", label: "Mixed", desc: "Comprehensive blend of tech & soft skills", icon: "⚡" },
]

const QUESTION_COUNTS = [
  { count: 3, label: "3 Questions", desc: "Quick sprint (~10 mins)" },
  { count: 5, label: "5 Questions", desc: "Standard session (~20 mins)" },
  { count: 7, label: "7 Questions", desc: "Comprehensive mock (~30 mins)" },
]

function InterviewSetup() {
  const navigate = useNavigate()

  const [jobRole, setJobRole] = useState("Software Engineer")
  const [customRole, setCustomRole] = useState("")
  const [isCustomRole, setIsCustomRole] = useState(false)
  const [experienceLevel, setExperienceLevel] = useState("Mid-Level")
  const [difficulty, setDifficulty] = useState("medium")
  const [interviewType, setInterviewType] = useState("Technical")
  const [numberOfQuestions, setNumberOfQuestions] = useState(5)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const isSubmittingRef = useRef(false)

  const effectiveJobRole = isCustomRole ? customRole.trim() : jobRole

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (isSubmittingRef.current || loading) {
      return
    }

    if (!effectiveJobRole) {
      setError("Please select or enter a target job role.")
      return
    }

    const token = localStorage.getItem("access_token")

    if (!token) {
      navigate("/login")
      return
    }

    isSubmittingRef.current = true
    setLoading(true)
    setError("")

    try {
      const response = await fetch(`${API_BASE_URL}/interview`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          job_role: effectiveJobRole,
          difficulty: difficulty,
          experience_level: experienceLevel,
          interview_type: interviewType,
          number_of_questions: numberOfQuestions,
        }),
      })

      if (response.status === 401) {
        localStorage.removeItem("access_token")
        navigate("/login")
        return
      }

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || "Failed to create interview session")
      }

      const interviewId = data.interview?.id

      if (!interviewId) {
        throw new Error("Interview was created but session ID is missing")
      }

      navigate(`/interview/${interviewId}`)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Something went wrong creating the interview session.",
      )
    } finally {
      setLoading(false)
      isSubmittingRef.current = false
    }
  }

  return (
    <div className="setup-page">
      {/* BACK */}
      <button
        type="button"
        className="back-button"
        onClick={() => navigate("/dashboard")}
      >
        ← Back to Dashboard
      </button>

      <div className="setup-container">
        {/* HEADER */}
        <div className="setup-header">
          <div className="setup-logo">AI</div>
          <h1>Configure Your AI Interview</h1>
          <p>
            Tailor the interview parameters to match your preparation goals, seniority, and target role.
          </p>
          <div style={{ display: "inline-flex", alignItems: "center", gap: "6px", padding: "4px 12px", borderRadius: "999px", background: "rgba(59, 130, 246, 0.1)", border: "1px solid rgba(59, 130, 246, 0.25)", color: "#93c5fd", fontSize: "0.78rem", fontWeight: 500, marginTop: "8px" }}>
            <span>⚡ RAG Grounded</span>
            <span style={{ opacity: 0.5 }}>•</span>
            <span>5,700+ Semantic Question Bank</span>
          </div>
        </div>

        {/* CARD */}
        <form className="setup-card" onSubmit={handleSubmit}>

          {/* 1. TARGET JOB ROLE */}
          <div className="setup-section">
            <label>1. Target Job Role</label>
            <p className="section-description">
              Select your target position or specify a custom role.
            </p>

            <div className="role-grid">
              {ROLE_OPTIONS.map((item) => (
                <button
                  type="button"
                  key={item.role}
                  className={`role-option ${
                    !isCustomRole && jobRole === item.role ? "selected" : ""
                  }`}
                  onClick={() => {
                    setIsCustomRole(false)
                    setJobRole(item.role)
                  }}
                >
                  <span className="role-icon">{item.icon}</span>
                  <span>{item.role}</span>
                </button>
              ))}

              <button
                type="button"
                className={`role-option custom-role-btn ${isCustomRole ? "selected" : ""}`}
                onClick={() => setIsCustomRole(true)}
              >
                <span className="role-icon">✎</span>
                <span>Other / Custom</span>
              </button>
            </div>

            {isCustomRole && (
              <div className="custom-role-input-box">
                <input
                  type="text"
                  placeholder="e.g. Cloud Security Specialist, iOS Engineer, QA Automation"
                  value={customRole}
                  onChange={(e) => setCustomRole(e.target.value)}
                  autoFocus
                  required={isCustomRole}
                />
              </div>
            )}
          </div>

          {/* 2. EXPERIENCE LEVEL */}
          <div className="setup-section">
            <label>2. Experience Level</label>
            <p className="section-description">
              Align question complexity and expectations with your seniority.
            </p>

            <div className="level-grid">
              {EXPERIENCE_LEVELS.map((item) => (
                <button
                  type="button"
                  key={item.level}
                  className={`option-card ${experienceLevel === item.level ? "selected" : ""}`}
                  onClick={() => setExperienceLevel(item.level)}
                >
                  <strong>{item.label}</strong>
                  <small>{item.desc}</small>
                </button>
              ))}
            </div>
          </div>

          {/* 3. DIFFICULTY */}
          <div className="setup-section">
            <label>3. Question Difficulty</label>
            <p className="section-description">
              Choose the depth and rigor for the interview questions.
            </p>

            <div className="difficulty-grid">
              {DIFFICULTIES.map((item) => (
                <button
                  type="button"
                  key={item.key}
                  className={`difficulty-option ${item.key} ${
                    difficulty === item.key ? "selected" : ""
                  }`}
                  onClick={() => setDifficulty(item.key)}
                >
                  <span className="difficulty-dot" />
                  <span>
                    <strong>{item.label}</strong>
                    <small>{item.desc}</small>
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* 4. INTERVIEW TYPE */}
          <div className="setup-section">
            <label>4. Interview Format & Type</label>
            <p className="section-description">
              Pick the focus domain to be evaluated by the AI interviewer.
            </p>

            <div className="type-grid">
              {INTERVIEW_TYPES.map((item) => (
                <button
                  type="button"
                  key={item.type}
                  className={`option-card type-option ${interviewType === item.type ? "selected" : ""}`}
                  onClick={() => setInterviewType(item.type)}
                >
                  <span className="type-badge">{item.icon}</span>
                  <div>
                    <strong>{item.label}</strong>
                    <small>{item.desc}</small>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* 5. NUMBER OF QUESTIONS */}
          <div className="setup-section">
            <label>5. Session Length & Question Count</label>
            <p className="section-description">
              Select how many questions you'd like to answer in this session.
            </p>

            <div className="count-grid">
              {QUESTION_COUNTS.map((item) => (
                <button
                  type="button"
                  key={item.count}
                  className={`option-card count-option ${
                    numberOfQuestions === item.count ? "selected" : ""
                  }`}
                  onClick={() => setNumberOfQuestions(item.count)}
                >
                  <span className="count-number">{item.count}</span>
                  <div>
                    <strong>{item.label}</strong>
                    <small>{item.desc}</small>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* SUMMARY CARD */}
          <div className="interview-summary">
            <div className="summary-item">
              <span>TARGET ROLE</span>
              <strong>{effectiveJobRole || "Not specified"}</strong>
            </div>

            <div className="summary-divider" />

            <div className="summary-item">
              <span>EXPERIENCE</span>
              <strong>{experienceLevel}</strong>
            </div>

            <div className="summary-divider" />

            <div className="summary-item">
              <span>DIFFICULTY</span>
              <strong>{difficulty.charAt(0).toUpperCase() + difficulty.slice(1)}</strong>
            </div>

            <div className="summary-divider" />

            <div className="summary-item">
              <span>TYPE</span>
              <strong>{interviewType}</strong>
            </div>

            <div className="summary-divider" />

            <div className="summary-item">
              <span>QUESTIONS</span>
              <strong>{numberOfQuestions} Qs</strong>
            </div>
          </div>

          {/* ERROR */}
          {error && <div className="setup-error">{error}</div>}

          {/* SUBMIT BUTTON */}
          <button
            type="submit"
            className="start-interview-button"
            disabled={loading || !effectiveJobRole}
          >
            {loading ? (
              <span className="button-loading-content">
                <span className="button-spinner" /> Generating AI Interview Session...
              </span>
            ) : (
              <>
                Start AI Interview <span>→</span>
              </>
            )}
          </button>
        </form>

        {/* FOOTER */}
        <p className="setup-footer">
          Your interview will be powered by real-time voice and conversational AI. You can pause or resume anytime.
        </p>
      </div>
    </div>
  )
}

export default InterviewSetup