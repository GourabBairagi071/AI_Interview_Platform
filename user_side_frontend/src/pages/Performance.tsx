import { useCallback, useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  getAnalyticsOverview,
  type AnalyticsOverviewResponse,
  type ScoreHistoryItem,
} from "../services/api"
import "./Performance.css"

export default function Performance() {
  const navigate = useNavigate()

  // State
  const [data, setData] = useState<AnalyticsOverviewResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [mobileMenu, setMobileMenu] = useState(false)
  const [period, setPeriod] = useState<"5" | "10" | "all">("all")
  const [topicFilter, setTopicFilter] = useState("")
  const [historyFilter, setHistoryFilter] = useState<"all" | "completed" | "active">("all")
  const [hoveredPoint, setHoveredPoint] = useState<{
    item: ScoreHistoryItem
    x: number
    y: number
  } | null>(null)

  // ------------------------------------------------------------
  // LOAD ANALYTICS DATA
  // ------------------------------------------------------------
  const loadData = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const response = await getAnalyticsOverview()
      setData(response)
    } catch (err: unknown) {
      console.error("Failed to load performance analytics:", err)
      setError("Unable to load performance analytics. Please verify your connection and try again.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadData()
  }, [loadData])

  // ------------------------------------------------------------
  // FILTERED SCORE HISTORY (FOR CHART)
  // ------------------------------------------------------------
  const filteredHistory = useMemo(() => {
    if (!data?.score_history) return []
    const list = [...data.score_history]
    if (period === "5") return list.slice(-5)
    if (period === "10") return list.slice(-10)
    return list
  }, [data?.score_history, period])

  // ------------------------------------------------------------
  // FILTERED TOPICS
  // ------------------------------------------------------------
  const filteredTopics = useMemo(() => {
    if (!data?.topic_performance) return []
    if (!topicFilter.trim()) return data.topic_performance
    const q = topicFilter.trim().toLowerCase()
    return data.topic_performance.filter((t) => t.topic.toLowerCase().includes(q))
  }, [data?.topic_performance, topicFilter])

  // ------------------------------------------------------------
  // FILTERED INTERVIEW HISTORY
  // ------------------------------------------------------------
  const filteredInterviewHistory = useMemo(() => {
    if (!data?.interview_history) return []
    if (historyFilter === "completed") {
      return data.interview_history.filter((h) => h.status === "completed")
    }
    if (historyFilter === "active") {
      return data.interview_history.filter((h) => h.status !== "completed")
    }
    return data.interview_history
  }, [data?.interview_history, historyFilter])

  // ------------------------------------------------------------
  // SVG CHART COORDINATES CALCULATION
  // ------------------------------------------------------------
  const chartPoints = useMemo(() => {
    if (filteredHistory.length === 0) return { path: "", area: "", points: [] }

    const width = 800
    const height = 240
    const padX = 40
    const padY = 30
    const usableW = width - padX * 2
    const usableH = height - padY * 2

    const len = filteredHistory.length

    const points = filteredHistory.map((item, idx) => {
      const x = len === 1 ? width / 2 : padX + (idx / (len - 1)) * usableW
      // Map score 0-100 to y (100 -> padY, 0 -> height - padY)
      const clampedScore = Math.max(0, Math.min(100, item.score))
      const y = height - padY - (clampedScore / 100) * usableH
      return { x, y, item }
    })

    const path = points.reduce((acc, p, idx) => {
      return idx === 0 ? `M ${p.x} ${p.y}` : `${acc} L ${p.x} ${p.y}`
    }, "")

    const area = `${path} L ${points[points.length - 1].x} ${height - padY} L ${points[0].x} ${
      height - padY
    } Z`

    return { path, area, points }
  }, [filteredHistory])

  // ------------------------------------------------------------
  // SKELETON RENDER
  // ------------------------------------------------------------
  if (loading) {
    return (
      <div className="perf-shell">
        <aside className="perf-sidebar">
          <div className="perf-brand">
            <div className="brand-logo"><span>AI</span></div>
            <div className="brand-name">
              <strong>AI Interview</strong>
              <span>Platform</span>
            </div>
          </div>
        </aside>
        <main className="perf-main">
          <div className="perf-skeleton-wrapper">
            <div className="skeleton-header" />
            <div className="skeleton-kpis">
              <div className="skeleton-kpi-card" />
              <div className="skeleton-kpi-card" />
              <div className="skeleton-kpi-card" />
              <div className="skeleton-kpi-card" />
            </div>
            <div className="skeleton-chart" />
            <div className="skeleton-grid">
              <div className="skeleton-card" />
              <div className="skeleton-card" />
            </div>
          </div>
        </main>
      </div>
    )
  }

  // ------------------------------------------------------------
  // ERROR RENDER
  // ------------------------------------------------------------
  if (error || !data) {
    return (
      <div className="perf-shell">
        <aside className="perf-sidebar">
          <div className="perf-brand">
            <div className="brand-logo"><span>AI</span></div>
            <div className="brand-name">
              <strong>AI Interview</strong>
              <span>Platform</span>
            </div>
          </div>
          <nav className="perf-nav">
            <button type="button" className="perf-nav-link" onClick={() => navigate("/dashboard")}>
              <span className="nav-icon">▦</span>
              <span>Dashboard</span>
            </button>
          </nav>
        </aside>
        <main className="perf-main">
          <div className="perf-error-card">
            <div className="error-icon">⚠️</div>
            <h2>Unable to Load Analytics</h2>
            <p>{error || "An unexpected error occurred while fetching your performance profile."}</p>
            <button type="button" className="perf-retry-btn" onClick={loadData}>
              Retry Loading Analytics
            </button>
          </div>
        </main>
      </div>
    )
  }

  const { overall, difficulty_performance, strengths, weaknesses, recommendations } = data
  const hasCompleted = overall.completed_interviews > 0

  return (
    <div className="perf-shell">
      {/* ======================================================
          SIDEBAR NAVIGATION
      ====================================================== */}
      <aside className={`perf-sidebar ${mobileMenu ? "mobile-open" : ""}`}>
        <div className="perf-brand">
          <div className="brand-logo"><span>AI</span></div>
          <div className="brand-name">
            <strong>AI Interview</strong>
            <span>Platform</span>
          </div>
          <button
            type="button"
            className="perf-collapse-btn"
            onClick={() => setMobileMenu(false)}
          >
            ‹
          </button>
        </div>

        <nav className="perf-nav">
          <button
            type="button"
            className="perf-nav-link"
            onClick={() => {
              setMobileMenu(false)
              navigate("/dashboard")
            }}
          >
            <span className="nav-icon">▦</span>
            <span>Dashboard</span>
          </button>

          <button
            type="button"
            className="perf-nav-link"
            onClick={() => {
              setMobileMenu(false)
              navigate("/resume")
            }}
          >
            <span className="nav-icon">▤</span>
            <span>Resume Analyzer</span>
          </button>

          <button
            type="button"
            className="perf-nav-link"
            onClick={() => {
              setMobileMenu(false)
              navigate("/interview-setup")
            }}
          >
            <span className="nav-icon">♙</span>
            <span>AI Interview</span>
          </button>

          <button
            type="button"
            className="perf-nav-link active"
            onClick={() => setMobileMenu(false)}
          >
            <span className="nav-icon">▥</span>
            <span>Performance</span>
          </button>

          <button
            type="button"
            className="perf-nav-link"
            onClick={() => {
              setMobileMenu(false)
              navigate("/practice")
            }}
          >
            <span className="nav-icon">✎</span>
            <span>Question Practice</span>
          </button>

          <button
            type="button"
            className="perf-nav-link"
            onClick={() => {
              setMobileMenu(false)
              navigate("/achievements")
            }}
          >
            <span className="nav-icon">🏆</span>
            <span>Achievements</span>
          </button>

          <button
            type="button"
            className="perf-nav-link"
            onClick={() => {
              setMobileMenu(false)
              navigate("/profile")
            }}
          >
            <span className="nav-icon">👤</span>
            <span>Profile</span>
          </button>

          <button
            type="button"
            className="perf-nav-link"
            onClick={() => {
              setMobileMenu(false)
              navigate("/settings")
            }}
          >
            <span className="nav-icon">⚙</span>
            <span>Settings</span>
          </button>
        </nav>

        {/* PRACTICE QUICK-LAUNCH CARD */}
        <div className="perf-practice-card">
          <div className="practice-icon">🎯</div>
          <h3>Practice Next</h3>
          <p>Target your improvement areas with an adaptive AI session.</p>
          <button
            type="button"
            onClick={() => {
              setMobileMenu(false)
              navigate("/interview-setup")
            }}
          >
            Start Interview <span>→</span>
          </button>
        </div>
      </aside>

      {/* ======================================================
          MAIN PERFORMANCE CONTENT
      ====================================================== */}
      <main className="perf-main">
        {/* TOP MOBILE TOGGLE & HEADER */}
        <header className="perf-top-bar">
          <div className="perf-bar-left">
            <button
              type="button"
              className="perf-mobile-toggle"
              onClick={() => setMobileMenu(true)}
              aria-label="Open menu"
            >
              ☰
            </button>
            <button
              type="button"
              className="perf-back-btn"
              onClick={() => navigate("/dashboard")}
            >
              ← Back to Dashboard
            </button>
          </div>

          <div className="perf-session-pill">
            <span className="pulse-dot" />
            <span>Real Analytics Synced</span>
          </div>
        </header>

        {/* HERO TITLE */}
        <section className="perf-hero">
          <div className="perf-hero-copy">
            <span className="perf-eyebrow">ANALYTICS & BENCHMARKING</span>
            <h1>Performance</h1>
            <p>
              Track your real interview trajectory, question-by-question topic mastery,
              and AI-evaluated preparation benchmarks.
            </p>
          </div>

          <div className="perf-hero-actions">
            <button
              type="button"
              className="perf-primary-btn"
              onClick={() => navigate("/interview-setup")}
            >
              <span>New Mock Session</span>
              <span className="btn-arrow">→</span>
            </button>
          </div>
        </section>

        {/* ======================================================
            1. KPI SUMMARY CARDS (REAL DATA ONLY)
        ====================================================== */}
        <section className="perf-kpi-grid">
          {/* AVERAGE SCORE */}
          <div className="perf-kpi-card cyan-glow">
            <div className="kpi-top">
              <span className="kpi-label">Average Score</span>
              <span className="kpi-icon">◎</span>
            </div>
            <div className="kpi-value">
              {overall.overall_score !== null ? `${Math.round(overall.overall_score)}%` : "—"}
            </div>
            <div className="kpi-foot">
              {overall.score_change !== null ? (
                <span
                  className={`trend-pill ${
                    overall.score_change_direction === "up"
                      ? "positive"
                      : overall.score_change_direction === "down"
                      ? "negative"
                      : "neutral"
                  }`}
                >
                  {overall.score_change > 0 ? `▲ +${overall.score_change}%` : `${overall.score_change}%`} vs last session
                </span>
              ) : (
                <span className="kpi-subtext">Across evaluated sessions</span>
              )}
            </div>
          </div>

          {/* BEST SCORE */}
          <div className="perf-kpi-card gold-glow">
            <div className="kpi-top">
              <span className="kpi-label">Best Score</span>
              <span className="kpi-icon">★</span>
            </div>
            <div className="kpi-value">
              {overall.best_score !== null ? `${Math.round(overall.best_score)}%` : "—"}
            </div>
            <div className="kpi-foot">
              <span className="kpi-subtext">
                {overall.recent_score !== null
                  ? `Latest: ${Math.round(overall.recent_score)}%`
                  : "Personal record benchmark"}
              </span>
            </div>
          </div>

          {/* COMPLETED INTERVIEWS */}
          <div className="perf-kpi-card emerald-glow">
            <div className="kpi-top">
              <span className="kpi-label">Interviews Completed</span>
              <span className="kpi-icon">✓</span>
            </div>
            <div className="kpi-value">{overall.completed_interviews}</div>
            <div className="kpi-foot">
              <span className="kpi-subtext">
                {overall.total_interviews} total sessions initiated
              </span>
            </div>
          </div>

          {/* QUESTIONS ANSWERED */}
          <div className="perf-kpi-card purple-glow">
            <div className="kpi-top">
              <span className="kpi-label">Questions Answered</span>
              <span className="kpi-icon">&lt;/&gt;</span>
            </div>
            <div className="kpi-value">{overall.total_questions_answered}</div>
            <div className="kpi-foot">
              <span className="kpi-subtext">Technical & scenario responses</span>
            </div>
          </div>
        </section>

        {/* ======================================================
            2. SCORE PROGRESSION LINE CHART
        ====================================================== */}
        <section className="perf-panel chart-panel">
          <div className="panel-header">
            <div>
              <span className="panel-tag">SCORE PROGRESSION</span>
              <h2>Interactive Score History</h2>
              <p>Historical trajectory across completed mock interview evaluations</p>
            </div>

            {hasCompleted && data.score_history.length >= 2 && (
              <div className="period-tabs">
                <button
                  type="button"
                  className={`tab-btn ${period === "5" ? "active" : ""}`}
                  onClick={() => setPeriod("5")}
                >
                  Last 5
                </button>
                <button
                  type="button"
                  className={`tab-btn ${period === "10" ? "active" : ""}`}
                  onClick={() => setPeriod("10")}
                >
                  Last 10
                </button>
                <button
                  type="button"
                  className={`tab-btn ${period === "all" ? "active" : ""}`}
                  onClick={() => setPeriod("all")}
                >
                  All ({data.score_history.length})
                </button>
              </div>
            )}
          </div>

          {chartPoints.points.length >= 2 ? (
            <div className="perf-chart-box">
              {/* Y-AXIS LABELS */}
              <div className="chart-axis-y">
                <span>100%</span>
                <span>75%</span>
                <span>50%</span>
                <span>25%</span>
                <span>0%</span>
              </div>

              {/* SVG GRAPH */}
              <div className="chart-canvas-wrap">
                <svg
                  viewBox="0 0 800 240"
                  className="perf-svg-chart"
                  preserveAspectRatio="none"
                >
                  <defs>
                    <linearGradient id="scoreAreaGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.45" />
                      <stop offset="100%" stopColor="#4c1d95" stopOpacity="0.0" />
                    </linearGradient>
                    <filter id="glowFilter" x="-20%" y="-20%" width="140%" height="140%">
                      <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#a78bfa" floodOpacity="0.6" />
                    </filter>
                  </defs>

                  {/* Horizontal Grid lines */}
                  <line x1="40" y1="30" x2="760" y2="30" stroke="rgba(255,255,255,0.06)" strokeDasharray="4 4" />
                  <line x1="40" y1="75" x2="760" y2="75" stroke="rgba(255,255,255,0.06)" strokeDasharray="4 4" />
                  <line x1="40" y1="120" x2="760" y2="120" stroke="rgba(255,255,255,0.06)" strokeDasharray="4 4" />
                  <line x1="40" y1="165" x2="760" y2="165" stroke="rgba(255,255,255,0.06)" strokeDasharray="4 4" />
                  <line x1="40" y1="210" x2="760" y2="210" stroke="rgba(255,255,255,0.12)" />

                  {/* Area fill */}
                  <path d={chartPoints.area} fill="url(#scoreAreaGrad)" />

                  {/* Line stroke */}
                  <path
                    d={chartPoints.path}
                    fill="none"
                    stroke="#a78bfa"
                    strokeWidth="3"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    filter="url(#glowFilter)"
                  />

                  {/* Interactive Points */}
                  {chartPoints.points.map((pt, idx) => (
                    <g key={pt.item.interview_id || idx}>
                      <circle
                        cx={pt.x}
                        cy={pt.y}
                        r="6"
                        className="chart-dot"
                        onMouseEnter={() => setHoveredPoint(pt)}
                        onClick={() => navigate(`/results/${pt.item.interview_id}`)}
                      />
                      <circle
                        cx={pt.x}
                        cy={pt.y}
                        r="3"
                        fill="#ffffff"
                        pointerEvents="none"
                      />
                    </g>
                  ))}
                </svg>

                {/* INTERACTIVE HOVER TOOLTIP */}
                {hoveredPoint && (
                  <div
                    className="chart-tooltip"
                    style={{
                      left: `${(hoveredPoint.x / 800) * 100}%`,
                      top: `${(hoveredPoint.y / 240) * 100}%`,
                    }}
                    onMouseLeave={() => setHoveredPoint(null)}
                  >
                    <div className="tooltip-head">
                      <strong>{hoveredPoint.item.role}</strong>
                      <span className="tooltip-badge">{hoveredPoint.item.difficulty}</span>
                    </div>
                    <div className="tooltip-score">
                      Score: <span>{hoveredPoint.item.score}%</span>
                    </div>
                    <div className="tooltip-date">{hoveredPoint.item.date}</div>
                    <button
                      type="button"
                      className="tooltip-link"
                      onClick={() => navigate(`/results/${hoveredPoint.item.interview_id}`)}
                    >
                      View Full Results →
                    </button>
                  </div>
                )}
              </div>

              {/* X-AXIS LABELS */}
              <div className="chart-axis-x">
                {filteredHistory.map((item, idx) => (
                  <span key={item.interview_id || idx}>{item.date}</span>
                ))}
              </div>
            </div>
          ) : (
            <div className="chart-empty-state">
              <div className="empty-chart-icon">📈</div>
              <h3>Need More Evaluation Data</h3>
              <p>
                Complete at least 2 interview sessions to unlock interactive score progression
                charts and trajectory analytics.
              </p>
              <button
                type="button"
                className="perf-outline-btn"
                onClick={() => navigate("/interview-setup")}
              >
                Launch Mock Interview →
              </button>
            </div>
          )}
        </section>

        {/* ======================================================
            3. TOPIC PERFORMANCE & DIFFICULTY BREAKDOWN
        ====================================================== */}
        <section className="two-column-grid">
          {/* TOPIC MASTERY */}
          <div className="perf-panel">
            <div className="panel-header">
              <div>
                <span className="panel-tag">TOPIC MASTERY</span>
                <h2>Competency Breakdown</h2>
                <p>Aggregated scores derived from evaluated question topics</p>
              </div>

              {data.topic_performance.length > 5 && (
                <div className="topic-search-wrap">
                  <input
                    type="text"
                    placeholder="Filter topics..."
                    value={topicFilter}
                    onChange={(e) => setTopicFilter(e.target.value)}
                    className="topic-search-input"
                  />
                </div>
              )}
            </div>

            {filteredTopics.length > 0 ? (
              <div className="topics-list">
                {filteredTopics.map((tp) => {
                  const score = Math.round(tp.average_score)
                  const scoreClass =
                    score >= 75 ? "score-high" : score >= 60 ? "score-mid" : "score-low"

                  return (
                    <div className="topic-row" key={tp.topic}>
                      <div className="topic-meta">
                        <strong className="topic-name">{tp.topic}</strong>
                        <div className="topic-badges">
                          <span className="count-badge">
                            {tp.question_count} question{tp.question_count === 1 ? "" : "s"}
                          </span>
                          {tp.trend === "improving" && (
                            <span className="trend-badge improving">↗ Improving</span>
                          )}
                          {tp.trend === "declining" && (
                            <span className="trend-badge declining">↘ Review</span>
                          )}
                          {tp.trend === "stable" && (
                            <span className="trend-badge stable">→ Stable</span>
                          )}
                        </div>
                      </div>

                      <div className="topic-bar-wrapper">
                        <div className="topic-bar-track">
                          <div
                            className={`topic-bar-fill ${scoreClass}`}
                            style={{ width: `${score}%` }}
                          />
                        </div>
                        <span className={`topic-score-num ${scoreClass}`}>{score}%</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="panel-empty">
                <p>
                  {hasCompleted
                    ? "No topics match the filter criteria."
                    : "Complete an interview session to benchmark topic mastery."}
                </p>
              </div>
            )}
          </div>

          {/* DIFFICULTY PERFORMANCE */}
          <div className="perf-panel">
            <div className="panel-header">
              <div>
                <span className="panel-tag">DIFFICULTY TIERS</span>
                <h2>Performance by Difficulty</h2>
                <p>Score averages categorized by interview difficulty levels</p>
              </div>
            </div>

            <div className="diff-cards-grid">
              {difficulty_performance.map((dp) => {
                const diffLower = dp.difficulty.toLowerCase()
                const score = dp.average_score !== null ? Math.round(dp.average_score) : null
                const colorClass =
                  diffLower === "easy"
                    ? "diff-easy"
                    : diffLower === "hard"
                    ? "diff-hard"
                    : "diff-medium"

                return (
                  <div className={`diff-card ${colorClass}`} key={dp.difficulty}>
                    <div className="diff-header">
                      <span className="diff-badge">{dp.difficulty}</span>
                      <span className="diff-count">
                        {dp.question_count} question{dp.question_count === 1 ? "" : "s"}
                      </span>
                    </div>

                    <div className="diff-score-box">
                      <span className="diff-score-val">
                        {score !== null ? `${score}%` : "—"}
                      </span>
                      <span className="diff-score-label">
                        {score !== null ? "Average Score" : "No questions yet"}
                      </span>
                    </div>

                    <div className="diff-progress-track">
                      <div
                        className="diff-progress-fill"
                        style={{ width: score !== null ? `${score}%` : "0%" }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </section>

        {/* ======================================================
            4. STRENGTHS & AREAS TO IMPROVE
        ====================================================== */}
        <section className="two-column-grid">
          {/* STRENGTHS */}
          <div className="perf-panel strengths-panel">
            <div className="panel-header">
              <div>
                <span className="panel-tag tag-green">VERIFIED STRENGTHS</span>
                <h2>Demonstrated Strengths</h2>
                <p>Areas and competencies validated across mock evaluations</p>
              </div>
            </div>

            {strengths.length > 0 ? (
              <div className="insights-list">
                {strengths.map((str, idx) => (
                  <div className="insight-item strength-item" key={idx}>
                    <span className="insight-bullet">✓</span>
                    <p>{str}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="panel-empty">
                <p>
                  Strengths will be extracted and highlighted automatically as you complete
                  evaluations.
                </p>
              </div>
            )}
          </div>

          {/* AREAS TO IMPROVE */}
          <div className="perf-panel weaknesses-panel">
            <div className="panel-header">
              <div>
                <span className="panel-tag tag-amber">AREAS FOR GROWTH</span>
                <h2>Focus Areas</h2>
                <p>Opportunities for conceptual depth and technical clarification</p>
              </div>
            </div>

            {weaknesses.length > 0 ? (
              <div className="insights-list">
                {weaknesses.map((wk, idx) => (
                  <div className="insight-item weakness-item" key={idx}>
                    <span className="insight-bullet">🎯</span>
                    <p>{wk}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="panel-empty">
                <p>
                  Focus areas will appear here as the AI analyzes your answers and identifies
                  growth vectors.
                </p>
              </div>
            )}
          </div>
        </section>

        {/* ======================================================
            5. AI RECOMMENDATIONS
        ====================================================== */}
        {recommendations.length > 0 && (
          <section className="perf-panel recommendations-panel">
            <div className="panel-header">
              <div>
                <span className="panel-tag tag-violet">AI ADVICE</span>
                <h2>Actionable Recommendations</h2>
                <p>Specific preparation guidance derived from your interview evaluations</p>
              </div>
            </div>

            <div className="recommendations-grid">
              {recommendations.map((rec, idx) => (
                <div className="rec-card" key={idx}>
                  <div className="rec-icon">⚡</div>
                  <div className="rec-body">
                    <strong>Recommendation {idx + 1}</strong>
                    <p>{rec}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ======================================================
            6. INTERVIEW HISTORY TABLE
        ====================================================== */}
        <section className="perf-panel">
          <div className="panel-header">
            <div>
              <span className="panel-tag">SESSION LOGS</span>
              <h2>Interview History</h2>
              <p>Chronological record of mock interview sessions and evaluations</p>
            </div>

            <div className="filter-pill-group">
              <button
                type="button"
                className={`filter-btn ${historyFilter === "all" ? "active" : ""}`}
                onClick={() => setHistoryFilter("all")}
              >
                All ({data.interview_history.length})
              </button>
              <button
                type="button"
                className={`filter-btn ${historyFilter === "completed" ? "active" : ""}`}
                onClick={() => setHistoryFilter("completed")}
              >
                Completed ({overall.completed_interviews})
              </button>
              <button
                type="button"
                className={`filter-btn ${historyFilter === "active" ? "active" : ""}`}
                onClick={() => setHistoryFilter("active")}
              >
                In Progress ({overall.total_interviews - overall.completed_interviews})
              </button>
            </div>
          </div>

          {filteredInterviewHistory.length > 0 ? (
            <div className="history-table-wrap">
              <table className="perf-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Target Role</th>
                    <th>Difficulty</th>
                    <th>Questions</th>
                    <th>Score</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredInterviewHistory.map((item) => {
                    const isCompleted = item.status === "completed"
                    const score = item.score !== null ? Math.round(item.score) : null
                    const scoreClass =
                      score !== null
                        ? score >= 75
                          ? "score-pill-high"
                          : score >= 60
                          ? "score-pill-mid"
                          : "score-pill-low"
                        : "score-pill-none"

                    return (
                      <tr key={item.interview_id}>
                        <td className="table-date">{item.date}</td>
                        <td className="table-role">
                          <strong>{item.role}</strong>
                        </td>
                        <td>
                          <span className="diff-tag">{item.difficulty}</span>
                        </td>
                        <td className="table-qcount">
                          {item.total_questions > 0 ? `${item.total_questions} Questions` : "—"}
                        </td>
                        <td>
                          <span className={`score-pill ${scoreClass}`}>
                            {score !== null ? `${score}%` : "—"}
                          </span>
                        </td>
                        <td>
                          <span
                            className={`status-pill ${
                              isCompleted ? "status-completed" : "status-in-progress"
                            }`}
                          >
                            <span className="status-dot" />
                            {isCompleted ? "Completed" : "In Progress"}
                          </span>
                        </td>
                        <td>
                          <button
                            type="button"
                            className="table-action-btn"
                            onClick={() => navigate(item.result_route)}
                          >
                            {isCompleted ? "View Results →" : "Continue →"}
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="panel-empty">
              <p>No interview records found for the selected filter.</p>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
