import { useCallback, useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  getAchievementDetail,
  getAchievements,
  getAchievementsSummary,
  getPracticeStats,
  type AchievementItem,
  type AchievementSummaryResponse,
  type PracticeStatsResponse,
} from "../services/api"
import "./Achievements.css"

const CATEGORIES = [
  "All",
  "Practice",
  "Consistency",
  "Mastery",
  "Difficulty",
  "Technology",
  "Problem Solving",
  "Interview",
  "Milestones",
]

export default function Achievements() {
  const navigate = useNavigate()

  const [mobileMenu, setMobileMenu] = useState(false)
  const [achievements, setAchievements] = useState<AchievementItem[]>([])
  const [summary, setSummary] = useState<AchievementSummaryResponse | null>(null)
  const [practiceStats, setPracticeStats] = useState<PracticeStatsResponse | null>(null)

  // Filters
  const [selectedCategory, setSelectedCategory] = useState("All")
  const [statusFilter, setStatusFilter] = useState<"all" | "unlocked" | "locked">("all")
  const [searchQuery, setSearchQuery] = useState("")

  // Detail Modal
  const [selectedAchievement, setSelectedAchievement] = useState<AchievementItem | null>(null)
  const [modalLoading, setModalLoading] = useState(false)

  // Loading & Error
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  // ------------------------------------------------------------
  // LOAD ACHIEVEMENTS & SUMMARY
  // ------------------------------------------------------------
  const loadData = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const [listRes, summaryRes, statsRes] = await Promise.all([
        getAchievements(selectedCategory !== "All" ? selectedCategory : undefined),
        getAchievementsSummary().catch(() => null),
        getPracticeStats().catch(() => null),
      ])
      setAchievements(listRes.achievements)
      if (summaryRes) setSummary(summaryRes)
      if (statsRes) setPracticeStats(statsRes)
    } catch (err) {
      console.error("Failed to load achievements data:", err)
      setError("Unable to load achievements. Please check your connection and retry.")
    } finally {
      setLoading(false)
    }
  }, [selectedCategory])

  useEffect(() => {
    void loadData()
  }, [loadData])

  // ------------------------------------------------------------
  // DETAIL MODAL
  // ------------------------------------------------------------
  const openDetail = useCallback(async (item: AchievementItem) => {
    setSelectedAchievement(item)
    setModalLoading(true)
    try {
      const res = await getAchievementDetail(item.id)
      setSelectedAchievement(res.achievement)
    } catch (err) {
      console.error("Failed to load achievement detail:", err)
    } finally {
      setModalLoading(false)
    }
  }, [])

  const closeDetail = useCallback(() => {
    setSelectedAchievement(null)
  }, [])

  // ------------------------------------------------------------
  // CLIENT FILTERING (SEARCH & STATUS)
  // ------------------------------------------------------------
  const filteredAchievements = useMemo(() => {
    let result = achievements

    // Status filter
    if (statusFilter === "unlocked") {
      result = result.filter((a) => a.unlocked)
    } else if (statusFilter === "locked") {
      result = result.filter((a) => !a.unlocked)
    }

    // Search query
    if (searchQuery.trim()) {
      const term = searchQuery.trim().toLowerCase()
      result = result.filter(
        (a) =>
          a.name.toLowerCase().includes(term) ||
          a.description.toLowerCase().includes(term) ||
          a.category.toLowerCase().includes(term) ||
          a.rarity.toLowerCase().includes(term),
      )
    }

    return result
  }, [achievements, statusFilter, searchQuery])

  // Category counts from summary or current list
  const categoryCountMap = useMemo(() => {
    const map = new Map<string, number>()
    if (summary) {
      for (const cat of summary.categories) {
        map.set(cat.category.toLowerCase(), cat.total)
      }
    }
    return map
  }, [summary])

  return (
    <div className="ach-shell">
      {/* ======================================================
          SIDEBAR NAVIGATION
      ====================================================== */}
      <aside className={`ach-sidebar ${mobileMenu ? "mobile-open" : ""}`}>
        <div className="ach-brand">
          <div className="brand-logo">
            <span>AI</span>
          </div>
          <div className="brand-name">
            <strong>AI Interview</strong>
            <span>Platform</span>
          </div>
          <button
            type="button"
            className="ach-collapse-btn"
            onClick={() => setMobileMenu(false)}
          >
            ‹
          </button>
        </div>

        <nav className="ach-nav">
          <button
            type="button"
            className="ach-nav-link"
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
            className="ach-nav-link"
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
            className="ach-nav-link"
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
            className="ach-nav-link"
            onClick={() => {
              setMobileMenu(false)
              navigate("/performance")
            }}
          >
            <span className="nav-icon">▥</span>
            <span>Performance</span>
          </button>

          <button
            type="button"
            className="ach-nav-link"
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
            className="ach-nav-link active"
            onClick={() => setMobileMenu(false)}
          >
            <span className="nav-icon">🏆</span>
            <span>Achievements</span>
          </button>

          <button
            type="button"
            className="ach-nav-link"
            onClick={() => {
              setMobileMenu(false)
              navigate("/notifications")
            }}
          >
            <span className="nav-icon">🔔</span>
            <span>Notifications</span>
          </button>

          <button
            type="button"
            className="ach-nav-link"
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
            className="ach-nav-link"
            onClick={() => {
              setMobileMenu(false)
              navigate("/settings")
            }}
          >
            <span className="nav-icon">⚙</span>
            <span>Settings</span>
          </button>
        </nav>

        {/* QUICK PRACTICE CARD */}
        <div className="ach-practice-card">
          <div className="practice-icon">🎯</div>
          <h3>Practice & Earn</h3>
          <p>Solve targeted questions in Question Practice to unlock more badges and XP.</p>
          <button
            type="button"
            onClick={() => {
              setMobileMenu(false)
              navigate("/practice")
            }}
          >
            Go to Practice <span>→</span>
          </button>
        </div>
      </aside>

      {/* ======================================================
          MAIN ACHIEVEMENTS INTERFACE
      ====================================================== */}
      <main className="ach-main">
        {/* TOP BAR */}
        <header className="ach-top-bar">
          <div className="ach-bar-left">
            <button
              type="button"
              className="ach-mobile-toggle"
              onClick={() => setMobileMenu(true)}
              aria-label="Open menu"
            >
              ☰
            </button>
            <button
              type="button"
              className="ach-back-btn"
              onClick={() => navigate("/dashboard")}
            >
              ← Back to Dashboard
            </button>
          </div>

          <div className="ach-bar-right">
            {practiceStats?.xp && (
              <div className="ach-stat-pill ach-xp-pill">
                <span>⚡ Lvl {practiceStats.xp.level}</span>
                <span>{practiceStats.xp.total_xp} XP</span>
              </div>
            )}
            {practiceStats?.streak && (
              <div className="ach-stat-pill ach-streak-pill">
                <span>🔥 {practiceStats.streak.current_streak} Day Streak</span>
              </div>
            )}
          </div>
        </header>

        {/* HERO HEADER */}
        <section className="ach-hero">
          <div className="ach-hero-copy">
            <span className="ach-eyebrow">ACCOMPLISHMENTS &amp; REWARDS</span>
            <h1>Achievements</h1>
            <p>
              Track your preparation milestones, unlock rare badges, and earn XP across
              all technical disciplines and mock interview sessions.
            </p>
          </div>

          {/* STATS OVERVIEW CARDS */}
          <div className="ach-kpi-row">
            <div className="ach-kpi-card purple-kpi">
              <span className="ach-kpi-label">Badges Unlocked</span>
              <strong className="ach-kpi-value">
                {summary ? summary.unlocked_count : "—"} / {summary ? summary.total_achievements : "—"}
              </strong>
              <small>{summary ? `${summary.locked_count} remaining to unlock` : "Total available badges"}</small>
            </div>

            <div className="ach-kpi-card cyan-kpi">
              <span className="ach-kpi-label">Completion Rate</span>
              <strong className="ach-kpi-value">
                {summary ? `${summary.completion_percentage}%` : "—"}
              </strong>
              <small>Across all canonical categories</small>
            </div>

            <div className="ach-kpi-card amber-kpi">
              <span className="ach-kpi-label">Achievement XP</span>
              <strong className="ach-kpi-value">
                {summary ? `+${summary.total_xp_earned}` : "—"}
              </strong>
              <small>XP earned from unlocked badges</small>
            </div>

            <div className="ach-kpi-card emerald-kpi">
              <span className="ach-kpi-label">Active Categories</span>
              <strong className="ach-kpi-value">8 Domains</strong>
              <small>Practice, Mastery, Consistency &amp; more</small>
            </div>
          </div>
        </section>

        {/* ERROR STATE */}
        {error && (
          <div className="ach-error-banner">
            <span>⚠️ {error}</span>
            <button type="button" onClick={() => void loadData()}>
              Retry
            </button>
          </div>
        )}

        {/* ======================================================
            FILTERS & SEARCH PANEL
        ====================================================== */}
        <section className="ach-filter-section">
          <div className="ach-search-row">
            <div className="ach-search-wrap">
              <span className="ach-search-icon">🔍</span>
              <input
                type="text"
                placeholder="Search achievements by title, requirement, or category..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="ach-search-input"
              />
              {searchQuery && (
                <button
                  type="button"
                  className="clear-search-btn"
                  onClick={() => setSearchQuery("")}
                >
                  ×
                </button>
              )}
            </div>

            {/* STATUS TOGGLE */}
            <div className="ach-status-filter">
              <button
                type="button"
                className={`status-tab-btn ${statusFilter === "all" ? "active" : ""}`}
                onClick={() => setStatusFilter("all")}
              >
                All
              </button>
              <button
                type="button"
                className={`status-tab-btn ${statusFilter === "unlocked" ? "active" : ""}`}
                onClick={() => setStatusFilter("unlocked")}
              >
                ✓ Unlocked
              </button>
              <button
                type="button"
                className={`status-tab-btn ${statusFilter === "locked" ? "active" : ""}`}
                onClick={() => setStatusFilter("locked")}
              >
                🔒 In Progress
              </button>
            </div>
          </div>

          {/* CATEGORY PILLS */}
          <div className="ach-category-pills">
            {CATEGORIES.map((cat) => {
              const count =
                cat === "All"
                  ? summary?.total_achievements
                  : categoryCountMap.get(cat.toLowerCase())

              return (
                <button
                  key={cat}
                  type="button"
                  className={`cat-pill-btn ${selectedCategory === cat ? "active" : ""}`}
                  onClick={() => setSelectedCategory(cat)}
                >
                  <span>{cat}</span>
                  {count !== undefined && (
                    <span className="cat-badge-count">{count}</span>
                  )}
                </button>
              )
            })}
          </div>
        </section>

        {/* RESULTS META */}
        <div className="ach-results-meta">
          <span>
            Showing <strong>{filteredAchievements.length}</strong> of{" "}
            <strong>{achievements.length}</strong> achievements
            {selectedCategory !== "All" && ` in ${selectedCategory}`}
          </span>
        </div>

        {/* ======================================================
            ACHIEVEMENTS GRID
        ====================================================== */}
        {loading ? (
          <div className="ach-skeleton-grid">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="skeleton-card" />
            ))}
          </div>
        ) : filteredAchievements.length > 0 ? (
          <div className="ach-grid">
            {filteredAchievements.map((item) => {
              const rarityLower = item.rarity.toLowerCase()
              const rarityClass =
                rarityLower === "legendary"
                  ? "rarity-legendary"
                  : rarityLower === "epic"
                  ? "rarity-epic"
                  : rarityLower === "rare"
                  ? "rarity-rare"
                  : "rarity-common"

              const pillClass =
                rarityLower === "legendary"
                  ? "rarity-pill-legendary"
                  : rarityLower === "epic"
                  ? "rarity-pill-epic"
                  : rarityLower === "rare"
                  ? "rarity-pill-rare"
                  : "rarity-pill-common"

              const fillWidth = Math.min(100, Math.max(item.progress_percentage, item.unlocked ? 100 : 0))

              return (
                <article
                  key={item.id}
                  className={`ach-card ${item.unlocked ? "card-unlocked" : ""} ${rarityClass}`}
                  onClick={() => void openDetail(item)}
                >
                  <div className="ach-card-header">
                    <div className="ach-card-icon-box">
                      <span>{item.icon}</span>
                    </div>

                    <div className="ach-card-badges">
                      <span className={`ach-rarity-pill ${pillClass}`}>
                        {item.rarity}
                      </span>
                      <span className="ach-xp-badge">
                        +{item.xp_reward} XP
                      </span>
                    </div>
                  </div>

                  <h3 className="ach-card-title">{item.name}</h3>
                  <p className="ach-card-desc">{item.description}</p>

                  <div className="ach-card-progress">
                    <div className="ach-progress-labels">
                      <span className="ach-category-tag">{item.category}</span>
                      <span className="ach-count-text">
                        {item.current_progress} / {item.target_progress}
                      </span>
                    </div>

                    <div className="ach-track">
                      <div
                        className="ach-fill"
                        style={{ width: `${fillWidth}%` }}
                      />
                    </div>
                  </div>

                  <div className="ach-card-footer">
                    {item.unlocked ? (
                      <span className="unlocked-status-badge">
                        ✓ Unlocked
                        {item.unlocked_at && (
                          <small className="ach-unlock-date">
                            {" "}• {new Date(item.unlocked_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                          </small>
                        )}
                      </span>
                    ) : (
                      <span className="locked-status-badge">
                        🔒 In Progress ({item.progress_percentage}%)
                      </span>
                    )}

                    <span className="ach-inspect-hint">Details →</span>
                  </div>
                </article>
              )
            })}
          </div>
        ) : (
          <div className="ach-empty-state">
            <div className="empty-icon">🏆</div>
            <h3>No Achievements Found</h3>
            <p>
              {searchQuery
                ? `No achievements match your search "${searchQuery}".`
                : "No achievements match your current filter selections."}
            </p>
            <button
              type="button"
              className="ach-primary-btn"
              onClick={() => {
                setSelectedCategory("All")
                setStatusFilter("all")
                setSearchQuery("")
              }}
            >
              Reset Filters
            </button>
          </div>
        )}

        {/* ======================================================
            ACHIEVEMENT DETAIL MODAL
        ====================================================== */}
        {selectedAchievement && (
          <div className="ach-modal-overlay" onClick={closeDetail}>
            <div className="ach-modal-content" onClick={(e) => e.stopPropagation()}>
              <button
                type="button"
                className="ach-modal-close"
                onClick={closeDetail}
                aria-label="Close"
              >
                ✕
              </button>

              <div className="ach-modal-header">
                <div className="ach-modal-icon">
                  <span>{selectedAchievement.icon}</span>
                </div>
                <div className="ach-modal-titles">
                  <h2>{selectedAchievement.name}</h2>
                  <div className="ach-modal-badges">
                    <span className="ach-rarity-pill rarity-pill-epic">
                      {selectedAchievement.rarity}
                    </span>
                    <span className="ach-xp-badge">
                      +{selectedAchievement.xp_reward} XP
                    </span>
                    <span className="ach-category-tag">
                      {selectedAchievement.category}
                    </span>
                    {modalLoading && (
                      <span className="ach-category-tag" style={{ opacity: 0.7 }}>
                        Syncing...
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div className="ach-modal-body">
                <div className="modal-desc-box">
                  <h4>Requirement</h4>
                  <p>{selectedAchievement.description}</p>
                </div>

                <div className="modal-progress-box">
                  <div className="modal-progress-meta">
                    <span>Progress:</span>
                    <strong>
                      {selectedAchievement.current_progress} / {selectedAchievement.target_progress} (
                      {selectedAchievement.progress_percentage}%)
                    </strong>
                  </div>

                  <div className="modal-track">
                    <div
                      className={`modal-fill ${selectedAchievement.unlocked ? "modal-fill-unlocked" : ""}`}
                      style={{
                        width: `${Math.min(100, Math.max(selectedAchievement.progress_percentage, selectedAchievement.unlocked ? 100 : 0))}%`,
                      }}
                    />
                  </div>

                  {selectedAchievement.unlocked ? (
                    <div className="modal-status-text unlocked">
                      ✓ Achievement Unlocked!{" "}
                      {selectedAchievement.unlocked_at &&
                        `on ${new Date(selectedAchievement.unlocked_at).toLocaleDateString("en-US", {
                          month: "long",
                          day: "numeric",
                          year: "numeric",
                        })}`}
                    </div>
                  ) : (
                    <div className="modal-status-text">
                      🔒 In Progress — Need{" "}
                      {Math.max(
                        0,
                        selectedAchievement.target_progress - selectedAchievement.current_progress,
                      )}{" "}
                      more to unlock this achievement.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
