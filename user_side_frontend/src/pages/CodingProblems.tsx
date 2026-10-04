import { useEffect, useState, useMemo, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import {
  getCodingProblems,
  getCodingStats,
  getArenaLeaderboard,
  getPersonalizedRecommendations,
  type CodingProblemListItem,
  type CodingStats,
  type LeaderboardItem,
  type PersonalizedRecommendationsResponse,
} from "../services/api"
import "./CodingProblems.css"

export default function CodingProblems() {
  const navigate = useNavigate()

  // Arena View Mode: "arena" | "leaderboard" | "recommendations"
  const [activeMode, setActiveMode] = useState<"arena" | "leaderboard" | "recommendations">("arena")

  // Problem list state
  const [problems, setProblems] = useState<CodingProblemListItem[]>([])
  const [totalProblems, setTotalProblems] = useState<number>(0)
  const [page, setPage] = useState<number>(1)
  const [totalPages, setTotalPages] = useState<number>(1)
  const pageSize = 15

  // Stats & Additional Views State
  const [stats, setStats] = useState<CodingStats | null>(null)
  const [leaderboard, setLeaderboard] = useState<LeaderboardItem[]>([])
  const [recommendations, setRecommendations] = useState<PersonalizedRecommendationsResponse | null>(null)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Advanced Filters
  const [search, setSearch] = useState("")
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>("All")
  const [selectedTopic, setSelectedTopic] = useState<string>("All")
  const [statusFilter, setStatusFilter] = useState<"all" | "solved" | "unsolved" | "attempted">("all")
  const [sortOption, setSortOption] = useState<string>("difficulty_asc")

  // Load problems based on active filters and page
  const fetchProblems = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      let solvedParam: boolean | undefined = undefined
      let attemptedParam: boolean | undefined = undefined

      if (statusFilter === "solved") solvedParam = true
      else if (statusFilter === "unsolved") solvedParam = false
      else if (statusFilter === "attempted") attemptedParam = true

      const res = await getCodingProblems({
        search: search.trim() || undefined,
        difficulty: selectedDifficulty,
        topic: selectedTopic,
        solved: solvedParam,
        attempted: attemptedParam,
        sort: sortOption,
        page,
        page_size: pageSize,
      })

      setProblems(res.problems || res.items || [])
      setTotalProblems(res.total)
      setTotalPages(res.total_pages || Math.max(1, Math.ceil(res.total / pageSize)))
    } catch (err: any) {
      setError(err?.message || "Failed to load coding arena challenges.")
    } finally {
      setLoading(false)
    }
  }, [search, selectedDifficulty, selectedTopic, statusFilter, sortOption, page])

  // Load general user stats
  const fetchStats = async () => {
    try {
      const statsRes = await getCodingStats()
      setStats(statsRes)
    } catch {
      // non-blocking
    }
  }

  // Load Leaderboard data
  const fetchLeaderboard = async () => {
    try {
      setLoading(true)
      const lbRes = await getArenaLeaderboard(50)
      setLeaderboard(lbRes.leaderboard || [])
    } catch (err: any) {
      setError(err?.message || "Failed to load leaderboard.")
    } finally {
      setLoading(false)
    }
  }

  // Load Recommendations data
  const fetchRecommendations = async () => {
    try {
      setLoading(true)
      const recRes = await getPersonalizedRecommendations()
      setRecommendations(recRes)
    } catch (err: any) {
      setError(err?.message || "Failed to load personalized recommendations.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStats()
  }, [])

  useEffect(() => {
    if (activeMode === "arena") {
      fetchProblems()
    } else if (activeMode === "leaderboard") {
      fetchLeaderboard()
    } else if (activeMode === "recommendations") {
      fetchRecommendations()
    }
  }, [activeMode, fetchProblems])

  // Unique topic list extracted from loaded problems
  const availableTopics = useMemo(() => {
    const topicSet = new Set<string>()
    problems.forEach((p) => {
      if (p.topic) topicSet.add(p.topic)
    })
    return ["All", ...Array.from(topicSet).sort()]
  }, [problems])

  return (
    <div className="coding-problems-container">
      {/* Sticky Header */}
      <header className="coding-header">
        <div className="coding-header-left">
          <button
            type="button"
            className="back-btn"
            onClick={() => navigate("/dashboard")}
          >
            ← Back to Dashboard
          </button>
          <div className="coding-brand">
            <div className="brand-icon">⌨</div>
            <div className="brand-text">
              <h1>Technical Coding Arena</h1>
              <p>Master Data Structures & Algorithms with Instant Isolated Sandbox Execution</p>
            </div>
          </div>
        </div>

        {/* Mode Selector Tabs (8B-5, 8B-7, 8B-9) */}
        <div className="arena-mode-nav">
          <button
            type="button"
            className={`arena-mode-btn ${activeMode === "arena" ? "active" : ""}`}
            onClick={() => setActiveMode("arena")}
          >
            <span>▦</span>
            <span>Problems</span>
          </button>
          <button
            type="button"
            className={`arena-mode-btn ${activeMode === "recommendations" ? "active" : ""}`}
            onClick={() => setActiveMode("recommendations")}
          >
            <span>🎯</span>
            <span>Recommended</span>
          </button>
          <button
            type="button"
            className={`arena-mode-btn ${activeMode === "leaderboard" ? "active" : ""}`}
            onClick={() => setActiveMode("leaderboard")}
          >
            <span>🏆</span>
            <span>Leaderboard</span>
          </button>
          <button
            type="button"
            className="arena-mode-btn"
            style={{
              background: "linear-gradient(135deg, #4f46e5, #7c3aed)",
              color: "#fff",
              borderColor: "#818cf8",
              boxShadow: "0 0 10px rgba(99, 102, 241, 0.35)",
            }}
            onClick={() => navigate("/contests")}
            title="Browse Live Contests & Tournaments"
          >
            <span>⚡</span>
            <span>Live Contests</span>
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="coding-main">
        {/* Real Performance Analytics Banner (8B-8) */}
        <div className="coding-stats-banner">
          <div className="stat-box">
            <div className="stat-icon-wrap purple">✦</div>
            <div className="stat-info">
              <span className="stat-value">{stats?.total_solved ?? 0}</span>
              <span className="stat-label">Solved ({stats?.easy_solved ?? 0}E / {stats?.medium_solved ?? 0}M / {stats?.hard_solved ?? 0}H)</span>
            </div>
          </div>

          <div className="stat-box">
            <div className="stat-icon-wrap blue">◎</div>
            <div className="stat-info">
              <span className="stat-value">{stats?.total_attempted ?? 0}</span>
              <span className="stat-label">Problems Attempted</span>
            </div>
          </div>

          <div className="stat-box">
            <div className="stat-icon-wrap green">✓</div>
            <div className="stat-info">
              <span className="stat-value">{stats?.success_rate ?? 0}%</span>
              <span className="stat-label">Accuracy Rate</span>
            </div>
          </div>

          <div className="stat-box">
            <div className="stat-icon-wrap red">🔥</div>
            <div className="stat-info">
              <span className="stat-value">{stats?.current_streak ?? 0} Days</span>
              <span className="stat-label">Current Streak (Best: {stats?.longest_streak ?? 0})</span>
            </div>
          </div>
        </div>

        {/* ============================================================
            VIEW 1: CODING ARENA PROBLEMS LIST
        ============================================================ */}
        {activeMode === "arena" && (
          <>
            {/* Filter Section */}
            <section className="filter-section">
              <div className="filter-top-row">
                {/* Search Bar */}
                <div className="search-input-wrapper">
                  <span className="search-icon">🔍</span>
                  <input
                    type="text"
                    className="problem-search-input"
                    placeholder="Search by problem title, keyword, or pattern..."
                    value={search}
                    onChange={(e) => {
                      setSearch(e.target.value)
                      setPage(1)
                    }}
                  />
                </div>

                {/* Sort Dropdown */}
                <div className="sort-select-wrapper">
                  <select
                    className="arena-select"
                    value={sortOption}
                    onChange={(e) => {
                      setSortOption(e.target.value)
                      setPage(1)
                    }}
                  >
                    <option value="difficulty_asc">Difficulty (Easy → Hard)</option>
                    <option value="difficulty_desc">Difficulty (Hard → Easy)</option>
                    <option value="title_asc">Title (A → Z)</option>
                    <option value="title_desc">Title (Z → A)</option>
                    <option value="newest">Newest Added</option>
                  </select>
                </div>
              </div>

              {/* Filter Pills Row */}
              <div className="filter-pills-row">
                {/* Difficulty Filters */}
                <div className="filter-group">
                  <span className="filter-group-label">Difficulty:</span>
                  {["All", "Easy", "Medium", "Hard"].map((diff) => (
                    <button
                      key={diff}
                      type="button"
                      className={`pill-btn ${selectedDifficulty === diff ? "active" : ""}`}
                      onClick={() => {
                        setSelectedDifficulty(diff)
                        setPage(1)
                      }}
                    >
                      {diff}
                    </button>
                  ))}
                </div>

                {/* Status Filters */}
                <div className="filter-group">
                  <span className="filter-group-label">Status:</span>
                  {[
                    { id: "all", label: "All" },
                    { id: "solved", label: "Solved" },
                    { id: "unsolved", label: "Unsolved" },
                    { id: "attempted", label: "Attempted" },
                  ].map((st) => (
                    <button
                      key={st.id}
                      type="button"
                      className={`pill-btn ${statusFilter === st.id ? "active" : ""}`}
                      onClick={() => {
                        setStatusFilter(st.id as any)
                        setPage(1)
                      }}
                    >
                      {st.label}
                    </button>
                  ))}
                </div>

                {/* Topic Filters */}
                <div className="filter-group">
                  <span className="filter-group-label">Topic:</span>
                  {availableTopics.slice(0, 8).map((tpc) => (
                    <button
                      key={tpc}
                      type="button"
                      className={`pill-btn ${selectedTopic === tpc ? "active" : ""}`}
                      onClick={() => {
                        setSelectedTopic(tpc)
                        setPage(1)
                      }}
                    >
                      {tpc}
                    </button>
                  ))}
                </div>
              </div>
            </section>

            {/* Problem List Display */}
            {loading ? (
              <div className="empty-state">
                <h3>Loading Challenges...</h3>
                <p>Querying verified problem sets from database.</p>
              </div>
            ) : error ? (
              <div className="empty-state">
                <h3 style={{ color: "#fb7185" }}>{error}</h3>
                <button
                  type="button"
                  className="solve-cta-btn"
                  style={{ margin: "1rem auto 0" }}
                  onClick={fetchProblems}
                >
                  Retry
                </button>
              </div>
            ) : problems.length === 0 ? (
              <div className="empty-state">
                <h3>No problems found</h3>
                <p>Try modifying your search or relaxing the filter criteria.</p>
              </div>
            ) : (
              <div className="problems-grid">
                {problems.map((problem) => {
                  const isSolved = problem.is_solved === true
                  const isAttempted = problem.is_attempted === true
                  const diffClass = problem.difficulty.toLowerCase()

                  return (
                    <div key={problem.id} className="problem-card">
                      <div className="problem-card-left">
                        <div
                          className={`problem-status-icon ${
                            isSolved ? "solved" : isAttempted ? "attempted" : "unsolved"
                          }`}
                          title={isSolved ? "Solved" : isAttempted ? "Attempted" : "Unsolved"}
                        >
                          {isSolved ? "✓" : isAttempted ? "◐" : "○"}
                        </div>

                        <div className="problem-meta">
                          <div className="problem-title-row">
                            <span className="problem-title">{problem.title}</span>
                            <span className={`difficulty-badge ${diffClass}`}>
                              {problem.difficulty}
                            </span>
                            {problem.acceptance_rate !== null && problem.acceptance_rate !== undefined && (
                              <span className="acceptance-badge">
                                {problem.acceptance_rate}% Acceptance
                              </span>
                            )}
                          </div>

                          <div className="problem-sub-meta">
                            <span className="topic-tag">🏷 {problem.topic}</span>

                            {problem.tags && problem.tags.length > 0 && (
                              <div className="tags-list-row">
                                {problem.tags.slice(0, 3).map((tag, idx) => (
                                  <span key={idx} className="arena-tag-pill">
                                    {tag}
                                  </span>
                                ))}
                              </div>
                            )}

                            <div className="langs-supported">
                              {problem.supported_languages?.map((lang) => (
                                <span key={lang} className="lang-pill">
                                  {lang === "cpp" ? "C++" : lang}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="problem-card-right">
                        <button
                          type="button"
                          className="solve-cta-btn"
                          onClick={() => navigate(`/coding/${problem.slug || problem.id}`)}
                        >
                          <span>{isSolved ? "Review Code" : "Solve Challenge"}</span>
                          <span>→</span>
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="pagination-bar">
                <button
                  type="button"
                  className="pagination-btn"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  ← Previous
                </button>
                <span style={{ fontSize: "0.85rem", color: "#94a3b8" }}>
                  Page {page} of {totalPages} ({totalProblems} challenges)
                </span>
                <button
                  type="button"
                  className="pagination-btn"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next →
                </button>
              </div>
            )}
          </>
        )}

        {/* ============================================================
            VIEW 2: ARENA LEADERBOARD (8B-7)
        ============================================================ */}
        {activeMode === "leaderboard" && (
          <div className="leaderboard-container">
            {loading ? (
              <div className="empty-state">Loading Arena Rankings...</div>
            ) : leaderboard.length === 0 ? (
              <div className="empty-state">
                <h3>No candidates ranked yet</h3>
                <p>Submit your first coding solution to claim rank #1 on the leaderboard!</p>
              </div>
            ) : (
              <table className="leaderboard-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Candidate</th>
                    <th>Problems Solved</th>
                    <th>Accepted Subs</th>
                    <th>Avg Score</th>
                    <th>Streak</th>
                    <th>Coding XP</th>
                  </tr>
                </thead>
                <tbody>
                  {leaderboard.map((item) => {
                    const rankMedal =
                      item.rank === 1 ? "🥇" : item.rank === 2 ? "🥈" : item.rank === 3 ? "🥉" : `#${item.rank}`

                    return (
                      <tr key={item.user_id}>
                        <td>
                          <span className="rank-medal">{rankMedal}</span>
                        </td>
                        <td style={{ fontWeight: 600, color: "#f8fafc" }}>{item.user_name}</td>
                        <td>{item.problems_solved}</td>
                        <td>{item.total_accepted}</td>
                        <td>{item.average_score} pts</td>
                        <td>🔥 {item.current_streak} days</td>
                        <td>
                          <span className="xp-pill">{item.coding_xp} XP</span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* ============================================================
            VIEW 3: PERSONALIZED PRACTICE (8B-9)
        ============================================================ */}
        {activeMode === "recommendations" && (
          <div className="recs-container">
            {loading ? (
              <div className="empty-state">Analyzing performance and building personalized curriculum...</div>
            ) : !recommendations ? (
              <div className="empty-state">Unable to load recommendations.</div>
            ) : (
              <>
                <div className="recs-header-card">
                  <h3 style={{ margin: "0 0 0.5rem", color: "#f8fafc" }}>
                    Personalized Skill Roadmap
                  </h3>
                  <p style={{ color: "#cbd5e1", fontSize: "0.9rem", margin: 0 }}>
                    Our recommendation engine continuously analyzes your submission history, pass rates, and runtime bottlenecks to curate targeted practice.
                  </p>

                  <div className="recs-topics-row">
                    <div className="topic-group weak">
                      <h4>Focus Areas (Areas to Strengthen)</h4>
                      <div className="topic-pills-wrap">
                        {recommendations.weak_topics.length > 0 ? (
                          recommendations.weak_topics.map((t, idx) => (
                            <span key={idx} className="arena-tag-pill" style={{ color: "#fbbf24", borderColor: "#fbbf24" }}>
                              {t}
                            </span>
                          ))
                        ) : (
                          <span style={{ fontSize: "0.8rem", color: "#94a3b8" }}>No weak areas detected!</span>
                        )}
                      </div>
                    </div>

                    <div className="topic-group strong">
                      <h4>Mastered Topics</h4>
                      <div className="topic-pills-wrap">
                        {recommendations.strong_topics.length > 0 ? (
                          recommendations.strong_topics.map((t, idx) => (
                            <span key={idx} className="arena-tag-pill" style={{ color: "#34d399", borderColor: "#34d399" }}>
                              ✓ {t}
                            </span>
                          ))
                        ) : (
                          <span style={{ fontSize: "0.8rem", color: "#94a3b8" }}>Solve challenges to unlock mastered topics.</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="problems-grid">
                  {recommendations.recommended_problems.map((prob, idx) => (
                    <div key={prob.id} className="problem-card">
                      <div className="problem-card-left">
                        <div className="problem-status-icon unsolved">○</div>
                        <div className="problem-meta">
                          <div className="problem-title-row">
                            <span className="problem-title">{prob.title}</span>
                            <span className={`difficulty-badge ${prob.difficulty.toLowerCase()}`}>
                              {prob.difficulty}
                            </span>
                          </div>
                          <p style={{ fontSize: "0.8125rem", color: "#818cf8", margin: "0.2rem 0 0" }}>
                            💡 {recommendations.recommendation_reasons[idx] || "Recommended challenge"}
                          </p>
                        </div>
                      </div>

                      <div className="problem-card-right">
                        <button
                          type="button"
                          className="solve-cta-btn"
                          onClick={() => navigate(`/coding/${prob.slug || prob.id}`)}
                        >
                          <span>Practice Now</span>
                          <span>→</span>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
