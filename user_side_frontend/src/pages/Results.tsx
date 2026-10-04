import { useEffect, useMemo, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"

import {
  getInterview,
  getAntiCheatingSummary,
  getAntiCheatingEvents,
  type AntiCheatingSummary,
  type AntiCheatingEvent,
} from "../services/api"

import "./Results.css"


// ============================================================
// TYPES
// ============================================================

interface Interview {
  id: string
  user_id: string
  job_role: string
  difficulty: string
  status: string

  questions: string | null
  answers: string | null
  transcript: string | null

  score: number | null

  feedback: string | null
  strengths: string | null
  weaknesses: string | null

  question_evaluations: string | null

  started_at: string | null
  completed_at: string | null

  created_at: string
  updated_at: string
}

interface QuestionEvaluation {
  question?: string
  answer?: string
  score?: number
  feedback?: string
  evaluation?: string
  strengths?: string[]
  weaknesses?: string[]
}

interface ResultResponse {
  interview?: Interview
}


// ============================================================
// HELPERS
// ============================================================

function parseJSON(value: string | null) {
  if (!value) return null

  try {
    return JSON.parse(value)
  } catch {
    return null
  }
}


function parseList(value: string | null): string[] {
  if (!value) return []

  const parsed = parseJSON(value)

  if (Array.isArray(parsed)) {
    return parsed.map(String)
  }

  return value
    .split("\n")
    .map((item) =>
      item
        .replace(/^[-•*]\s*/, "")
        .trim(),
    )
    .filter(Boolean)
}


function parseQuestionEvaluations(
  value: string | null,
): QuestionEvaluation[] {

  if (!value) return []

  const parsed = parseJSON(value)

  if (Array.isArray(parsed)) {
    return parsed
  }

  if (
    parsed &&
    typeof parsed === "object"
  ) {
    const possible =
      parsed.evaluations ||
      parsed.questions ||
      parsed.results

    if (Array.isArray(possible)) {
      return possible
    }
  }

  return []
}


function formatDate(
  value: string | null,
) {

  if (!value) {
    return "Not available"
  }

  try {
    return new Date(value).toLocaleString(
      "en-US",
      {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit",
      },
    )
  } catch {
    return "Not available"
  }
}


function getScoreLabel(
  score: number,
) {

  if (score >= 90) return "Outstanding!"
  if (score >= 80) return "Excellent!"
  if (score >= 70) return "Very Good"
  if (score >= 60) return "Good"
  if (score >= 50) return "Needs Improvement"

  return "Keep Practicing"
}


function getScoreClass(
  score: number,
) {

  if (score >= 80) return "excellent"
  if (score >= 60) return "good"
  if (score >= 40) return "average"

  return "low"
}


function getDifficultyClass(
  difficulty: string,
) {

  const value =
    difficulty.toLowerCase()

  if (value === "easy") {
    return "easy"
  }

  if (value === "hard") {
    return "hard"
  }

  return "medium"
}


// ============================================================
// SCORE RING
// ============================================================

function ScoreRing({
  score,
}: {
  score: number
}) {

  const safeScore = Math.max(
    0,
    Math.min(100, score),
  )

  const radius = 70
  const circumference =
    2 * Math.PI * radius

  const offset =
    circumference -
    (safeScore / 100) *
      circumference

  return (
    <div className="score-ring">

      <svg
        viewBox="0 0 180 180"
        className="score-svg"
      >

        <circle
          cx="90"
          cy="90"
          r={radius}
          className="score-track"
        />

        <circle
          cx="90"
          cy="90"
          r={radius}
          className={`score-progress ${getScoreClass(
            safeScore,
          )}`}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />

      </svg>

      <div className="score-ring-content">

        <strong>
          {Math.round(safeScore)}
        </strong>

        <span>/100</span>

        <small>
          {getScoreLabel(safeScore)}
        </small>

      </div>

    </div>
  )
}


// ============================================================
// PAGE
// ============================================================

function Results() {

  const navigate = useNavigate()

  const { id } = useParams<{
    id: string
  }>()

  const [interview, setInterview] =
    useState<Interview | null>(null)

  const [antiCheatingSummary, setAntiCheatingSummary] =
    useState<AntiCheatingSummary | null>(null)

  const [antiCheatingEvents, setAntiCheatingEvents] =
    useState<AntiCheatingEvent[]>([])

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState("")


  // ==========================================================
  // LOAD RESULT
  // ==========================================================

  useEffect(() => {

    async function loadResult() {

      if (!id) {
        setError(
          "Interview result ID is missing.",
        )
        setLoading(false)
        return
      }

      try {

        const [response, summaryRes, eventsRes] = await Promise.all([
          getInterview(id),
          getAntiCheatingSummary(id).catch(() => null),
          getAntiCheatingEvents(id).catch(() => ({ events: [], total: 0 })),
        ])

        const result =
          response as ResultResponse

        const data =
          result.interview ||
          (response as Interview)

        if (!data?.id) {
          throw new Error(
            "Interview result not found.",
          )
        }

        setInterview(data)
        if (summaryRes) setAntiCheatingSummary(summaryRes)
        if (eventsRes?.events) setAntiCheatingEvents(eventsRes.events)

      } catch (err) {

        setError(
          err instanceof Error
            ? err.message
            : "Failed to load interview result.",
        )

      } finally {

        setLoading(false)

      }
    }

    loadResult()

  }, [id])


  // ==========================================================
  // DERIVED DATA
  // ==========================================================

  const score = useMemo(
    () =>
      Math.max(
        0,
        Math.min(
          100,
          Number(interview?.score ?? 0),
        ),
      ),
    [interview],
  )


  const strengths = useMemo(
    () =>
      parseList(
        interview?.strengths ?? null,
      ),
    [interview],
  )


  const weaknesses = useMemo(
    () =>
      parseList(
        interview?.weaknesses ?? null,
      ),
    [interview],
  )


  const evaluations = useMemo(
    () =>
      parseQuestionEvaluations(
        interview?.question_evaluations ??
          null,
      ),
    [interview],
  )


  // ==========================================================
  // SHARE
  // ==========================================================

  async function handleShare() {

    if (!interview) return

    const text =
      `AI Interview Result\n` +
      `${interview.job_role}\n` +
      `Score: ${Math.round(score)}/100`

    try {

      if (
        navigator.share
      ) {

        await navigator.share({
          title:
            "AI Interview Result",
          text,
          url:
            window.location.href,
        })

      } else {

        await navigator.clipboard.writeText(
          window.location.href,
        )

        alert(
          "Result link copied to clipboard.",
        )
      }

    } catch {
      // User cancelled sharing.
    }
  }


  // ==========================================================
  // PRINT / DOWNLOAD
  // ==========================================================

  function handleDownload() {
    window.print()
  }


  // ==========================================================
  // LOADING
  // ==========================================================

  if (loading) {

    return (
      <div className="results-page">

        <div className="results-loading">

          <div className="loading-spinner" />

          <h2>
            Generating your result...
          </h2>

          <p>
            We're preparing your AI interview
            performance report.
          </p>

        </div>

      </div>
    )
  }


  // ==========================================================
  // ERROR
  // ==========================================================

  if (error || !interview) {

    return (
      <div className="results-page">

        <div className="results-error">

          <div className="error-icon">
            !
          </div>

          <h2>
            Unable to load result
          </h2>

          <p>
            {error ||
              "Interview result could not be found."}
          </p>

          <button
            onClick={() =>
              navigate("/dashboard")
            }
          >
            ← Back to Dashboard
          </button>

        </div>

      </div>
    )
  }


  // ==========================================================
  // MAIN
  // ==========================================================

  return (
    <div className="results-page">

      {/* ======================================================
          HEADER
          ====================================================== */}

      <header className="results-header">

        <button
          className="results-back"
          onClick={() =>
            navigate("/dashboard")
          }
        >
          ← Dashboard
        </button>


        <div className="results-brand">

          <div className="results-logo">
            AI
          </div>

          <div>
            <strong>
              AI Interview
            </strong>

            <span>
              Performance Report
            </span>
          </div>

        </div>


        <div className="header-actions">

          <button
            className="share-button"
            onClick={handleShare}
          >
            <span>⌯</span>
            Share Result
          </button>

          <button
            className="download-button"
            onClick={handleDownload}
          >
            ↓
            Download Report
          </button>

        </div>

      </header>


      {/* ======================================================
          CONTENT
          ====================================================== */}

      <main className="results-container">


        {/* ====================================================
            TITLE
            ==================================================== */}

        <section className="results-title">

          <div className="title-row">

            <div>

              <span className="results-eyebrow">
                INTERVIEW COMPLETED
              </span>

              <h1>
                Interview Result
              </h1>

              <p>
                Great job! Here's your complete
                AI-powered interview performance.
              </p>

            </div>

            <div
              className={`status-pill ${
                interview.status
              }`}
            >
              <span />
              {interview.status}
            </div>

          </div>

        </section>


        {/* ====================================================
            TOP GRID
            ==================================================== */}

        <section className="top-result-grid">


          {/* INTERVIEW CARD */}

          <div className="interview-card">

            <div className="card-label">
              INTERVIEW
            </div>

            <h2>
              {interview.job_role}
            </h2>

            <div className="interview-meta">

              <div className="meta-item">

                <span>
                  Difficulty
                </span>

                <strong
                  className={`difficulty-badge ${getDifficultyClass(
                    interview.difficulty,
                  )}`}
                >
                  {interview.difficulty}
                </strong>

              </div>


              <div className="meta-item">

                <span>
                  Completed
                </span>

                <strong>
                  {formatDate(
                    interview.completed_at,
                  )}
                </strong>

              </div>


              <div className="meta-item">

                <span>
                  Started
                </span>

                <strong>
                  {formatDate(
                    interview.started_at,
                  )}
                </strong>

              </div>

            </div>

          </div>


          {/* SCORE CARD */}

          <div className="overall-score-card">

            <div>

              <span className="card-label">
                OVERALL SCORE
              </span>

              <h3>
                Your Interview Performance
              </h3>

            </div>

            <ScoreRing
              score={score}
            />

          </div>

        </section>


        {/* ====================================================
            QUICK STATS
            ==================================================== */}

        <section className="stats-grid">

          <div className="stat-card">

            <span>
              SCORE
            </span>

            <strong>
              {Math.round(score)}/100
            </strong>

          </div>


          <div className="stat-card">

            <span>
              DIFFICULTY
            </span>

            <strong>
              {interview.difficulty}
            </strong>

          </div>


          <div className="stat-card">

            <span>
              QUESTIONS
            </span>

            <strong>
              {evaluations.length ||
                "AI Evaluated"}
            </strong>

          </div>


          <div className="stat-card">

            <span>
              STATUS
            </span>

            <strong className="completed">
              Completed
            </strong>

          </div>

        </section>


        {/* ====================================================
            AI FEEDBACK
            ==================================================== */}

        <section className="result-section">

          <div className="section-heading">

            <div className="section-number">
              01
            </div>

            <div>

              <h2>
                AI Feedback
              </h2>

              <p>
                Detailed feedback generated by
                your AI interviewer.
              </p>

            </div>

          </div>


          <div className="feedback-card">

            <div className="feedback-icon">
              ✦
            </div>

            <div>

              <div className="feedback-title">
                Overall Assessment
              </div>

              <p>
                {interview.feedback ||
                  "No detailed feedback was generated for this interview."}
              </p>

            </div>

          </div>

        </section>


        {/* ====================================================
            STRENGTHS + WEAKNESSES
            ==================================================== */}

        <section className="result-section">

          <div className="section-heading">

            <div className="section-number">
              02
            </div>

            <div>

              <h2>
                Performance Insights
              </h2>

              <p>
                Understand what's working and
                where you can improve.
              </p>

            </div>

          </div>


          <div className="two-column">


            {/* STRENGTHS */}

            <div className="insight-card">

              <div className="insight-header">

                <div className="insight-icon strength">
                  ✓
                </div>

                <div>

                  <h3>
                    Strengths
                  </h3>

                  <span>
                    Areas where you performed well
                  </span>

                </div>

              </div>


              {strengths.length > 0 ? (

                <ul>

                  {strengths.map(
                    (item, index) => (

                      <li key={index}>
                        <span className="bullet-check">
                          ✓
                        </span>

                        {item}
                      </li>

                    ),
                  )}

                </ul>

              ) : (

                <p className="empty-text">
                  No strengths were recorded.
                </p>

              )}

            </div>


            {/* WEAKNESSES */}

            <div className="insight-card">

              <div className="insight-header">

                <div className="insight-icon weakness">
                  !
                </div>

                <div>

                  <h3>
                    Areas to Improve
                  </h3>

                  <span>
                    Focus areas for your next interview
                  </span>

                </div>

              </div>


              {weaknesses.length > 0 ? (

                <ul>

                  {weaknesses.map(
                    (item, index) => (

                      <li key={index}>
                        <span className="bullet-warning">
                          !
                        </span>

                        {item}
                      </li>

                    ),
                  )}

                </ul>

              ) : (

                <p className="empty-text">
                  No major weaknesses were recorded.
                </p>

              )}

            </div>

          </div>

        </section>


        {/* ====================================================
            QUESTION ANALYSIS
            ==================================================== */}

        {evaluations.length > 0 && (

          <section className="result-section">

            <div className="section-heading">

              <div className="section-number">
                03
              </div>

              <div>

                <h2>
                  Question Analysis
                </h2>

                <p>
                  See how the AI evaluated your
                  individual answers.
                </p>

              </div>

            </div>


            <div className="question-list">

              {evaluations.map(
                (evaluation, index) => {

                  const questionScore =
                    Number(
                      evaluation.score ?? 0,
                    )

                  return (

                    <div
                      className="question-result"
                      key={index}
                    >

                      <div className="question-top">

                        <span className="question-number">
                          QUESTION{" "}
                          {String(index + 1).padStart(
                            2,
                            "0",
                          )}
                        </span>

                        <span
                          className={`question-score ${getScoreClass(
                            questionScore,
                          )}`}
                        >
                          {evaluation.score !==
                          undefined
                            ? `${Math.round(
                                questionScore,
                              )}/100`
                            : "Evaluated"}
                        </span>

                      </div>


                      {evaluation.question && (

                        <h3>
                          {evaluation.question}
                        </h3>

                      )}


                      {evaluation.answer && (

                        <div className="answer-box">

                          <span>
                            YOUR ANSWER
                          </span>

                          <p>
                            {evaluation.answer}
                          </p>

                        </div>

                      )}


                      {(evaluation.feedback ||
                        evaluation.evaluation) && (

                        <p className="question-feedback">

                          {evaluation.feedback ||
                            evaluation.evaluation}

                        </p>

                      )}

                    </div>

                  )
                },
              )}

            </div>

          </section>

        )}


        {/* ====================================================
            INTERVIEW ANALYSIS
            ==================================================== */}

        <section className="result-section">

          <div className="section-heading">

            <div className="section-number">
              04
            </div>

            <div>

              <h2>
                Interview Performance Analysis
              </h2>

              <p>
                A high-level view of your interview
                readiness.
              </p>

            </div>

          </div>


          <div className="analysis-grid">


            <div className="analysis-card">

              <div className="analysis-icon">
                ◉
              </div>

              <div>

                <span>
                  OVERALL PERFORMANCE
                </span>

                <strong>
                  {getScoreLabel(score)}
                </strong>

                <p>
                  Your overall interview score
                  reflects your responses,
                  communication and technical
                  understanding.
                </p>

              </div>

            </div>


            <div className="analysis-card">

              <div className="analysis-icon">
                AI
              </div>

              <div>

                <span>
                  AI EVALUATION
                </span>

                <strong>
                  AI Powered
                </strong>

                <p>
                  Your answers were analyzed using
                  the AI interview evaluation system.
                </p>

              </div>

            </div>


            <div className="analysis-card">

              <div className="analysis-icon">
                ↗
              </div>

              <div>

                <span>
                  NEXT STEP
                </span>

                <strong>
                  Keep Practicing
                </strong>

                <p>
                  Review your weak areas and take
                  another mock interview.
                </p>

              </div>

            </div>

          </div>

        </section>


        {/* ====================================================
            INTERVIEW INTEGRITY & ANTI-CHEATING REPORT
            ==================================================== */}

        <section className="result-section">

          <div className="section-heading">

            <div className="section-number">
              04
            </div>

            <div>

              <h2>
                Interview Integrity & Anti-Cheating
              </h2>

              <p>
                Automated computer-vision analysis of candidate presence, identity, and session authenticity.
              </p>

            </div>

          </div>

          <div className="integrity-overview-card">

            <div className="integrity-status-banner">

              <div className="integrity-status-info">

                <span className="integrity-tag">
                  PROCTORING ASSESSMENT STATUS
                </span>

                <div className="integrity-status-row">

                  <span
                    className={`integrity-status-badge status-${(
                      antiCheatingSummary?.overall_status || "CLEAR"
                    ).toLowerCase()}`}
                  >
                    <span className="integrity-dot" />
                    {antiCheatingSummary?.overall_status === "CLEAR"
                      ? "Integrity Verified • CLEAR"
                      : antiCheatingSummary?.overall_status === "REVIEW"
                        ? "Review Advised • REVIEW"
                        : "Suspicious Activity Detected • SUSPICIOUS"}
                  </span>

                  <span className="integrity-risk-badge">
                    Risk Score:{" "}
                    <strong>
                      {antiCheatingSummary?.risk_score ?? 0}
                    </strong>{" "}
                    / 100
                  </span>

                </div>

              </div>

            </div>

            {/* INTEGRITY METRICS GRID */}
            <div className="integrity-metrics-grid">

              <div className="integrity-metric">
                <span>Total Suspicious Events</span>
                <strong>{antiCheatingSummary?.total_events ?? 0}</strong>
              </div>

              <div className="integrity-metric">
                <span>Face Missing Events</span>
                <strong>{antiCheatingSummary?.face_missing_events ?? 0}</strong>
              </div>

              <div className="integrity-metric">
                <span>Multiple-Person Events</span>
                <strong>{antiCheatingSummary?.multiple_person_events ?? 0}</strong>
              </div>

              <div className="integrity-metric">
                <span>Identity Mismatch Events</span>
                <strong>{antiCheatingSummary?.identity_mismatch_events ?? 0}</strong>
              </div>

              <div className="integrity-metric">
                <span>Mobile / Device Events</span>
                <strong>{antiCheatingSummary?.device_events ?? 0}</strong>
              </div>

              <div className="integrity-metric">
                <span>Suspicious Duration</span>
                <strong>{antiCheatingSummary?.total_suspicious_duration ?? 0}s</strong>
              </div>

            </div>

            {/* EVENTS TIMELINE */}
            <div className="integrity-events-section">

              <h4>Incident Timeline</h4>

              {antiCheatingEvents.length === 0 ? (
                <div className="integrity-empty-state">
                  <span className="integrity-empty-icon">✓</span>
                  <div>
                    <strong>No suspicious activity detected.</strong>
                    <p>
                      Candidate maintained continuous face presence and session compliance throughout the interview.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="integrity-events-list">
                  {antiCheatingEvents.map((evt, idx) => (
                    <div
                      key={evt.id || idx}
                      className={`integrity-event-card severity-${evt.severity.toLowerCase()}`}
                    >
                      <div className="integrity-event-top">
                        <div className="event-badges">
                          <span className="event-type-badge">
                            {evt.event_type.replace(/_/g, " ")}
                          </span>
                          <span
                            className={`event-severity-badge severity-${evt.severity.toLowerCase()}`}
                          >
                            {evt.severity} SEVERITY
                          </span>
                        </div>
                        <span className="event-time">
                          {formatDate(evt.timestamp)}
                        </span>
                      </div>
                      <p className="event-desc">{evt.description}</p>
                      <div className="event-footer">
                        <span>
                          Duration: <strong>{evt.duration}s</strong>
                        </span>
                        <span>
                          Confidence:{" "}
                          <strong>{Math.round(evt.confidence * 100)}%</strong>
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

            </div>

          </div>

        </section>


        {/* ====================================================
            TRANSCRIPT
            ==================================================== */}

        {interview.transcript && (

          <section className="result-section">

            <div className="section-heading">

              <div className="section-number">
                05
              </div>

              <div>

                <h2>
                  Interview Transcript
                </h2>

                <p>
                  Your recorded interview conversation.
                </p>

              </div>

            </div>


            <div className="transcript-card">

              <pre>
                {(() => {

                  const parsed =
                    parseJSON(
                      interview.transcript,
                    )

                  if (parsed) {
                    return JSON.stringify(
                      parsed,
                      null,
                      2,
                    )
                  }

                  return interview.transcript

                })()}
              </pre>

            </div>

          </section>

        )}


        {/* ====================================================
            ACTIONS
            ==================================================== */}

        <section className="results-actions">

          <button
            className="secondary-action"
            onClick={() =>
              navigate("/dashboard")
            }
          >
            ← Dashboard
          </button>


          <button
            className="secondary-action"
            onClick={() =>
              navigate("/interview-setup")
            }
          >
            Practice Again
          </button>


          <button
            className="primary-action"
            onClick={handleDownload}
          >
            Download Report
            <span>↓</span>
          </button>

        </section>


      </main>

    </div>
  )
}


export default Results