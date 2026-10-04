import { useEffect, useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import {
  getContestDetail,
  registerForContest,
  type ContestDetail,
} from "../services/api"
import "./ContestDetails.css"

export default function ContestDetails() {
  const { contestId } = useParams<{ contestId: string }>()
  const navigate = useNavigate()

  const [contest, setContest] = useState<ContestDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [registering, setRegistering] = useState(false)

  // Local ticker for live second-by-second countdown
  const [clock, setClock] = useState<number>(Date.now())
  useEffect(() => {
    const timer = setInterval(() => setClock(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [])

  const fetchDetail = async () => {
    if (!contestId) return
    try {
      setLoading(true)
      setError(null)
      const data = await getContestDetail(contestId)
      setContest(data)
    } catch (err: any) {
      setError(err.message || "Failed to load contest details")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDetail()
  }, [contestId])

  const handleRegister = async () => {
    if (!contest) return
    try {
      setRegistering(true)
      await registerForContest(contest.id)
      await fetchDetail()
    } catch (err: any) {
      alert(err.message || "Registration error")
    } finally {
      setRegistering(false)
    }
  }

  if (loading) {
    return (
      <div className="contest-detail-loading">
        <div className="spinner"></div>
        <p>Loading contest arena specifications...</p>
      </div>
    )
  }

  if (error || !contest) {
    return (
      <div className="contest-detail-error">
        <h2>Contest Not Found</h2>
        <p>{error || "The requested contest could not be found."}</p>
        <button className="secondary-btn" onClick={() => navigate("/contests")}>
          ← Back to Contests
        </button>
      </div>
    )
  }

  const isLive = contest.status === "LIVE"
  const isUpcoming = contest.status === "UPCOMING"

  // Countdown calculations
  const startMs = new Date(contest.start_time).getTime()
  const endMs = new Date(contest.end_time).getTime()
  const nowMs = clock

  let diffSec = 0
  let countdownLabel = "Contest Concluded"

  if (isLive) {
    diffSec = Math.max(0, Math.floor((endMs - nowMs) / 1000))
    countdownLabel = "Time Remaining Until Contest Ends"
  } else if (isUpcoming) {
    diffSec = Math.max(0, Math.floor((startMs - nowMs) / 1000))
    countdownLabel = "Countdown Until Contest Starts"
  }

  const days = Math.floor(diffSec / 86400)
  const hours = Math.floor((diffSec % 86400) / 3600)
  const minutes = Math.floor((diffSec % 3600) / 60)
  const seconds = diffSec % 60

  return (
    <div className="contest-detail-container">
      {/* Top breadcrumb navigation */}
      <div className="contest-detail-breadcrumb">
        <button className="breadcrumb-link" onClick={() => navigate("/contests")}>
          ← All Contests
        </button>
        <span className="breadcrumb-divider">/</span>
        <span className="breadcrumb-current">{contest.title}</span>
      </div>

      {/* Hero Banner Card */}
      <div className={`contest-hero-card ${isLive ? "hero-live" : ""}`}>
        <div className="hero-top-row">
          <div className="hero-status-badges">
            <span className={`hero-status-pill status-${contest.status.toLowerCase()}`}>
              {isLive && <span className="hero-live-dot"></span>}
              {contest.status}
            </span>
            {contest.is_proctored && (
              <span className="hero-proctor-pill">
                🛡️ AI PROCTORED CONTEST
              </span>
            )}
            <span className="hero-scoring-pill">
              SCORING: {contest.scoring_type}
            </span>
          </div>

          <div className="hero-participants-count">
            👥 <strong>{contest.registered_count}</strong> Registered Coders
          </div>
        </div>

        <h1 className="hero-title">{contest.title}</h1>
        <p className="hero-description">{contest.description}</p>

        {/* Live Countdown Display */}
        {(isLive || isUpcoming) && (
          <div className="countdown-container">
            <span className="countdown-header-text">{countdownLabel}</span>
            <div className="countdown-grid">
              {days > 0 && (
                <div className="time-block">
                  <span className="time-num">{days}</span>
                  <span className="time-unit">DAYS</span>
                </div>
              )}
              <div className="time-block">
                <span className="time-num">{hours < 10 ? `0${hours}` : hours}</span>
                <span className="time-unit">HOURS</span>
              </div>
              <div className="time-block">
                <span className="time-num">{minutes < 10 ? `0${minutes}` : minutes}</span>
                <span className="time-unit">MINUTES</span>
              </div>
              <div className="time-block highlight-sec">
                <span className="time-num">{seconds < 10 ? `0${seconds}` : seconds}</span>
                <span className="time-unit">SECONDS</span>
              </div>
            </div>
          </div>
        )}

        {/* Action Button Bar */}
        <div className="hero-action-bar">
          {isLive ? (
            <button
              className="action-btn enter-live-btn"
              onClick={() => navigate(`/contests/${contest.id}/arena`)}
            >
              Enter Contest Arena ⚡
            </button>
          ) : isUpcoming ? (
            contest.is_registered ? (
              <div className="registered-badge-box">
                <span className="check-icon">✓</span> You are registered! The arena will unlock automatically when the timer reaches zero.
              </div>
            ) : (
              <button
                className="action-btn register-now-btn"
                disabled={registering}
                onClick={handleRegister}
              >
                {registering ? "Registering..." : "Register For Contest"}
              </button>
            )
          ) : (
            <div className="ended-action-buttons">
              <button
                className="action-btn results-view-btn"
                onClick={() => navigate(`/contests/${contest.id}/results`)}
              >
                View My Results & Percentile →
              </button>
              <button
                className="secondary-btn"
                onClick={() => navigate(`/contests/${contest.id}/leaderboard`)}
              >
                Full Leaderboard Standings
              </button>
            </div>
          )}

          {isLive && (
            <button
              className="secondary-btn"
              onClick={() => navigate(`/contests/${contest.id}/leaderboard`)}
            >
              Live Leaderboard 📊
            </button>
          )}
        </div>
      </div>

      {/* Main Specs & Rules Grid */}
      <div className="contest-detail-content-grid">
        {/* Left Column: Rules & Info */}
        <div className="specs-card">
          <h2 className="section-title">Contest Rules & Format</h2>
          <div className="rules-content">
            <div className="rule-item">
              <div className="rule-icon">⏱️</div>
              <div>
                <strong>Duration & Timing</strong>
                <p>
                  Total duration is {contest.duration_minutes} minutes. Once the contest concludes, no additional submissions are accepted. Server time determines all deadlines strictly.
                </p>
              </div>
            </div>

            <div className="rule-item">
              <div className="rule-icon">🎯</div>
              <div>
                <strong>Scoring & Penalty System</strong>
                <p>
                  This contest follows <strong>{contest.scoring_type}</strong> scoring. For each challenge, you earn points upon passing all test cases. Each incorrect submission incurs a <strong>{contest.penalty_per_wrong_attempt_mins}-minute penalty</strong> upon eventual solve.
                </p>
              </div>
            </div>

            <div className="rule-item">
              <div className="rule-icon">💻</div>
              <div>
                <strong>Supported Programming Languages</strong>
                <p>
                  {contest.allowed_languages.map((l) => l.toUpperCase()).join(", ")}. Starter code is provided in Python, JavaScript, C++, and Java.
                </p>
              </div>
            </div>

            {contest.is_proctored && (
              <div className="rule-item proctored-rule">
                <div className="rule-icon">🛡️</div>
                <div>
                  <strong>Proctoring & Anti-Cheating Protocol</strong>
                  <p>
                    This is an officially proctored contest. Web camera presence, tab switching, and multi-face events are actively monitored. Unauthorized device presence will disqualify submissions.
                  </p>
                </div>
              </div>
            )}
          </div>

          {contest.rules && (
            <div className="custom-rules-block">
              <h3>Specific Event Guidelines</h3>
              <pre>{contest.rules}</pre>
            </div>
          )}
        </div>

        {/* Right Column: Schedule & Overview */}
        <div className="overview-sidebar">
          <div className="sidebar-card">
            <h3>Event Overview</h3>
            <ul className="overview-list">
              <li>
                <span className="item-label">Start Time</span>
                <span className="item-val">
                  {new Date(contest.start_time).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })}
                </span>
              </li>
              <li>
                <span className="item-label">End Time</span>
                <span className="item-val">
                  {new Date(contest.end_time).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })}
                </span>
              </li>
              <li>
                <span className="item-label">Duration</span>
                <span className="item-val">{contest.duration_minutes} Minutes</span>
              </li>
              <li>
                <span className="item-label">Challenges Count</span>
                <span className="item-val">{contest.problems_count} Problems</span>
              </li>
              <li>
                <span className="item-label">Wrong Attempt Penalty</span>
                <span className="item-val">+{contest.penalty_per_wrong_attempt_mins} Mins</span>
              </li>
              <li>
                <span className="item-label">Security Mode</span>
                <span className="item-val">{contest.is_proctored ? "AI Proctored" : "Standard"}</span>
              </li>
            </ul>
          </div>

          <div className="sidebar-card prep-tip-card">
            <h4>💡 Competitive Strategy Tip</h4>
            <p>
              Read all {contest.problems_count} problems first before jumping into code. Solving problems in order of difficulty minimizes penalty time. Test your code against edge cases before final submission!
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
