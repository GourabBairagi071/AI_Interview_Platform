import { useEffect, useState, useCallback } from "react"
import { useParams, useNavigate } from "react-router-dom"
import {
  getContestResults,
  type ContestResultsResponse,
  type ProblemPerformance,
} from "../services/api"
import "./ContestResults.css"

export default function ContestResults() {
  const { contestId } = useParams<{ contestId: string }>()
  const navigate = useNavigate()

  const [results, setResults] = useState<ContestResultsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadResults = useCallback(async () => {
    if (!contestId) return
    try {
      setLoading(true)
      setError(null)
      const data = await getContestResults(contestId)
      setResults(data)
    } catch (err: any) {
      setError(err?.message || "Failed to load contest results")
    } finally {
      setLoading(false)
    }
  }, [contestId])

  useEffect(() => {
    loadResults()
  }, [loadResults])

  if (loading) {
    return (
      <div className="cr-page cr-loading">
        <div className="cr-spinner" />
        <h2>Calculating Contest Analytics...</h2>
        <p>Aggregating standings, percentile distributions, and submission logs.</p>
      </div>
    )
  }

  if (error || !results) {
    return (
      <div className="cr-page cr-error">
        <h2>Contest Performance Summary</h2>
        <p>{error || "No contest results available."}</p>
        <div className="cr-btn-row">
          <button className="cr-btn cr-btn-secondary" onClick={() => navigate(`/contests/${contestId}`)}>
            Contest Details
          </button>
          <button className="cr-btn cr-btn-primary" onClick={() => navigate("/contests")}>
            Browse Contests
          </button>
        </div>
      </div>
    )
  }

  const {
    contest_title,
    final_rank,
    total_participants,
    percentile,
    solved_count,
    total_score,
    penalty_minutes,
    problems,
    submissions,
  } = results

  return (
    <div className="cr-page">
      {/* Top Header */}
      <header className="cr-header">
        <div className="cr-header-inner">
          <div className="cr-nav-row">
            <button className="cr-back-btn" onClick={() => navigate(`/contests/${contestId}`)}>
              ← Contest Hub
            </button>
            <button
              className="cr-btn cr-btn-leaderboard"
              onClick={() => navigate(`/contests/${contestId}/leaderboard`)}
            >
              Full Standings ↗
            </button>
          </div>

          <div className="cr-hero">
            <span className="cr-category">COMPETITIVE RECAP</span>
            <h1>{contest_title} — Official Results</h1>
            <p className="cr-date">Official contest standings and score breakdown.</p>
          </div>
        </div>
      </header>

      {/* Main Analytics Cards */}
      <main className="cr-body">
        {/* Metric Cards Row */}
        <section className="cr-metrics-grid">
          <div className="cr-card metric-card highlight">
            <span className="metric-label">FINAL STANDING</span>
            <div className="metric-val-big">
              {final_rank ? `#${final_rank}` : "Unranked"}
              {total_participants > 0 && (
                <span className="metric-sub"> / {total_participants}</span>
              )}
            </div>
            {percentile !== null && percentile !== undefined && (
              <span className="percentile-tag">
                Top {(100 - percentile).toFixed(1)}% of all candidates
              </span>
            )}
          </div>

          <div className="cr-card metric-card">
            <span className="metric-label">PROBLEMS SOLVED</span>
            <div className="metric-val-big">
              {solved_count}
              <span className="metric-sub"> / {problems.length}</span>
            </div>
            <span className="metric-desc">
              {solved_count === problems.length && problems.length > 0
                ? "Perfect score achieved!"
                : "Solutions accepted"}
            </span>
          </div>

          <div className="cr-card metric-card">
            <span className="metric-label">TOTAL SCORE</span>
            <div className="metric-val-big">{total_score}</div>
            <span className="metric-desc">Points accumulated</span>
          </div>

          <div className="cr-card metric-card">
            <span className="metric-label">ICPC TIME PENALTY</span>
            <div className="metric-val-big">{penalty_minutes}m</div>
            <span className="metric-desc">Minutes including wrong attempts</span>
          </div>
        </section>

        {/* Problem-wise Breakdown */}
        <section className="cr-section">
          <h2>Problem Performance Breakdown</h2>
          <div className="problem-breakdown-grid">
            {problems.map((prob: ProblemPerformance, idx: number) => (
              <div
                key={idx}
                className={`prob-perf-card ${prob.solved ? "card-solved" : prob.attempts > 0 ? "card-attempted" : ""}`}
              >
                <div className="prob-perf-header">
                  <span className="prob-perf-label">{prob.label}</span>
                  <span className={`prob-status-badge ${prob.solved ? "badge-solved" : prob.attempts > 0 ? "badge-attempted" : ""}`}>
                    {prob.solved ? "SOLVED" : prob.attempts > 0 ? "ATTEMPTED" : "UNATTEMPTED"}
                  </span>
                </div>

                <h3 className="prob-perf-title">{prob.title}</h3>

                <div className="prob-perf-metrics">
                  <div>
                    <span className="k">Points:</span>
                    <span className="v">{prob.points}</span>
                  </div>
                  <div>
                    <span className="k">Attempts:</span>
                    <span className="v">{prob.attempts}</span>
                  </div>
                  <div>
                    <span className="k">Time:</span>
                    <span className="v">{prob.time_taken_mins ? `${prob.time_taken_mins}m` : "—"}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Submission Log */}
        <section className="cr-section">
          <h2>Contest Submission Audit</h2>
          {!submissions || submissions.length === 0 ? (
            <p className="no-sub-msg">No submissions recorded during this contest window.</p>
          ) : (
            <div className="cr-table-wrap">
              <table className="cr-table">
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Language</th>
                    <th>Verdict</th>
                    <th>Score</th>
                    <th>Penalty</th>
                  </tr>
                </thead>
                <tbody>
                  {submissions.map((sub: any, idx: number) => (
                    <tr key={idx}>
                      <td className="font-mono">
                        {sub.submitted_at
                          ? new Date(sub.submitted_at).toLocaleTimeString()
                          : "—"}
                      </td>
                      <td>{sub.language || "python"}</td>
                      <td>
                        <span className={`sub-verdict-tag ${sub.status === "Accepted" ? "verdict-pass" : "verdict-fail"}`}>
                          {sub.status}
                        </span>
                      </td>
                      <td className="font-bold">+{sub.score || 0}</td>
                      <td className="font-mono">
                        {sub.penalty_minutes ? `${sub.penalty_minutes}m` : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
