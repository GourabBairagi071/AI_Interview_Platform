import { useCallback, useEffect, useMemo, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import {
  bookmarkPracticeQuestion,
  getPracticeHistory,
  getPracticeProgress,
  getPracticeQuestionDetail,
  getPracticeQuestions,
  getPracticeStats,
  getPracticeTechnologies,
  getPracticeTechnologyTopics,
  solvePracticeQuestion,
  unbookmarkPracticeQuestion,
  type PracticeHistoryItem,
  type PracticeProgressResponse,
  type PracticeQuestionDetailResponse,
  type PracticeQuestionSummary,
  type PracticeStatsResponse,
  type TechnologySummary,
  type TopicSummary,
} from "../services/api"
import "./QuestionPractice.css"

const TECH_ICONS: Record<string, string> = {
  python: "🐍",
  java: "☕",
  "c++": "⚙️",
  cpp: "⚙️",
  c: "🔧",
  javascript: "🟨",
  typescript: "🔷",
  react: "⚛️",
  "next.js": "▲",
  nextjs: "▲",
  "node.js": "🟢",
  nodejs: "🟢",
  express: "🚂",
  sql: "🗄️",
  dbms: "💾",
  postgresql: "🐘",
  mongodb: "🍃",
  dsa: "🌲",
  algorithms: "🧮",
  os: "🖥️",
  "computer networks": "🌐",
  oop: "📦",
  kotlin: "🟣",
  statistics: "📊",
  "data science": "📈",
  "machine learning": "🤖",
  "deep learning": "🧠",
  nlp: "🗣️",
  "computer vision": "👁️",
  ai: "✨",
  genai: "🔮",
  llms: "📚",
  rag: "🔍",
  "vector databases": "🗃️",
  langchain: "🦜",
  "data engineering": "🏗️",
  spark: "⚡",
  kafka: "📨",
  cloud: "☁️",
  aws: "🟧",
  gcp: "🌈",
  azure: "🟦",
  docker: "🐳",
  kubernetes: "☸️",
  devops: "♾️",
  linux: "🐧",
  git: "🌿",
  "system design": "🏛️",
  "distributed systems": "🕸️",
  cybersecurity: "🛡️",
}

function getTechIcon(slug: string, name: string): string {
  const s = slug.toLowerCase()
  const n = name.toLowerCase()
  return TECH_ICONS[s] || TECH_ICONS[n] || "💻"
}

export default function QuestionPractice() {
  const navigate = useNavigate()
  const { techSlug, topicSlug } = useParams<{ techSlug?: string; topicSlug?: string }>()

  // View Level: "technologies" | "topics" | "questions"
  const viewLevel = useMemo(() => {
    if (techSlug && topicSlug) return "questions"
    if (techSlug) return "topics"
    return "technologies"
  }, [techSlug, topicSlug])

  // Tabs: 'bank' | 'progress' | 'history'
  const [activeTab, setActiveTab] = useState<"bank" | "progress" | "history">("bank")
  const [mobileMenu, setMobileMenu] = useState(false)
  const [practiceStats, setPracticeStats] = useState<PracticeStatsResponse | null>(null)

  // Level 1: Technologies State
  const [technologies, setTechnologies] = useState<TechnologySummary[]>([])
  const [techSearch, setTechSearch] = useState("")
  const [techsLoading, setTechsLoading] = useState(false)
  const [totalBankQuestions, setTotalBankQuestions] = useState(0)
  const [totalBankSolved, setTotalBankSolved] = useState(0)

  // Level 2: Topics State
  const [topics, setTopics] = useState<TopicSummary[]>([])
  const [topicSearch, setTopicSearch] = useState("")
  const [topicsLoading, setTopicsLoading] = useState(false)
  const [currentTechName, setCurrentTechName] = useState("")
  const [currentTechSolved, setCurrentTechSolved] = useState(0)
  const [currentTechTotal, setCurrentTechTotal] = useState(0)
  const [currentTechMastery, setCurrentTechMastery] = useState(0)

  // Level 3: Question Bank State
  const [questions, setQuestions] = useState<PracticeQuestionSummary[]>([])
  const [totalQuestions, setTotalQuestions] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(15)

  // Level 3 Filters State
  const [questionSearch, setQuestionSearch] = useState("")
  const [selectedDifficulty, setSelectedDifficulty] = useState("all")
  const [selectedStatus, setSelectedStatus] = useState("all")
  const [selectedType, setSelectedType] = useState("all")
  const [currentTopicName, setCurrentTopicName] = useState("")

  // Question Detail / Modal State
  const [activeQuestionId, setActiveQuestionId] = useState<string | null>(null)
  const [questionDetail, setQuestionDetail] = useState<PracticeQuestionDetailResponse | null>(null)
  const [userAnswer, setUserAnswer] = useState("")
  const [submittingAnswer, setSubmittingAnswer] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const [showExplanation, setShowExplanation] = useState(false)

  // Progress & History State
  const [progressData, setProgressData] = useState<PracticeProgressResponse | null>(null)
  const [historyItems, setHistoryItems] = useState<PracticeHistoryItem[]>([])
  const [progressLoading, setProgressLoading] = useState(false)
  const [historyLoading, setHistoryLoading] = useState(false)

  // General Loading & Toast
  const [questionsLoading, setQuestionsLoading] = useState(false)
  const [error, setError] = useState("")
  const [toastMessage, setToastMessage] = useState<string | null>(null)

  const showToast = useCallback((msg: string) => {
    setToastMessage(msg)
    window.setTimeout(() => setToastMessage(null), 3000)
  }, [])

  // ------------------------------------------------------------
  // LOAD STATS (Gamification Pipeline)
  // ------------------------------------------------------------
  const loadStats = useCallback(async () => {
    try {
      const stats = await getPracticeStats()
      setPracticeStats(stats)
    } catch (err) {
      console.error("Failed to load practice stats:", err)
    }
  }, [])

  useEffect(() => {
    void loadStats()
  }, [loadStats])

  // ------------------------------------------------------------
  // LEVEL 1: LOAD TECHNOLOGIES
  // ------------------------------------------------------------
  const loadTechnologies = useCallback(async () => {
    setTechsLoading(true)
    setError("")
    try {
      const res = await getPracticeTechnologies(techSearch.trim() || undefined)
      setTechnologies(res.technologies)
      setTotalBankQuestions(res.total_questions)
      setTotalBankSolved(res.total_solved)
    } catch (err) {
      console.error("Failed to load technologies:", err)
      setError("Unable to load technology catalog. Please retry.")
    } finally {
      setTechsLoading(false)
    }
  }, [techSearch])

  // ------------------------------------------------------------
  // LEVEL 2: LOAD TOPICS FOR SELECTED TECH
  // ------------------------------------------------------------
  const loadTopics = useCallback(async (slug: string) => {
    setTopicsLoading(true)
    setError("")
    try {
      const res = await getPracticeTechnologyTopics(slug)
      setTopics(res.topics)
      setCurrentTechName(res.technology)
      setCurrentTechSolved(res.total_solved)
      setCurrentTechTotal(res.total_questions)
      setCurrentTechMastery(res.total_questions > 0 ? Math.round((res.total_solved / res.total_questions) * 100) : 0)
    } catch (err) {
      console.error(`Failed to load topics for ${slug}:`, err)
      setError(`Unable to load topics for technology '${slug}'.`)
    } finally {
      setTopicsLoading(false)
    }
  }, [])

  // ------------------------------------------------------------
  // LEVEL 3: LOAD QUESTIONS FOR TECH + TOPIC
  // ------------------------------------------------------------
  const loadQuestions = useCallback(async (tSlug: string, topSlug: string) => {
    setQuestionsLoading(true)
    setError("")
    try {
      const res = await getPracticeQuestions({
        technology: tSlug,
        topic: topSlug,
        search: questionSearch.trim() || undefined,
        difficulty: selectedDifficulty !== "all" ? selectedDifficulty : undefined,
        question_type: selectedType !== "all" ? selectedType : undefined,
        status: selectedStatus !== "all" ? selectedStatus : undefined,
        page,
        page_size: pageSize,
      })
      setQuestions(res.questions)
      setTotalQuestions(res.total)
      if (res.questions.length > 0) {
        if (res.questions[0].technology) setCurrentTechName(res.questions[0].technology)
        if (res.questions[0].topic) setCurrentTopicName(res.questions[0].topic)
      }
    } catch (err) {
      console.error("Failed to load questions:", err)
      setError("Unable to load questions for this topic.")
    } finally {
      setQuestionsLoading(false)
    }
  }, [questionSearch, selectedDifficulty, selectedType, selectedStatus, page, pageSize])

  // Route-driven data loader
  useEffect(() => {
    if (activeTab !== "bank") return

    if (viewLevel === "technologies") {
      void loadTechnologies()
    } else if (viewLevel === "topics" && techSlug) {
      void loadTopics(techSlug)
    } else if (viewLevel === "questions" && techSlug && topicSlug) {
      void loadQuestions(techSlug, topicSlug)
    }
  }, [viewLevel, techSlug, topicSlug, activeTab, loadTechnologies, loadTopics, loadQuestions])

  // ------------------------------------------------------------
  // LOAD PROGRESS & HISTORY TABS
  // ------------------------------------------------------------
  const loadProgress = useCallback(async () => {
    setProgressLoading(true)
    try {
      const [res, stats] = await Promise.all([
        getPracticeProgress(),
        getPracticeStats().catch(() => null),
      ])
      setProgressData(res)
      if (stats) setPracticeStats(stats)
    } catch (err) {
      console.error("Failed to load practice progress:", err)
    } finally {
      setProgressLoading(false)
    }
  }, [])

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true)
    try {
      const res = await getPracticeHistory()
      setHistoryItems(res.history)
    } catch (err) {
      console.error("Failed to load practice history:", err)
    } finally {
      setHistoryLoading(false)
    }
  }, [])

  useEffect(() => {
    if (activeTab === "progress") {
      void loadProgress()
    } else if (activeTab === "history") {
      void loadHistory()
    }
  }, [activeTab, loadProgress, loadHistory])

  // ------------------------------------------------------------
  // OPEN QUESTION DETAIL
  // ------------------------------------------------------------
  const openQuestion = useCallback(async (qid: string) => {
    setActiveQuestionId(qid)
    setDetailLoading(true)
    setShowExplanation(false)
    try {
      const detail = await getPracticeQuestionDetail(qid)
      setQuestionDetail(detail)
      setUserAnswer(detail.last_answer || "")
      if (detail.solved && detail.explanation) {
        setShowExplanation(true)
      }
    } catch (err) {
      console.error("Failed to load question details:", err)
      showToast("Unable to load question details.")
      setActiveQuestionId(null)
    } finally {
      setDetailLoading(false)
    }
  }, [showToast])

  const closeDetail = useCallback(() => {
    setActiveQuestionId(null)
    setQuestionDetail(null)
    setUserAnswer("")
    setShowExplanation(false)
  }, [])

  // ------------------------------------------------------------
  // SUBMIT / SOLVE QUESTION
  // ------------------------------------------------------------
  async function handleSolveSubmit(markSolved: boolean = true) {
    if (!questionDetail) return

    setSubmittingAnswer(true)
    try {
      const res = await solvePracticeQuestion(questionDetail.id, userAnswer, markSolved)
      setQuestionDetail((prev) =>
        prev
          ? {
              ...prev,
              solved: res.solved,
              attempts: res.attempts,
              last_answer: userAnswer,
              last_attempted_at: new Date().toISOString(),
            }
          : null,
      )

      // Update question in local question list state
      setQuestions((prev) =>
        prev.map((q) =>
          q.id === questionDetail.id
            ? { ...q, solved: res.solved, attempts: res.attempts }
            : q,
        ),
      )

      if (questionDetail.explanation) {
        setShowExplanation(true)
      }

      if (res.xp_earned && res.xp_earned > 0) {
        showToast(
          `🎉 +${res.xp_earned} XP earned! ${
            res.leveled_up
              ? `🔥 Leveled up to Level ${res.current_level}: ${res.level_title}!`
              : ""
          }`,
        )
      } else {
        showToast(res.message)
      }
      void loadStats()
    } catch (err) {
      console.error("Failed to submit practice answer:", err)
      showToast("Failed to save practice answer.")
    } finally {
      setSubmittingAnswer(false)
    }
  }

  // ------------------------------------------------------------
  // BOOKMARK TOGGLE
  // ------------------------------------------------------------
  async function handleBookmarkToggle(
    qid: string,
    currentBookmarked: boolean,
    e?: React.MouseEvent,
  ) {
    if (e) e.stopPropagation()

    try {
      if (currentBookmarked) {
        await unbookmarkPracticeQuestion(qid)
        showToast("Bookmark removed")
      } else {
        await bookmarkPracticeQuestion(qid)
        showToast("Question bookmarked ✓")
      }

      // Update local question state
      setQuestions((prev) =>
        prev.map((q) => (q.id === qid ? { ...q, bookmarked: !currentBookmarked } : q)),
      )

      // Update detail if opened
      setQuestionDetail((prev) =>
        prev && prev.id === qid ? { ...prev, bookmarked: !currentBookmarked } : prev,
      )
    } catch (err) {
      console.error("Bookmark toggle failed:", err)
      showToast("Failed to update bookmark.")
    }
  }

  // Filter topics in Level 2 client-side
  const filteredTopics = useMemo(() => {
    if (!topicSearch.trim()) return topics
    const term = topicSearch.trim().toLowerCase()
    return topics.filter(
      (t) =>
        t.topic.toLowerCase().includes(term) ||
        t.slug.toLowerCase().includes(term),
    )
  }, [topics, topicSearch])

  // Filter technologies in Level 1 client-side
  const filteredTechs = useMemo(() => {
    if (!techSearch.trim()) return technologies
    const term = techSearch.trim().toLowerCase()
    return technologies.filter(
      (t) =>
        t.technology.toLowerCase().includes(term) ||
        t.slug.toLowerCase().includes(term),
    )
  }, [technologies, techSearch])

  const totalPages = Math.ceil(totalQuestions / pageSize) || 1

  return (
    <div className="qp-shell">
      {/* TOAST NOTIFICATION */}
      {toastMessage && (
        <div className="qp-toast">
          <span>{toastMessage}</span>
        </div>
      )}

      {/* ======================================================
          SIDEBAR NAVIGATION
      ====================================================== */}
      <aside className={`qp-sidebar ${mobileMenu ? "mobile-open" : ""}`}>
        <div className="qp-brand">
          <div className="brand-logo">
            <span>AI</span>
          </div>
          <div className="brand-name">
            <strong>AI Interview</strong>
            <span>Platform</span>
          </div>
          <button
            type="button"
            className="qp-collapse-btn"
            onClick={() => setMobileMenu(false)}
          >
            ‹
          </button>
        </div>

        <nav className="qp-nav">
          <button
            type="button"
            className="qp-nav-link"
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
            className="qp-nav-link"
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
            className="qp-nav-link"
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
            className="qp-nav-link"
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
            className="qp-nav-link active"
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
            className="qp-nav-link"
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
            className="qp-nav-link"
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
            className="qp-nav-link"
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
            className="qp-nav-link"
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
        <div className="qp-practice-card">
          <div className="practice-icon">🎯</div>
          <h3>Full Simulation</h3>
          <p>Ready for a real voice-based mock interview session?</p>
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
          MAIN PRACTICE INTERFACE
      ====================================================== */}
      <main className="qp-main">
        {/* TOP BAR */}
        <header className="qp-top-bar">
          <div className="qp-bar-left">
            <button
              type="button"
              className="qp-mobile-toggle"
              onClick={() => setMobileMenu(true)}
              aria-label="Open menu"
            >
              ☰
            </button>
            <button
              type="button"
              className="qp-back-btn"
              onClick={() => navigate("/dashboard")}
            >
              ← Back to Dashboard
            </button>
          </div>

          <div className="qp-bar-right">
            {practiceStats?.xp && (
              <div
                className="qp-xp-pill"
                title={`${practiceStats.xp.level_title} • ${practiceStats.xp.progress_pct}% to next level`}
              >
                <span>⚡ Lvl {practiceStats.xp.level}</span>
                <span className="qp-xp-val">{practiceStats.xp.total_xp} XP</span>
              </div>
            )}
            {practiceStats?.streak && (
              <div
                className="qp-streak-pill"
                title={
                  practiceStats.streak.is_active_today
                    ? "Practice active today"
                    : "Practice today to maintain streak"
                }
              >
                <span>
                  🔥 {practiceStats.streak.current_streak} Day
                  {practiceStats.streak.current_streak === 1 ? "" : "s"}
                </span>
              </div>
            )}
            <div className="qp-session-pill">
              <span className="pulse-dot" />
              <span>Practice Sync Active</span>
            </div>
          </div>
        </header>

        {/* HERO HEADER */}
        <section className="qp-hero">
          <div className="qp-hero-copy">
            <span className="qp-eyebrow">
              CANONICAL QUESTION BANK • {totalBankQuestions > 0 ? `${totalBankQuestions.toLocaleString()} PROBLEMS (${totalBankSolved} SOLVED)` : "5,000+ CURATED PROBLEMS"}
            </span>
            <h1>Question Practice</h1>
            <p>
              Drill down by technology and core topic, master architectural and algorithmic
              patterns, track topic-level mastery, and earn XP.
            </p>
          </div>

          {/* TABS */}
          <div className="qp-tabs">
            <button
              type="button"
              className={`qp-tab-btn ${activeTab === "bank" ? "active" : ""}`}
              onClick={() => setActiveTab("bank")}
            >
              📚 Question Bank
            </button>
            <button
              type="button"
              className={`qp-tab-btn ${activeTab === "progress" ? "active" : ""}`}
              onClick={() => setActiveTab("progress")}
            >
              📊 Practice Progress
            </button>
            <button
              type="button"
              className={`qp-tab-btn ${activeTab === "history" ? "active" : ""}`}
              onClick={() => setActiveTab("history")}
            >
              ⏱ Attempt History
            </button>
          </div>
        </section>

        {/* ERROR STATE */}
        {error && (
          <div className="qp-error-banner">
            <span>⚠️ {error}</span>
            <button
              type="button"
              onClick={() => {
                if (viewLevel === "technologies") void loadTechnologies()
                else if (viewLevel === "topics" && techSlug) void loadTopics(techSlug)
                else if (viewLevel === "questions" && techSlug && topicSlug)
                  void loadQuestions(techSlug, topicSlug)
              }}
            >
              Retry
            </button>
          </div>
        )}

        {/* ======================================================
            TAB 1: QUESTION BANK (3-TIER HIERARCHY)
        ====================================================== */}
        {activeTab === "bank" && (
          <section className="qp-bank-view">
            {/* ----------------------------------------------------
                LEVEL 1: /practice (TECHNOLOGY CARDS)
            ---------------------------------------------------- */}
            {viewLevel === "technologies" && (
              <div className="qp-level-container">
                {/* SEARCH & FILTERS BAR */}
                <div className="qp-filter-panel">
                  <div className="qp-search-wrap">
                    <span className="search-icon">🔍</span>
                    <input
                      type="text"
                      placeholder="Search technologies & subjects (e.g. Python, React, DSA, Docker, System Design)..."
                      value={techSearch}
                      onChange={(e) => setTechSearch(e.target.value)}
                      className="qp-search-input"
                    />
                    {techSearch && (
                      <button
                        type="button"
                        className="clear-search-btn"
                        onClick={() => setTechSearch("")}
                      >
                        ×
                      </button>
                    )}
                  </div>
                </div>

                {/* RESULTS COUNTER */}
                <div className="qp-results-meta">
                  <span>
                    Showing <strong>{filteredTechs.length}</strong> of{" "}
                    <strong>{technologies.length}</strong> technologies (
                    <strong>{totalBankQuestions}</strong> unique questions)
                  </span>
                </div>

                {/* TECHNOLOGIES GRID */}
                {techsLoading ? (
                  <div className="qp-questions-skeleton">
                    {[1, 2, 3, 4, 5, 6].map((i) => (
                      <div key={i} className="skeleton-question-card" />
                    ))}
                  </div>
                ) : filteredTechs.length > 0 ? (
                  <div className="qp-tech-grid">
                    {filteredTechs.map((tech) => {
                      const icon = getTechIcon(tech.slug, tech.technology)
                      return (
                        <article
                          key={tech.slug}
                          className="qp-tech-card"
                          onClick={() => navigate(`/practice/${tech.slug}`)}
                        >
                          <div className="qp-tech-card-header">
                            <div className="qp-tech-info">
                              <div className="qp-tech-icon">{icon}</div>
                              <div className="qp-tech-names">
                                <h3>{tech.technology}</h3>
                                <span className="qp-tech-topics-badge">
                                  {tech.topics_count} Topics
                                </span>
                              </div>
                            </div>
                            <div className="qp-tech-xp-badge">
                              <span>⚡ +{tech.xp_earned} XP</span>
                            </div>
                          </div>

                          {/* METRICS ROW */}
                          <div className="qp-tech-stats-grid">
                            <div className="qp-tech-stat-col">
                              <span className="mini-label">Total</span>
                              <span className="mini-val">{tech.total_questions}</span>
                            </div>
                            <div className="qp-tech-stat-col col-solved">
                              <span className="mini-label">Solved</span>
                              <span className="mini-val">{tech.solved}</span>
                            </div>
                            <div className="qp-tech-stat-col col-rem">
                              <span className="mini-label">Remaining</span>
                              <span className="mini-val">{tech.remaining}</span>
                            </div>
                            <div className="qp-tech-stat-col col-mastery">
                              <span className="mini-label">Mastery</span>
                              <span className="mini-val">{tech.mastery_percentage}%</span>
                            </div>
                          </div>

                          {/* PROGRESS BAR */}
                          <div className="qp-card-progress">
                            <div className="qp-card-progress-bar">
                              <div
                                className="qp-card-progress-fill"
                                style={{ width: `${Math.min(100, Math.max(tech.mastery_percentage, tech.solved > 0 ? 3 : 0))}%` }}
                              />
                            </div>
                          </div>

                          {/* FOOTER */}
                          <div className="qp-tech-card-footer">
                            <span className="qp-tech-card-action">
                              Explore Topics →
                            </span>
                          </div>
                        </article>
                      )
                    })}
                  </div>
                ) : (
                  <div className="qp-empty-state">
                    <div className="empty-icon">🔍</div>
                    <h3>No Technologies Found</h3>
                    <p>No technologies matched your search "{techSearch}".</p>
                    <button
                      type="button"
                      className="qp-primary-btn"
                      onClick={() => setTechSearch("")}
                    >
                      Clear Search
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* ----------------------------------------------------
                LEVEL 2: /practice/:techSlug (TOPICS FOR SELECTED TECH)
            ---------------------------------------------------- */}
            {viewLevel === "topics" && techSlug && (
              <div className="qp-level-container">
                {/* BREADCRUMB */}
                <div className="qp-breadcrumbs">
                  <button
                    type="button"
                    className="qp-breadcrumb-link"
                    onClick={() => navigate("/practice")}
                  >
                    Practice
                  </button>
                  <span className="qp-breadcrumb-sep">/</span>
                  <span className="qp-breadcrumb-current">
                    {currentTechName || techSlug}
                  </span>
                </div>

                {/* TECHNOLOGY CONTEXT BANNER */}
                <div className="qp-level-banner">
                  <div className="qp-banner-top">
                    <button
                      type="button"
                      className="qp-banner-back-btn"
                      onClick={() => navigate("/practice")}
                    >
                      ← All Technologies
                    </button>
                  </div>

                  <div className="qp-banner-header">
                    <div className="qp-banner-icon">
                      {getTechIcon(techSlug, currentTechName)}
                    </div>
                    <div className="qp-banner-title">
                      <h2>{currentTechName || techSlug}</h2>
                      <p>
                        Explore topic breakdown and targeted problem sets for{" "}
                        {currentTechName || techSlug}.
                      </p>
                    </div>
                  </div>

                  <div className="qp-banner-metrics">
                    <div className="qp-banner-stat-box highlight-cyan">
                      <span className="stat-label">Total Questions</span>
                      <span className="stat-val">{currentTechTotal}</span>
                    </div>
                    <div className="qp-banner-stat-box highlight-emerald">
                      <span className="stat-label">Solved</span>
                      <span className="stat-val">{currentTechSolved}</span>
                    </div>
                    <div className="qp-banner-stat-box highlight-amber">
                      <span className="stat-label">Remaining</span>
                      <span className="stat-val">
                        {Math.max(0, currentTechTotal - currentTechSolved)}
                      </span>
                    </div>
                    <div className="qp-banner-stat-box highlight-purple">
                      <span className="stat-label">Mastery</span>
                      <span className="stat-val">{currentTechMastery}%</span>
                    </div>
                  </div>
                </div>

                {/* SEARCH TOPICS */}
                <div className="qp-filter-panel">
                  <div className="qp-search-wrap">
                    <span className="search-icon">🔍</span>
                    <input
                      type="text"
                      placeholder={`Search ${currentTechName || techSlug} topics (e.g. OOP, AsyncIO, Functions)...`}
                      value={topicSearch}
                      onChange={(e) => setTopicSearch(e.target.value)}
                      className="qp-search-input"
                    />
                    {topicSearch && (
                      <button
                        type="button"
                        className="clear-search-btn"
                        onClick={() => setTopicSearch("")}
                      >
                        ×
                      </button>
                    )}
                  </div>
                </div>

                {/* TOPICS RESULTS COUNTER */}
                <div className="qp-results-meta">
                  <span>
                    Showing <strong>{filteredTopics.length}</strong> of{" "}
                    <strong>{topics.length}</strong> topics in {currentTechName || techSlug}
                  </span>
                </div>

                {/* TOPICS GRID */}
                {topicsLoading ? (
                  <div className="qp-questions-skeleton">
                    {[1, 2, 3, 4, 5, 6].map((i) => (
                      <div key={i} className="skeleton-question-card" />
                    ))}
                  </div>
                ) : filteredTopics.length > 0 ? (
                  <div className="qp-topics-grid">
                    {filteredTopics.map((top) => (
                      <article
                        key={top.slug}
                        className="qp-topic-card"
                        onClick={() => navigate(`/practice/${techSlug}/${top.slug}`)}
                      >
                        <div className="qp-topic-card-header">
                          <h3>{top.topic}</h3>
                          <span className="qp-topic-mastery-tag">
                            {top.mastery_percentage}% Mastery
                          </span>
                        </div>

                        {/* STATS ROW */}
                        <div className="qp-topic-stats-row">
                          <div className="qp-topic-stat-item">
                            <span className="label">Total</span>
                            <span className="val">{top.total_questions}</span>
                          </div>
                          <div className="qp-topic-stat-item solved-val">
                            <span className="label">Solved</span>
                            <span className="val">{top.solved}</span>
                          </div>
                          <div className="qp-topic-stat-item rem-val">
                            <span className="label">Remaining</span>
                            <span className="val">{top.remaining}</span>
                          </div>
                        </div>

                        {/* PROGRESS BAR */}
                        <div className="qp-card-progress">
                          <div className="qp-card-progress-bar">
                            <div
                              className="qp-card-progress-fill"
                              style={{ width: `${Math.min(100, Math.max(top.mastery_percentage, top.solved > 0 ? 3 : 0))}%` }}
                            />
                          </div>
                        </div>

                        {/* FOOTER */}
                        <div className="qp-topic-card-footer">
                          <span className="qp-topic-card-action">
                            Practice Questions →
                          </span>
                        </div>
                      </article>
                    ))}
                  </div>
                ) : (
                  <div className="qp-empty-state">
                    <div className="empty-icon">🔍</div>
                    <h3>No Topics Found</h3>
                    <p>No topics matched your search "{topicSearch}".</p>
                    <button
                      type="button"
                      className="qp-primary-btn"
                      onClick={() => setTopicSearch("")}
                    >
                      Clear Search
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* ----------------------------------------------------
                LEVEL 3: /practice/:techSlug/:topicSlug (PAGINATED QUESTIONS)
            ---------------------------------------------------- */}
            {viewLevel === "questions" && techSlug && topicSlug && (
              <div className="qp-level-container">
                {/* BREADCRUMB */}
                <div className="qp-breadcrumbs">
                  <button
                    type="button"
                    className="qp-breadcrumb-link"
                    onClick={() => navigate("/practice")}
                  >
                    Practice
                  </button>
                  <span className="qp-breadcrumb-sep">/</span>
                  <button
                    type="button"
                    className="qp-breadcrumb-link"
                    onClick={() => navigate(`/practice/${techSlug}`)}
                  >
                    {currentTechName || techSlug}
                  </button>
                  <span className="qp-breadcrumb-sep">/</span>
                  <span className="qp-breadcrumb-current">
                    {currentTopicName || topicSlug}
                  </span>
                </div>

                {/* BANNER */}
                <div className="qp-level-banner">
                  <div className="qp-banner-top">
                    <button
                      type="button"
                      className="qp-banner-back-btn"
                      onClick={() => navigate(`/practice/${techSlug}`)}
                    >
                      ← Back to {currentTechName || techSlug} Topics
                    </button>
                  </div>

                  <div className="qp-banner-header">
                    <div className="qp-banner-icon">
                      {getTechIcon(techSlug, currentTechName)}
                    </div>
                    <div className="qp-banner-title">
                      <h2>{currentTopicName || topicSlug}</h2>
                      <p>
                        Targeted questions in {currentTechName || techSlug} &bull;{" "}
                        {currentTopicName || topicSlug}. Server-side paginated practice.
                      </p>
                    </div>
                  </div>
                </div>

                {/* FILTERS & SEARCH */}
                <div className="qp-filter-panel">
                  <div className="qp-search-wrap">
                    <span className="search-icon">🔍</span>
                    <input
                      type="text"
                      placeholder={`Search questions in ${currentTopicName || topicSlug}...`}
                      value={questionSearch}
                      onChange={(e) => {
                        setQuestionSearch(e.target.value)
                        setPage(1)
                      }}
                      className="qp-search-input"
                    />
                    {questionSearch && (
                      <button
                        type="button"
                        className="clear-search-btn"
                        onClick={() => {
                          setQuestionSearch("")
                          setPage(1)
                        }}
                      >
                        ×
                      </button>
                    )}
                  </div>

                  <div className="qp-filters-row">
                    {/* DIFFICULTY FILTER */}
                    <div className="filter-select-group">
                      <label htmlFor="diff-filter">Difficulty:</label>
                      <select
                        id="diff-filter"
                        value={selectedDifficulty}
                        onChange={(e) => {
                          setSelectedDifficulty(e.target.value)
                          setPage(1)
                        }}
                      >
                        <option value="all">All Difficulties</option>
                        <option value="Easy">Easy</option>
                        <option value="Medium">Medium</option>
                        <option value="Hard">Hard</option>
                      </select>
                    </div>

                    {/* QUESTION TYPE FILTER */}
                    <div className="filter-select-group">
                      <label htmlFor="type-filter">Type:</label>
                      <select
                        id="type-filter"
                        value={selectedType}
                        onChange={(e) => {
                          setSelectedType(e.target.value)
                          setPage(1)
                        }}
                      >
                        <option value="all">All Types</option>
                        <option value="Coding">Coding</option>
                        <option value="Concept">Concept</option>
                        <option value="Architecture">Architecture</option>
                        <option value="Scenario">Scenario</option>
                      </select>
                    </div>

                    {/* STATUS FILTER */}
                    <div className="filter-select-group">
                      <label htmlFor="status-filter">Status:</label>
                      <select
                        id="status-filter"
                        value={selectedStatus}
                        onChange={(e) => {
                          setSelectedStatus(e.target.value)
                          setPage(1)
                        }}
                      >
                        <option value="all">All Statuses</option>
                        <option value="unsolved">Unsolved</option>
                        <option value="solved">Solved ✓</option>
                        <option value="bookmarked">Bookmarked ★</option>
                      </select>
                    </div>

                    {(questionSearch ||
                      selectedDifficulty !== "all" ||
                      selectedType !== "all" ||
                      selectedStatus !== "all") && (
                      <button
                        type="button"
                        className="qp-reset-filters-btn"
                        onClick={() => {
                          setQuestionSearch("")
                          setSelectedDifficulty("all")
                          setSelectedType("all")
                          setSelectedStatus("all")
                          setPage(1)
                        }}
                      >
                        Reset Filters
                      </button>
                    )}
                  </div>
                </div>

                {/* RESULTS COUNTER */}
                <div className="qp-results-meta">
                  <span>
                    Showing <strong>{questions.length}</strong> of{" "}
                    <strong>{totalQuestions}</strong> questions in this topic
                  </span>
                </div>

                {/* QUESTIONS LIST */}
                {questionsLoading ? (
                  <div className="qp-questions-skeleton">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <div key={i} className="skeleton-question-card" />
                    ))}
                  </div>
                ) : questions.length > 0 ? (
                  <div className="qp-questions-grid">
                    {questions.map((q) => {
                      const diffLower = q.difficulty.toLowerCase()
                      const diffClass =
                        diffLower === "easy"
                          ? "diff-pill-easy"
                          : diffLower === "hard"
                          ? "diff-pill-hard"
                          : "diff-pill-med"

                      const xpVal =
                        q.xp_reward ||
                        (diffLower === "hard" ? 35 : diffLower === "easy" ? 10 : 20)

                      return (
                        <article
                          key={q.id}
                          className={`qp-question-card ${q.solved ? "card-solved" : ""}`}
                          onClick={() => void openQuestion(q.id)}
                        >
                          <div className="q-card-header">
                            <div className="q-card-tags">
                              <span className="q-topic-tag">{q.topic}</span>
                              {q.subtopic && q.subtopic !== "General" && (
                                <span className="q-subtopic-tag">{q.subtopic}</span>
                              )}
                              <span className={`q-diff-tag ${diffClass}`}>
                                {q.difficulty}
                              </span>
                              <span className="q-type-badge">{q.question_type}</span>
                              <span className="q-xp-reward-pill">+{xpVal} XP</span>
                            </div>

                            <button
                              type="button"
                              className={`q-bookmark-btn ${q.bookmarked ? "bookmarked" : ""}`}
                              onClick={(e) => void handleBookmarkToggle(q.id, q.bookmarked, e)}
                              title={q.bookmarked ? "Remove bookmark" : "Bookmark question"}
                            >
                              {q.bookmarked ? "★" : "☆"}
                            </button>
                          </div>

                          <h3 className="q-card-title">{q.question}</h3>

                          <div className="q-card-footer">
                            <div className="q-card-status">
                              {q.solved ? (
                                <span className="status-solved-badge">
                                  ✓ Solved {q.attempts > 1 ? `(${q.attempts} attempts)` : ""}
                                </span>
                              ) : (
                                <span className="status-unsolved-badge">
                                  {q.attempts > 0 ? `${q.attempts} attempts` : "Unsolved"}
                                </span>
                              )}
                            </div>

                            <span className="q-open-btn">
                              {q.solved ? "Review Solution →" : "Practice Question →"}
                            </span>
                          </div>
                        </article>
                      )
                    })}
                  </div>
                ) : (
                  <div className="qp-empty-state">
                    <div className="empty-icon">🔍</div>
                    <h3>No Questions Found</h3>
                    <p>No questions matched your current filter criteria.</p>
                    <button
                      type="button"
                      className="qp-primary-btn"
                      onClick={() => {
                        setQuestionSearch("")
                        setSelectedDifficulty("all")
                        setSelectedType("all")
                        setSelectedStatus("all")
                        setPage(1)
                      }}
                    >
                      Clear Filters
                    </button>
                  </div>
                )}

                {/* PAGINATION */}
                {totalPages > 1 && (
                  <div className="qp-pagination">
                    <button
                      type="button"
                      disabled={page <= 1}
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      className="page-nav-btn"
                    >
                      ← Previous
                    </button>
                    <span className="page-indicator">
                      Page <strong>{page}</strong> of <strong>{totalPages}</strong>
                    </span>
                    <button
                      type="button"
                      disabled={page >= totalPages}
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      className="page-nav-btn"
                    >
                      Next →
                    </button>
                  </div>
                )}
              </div>
            )}
          </section>
        )}

        {/* ======================================================
            TAB 2: PRACTICE PROGRESS (Gamification Engine)
        ====================================================== */}
        {activeTab === "progress" && (
          <section className="qp-progress-view">
            {progressLoading || !progressData ? (
              <div className="qp-progress-skeleton">
                <div className="skeleton-kpis" />
                <div className="skeleton-card" />
              </div>
            ) : (
              <>
                {/* XP & DAILY MISSIONS OVERVIEW */}
                {practiceStats && (
                  <div className="qp-stats-banner">
                    {/* XP & LEVEL PROGRESSION */}
                    <div className="qp-xp-banner-card">
                      <div className="qp-xp-banner-header">
                        <div>
                          <span className="qp-badge-pill">EXPERIENCE &amp; RANK</span>
                          <h3>
                            Level {practiceStats.xp.level}: {practiceStats.xp.level_title}
                          </h3>
                        </div>
                        <div className="qp-xp-metric">
                          <strong>{practiceStats.xp.total_xp}</strong>
                          <span>TOTAL XP</span>
                        </div>
                      </div>

                      <div className="qp-xp-track-lg">
                        <div
                          className="qp-xp-fill-lg"
                          style={{ width: `${practiceStats.xp.progress_pct}%` }}
                        />
                      </div>
                      <div className="qp-xp-footer">
                        <span>
                          {practiceStats.xp.current_level_xp} /{" "}
                          {practiceStats.xp.next_level_xp} XP to next rank
                        </span>
                        <span>{practiceStats.xp.progress_pct}% Completed</span>
                      </div>
                    </div>

                    {/* DAILY MISSIONS GRID */}
                    <div className="qp-missions-box">
                      <div className="qp-missions-header">
                        <span className="qp-badge-pill">DAILY QUESTS</span>
                        <h4>Today's Missions</h4>
                      </div>

                      <div className="qp-missions-items">
                        {practiceStats.missions.map((m) => (
                          <div
                            key={m.id}
                            className={`qp-mission-chip ${
                              m.completed ? "mission-chip-done" : ""
                            }`}
                          >
                            <div className="chip-left">
                              <span className="chip-icon">{m.icon}</span>
                              <div className="chip-text">
                                <strong>{m.title}</strong>
                                <small>{m.description}</small>
                              </div>
                            </div>
                            <div className="chip-right">
                              <span className="chip-xp">+{m.xp_reward} XP</span>
                              <span className="chip-progress">
                                {m.progress}/{m.target}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* KPI PROGRESS CARDS */}
                <div className="qp-kpi-row">
                  <div className="qp-kpi-card cyan-card">
                    <span className="kpi-label">Total Questions</span>
                    <strong className="kpi-value">{progressData.total_questions}</strong>
                    <small>Available in platform bank</small>
                  </div>
                  <div className="qp-kpi-card emerald-card">
                    <span className="kpi-label">Questions Solved</span>
                    <strong className="kpi-value">{progressData.solved_count}</strong>
                    <small>{progressData.completion_percentage}% solved</small>
                  </div>
                  <div className="qp-kpi-card orange-card">
                    <span className="kpi-label">Remaining Unsolved</span>
                    <strong className="kpi-value">{progressData.unsolved_count}</strong>
                    <small>Questions to practice</small>
                  </div>
                  <div className="qp-kpi-card gold-card">
                    <span className="kpi-label">Bookmarked</span>
                    <strong className="kpi-value">
                      {progressData.bookmarked_count}
                    </strong>
                    <small>Saved for review</small>
                  </div>
                </div>

                <div className="qp-two-column">
                  {/* DIFFICULTY BREAKDOWN */}
                  <div className="qp-panel">
                    <div className="panel-header">
                      <div>
                        <span className="panel-tag">DIFFICULTY TIERS</span>
                        <h2>Difficulty Mastery</h2>
                        <p>Completion percentage across problem difficulties</p>
                      </div>
                    </div>

                    <div className="diff-progress-list">
                      {progressData.difficulty_progress.map((dp) => (
                        <div key={dp.difficulty} className="diff-progress-row">
                          <div className="diff-meta">
                            <span className="diff-name">{dp.difficulty}</span>
                            <span className="diff-nums">
                              <strong>{dp.solved}</strong> / {dp.total} solved (
                              {dp.percentage}%)
                            </span>
                          </div>
                          <div className="progress-track">
                            <div
                              className={`progress-fill ${
                                dp.difficulty.toLowerCase() === "easy"
                                  ? "fill-easy"
                                  : dp.difficulty.toLowerCase() === "hard"
                                  ? "fill-hard"
                                  : "fill-medium"
                              }`}
                              style={{ width: `${dp.percentage}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* TOPIC MASTERY BREAKDOWN */}
                  <div className="qp-panel">
                    <div className="panel-header">
                      <div>
                        <span className="panel-tag">TOPIC COMPLETION</span>
                        <h2>Topic Mastery</h2>
                        <p>Progress across technical competencies</p>
                      </div>
                    </div>

                    <div className="topic-progress-list">
                      {progressData.topic_progress.slice(0, 15).map((tp) => (
                        <div key={tp.topic} className="topic-progress-row">
                          <div className="topic-meta">
                            <span className="topic-title">{tp.topic}</span>
                            <span className="topic-stats">
                              {tp.solved}/{tp.total} ({tp.percentage}%)
                            </span>
                          </div>
                          <div className="progress-track">
                            <div
                              className="progress-fill fill-purple"
                              style={{ width: `${tp.percentage}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </>
            )}
          </section>
        )}

        {/* ======================================================
            TAB 3: PRACTICE HISTORY
        ====================================================== */}
        {activeTab === "history" && (
          <section className="qp-history-view">
            {historyLoading ? (
              <div className="qp-questions-skeleton">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="skeleton-question-card" />
                ))}
              </div>
            ) : historyItems.length > 0 ? (
              <div className="history-cards-list">
                {historyItems.map((item) => (
                  <div key={item.question_id} className="history-item-card">
                    <div className="history-meta-bar">
                      <span className="history-topic">{item.topic}</span>
                      <span className="history-diff">{item.difficulty}</span>
                      <span className="history-attempts">
                        {item.attempts} attempt{item.attempts === 1 ? "" : "s"}
                      </span>
                      {item.last_attempted_at && (
                        <span className="history-date">
                          {new Date(item.last_attempted_at).toLocaleDateString(
                            "en-US",
                            {
                              month: "short",
                              day: "numeric",
                              year: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            },
                          )}
                        </span>
                      )}
                    </div>

                    <h3 className="history-title">{item.question}</h3>

                    {item.last_answer && (
                      <div className="history-answer-snippet">
                        <strong>Your Saved Solution:</strong>
                        <p>{item.last_answer}</p>
                      </div>
                    )}

                    <div className="history-actions">
                      <span
                        className={
                          item.solved
                            ? "status-solved-badge"
                            : "status-unsolved-badge"
                        }
                      >
                        {item.solved ? "✓ Solved" : "Attempted (Unsolved)"}
                      </span>

                      <button
                        type="button"
                        className="qp-primary-btn"
                        style={{ padding: "6px 14px", fontSize: 12 }}
                        onClick={() => void openQuestion(item.question_id)}
                      >
                        Re-attempt / Review →
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="qp-empty-state">
                <div className="empty-icon">📝</div>
                <h3>No Practice Attempts Recorded</h3>
                <p>
                  Attempt questions in the Question Bank to build your practice history.
                </p>
                <button
                  type="button"
                  className="qp-primary-btn"
                  onClick={() => {
                    setActiveTab("bank")
                    navigate("/practice")
                  }}
                >
                  Explore Question Bank →
                </button>
              </div>
            )}
          </section>
        )}

        {/* ======================================================
            QUESTION DETAIL MODAL / WORKSPACE
        ====================================================== */}
        {activeQuestionId && (
          <div className="qp-modal-overlay" onClick={closeDetail}>
            <div className="qp-modal-content" onClick={(e) => e.stopPropagation()}>
              {detailLoading || !questionDetail ? (
                <div className="modal-loading-box">
                  <div className="qp-spinner" />
                  <p>Loading question workspace...</p>
                </div>
              ) : (
                <>
                  {/* MODAL HEADER */}
                  <div className="modal-top-bar">
                    <div className="modal-tags">
                      <span className="q-topic-tag">{questionDetail.topic}</span>
                      {questionDetail.subtopic && questionDetail.subtopic !== "General" && (
                        <span className="q-subtopic-tag">
                          {questionDetail.subtopic}
                        </span>
                      )}
                      <span className="q-diff-tag diff-pill-med">
                        {questionDetail.difficulty}
                      </span>
                      <span className="q-type-tag">
                        {questionDetail.question_type}
                      </span>
                      <span className="q-xp-reward-pill">
                        +
                        {questionDetail.xp_reward ||
                          (questionDetail.difficulty.toLowerCase() === "hard"
                            ? 35
                            : questionDetail.difficulty.toLowerCase() === "easy"
                            ? 10
                            : 20)}{" "}
                        XP
                      </span>
                      {questionDetail.solved && (
                        <span className="status-solved-badge">✓ Solved</span>
                      )}
                    </div>

                    <div className="modal-controls">
                      <button
                        type="button"
                        className={`modal-bookmark-btn ${
                          questionDetail.bookmarked ? "bookmarked" : ""
                        }`}
                        onClick={() =>
                          void handleBookmarkToggle(
                            questionDetail.id,
                            questionDetail.bookmarked,
                          )
                        }
                        title={
                          questionDetail.bookmarked
                            ? "Remove bookmark"
                            : "Bookmark question"
                        }
                      >
                        {questionDetail.bookmarked ? "★ Bookmarked" : "☆ Bookmark"}
                      </button>

                      <button
                        type="button"
                        className="modal-close-btn"
                        onClick={closeDetail}
                        aria-label="Close"
                      >
                        ✕
                      </button>
                    </div>
                  </div>

                  {/* PREV / NEXT NAVIGATION */}
                  <div className="modal-nav-bar">
                    <button
                      type="button"
                      disabled={!questionDetail.previous_id}
                      onClick={() =>
                        questionDetail.previous_id &&
                        void openQuestion(questionDetail.previous_id)
                      }
                      className="modal-nav-arrow"
                    >
                      ← Previous Question
                    </button>
                    <button
                      type="button"
                      disabled={!questionDetail.next_id}
                      onClick={() =>
                        questionDetail.next_id &&
                        void openQuestion(questionDetail.next_id)
                      }
                      className="modal-nav-arrow"
                    >
                      Next Question →
                    </button>
                  </div>

                  {/* QUESTION TEXT PROMPT */}
                  <div className="modal-question-prompt">
                    <h2>{questionDetail.question}</h2>
                    {questionDetail.technology && (
                      <span className="modal-role-hint">
                        Technology: {questionDetail.technology} &bull;{" "}
                        {questionDetail.topic}
                      </span>
                    )}
                  </div>

                  {/* ANSWER WORKSPACE */}
                  <div className="modal-answer-area">
                    <div className="answer-header">
                      <label htmlFor="user-answer-input">
                        YOUR SOLUTION &amp; NOTES:
                      </label>
                      <span className="char-count">
                        {userAnswer.length} characters
                      </span>
                    </div>

                    <textarea
                      id="user-answer-input"
                      value={userAnswer}
                      onChange={(e) => setUserAnswer(e.target.value)}
                      placeholder="Formulate your technical answer, system design trade-offs, code snippet, or approach here..."
                      rows={8}
                    />

                    <div className="answer-actions">
                      <div className="action-left">
                        <button
                          type="button"
                          className="toggle-solved-btn"
                          onClick={() =>
                            void handleSolveSubmit(!questionDetail.solved)
                          }
                          disabled={submittingAnswer}
                        >
                          {questionDetail.solved
                            ? "Mark as Unsolved"
                            : "Mark as Solved ✓"}
                        </button>

                        {questionDetail.explanation && (
                          <button
                            type="button"
                            className="toggle-explanation-btn"
                            onClick={() => setShowExplanation((prev) => !prev)}
                          >
                            {showExplanation
                              ? "Hide Solution Details"
                              : "View Solution Details 💡"}
                          </button>
                        )}
                      </div>

                      <button
                        type="button"
                        className="submit-solution-btn"
                        onClick={() => void handleSolveSubmit(true)}
                        disabled={submittingAnswer || !userAnswer.trim()}
                      >
                        {submittingAnswer
                          ? "Saving..."
                          : "Save Answer & Mark Solved ✓"}
                      </button>
                    </div>
                  </div>

                  {/* SOLUTION / EXPLANATION PANEL */}
                  {showExplanation && questionDetail.explanation && (
                    <div className="modal-explanation-panel">
                      <div className="explanation-head">
                        <span className="lightbulb-icon">💡</span>
                        <strong>
                          Recommended Solution &amp; Technical Explanation:
                        </strong>
                      </div>
                      <p>{questionDetail.explanation}</p>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
