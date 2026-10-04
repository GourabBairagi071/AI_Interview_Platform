import { useEffect, useState, useCallback } from "react"
import { useParams, useNavigate } from "react-router-dom"
import {
  getContestDetail,
  getContestLeaderboard,
  type ContestDetail,
  type ContestLeaderboardResponse,
} from "../services/api"
import { useWebSocketEvent } from "../hooks/useWebSocket"
import RealtimeStatusBadge from "../components/RealtimeStatusBadge"
import "./ContestLeaderboard.css"

export default function ContestLeaderboard() {
  const { contestId } = useParams<{ contestId: string }>()
  const navigate = useNavigate()

  const [contest, setContest] = useState<ContestDetail | null>(null)
  const [leaderboard, setLeaderboard] = useState<ContestLeaderboardResponse | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true)
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date())

  // Current logged in user ID from JWT if available
  const currentUserId = (() => {
    try {
      const token = localStorage.getItem("token")
      if (!token) return null
      const payloadBase64 = token.split(".")[1]
      const decoded = JSON.parse(atob(payloadBase64))
      return decoded.sub || decoded.user_id || null
    } catch {
      return null
    }
  })()

  const fetchLeaderboardData = useCallback(async (isSilent = false) => {
    if (!contestId) return
    try {
      if (!isSilent) setLoading(true)
      setError(null)

      const [contestData, lbData] = await Promise.all([
        getContestDetail(contestId),
        getContestLeaderboard(contestId),
      ])

      setContest(contestData)
      setLeaderboard(lbData)
      setLastRefreshed(new Date())
    } catch (err: any) {
      if (!isSilent) setError(err?.message || "Failed to load leaderboard standings")
    } finally {
      if (!isSilent) setLoading(false)
    }
  }, [contestId])

  useEffect(() => {
    fetchLeaderboardData()
  }, [fetchLeaderboardData])

  // Polling for live updates during LIVE contests (every 20s)
  useEffect(() => {
    if (!autoRefresh || contest?.status === "ENDED") return

    const interval = setInterval(() => {
      fetchLeaderboardData(true)
    }, 20000)

    return () => clearInterval(interval)
  }, [autoRefresh, contest?.status, fetchLeaderboardData])

  // Real-time contest leaderboard updates
  useWebSocketEvent("contest.leaderboard.updated", (data: any) => {
    if (!data || (data.contest_id && data.contest_id !== contestId)) return
    fetchLeaderboardData(true)
  })

  useWebSocketEvent("contest.status", (data: any) => {
    if (!data || (data.contest_id && data.contest_id !== contestId)) return
    fetchLeaderboardData(true)
  })

  useWebSocketEvent("contest.participant.updated", (data: any) => {
    if (!data || (data.contest_id && data.contest_id !== contestId)) return
    fetchLeaderboardData(true)
  })

  return (
    <div className="contest-leaderboard-page">
      {/* Top Header */}
      <header className="cl-header">
        <div className="cl-header-content">
          <div className="cl-header-nav">
            <button className="cl-back-btn" onClick={() => navigate(`/contests/${contestId}`)}>
              ← Contest Hub
            </button>
            {contest?.status === "LIVE" && (
              <button
                className="cl-arena-btn"
                onClick={() => navigate(`/contests/${contestId}/arena`)}
              >
                Enter Coding Arena →
              </button>
            )}
          </div>

          <div className="cl-title-block">
            <div className="cl-title-row">
              <h1>{contest?.title || "Contest"} — Live Leaderboard</h1>
              {contest && (
                <span className={`cl-status-pill pill-${contest.status.toLowerCase()}`}>
                  {contest.status}
                </span>
              )}
            </div>
            <p className="cl-subtitle">
              Official ICPC competitive ranking. Sorted by problems solved, total score, and time penalty.
            </p>
          </div>

          {/* Controls Bar */}
          <div className="cl-controls-bar">
            <div className="cl-meta-items">
              <span className="cl-meta-tag">
                Participants: <strong>{leaderboard?.total_participants || 0}</strong>
              </span>
              <span className="cl-meta-tag">
                Scoring: <strong>{contest?.scoring_type || "ICPC"}</strong>
              </span>
              <span className="cl-meta-tag">
                Penalty per WA: <strong>{contest?.penalty_per_wrong_attempt_mins || 20}m</strong>
              </span>
            </div>

            <div className="cl-actions">
              <RealtimeStatusBadge />
              <label className="cl-auto-refresh">
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                />
                Auto-refresh (20s)
              </label>
              <button
                className="cl-refresh-btn"
                onClick={() => fetchLeaderboardData(false)}
                title="Refresh Standings Now"
              >
                🔄 Refresh
              </button>
              <span className="cl-last-updated">
                Updated: {lastRefreshed.toLocaleTimeString()}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Leaderboard Table Section */}
      <main className="cl-main-container">
        {loading ? (
          <div className="cl-loading-state">
            <div className="cl-spinner" />
            <p>Loading real-time competitive rankings...</p>
          </div>
        ) : error ? (
          <div className="cl-error-state">
            <h3>Leaderboard Error</h3>
            <p>{error}</p>
            <button className="cl-refresh-btn" onClick={() => fetchLeaderboardData(false)}>
              Retry
            </button>
          </div>
        ) : !leaderboard || leaderboard.leaderboard.length === 0 ? (
          <div className="cl-empty-state">
            <div className="cl-empty-icon">📊</div>
            <h3>No Submissions Recorded Yet</h3>
            <p>Be the first to submit a working solution and secure rank #1!</p>
            {contest?.status === "LIVE" && (
              <button
                className="cl-arena-btn"
                onClick={() => navigate(`/contests/${contestId}/arena`)}
              >
                Open Contest Arena
              </button>
            )}
          </div>
        ) : (
          <div className="cl-table-wrapper">
            <table className="cl-table">
              <thead>
                <tr>
                  <th className="th-rank">Rank</th>
                  <th className="th-user">Candidate</th>
                  <th className="th-solved">Solved</th>
                  <th className="th-score">Score</th>
                  <th className="th-penalty">Penalty</th>
                  {leaderboard.problems?.map((prob) => (
                    <th key={prob.problem_id} className="th-prob">
                      <span className="th-prob-label">{prob.label}</span>
                      <span className="th-prob-pts">{prob.points} pts</span>
                    </th>
                  ))}
                  <th className="th-last">Last Submit</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.leaderboard.map((row) => {
                  const isCurrentUser =
                    currentUserId && String(row.user_id) === String(currentUserId)
                  const isTopThree = row.rank <= 3

                  return (
                    <tr
                      key={row.user_id}
                      className={`cl-row ${isCurrentUser ? "current-user-row" : ""} ${
                        isTopThree ? `rank-top-${row.rank}` : ""
                      }`}
                    >
                      <td className="td-rank">
                        {row.rank === 1 ? (
                          <span className="trophy-badge gold">🥇 1</span>
                        ) : row.rank === 2 ? (
                          <span className="trophy-badge silver">🥈 2</span>
                        ) : row.rank === 3 ? (
                          <span className="trophy-badge bronze">🥉 3</span>
                        ) : (
                          <span className="rank-num">#{row.rank}</span>
                        )}
                      </td>
                      <td className="td-user">
                        <div className="user-info-box">
                          <span className="username">
                            {row.username || "Candidate"}
                            {isCurrentUser && <span className="you-pill">YOU</span>}
                          </span>
                          {row.full_name && (
                            <span className="fullname">{row.full_name}</span>
                          )}
                        </div>
                      </td>
                      <td className="td-solved">
                        <span className="solved-count-badge">{row.solved_count}</span>
                      </td>
                      <td className="td-score font-mono">
                        <strong>{row.total_score}</strong>
                      </td>
                      <td className="td-penalty font-mono">
                        {row.penalty_minutes}m
                      </td>

                      {/* Problem columns */}
                      {leaderboard.problems?.map((prob) => {
                        const probStatus = row.problem_results?.[prob.problem_id]
                        const isSolved = probStatus?.solved
                        const attempts = probStatus?.attempts || 0

                        return (
                          <td key={prob.problem_id} className="td-prob-cell">
                            {isSolved ? (
                              <div className="cell-solved">
                                <span className="solve-time">+{probStatus.points || prob.points}</span>
                                {attempts > 1 && (
                                  <span className="attempts-tag">({attempts})</span>
                                )}
                              </div>
                            ) : attempts > 0 ? (
                              <div className="cell-failed">
                                <span className="fail-attempts">-{attempts}</span>
                              </div>
                            ) : (
                              <span className="cell-empty">—</span>
                            )}
                          </td>
                        )
                      })}

                      <td className="td-last font-mono">
                        {row.last_submission_at
                          ? new Date(row.last_submission_at).toLocaleTimeString()
                          : "—"}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  )
}
