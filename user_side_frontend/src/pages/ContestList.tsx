import { useEffect, useState, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import {
  getContests,
  getUserContestHistory,
  registerForContest,
  type ContestListItem,
  type UserContestHistoryItem,
} from "../services/api"
import "./ContestList.css"

export default function ContestList() {
  const navigate = useNavigate()

  // Tabs: "all" | "LIVE" | "UPCOMING" | "ENDED" | "my-contests"
  const [activeTab, setActiveTab] = useState<string>("all")
  const [search, setSearch] = useState("")

  const [contests, setContests] = useState<ContestListItem[]>([])
  const [totalContests, setTotalContests] = useState<number>(0)
  const [page, setPage] = useState<number>(1)
  const [totalPages, setTotalPages] = useState<number>(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // My contests state
  const [myHistory, setMyHistory] = useState<UserContestHistoryItem[]>([])
  const [myStats, setMyStats] = useState<{ total: number; bestRank?: number | null; avgRank?: number | null; totalSolved: number }>({
    total: 0,
    totalSolved: 0,
  })

  // Action pending state
  const [registeringId, setRegisteringId] = useState<string | null>(null)

  // Server time & local clock ticker for countdowns
  const [clock, setClock] = useState<number>(Date.now())
  useEffect(() => {
    const timer = setInterval(() => setClock(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [])

  // Fetch contests list
  const fetchContests = useCallback(async () => {
    if (activeTab === "my-contests") {
      try {
        setLoading(true)
        setError(null)
        const hist = await getUserContestHistory()
        setMyHistory(hist.contests)
        setMyStats({
          total: hist.total_contests,
          bestRank: hist.best_rank,
          avgRank: hist.average_rank,
          totalSolved: hist.total_problems_solved,
        })
      } catch (err: any) {
        setError(err.message || "Failed to load contest history")
      } finally {
        setLoading(false)
      }
      return
    }

    try {
      setLoading(true)
      setError(null)
      const statusParam = activeTab === "all" ? "ALL" : activeTab
      const res = await getContests({
        status: statusParam,
        search: search.trim() || undefined,
        page,
        page_size: 9,
      })
      setContests(res.contests)
      setTotalContests(res.total)
      setTotalPages(res.total_pages)
    } catch (err: any) {
      setError(err.message || "Failed to load contests")
    } finally {
      setLoading(false)
    }
  }, [activeTab, search, page])

  useEffect(() => {
    fetchContests()
  }, [fetchContests])

  // Handle register
  const handleRegister = async (contestId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      setRegisteringId(contestId)
      await registerForContest(contestId)
      await fetchContests()
    } catch (err: any) {
      alert(err.message || "Registration failed")
    } finally {
      setRegisteringId(null)
    }
  }

  // Format countdown string
  const getCountdownText = (startStr: string, endStr: string, status: string) => {
    const start = new Date(startStr).getTime()
    const end = new Date(endStr).getTime()
    const now = clock

    if (status === "LIVE") {
      const diff = Math.max(0, Math.floor((end - now) / 1000))
      const m = Math.floor(diff / 60)
      const s = diff % 60
      return `Ends in ${m}m ${s < 10 ? "0" : ""}${s}s`
    } else if (status === "UPCOMING") {
      const diff = Math.max(0, Math.floor((start - now) / 1000))
      const d = Math.floor(diff / 86400)
      const h = Math.floor((diff % 86400) / 3600)
      const m = Math.floor((diff % 3600) / 60)
      const s = diff % 60
      if (d > 0) return `Starts in ${d}d ${h}h ${m}m`
      return `Starts in ${h}h ${m}m ${s < 10 ? "0" : ""}${s}s`
    }
    return "Contest Concluded"
  }

  return (
    <div className="contest-arena-container">
      {/* Top Header */}
      <header className="contest-arena-header">
        <div className="contest-header-left">
          <div className="contest-badge-row">
            <span className="platform-tag">ARENA MODE</span>
            <span className="live-indicator-pill">
              <span className="pulse-dot"></span> LIVE COMPETITIVE PLATFORM
            </span>
          </div>
          <h1 className="contest-arena-title">Competitive Contest Arena</h1>
          <p className="contest-arena-subtitle">
            Compete in real-time rating contests, solve algorithmic problems under time pressure, and climb the global leaderboards.
          </p>
        </div>

        <div className="contest-header-actions">
          <button
            className="secondary-btn"
            onClick={() => navigate("/coding")}
          >
            ← Practice Bank (1,000)
          </button>
        </div>
      </header>

      {/* Main Navigation Tabs */}
      <div className="contest-tabs-bar">
        <div className="contest-tab-group">
          <button
            className={`contest-tab-btn ${activeTab === "all" ? "active" : ""}`}
            onClick={() => { setActiveTab("all"); setPage(1); }}
          >
            All Contests
          </button>
          <button
            className={`contest-tab-btn ${activeTab === "LIVE" ? "active" : ""}`}
            onClick={() => { setActiveTab("LIVE"); setPage(1); }}
          >
            <span className="tab-live-dot"></span> Live Now
          </button>
          <button
            className={`contest-tab-btn ${activeTab === "UPCOMING" ? "active" : ""}`}
            onClick={() => { setActiveTab("UPCOMING"); setPage(1); }}
          >
            Upcoming
          </button>
          <button
            className={`contest-tab-btn ${activeTab === "ENDED" ? "active" : ""}`}
            onClick={() => { setActiveTab("ENDED"); setPage(1); }}
          >
            Past & Archive
          </button>
          <button
            className={`contest-tab-btn ${activeTab === "my-contests" ? "active" : ""}`}
            onClick={() => { setActiveTab("my-contests"); }}
          >
            My Contests
          </button>
        </div>

        {activeTab !== "my-contests" && (
          <div className="contest-search-box">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <input
              type="text"
              placeholder="Search contests by title..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            />
          </div>
        )}
      </div>

      {/* Content Area */}
      {loading ? (
        <div className="contest-loading-state">
          <div className="spinner"></div>
          <p>Syncing competitive arena server data...</p>
        </div>
      ) : error ? (
        <div className="contest-error-card">
          <p>{error}</p>
          <button className="primary-btn" onClick={fetchContests}>Retry Connection</button>
        </div>
      ) : activeTab === "my-contests" ? (
        /* User Contest History View */
        <div className="my-contests-view">
          <div className="my-contests-stats-row">
            <div className="stat-card">
              <span className="stat-label">Contests Entered</span>
              <span className="stat-value">{myStats.total}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Best Rank Achieved</span>
              <span className="stat-value highlight-gold">
                {myStats.bestRank ? `#${myStats.bestRank}` : "—"}
              </span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Average Placement</span>
              <span className="stat-value">
                {myStats.avgRank ? `#${myStats.avgRank}` : "—"}
              </span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Contest Challenges Solved</span>
              <span className="stat-value highlight-cyan">{myStats.totalSolved}</span>
            </div>
          </div>

          {myHistory.length === 0 ? (
            <div className="empty-history-box">
              <h3>No contest participations yet</h3>
              <p>Register for an upcoming contest or join an active live clash to start building your competitive record!</p>
              <button className="primary-btn" onClick={() => setActiveTab("all")}>
                Explore Active Contests
              </button>
            </div>
          ) : (
            <div className="history-table-container">
              <table className="contest-history-table">
                <thead>
                  <tr>
                    <th>Contest Name</th>
                    <th>Date</th>
                    <th>Status</th>
                    <th>Rank</th>
                    <th>Solved</th>
                    <th>Score</th>
                    <th>Penalty</th>
                    <th>Percentile</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {myHistory.map((item) => (
                    <tr key={item.contest_id}>
                      <td className="contest-cell-title">
                        <strong>{item.contest_title}</strong>
                      </td>
                      <td>{new Date(item.start_time).toLocaleDateString()}</td>
                      <td>
                        <span className={`status-pill pill-${item.status.toLowerCase()}`}>
                          {item.status}
                        </span>
                      </td>
                      <td className="rank-cell">
                        {item.rank ? <strong>#{item.rank}</strong> : "—"}
                        <small className="participants-hint">/{item.total_participants}</small>
                      </td>
                      <td>{item.solved_count}</td>
                      <td><strong>{item.total_score} pts</strong></td>
                      <td>{item.penalty_minutes}m</td>
                      <td>
                        {item.percentile !== null && item.percentile !== undefined ? (
                          <span className="percentile-badge">Top {100 - item.percentile}%</span>
                        ) : "—"}
                      </td>
                      <td>
                        <button
                          className="table-action-btn"
                          onClick={() => navigate(`/contests/${item.contest_id}/results`)}
                        >
                          View Results →
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        /* Regular Contests Grid */
        <div>
          {contests.length === 0 ? (
            <div className="empty-contests-box">
              <h3>No contests found</h3>
              <p>Try clearing your search query or switching between Live, Upcoming, and Past tabs.</p>
            </div>
          ) : (
            <div className="contests-grid">
              {contests.map((c) => {
                const countdown = getCountdownText(c.start_time, c.end_time, c.status)
                const isLive = c.status === "LIVE"
                const isUpcoming = c.status === "UPCOMING"

                return (
                  <div
                    key={c.id}
                    className={`contest-card ${isLive ? "card-live" : ""} ${c.is_proctored ? "card-proctored" : ""}`}
                    onClick={() => navigate(`/contests/${c.slug || c.id}`)}
                  >
                    <div className="contest-card-top">
                      <div className="badge-cluster">
                        <span className={`status-badge badge-${c.status.toLowerCase()}`}>
                          {isLive && <span className="live-dot-inner"></span>}
                          {c.status}
                        </span>
                        {c.is_proctored && (
                          <span className="proctor-badge" title="Webcam & tab monitoring active">
                            🛡️ PROCTORED
                          </span>
                        )}
                        <span className="scoring-badge">{c.scoring_type}</span>
                      </div>

                      <div className="countdown-pill">
                        {countdown}
                      </div>
                    </div>

                    <h3 className="contest-card-title">{c.title}</h3>
                    <p className="contest-card-desc">{c.description}</p>

                    <div className="contest-card-specs">
                      <div className="spec-item">
                        <span className="spec-label">Duration</span>
                        <span className="spec-val">{c.duration_minutes} mins</span>
                      </div>
                      <div className="spec-item">
                        <span className="spec-label">Problems</span>
                        <span className="spec-val">{c.problems_count} Challenges</span>
                      </div>
                      <div className="spec-item">
                        <span className="spec-label">Registered</span>
                        <span className="spec-val">{c.registered_count} coders</span>
                      </div>
                    </div>

                    <div className="contest-card-footer">
                      <div className="timing-info">
                        <small>Starts: {new Date(c.start_time).toLocaleDateString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</small>
                      </div>

                      <div className="card-action">
                        {isLive ? (
                          <button
                            className="enter-arena-btn"
                            onClick={(e) => {
                              e.stopPropagation()
                              navigate(`/contests/${c.id}/arena`)
                            }}
                          >
                            Enter Arena ⚡
                          </button>
                        ) : isUpcoming ? (
                          c.is_registered ? (
                            <span className="registered-indicator">Registered ✓</span>
                          ) : (
                            <button
                              className="register-btn"
                              disabled={registeringId === c.id}
                              onClick={(e) => handleRegister(c.id, e)}
                            >
                              {registeringId === c.id ? "Registering..." : "Register Now"}
                            </button>
                          )
                        ) : (
                          <button
                            className="results-btn"
                            onClick={(e) => {
                              e.stopPropagation()
                              navigate(`/contests/${c.id}/leaderboard`)
                            }}
                          >
                            Leaderboard →
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="contest-pagination">
              <button
                className="page-nav-btn"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                ← Previous
              </button>
              <span className="page-indicator">
                Page {page} of {totalPages} ({totalContests} total)
              </span>
              <button
                className="page-nav-btn"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                Next →
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
