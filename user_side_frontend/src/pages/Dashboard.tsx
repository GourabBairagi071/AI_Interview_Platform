import type { KeyboardEvent as ReactKeyboardEvent } from "react"
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react"
import { useNavigate } from "react-router-dom"
import {
  getNotifications,
  getPracticeStats,
  getUserCodingStats,
  getUnreadNotificationCount,
  markAllNotificationsAsRead,
  markNotificationAsRead,
  getWeakTopics,
  getDailyPracticePlan,
  toggleDailyPracticeTask,
  type NotificationItem,
  type PracticeStatsResponse,
  type UserCodingStats,
  type WeakTopicItem,
  type DailyPracticePlan,
} from "../services/api"
import { realtimeService } from "../services/websocket"
import { useWebSocketEvent } from "../hooks/useWebSocket"
import RealtimeStatusBadge from "../components/RealtimeStatusBadge"

import "./Dashboard.css"

type User = {
  id: string
  full_name: string
  email: string
  is_verified?: boolean
}

type Interview = {
  id: string
  user_id?: string
  job_role?: string
  difficulty?: string
  status?: string
  score?: number | null
  questions?: string | null
  answers?: string | null
  transcript?: string | null
  feedback?: string | null
  strengths?: string | null
  weaknesses?: string | null
  question_evaluations?: string | null
  started_at?: string | null
  completed_at?: string | null
  created_at?: string
  updated_at?: string
}

const API_BASE_URL = "http://127.0.0.1:8000/api/v1"

const EMPTY_USER: User = {
  id: "",
  full_name: "Candidate",
  email: "",
  is_verified: false,
}

function Dashboard() {
  const navigate = useNavigate()

  const [user, setUser] = useState<User | null>(null)
  const [interviews, setInterviews] = useState<Interview[]>([])
  const [practiceStats, setPracticeStats] = useState<PracticeStatsResponse | null>(null)
  const [codingStats, setCodingStats] = useState<UserCodingStats | null>(null)
  const [weakTopics, setWeakTopics] = useState<WeakTopicItem[]>([])
  const [dailyPlan, setDailyPlan] = useState<DailyPracticePlan | null>(null)
  const [togglingTask, setTogglingTask] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [mobileMenu, setMobileMenu] = useState(false)
  const [profileMenu, setProfileMenu] = useState(false)
  const [notificationMenu, setNotificationMenu] = useState(false)
  const [dashboardNotifications, setDashboardNotifications] = useState<NotificationItem[]>([])
  const [dashboardUnreadCount, setDashboardUnreadCount] = useState<number>(0)
  const [realtimeToast, setRealtimeToast] = useState<{ title: string; message: string; icon?: string } | null>(null)
  const [search, setSearch] = useState("")
  const [activePeriod, setActivePeriod] = useState<"5" | "10" | "all">("10")
  const [showAllSessions, setShowAllSessions] = useState(false)

  const profileRef = useRef<HTMLDivElement | null>(null)
  const notificationRef = useRef<HTMLDivElement | null>(null)

  /* ============================================================
     AUTH HELPERS (UNTOUCHED)
  ============================================================ */

  const getToken = useCallback(() => {
    return localStorage.getItem("access_token")
  }, [])

  const logout = useCallback(() => {
    realtimeService.disconnect()
    localStorage.removeItem("access_token")
    setUser(null)
    setInterviews([])
    navigate("/login", { replace: true })
  }, [navigate])

  const handleUnauthorized = useCallback(() => {
    localStorage.removeItem("access_token")
    navigate("/login", { replace: true })
  }, [navigate])

  /* ============================================================
     API REQUEST (REUSING EXISTING TOKEN & ENDPOINTS)
  ============================================================ */

  const apiRequest = useCallback(
    async (url: string, options: RequestInit = {}) => {
      const token = getToken()

      if (!token) {
        handleUnauthorized()
        throw new Error("Authentication required")
      }

      const response = await fetch(`${API_BASE_URL}${url}`, {
        ...options,
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          ...(options.headers || {}),
          Authorization: `Bearer ${token}`,
        },
      })

      if (response.status === 401) {
        handleUnauthorized()
        throw new Error("Session expired")
      }

      return response
    },
    [getToken, handleUnauthorized],
  )

  /* ============================================================
     LOAD DASHBOARD
  ============================================================ */

  const loadDashboard = useCallback(async () => {
    const token = getToken()

    if (!token) {
      handleUnauthorized()
      return
    }

    setLoading(true)
    setError("")

    try {
      const [userResponse, interviewResponse, statsData, notifList, unreadData, codingStatsData, weakTopicsData, dailyPlanData] = await Promise.all([
        apiRequest("/auth/me"),
        apiRequest("/interview"),
        getPracticeStats().catch(() => null),
        getNotifications({ limit: 5 }).catch(() => null),
        getUnreadNotificationCount().catch(() => ({ unread_count: 0 })),
        getUserCodingStats().catch(() => null),
        getWeakTopics().catch(() => []),
        getDailyPracticePlan().catch(() => null),
      ])

      if (statsData) {
        setPracticeStats(statsData)
      }

      if (codingStatsData) {
        setCodingStats(codingStatsData)
      }

      if (Array.isArray(weakTopicsData)) {
        setWeakTopics(weakTopicsData)
      }

      if (dailyPlanData) {
        setDailyPlan(dailyPlanData)
      }

      if (notifList) {
        setDashboardNotifications(notifList.notifications)
      }

      if (unreadData) {
        setDashboardUnreadCount(unreadData.unread_count)
      }

      if (!userResponse.ok) {
        throw new Error("Unable to load user profile")
      }

      if (!interviewResponse.ok) {
        throw new Error("Unable to load interview sessions")
      }

      const userData = await userResponse.json()
      const interviewData = await interviewResponse.json()

      setUser({
        ...EMPTY_USER,
        ...userData,
      })

      const list: Interview[] = Array.isArray(interviewData)
        ? interviewData
        : Array.isArray(interviewData?.interviews)
        ? interviewData.interviews
        : Array.isArray(interviewData?.data)
        ? interviewData.data
        : []

      setInterviews(list)
    } catch (err: unknown) {
      console.error("Dashboard loading error:", err)
      if (!(err instanceof Error) || err.message !== "Session expired") {
        setError("Unable to load dashboard data. Please try again.")
      }
    } finally {
      setLoading(false)
    }
  }, [apiRequest, getToken, handleUnauthorized])

  useEffect(() => {
    loadDashboard()
  }, [loadDashboard])

  // Establish WebSocket connection on dashboard mount
  useEffect(() => {
    realtimeService.connect()
  }, [])

  // Real-time notification arrival
  useWebSocketEvent("notification.created", (data: NotificationItem) => {
    if (!data || !data.id) return
    setDashboardNotifications((prev) => {
      if (prev.some((n) => n.id === data.id)) return prev
      return [data, ...prev].slice(0, 8)
    })
    setDashboardUnreadCount((prev) => prev + 1)
    setRealtimeToast({
      title: data.title || "New Notification",
      message: data.message || "",
      icon: data.icon || "🔔",
    })
    setTimeout(() => {
      setRealtimeToast((curr) => (curr?.title === data.title ? null : curr))
    }, 4500)
  })

  // Real-time notification read status
  useWebSocketEvent("notification.read", (data: { id?: string; all?: boolean; unread_count?: number }) => {
    if (data?.all) {
      setDashboardUnreadCount(0)
      setDashboardNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })))
    } else if (data?.id) {
      setDashboardNotifications((prev) =>
        prev.map((n) => (n.id === data.id ? { ...n, is_read: true } : n))
      )
      if (typeof data.unread_count === "number") {
        setDashboardUnreadCount(data.unread_count)
      } else {
        setDashboardUnreadCount((prev) => Math.max(0, prev - 1))
      }
    }
  })

  // Real-time learning plan updates
  useWebSocketEvent("learning.plan.updated", () => {
    getDailyPracticePlan().then((p) => p && setDailyPlan(p)).catch(() => null)
    getWeakTopics().then((w) => Array.isArray(w) && setWeakTopics(w)).catch(() => null)
  })

  /* ============================================================
     CLICK OUTSIDE MENUS
  ============================================================ */

  useEffect(() => {
    function handleOutsideClick(event: globalThis.MouseEvent) {
      const target = event.target

      if (
        target instanceof Node &&
        profileRef.current &&
        !profileRef.current.contains(target)
      ) {
        setProfileMenu(false)
      }

      if (
        target instanceof Node &&
        notificationRef.current &&
        !notificationRef.current.contains(target)
      ) {
        setNotificationMenu(false)
      }
    }

    document.addEventListener("mousedown", handleOutsideClick)
    return () => {
      document.removeEventListener("mousedown", handleOutsideClick)
    }
  }, [])

  /* ============================================================
     DERIVED DATA (100% REAL POSTGRESQL DATA)
  ============================================================ */

  const completedInterviews = useMemo(() => {
    return interviews.filter(
      (item) => String(item?.status || "").toLowerCase() === "completed",
    )
  }, [interviews])


  const activeInterview = useMemo(() => {
    return (
      interviews.find((i) => i.status === "started") ||
      interviews.find((i) => i.status === "created") ||
      null
    )
  }, [interviews])

  const scores = useMemo(() => {
    return completedInterviews
      .map((item) => Number(item?.score))
      .filter((score) => Number.isFinite(score))
  }, [completedInterviews])

  const averageScore = useMemo(() => {
    if (!scores.length) return 0
    return scores.reduce((total, score) => total + score, 0) / scores.length
  }, [scores])

  const bestScore = useMemo(() => {
    if (!scores.length) return 0
    return Math.max(...scores)
  }, [scores])

  // Count total questions attempted across all interviews
  const totalQuestionsAttempted = useMemo(() => {
    return interviews.reduce((sum, item) => {
      try {
        if (item.questions) {
          const parsed = JSON.parse(item.questions)
          if (Array.isArray(parsed)) return sum + parsed.length
        }
      } catch {}
      return sum
    }, 0)
  }, [interviews])

  // Real consecutive days streak
  const streakDays = useMemo(() => {
    if (!interviews.length) return 0
    const dates = new Set(
      interviews
        .filter((item) => item?.created_at)
        .map((item) => new Date(item.created_at!).toISOString().split("T")[0]),
    )
    const today = new Date()
    let count = 0
    const checkDate = new Date(today)

    const todayStr = checkDate.toISOString().split("T")[0]
    if (!dates.has(todayStr)) {
      checkDate.setDate(checkDate.getDate() - 1)
      const yesterdayStr = checkDate.toISOString().split("T")[0]
      if (!dates.has(yesterdayStr)) {
        return 0
      }
    }

    while (true) {
      const dateStr = checkDate.toISOString().split("T")[0]
      if (dates.has(dateStr)) {
        count++
        checkDate.setDate(checkDate.getDate() - 1)
      } else {
        break
      }
    }
    return count
  }, [interviews])

  // Combined streak between mock interviews and question practice
  const effectiveStreak = useMemo(() => {
    return Math.max(streakDays, practiceStats?.streak?.current_streak || 0)
  }, [streakDays, practiceStats?.streak?.current_streak])

  /* ============================================================
     FILTERED & SORTED RECENT INTERVIEWS
  ============================================================ */

  const filteredInterviews = useMemo(() => {
    const query = search.trim().toLowerCase()
    if (!query) return interviews

    return interviews.filter((item) => {
      return [item?.job_role, item?.difficulty, item?.status]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(query))
    })
  }, [interviews, search])

  const recentInterviews = useMemo(() => {
    return [...filteredInterviews]
      .sort(
        (a, b) =>
          new Date(b?.created_at || 0).getTime() -
          new Date(a?.created_at || 0).getTime(),
      )
      .slice(0, showAllSessions ? 20 : 6)
  }, [filteredInterviews, showAllSessions])

  /* ============================================================
     PERFORMANCE OVERVIEW GRAPH
  ============================================================ */

  const performanceInterviews = useMemo(() => {
    const sorted = [...completedInterviews]
      .filter((item) => Number.isFinite(Number(item?.score)))
      .sort(
        (a, b) =>
          new Date(a?.created_at || 0).getTime() -
          new Date(b?.created_at || 0).getTime(),
      )

    if (activePeriod === "5") return sorted.slice(-5)
    if (activePeriod === "10") return sorted.slice(-10)
    return sorted
  }, [completedInterviews, activePeriod])

  const graphPoints = useMemo(() => {
    if (!performanceInterviews.length) return ""

    if (performanceInterviews.length === 1) {
      const score = Number(performanceInterviews[0]?.score || 0)
      const y = 150 - score * 1.25
      return `225,${Math.max(5, Math.min(150, y))}`
    }

    return performanceInterviews
      .map((item, index) => {
        const x = (index / (performanceInterviews.length - 1)) * 450
        const score = Number(item?.score || 0)
        const y = 150 - score * 1.25
        return `${x},${Math.max(5, Math.min(150, y))}`
      })
      .join(" ")
  }, [performanceInterviews])

  /* ============================================================
     REAL ROLE & DIFFICULTY ANALYTICS (NO FAKE RADAR SCORES)
  ============================================================ */

  const rolePerformance = useMemo(() => {
    const map = new Map<string, { totalScore: number; count: number }>()

    completedInterviews.forEach((item) => {
      const role = item.job_role || "General"
      const score = Number(item.score)
      if (Number.isFinite(score)) {
        const cur = map.get(role) || { totalScore: 0, count: 0 }
        map.set(role, { totalScore: cur.totalScore + score, count: cur.count + 1 })
      }
    })

    return Array.from(map.entries())
      .map(([role, data]) => ({
        role,
        average: Math.round(data.totalScore / data.count),
        count: data.count,
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 4)
  }, [completedInterviews])

  const difficultyPerformance = useMemo(() => {
    const map: Record<string, { total: number; count: number }> = {
      easy: { total: 0, count: 0 },
      medium: { total: 0, count: 0 },
      hard: { total: 0, count: 0 },
    }

    completedInterviews.forEach((item) => {
      const diff = (item.difficulty || "medium").toLowerCase()
      const score = Number(item.score)
      if (Number.isFinite(score) && map[diff]) {
        map[diff].total += score
        map[diff].count += 1
      }
    })

    return [
      {
        level: "Easy",
        avg: map.easy.count ? Math.round(map.easy.total / map.easy.count) : null,
        count: map.easy.count,
      },
      {
        level: "Medium",
        avg: map.medium.count ? Math.round(map.medium.total / map.medium.count) : null,
        count: map.medium.count,
      },
      {
        level: "Hard",
        avg: map.hard.count ? Math.round(map.hard.total / map.hard.count) : null,
        count: map.hard.count,
      },
    ]
  }, [completedInterviews])

  /* ============================================================
     DYNAMIC SMART RECOMMENDATIONS (RULE-BASED ON REAL DATA)
  ============================================================ */

  const recommendation = useMemo(() => {
    if (!interviews.length) {
      return {
        badge: "GET STARTED",
        title: "Take Your Baseline Mock Interview",
        desc: "Complete your first AI mock session to identify key strengths, technical gaps, and establish your benchmark score.",
        buttonText: "Start First Mock Interview",
        action: () => navigate("/interview-setup"),
      }
    }

    if (activeInterview) {
      return {
        badge: "IN PROGRESS",
        title: `Resume Session: ${activeInterview.job_role || "Interview"}`,
        desc: `You have an unfinished ${activeInterview.difficulty || "standard"} interview. Answer the remaining questions to receive your comprehensive AI score report.`,
        buttonText: "Continue Interview Now",
        action: () => navigate(`/interview/${activeInterview.id}`),
      }
    }

    const latest = [...completedInterviews].sort(
      (a, b) =>
        new Date(b?.completed_at || b?.created_at || 0).getTime() -
        new Date(a?.completed_at || a?.created_at || 0).getTime(),
    )[0]

    const latestScore = Number(latest?.score ?? 0)

    if (latestScore < 70) {
      return {
        badge: "TARGETED PRACTICE",
        title: `Strengthen Your Responses in ${latest?.job_role || "Engineering"}`,
        desc: `Your last session scored ${Math.round(latestScore)}%. Focus on depth, practical trade-offs, and clear communication in another session.`,
        buttonText: "Practice Role Again",
        action: () => navigate("/interview-setup"),
      }
    }

    return {
      badge: "READY TO LEVEL UP",
      title: "Challenge Yourself with Hard Difficulty",
      desc: `Impressive recent performance (${Math.round(latestScore)}%)! Push your boundaries by practicing system architecture and edge cases under Hard difficulty.`,
      buttonText: "Level Up Difficulty",
      action: () => navigate("/interview-setup"),
    }
  }, [interviews, activeInterview, completedInterviews, navigate])

  /* ============================================================
     REAL PROGRESS MILESTONES (NO FAKE ACHIEVEMENTS)
  ============================================================ */

  const milestones = useMemo(() => {
    const count = completedInterviews.length
    const pAch = practiceStats?.achievements || []
    const achMap = new Map(pAch.map((a) => [a.id, a]))

    return [
      {
        id: "first",
        title: "First Interview",
        desc: "Complete your first interview",
        unlocked: count >= 1,
        progress: `${Math.min(count, 1)} / 1`,
        icon: "★",
      },
      {
        id: "first_solve",
        title: "First Practice Solve",
        desc: "Solve a problem in Question Practice",
        unlocked: achMap.get("first_solve")?.unlocked || false,
        progress: achMap.get("first_solve")?.progress || "0 / 1",
        icon: "🎯",
      },
      {
        id: "consistent",
        title: "Consistent Practice",
        desc: "Complete 5 mock sessions",
        unlocked: count >= 5,
        progress: `${Math.min(count, 5)} / 5`,
        icon: "⚡",
      },
      {
        id: "streak_3",
        title: "Streak Initiate",
        desc: "Maintain a 3-day practice streak",
        unlocked: (practiceStats?.streak?.current_streak || 0) >= 3 || (practiceStats?.streak?.longest_streak || 0) >= 3,
        progress: `${Math.min(practiceStats?.streak?.current_streak || 0, 3)} / 3 days`,
        icon: "🔥",
      },
      {
        id: "xp_100",
        title: "Century Club",
        desc: "Earn 100+ Practice XP points",
        unlocked: (practiceStats?.xp?.total_xp || 0) >= 100,
        progress: `${Math.min(practiceStats?.xp?.total_xp || 0, 100)} / 100 XP`,
        icon: "⭐",
      },
      {
        id: "score75",
        title: "High Performer",
        desc: "Score 75% or higher in mock interview",
        unlocked: bestScore >= 75,
        progress: bestScore ? `${Math.round(bestScore)}% / 75%` : "0 / 75%",
        icon: "✦",
      },
      {
        id: "master",
        title: "Interview Pro",
        desc: "Complete 10 mock sessions",
        unlocked: count >= 10,
        progress: `${Math.min(count, 10)} / 10`,
        icon: "♛",
      },
    ]
  }, [completedInterviews, bestScore, practiceStats])

  /* ============================================================
     NAVIGATION HELPERS
  ============================================================ */

  function formatDate(value: string | null | undefined) {
    if (!value) return "—"
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return "—"
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    })
  }

  function formatStatus(status: string | null | undefined) {
    if (!status) return "Unknown"
    if (status.toLowerCase() === "completed") return "Completed"
    if (status.toLowerCase() === "started") return "In Progress"
    return "Ready"
  }

  function startInterview() {
    setMobileMenu(false)
    navigate("/interview-setup")
  }

  function openResume() {
    setMobileMenu(false)
    navigate("/resume")
  }

  function openPerformance() {
    setMobileMenu(false)
    navigate("/performance")
  }

  function openPractice() {
    setMobileMenu(false)
    navigate("/practice")
  }

  function openCoding() {
    setMobileMenu(false)
    navigate("/coding")
  }

  function openSettings() {
    setProfileMenu(false)
    setMobileMenu(false)
    navigate("/settings")
  }

  function scrollToSection(id: string) {
    setMobileMenu(false)
    const element = document.getElementById(id)
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }

  function handleSearchKeyDown(event: ReactKeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      setSearch("")
      event.currentTarget.blur()
    }
  }

  // Time-based personalized greeting
  const greeting = useMemo(() => {
    const hour = new Date().getHours()
    if (hour < 12) return "Good morning"
    if (hour < 17) return "Good afternoon"
    return "Good evening"
  }, [])

  const displayName = user?.full_name?.trim() || user?.email?.split("@")[0] || "Candidate"
  const firstName = displayName.split(" ")[0]
  const avatarLetter = displayName.charAt(0).toUpperCase()

  /* ============================================================
     RENDER: SKELETON LOADING
  ============================================================ */

  if (loading) {
    return (
      <div className="dashboard-shell">
        <aside className="dashboard-sidebar">
          <div className="sidebar-brand">
            <div className="brand-logo"><span>AI</span></div>
            <div className="brand-name">
              <strong>AI Interview</strong>
              <span>Platform</span>
            </div>
          </div>
        </aside>
        <main className="dashboard-main">
          <div className="dashboard-loading-skeleton">
            <div className="skeleton-welcome" />
            <div className="skeleton-stats-grid">
              <div className="skeleton-card" />
              <div className="skeleton-card" />
              <div className="skeleton-card" />
              <div className="skeleton-card" />
              <div className="skeleton-card" />
              <div className="skeleton-card" />
            </div>
            <div className="skeleton-main-grid">
              <div className="skeleton-panel" />
              <div className="skeleton-panel" />
            </div>
          </div>
        </main>
      </div>
    )
  }

  /* ============================================================
     MAIN DASHBOARD RENDER
  ============================================================ */

  return (
    <div className="dashboard-shell">
      {/* ======================================================
          SIDEBAR
      ====================================================== */}
      <aside className={`dashboard-sidebar ${mobileMenu ? "mobile-open" : ""}`}>
        <div className="sidebar-brand">
          <div className="brand-logo">
            <span>AI</span>
          </div>
          <div className="brand-name">
            <strong>AI Interview</strong>
            <span>Platform</span>
          </div>
          <button
            type="button"
            className="collapse-button"
            onClick={() => setMobileMenu(false)}
          >
            ‹
          </button>
        </div>

        <nav className="sidebar-menu">
          <button
            type="button"
            className="sidebar-link active"
            onClick={() => setMobileMenu(false)}
          >
            <span className="nav-icon">▦</span>
            <span>Dashboard</span>
          </button>

          <button
            type="button"
            className="sidebar-link"
            onClick={openResume}
          >
            <span className="nav-icon">▤</span>
            <span>Resume Analyzer</span>
          </button>

          <button
            type="button"
            className="sidebar-link"
            onClick={startInterview}
          >
            <span className="nav-icon">♙</span>
            <span>AI Interview</span>
          </button>

          <button
            type="button"
            className="sidebar-link"
            onClick={openPerformance}
          >
            <span className="nav-icon">▥</span>
            <span>Performance</span>
          </button>

          <button
            type="button"
            className="sidebar-link"
            onClick={openPractice}
          >
            <span className="nav-icon">✎</span>
            <span>Question Practice</span>
          </button>

          <button
            type="button"
            className="sidebar-link"
            onClick={openCoding}
          >
            <span className="nav-icon">⌨</span>
            <span>Coding Arena</span>
          </button>

          <button
            type="button"
            className="sidebar-link"
            onClick={() => scrollToSection("analytics-section")}
          >
            <span className="nav-icon">◉</span>
            <span>Analytics</span>
          </button>

          <button
            type="button"
            className="sidebar-link"
            onClick={() => scrollToSection("recent-section")}
          >
            <span className="nav-icon">⌁</span>
            <span>Recent Sessions</span>
          </button>

          <button
            type="button"
            className="sidebar-link"
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
            className="sidebar-link"
            onClick={() => {
              setMobileMenu(false)
              navigate("/notifications")
            }}
          >
            <span className="nav-icon">🔔</span>
            <span>Notifications</span>
            {dashboardUnreadCount > 0 && (
              <span className="notification-badge" style={{ marginLeft: "auto", position: "static" }}>
                {dashboardUnreadCount > 99 ? "99+" : dashboardUnreadCount}
              </span>
            )}
          </button>

          <button
            type="button"
            className="sidebar-link"
            onClick={() => scrollToSection("milestones-section")}
          >
            <span className="nav-icon">★</span>
            <span>Milestones</span>
          </button>

          <button
            type="button"
            className="sidebar-link"
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
            className="sidebar-link"
            onClick={() => {
              setMobileMenu(false)
              navigate("/subscription")
            }}
          >
            <span className="nav-icon">💎</span>
            <span>Subscription</span>
          </button>

          <button
            type="button"
            className="sidebar-link"
            onClick={() => {
              setMobileMenu(false)
              navigate("/support")
            }}
          >
            <span className="nav-icon">🎧</span>
            <span>Help & Support</span>
          </button>

          <button
            type="button"
            className="sidebar-link"
            onClick={openSettings}
          >
            <span className="nav-icon">⚙</span>
            <span>Settings</span>
          </button>
        </nav>

        {/* PRACTICE QUICK-LAUNCH CARD */}
        <div className="practice-card">
          <div className="practice-trophy">🎯</div>
          <h3>Ready to Practice?</h3>
          <p>
            Sharpen your technical & behavioral skills with realistic AI interviewers.
          </p>
          <button type="button" onClick={startInterview}>
            Start Interview <span>→</span>
          </button>
        </div>
      </aside>

      {/* ======================================================
          MAIN WORKSPACE
      ====================================================== */}
      <main className="dashboard-main">
        {/* HEADER */}
        <header className="dashboard-header">
          <button
            type="button"
            className="mobile-menu-button"
            onClick={() => setMobileMenu((value) => !value)}
            aria-label="Open navigation menu"
          >
            ☰
          </button>

          {/* SEARCH */}
          <div className="search-container">
            <span className="search-icon">⌕</span>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={handleSearchKeyDown}
              placeholder="Search by role or difficulty..."
              aria-label="Search interviews"
            />
            {search && (
              <button
                type="button"
                className="search-clear"
                onClick={() => setSearch("")}
              >
                ×
              </button>
            )}
            <kbd>Esc</kbd>
          </div>

          <div className="header-right">
            <RealtimeStatusBadge />

            {/* NOTIFICATIONS */}
            <div className="notification-wrapper" ref={notificationRef}>
              <button
                type="button"
                className="notification"
                onClick={() => setNotificationMenu((val) => !val)}
                aria-label="Notifications"
              >
                🔔
                {dashboardUnreadCount > 0 && (
                  <span className="notification-badge">
                    {dashboardUnreadCount > 9 ? "9+" : dashboardUnreadCount}
                  </span>
                )}
              </button>

              {notificationMenu && (
                <div className="notification-dropdown">
                  <div className="dropdown-title-row">
                    <span className="dropdown-title">Notifications</span>
                    {dashboardUnreadCount > 0 && (
                      <button
                        type="button"
                        className="dropdown-mark-read"
                        onClick={async () => {
                          setDashboardUnreadCount(0)
                          setDashboardNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })))
                          await markAllNotificationsAsRead().catch(() => null)
                        }}
                      >
                        Mark all read
                      </button>
                    )}
                  </div>

                  {dashboardNotifications.length === 0 ? (
                    <div className="dropdown-empty">
                      You&apos;re all caught up. No notifications yet.
                    </div>
                  ) : (
                    <div className="dropdown-scroll-list">
                      {dashboardNotifications.map((n) => (
                        <div
                          key={n.id}
                          className={`dropdown-item ${!n.is_read ? "unread" : ""}`}
                          onClick={async () => {
                            if (!n.is_read) {
                              setDashboardUnreadCount((prev) => Math.max(0, prev - 1))
                              setDashboardNotifications((prev) =>
                                prev.map((item) => (item.id === n.id ? { ...item, is_read: true } : item))
                              )
                              await markNotificationAsRead(n.id).catch(() => null)
                            }
                            setNotificationMenu(false)
                            if (n.action_url) {
                              navigate(n.action_url)
                            } else {
                              navigate("/notifications")
                            }
                          }}
                        >
                          <div className="dropdown-item-header">
                            <span className="dropdown-icon">{n.icon || "🔔"}</span>
                            <strong>{n.title}</strong>
                            {!n.is_read && <span className="dropdown-unread-dot" />}
                          </div>
                          <span>{n.message}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="dropdown-footer">
                    <button
                      type="button"
                      className="view-all-notifs-btn"
                      onClick={() => {
                        setNotificationMenu(false)
                        navigate("/notifications")
                      }}
                    >
                      View All Notifications →
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* PROFILE DROPDOWN */}
            <div className="header-profile-wrapper" ref={profileRef}>
              <button
                type="button"
                className="header-profile"
                onClick={() => setProfileMenu((val) => !val)}
                aria-expanded={profileMenu}
              >
                <div className="profile-avatar">{avatarLetter}</div>
                <div className="profile-details">
                  <div className="profile-name-row">
                    <strong>{displayName}</strong>
                    {practiceStats?.xp && (
                      <span className="user-level-badge">
                        Lvl {practiceStats.xp.level}
                      </span>
                    )}
                  </div>
                  <span>{practiceStats?.xp ? `${practiceStats.xp.total_xp} XP • ${practiceStats.xp.level_title}` : (user?.email || "Candidate")}</span>
                </div>
                <span className="profile-dropdown">{profileMenu ? "⌃" : "⌄"}</span>
              </button>

              {profileMenu && (
                <div className="profile-menu">
                  {practiceStats?.xp && (
                    <div className="profile-xp-summary">
                      <div className="profile-xp-row">
                        <span className="xp-rank">{practiceStats.xp.level_title}</span>
                        <span className="xp-pts">{practiceStats.xp.total_xp} XP</span>
                      </div>
                      <div className="profile-xp-track">
                        <div
                          className="profile-xp-fill"
                          style={{ width: `${practiceStats.xp.progress_pct}%` }}
                        />
                      </div>
                      <small className="xp-next">
                        {practiceStats.xp.current_level_xp} / {practiceStats.xp.next_level_xp} XP to Lvl {practiceStats.xp.level + 1}
                      </small>
                    </div>
                  )}

                  <button
                    type="button"
                    onClick={() => {
                      setProfileMenu(false)
                      navigate("/profile")
                    }}
                  >
                    <span>👤</span> View Profile
                  </button>
                  <button type="button" onClick={openPractice}>
                    <span>✎</span> Practice Questions
                  </button>
                  <button type="button" onClick={openSettings}>
                    <span>⚙</span> Settings
                  </button>
                  <button type="button" onClick={openResume}>
                    <span>▤</span> Resume Analyzer
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setProfileMenu(false)
                      navigate("/support")
                    }}
                  >
                    <span>🎧</span> Help & Support
                  </button>
                  <div className="profile-divider" />
                  <button
                    type="button"
                    className="logout-menu-button"
                    onClick={logout}
                  >
                    <span>⇥</span> Logout
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* CONTENT */}
        <div className="dashboard-content">
          {/* ERROR BANNER */}
          {error && (
            <div className="dashboard-error">
              <span>⚠️ {error}</span>
              <button type="button" onClick={loadDashboard}>
                Retry
              </button>
            </div>
          )}

          {/* ==================================================
              A. WELCOME SECTION
          ================================================== */}
          <section className="welcome-banner">
            <div className="welcome-copy">
              <span className="welcome-eyebrow">CANDIDATE DASHBOARD</span>
              <h1>
                {greeting}, {firstName}! <span>👋</span>
              </h1>
              <p>
                {completedInterviews.length > 0
                  ? `You have completed ${completedInterviews.length} mock interview${
                      completedInterviews.length === 1 ? "" : "s"
                    } with an overall average score of ${Math.round(averageScore)}%.`
                  : activeInterview
                  ? "You have an ongoing interview session waiting to be completed."
                  : "Welcome to your AI Interview Platform. Start a session to benchmark your technical preparation."}
              </p>
            </div>

            <div className="welcome-actions">
              <button
                type="button"
                className="welcome-primary-cta"
                onClick={startInterview}
              >
                <span>Start AI Interview</span>
                <span className="cta-arrow">→</span>
              </button>

              <button
                type="button"
                className="welcome-secondary-cta"
                onClick={openResume}
              >
                Analyze Resume
              </button>
            </div>
          </section>

          {/* ==================================================
              B. QUICK STATS (100% REAL DATA)
          ================================================== */}
          <section className="stats-row">
            <div className="stat-card purple-card">
              <div className="stat-icon">♙</div>
              <div className="stat-info">
                <span>Total Interviews</span>
                <strong>{interviews.length}</strong>
                <small>Sessions created</small>
              </div>
            </div>

            <div className="stat-card blue-card">
              <div className="stat-icon">✓</div>
              <div className="stat-info">
                <span>Completed</span>
                <strong>{completedInterviews.length}</strong>
                <small>Evaluated sessions</small>
              </div>
            </div>

            <div className="stat-card cyan-card">
              <div className="stat-icon">◎</div>
              <div className="stat-info">
                <span>Average Score</span>
                <strong>
                  {scores.length ? `${Math.round(averageScore)}%` : "—"}
                </strong>
                <small>{scores.length ? "Across completed" : "No scores yet"}</small>
              </div>
            </div>

            <div className="stat-card gold-card">
              <div className="stat-icon">★</div>
              <div className="stat-info">
                <span>Best Score</span>
                <strong>
                  {scores.length ? `${Math.round(bestScore)}%` : "—"}
                </strong>
                <small>{scores.length ? "Personal record" : "Pending completion"}</small>
              </div>
            </div>

            <div className="stat-card orange-card">
              <div className="stat-icon">&lt;/&gt;</div>
              <div className="stat-info">
                <span>Questions Attempted</span>
                <strong>{totalQuestionsAttempted}</strong>
                <small>Technical & soft skill</small>
              </div>
            </div>

            <div className="stat-card pink-card">
              <div className="stat-icon">🔥</div>
              <div className="stat-info">
                <span>Practice Streak</span>
                <strong>{effectiveStreak} Day{effectiveStreak === 1 ? "" : "s"}</strong>
                <small>
                  {practiceStats?.streak?.is_active_today
                    ? "Active today • Consistent"
                    : effectiveStreak > 0
                    ? "Streak active from yesterday"
                    : "Solve a question to begin"}
                </small>
              </div>
            </div>
          </section>

          {/* ==================================================
              C & H. UPCOMING / ACTIVE + AI RECOMMENDATION
          ================================================== */}
          <section className="two-column-action-grid">
            {/* C. UPCOMING / ACTIVE INTERVIEW */}
            <div className="panel action-panel">
              <div className="panel-header">
                <div>
                  <span className="panel-badge">CURRENT SESSION</span>
                  <h2>Active Interview Session</h2>
                </div>
              </div>

              {activeInterview ? (
                <div className="active-interview-card">
                  <div className="active-card-top">
                    <div className="active-role-icon">&lt;/&gt;</div>
                    <div className="active-card-title">
                      <strong>{activeInterview.job_role || "Technical Interview"}</strong>
                      <span>
                        {activeInterview.difficulty?.toUpperCase()} • Created{" "}
                        {formatDate(activeInterview.created_at)}
                      </span>
                    </div>
                    <span className="live-status-pill">
                      <span className="pulsing-dot" />
                      {activeInterview.status === "started" ? "IN PROGRESS" : "READY"}
                    </span>
                  </div>

                  <p className="active-card-desc">
                    You have an ongoing interview session. Continue right where you left off with voice or text responses.
                  </p>

                  <button
                    type="button"
                    className="action-card-button"
                    onClick={() => navigate(`/interview/${activeInterview.id}`)}
                  >
                    Continue Interview <span>→</span>
                  </button>
                </div>
              ) : (
                <div className="empty-active-interview">
                  <div className="empty-target-icon">🎯</div>
                  <strong>No active interview session</strong>
                  <p>
                    Start a realistic AI mock interview tailored to your target role, difficulty, and seniority level.
                  </p>
                  <button
                    type="button"
                    className="action-card-button outline"
                    onClick={startInterview}
                  >
                    Configure New Interview <span>→</span>
                  </button>
                </div>
              )}
            </div>

            {/* H. RECOMMENDED NEXT STEP */}
            <div className="panel recommendation-panel">
              <div className="panel-header">
                <div>
                  <span className="panel-badge">{recommendation.badge}</span>
                  <h2>Recommended Preparation Step</h2>
                </div>
              </div>

              <div className="recommendation-card">
                <div className="recommendation-content">
                  <div className="rec-icon">⚡</div>
                  <div>
                    <strong>{recommendation.title}</strong>
                    <p>{recommendation.desc}</p>
                  </div>
                </div>

                <button
                  type="button"
                  className="action-card-button secondary"
                  onClick={recommendation.action}
                >
                  {recommendation.buttonText} <span>→</span>
                </button>
              </div>
            </div>
          </section>

          {/* ==================================================
              PRACTICE MISSIONS & TOPIC MASTERY (TASK 6 ARCHITECTURE)
          ================================================== */}
          <section className="two-column-action-grid practice-stats-row">
            {/* DAILY PRACTICE MISSIONS */}
            <div className="panel practice-missions-panel">
              <div className="panel-header">
                <div>
                  <span className="panel-badge">DAILY QUESTS</span>
                  <h2>Daily Practice Missions</h2>
                  <p>Daily coding and architectural challenges to sharpen your skills</p>
                </div>
                {practiceStats?.xp && (
                  <span className="xp-pill-badge">
                    ⚡ {practiceStats.xp.total_xp} Total XP
                  </span>
                )}
              </div>

              <div className="missions-list">
                {practiceStats?.missions?.map((m) => (
                  <div key={m.id} className={`mission-item ${m.completed ? "mission-completed" : ""}`}>
                    <div className="mission-left">
                      <span className="mission-icon">{m.icon}</span>
                      <div className="mission-info">
                        <div className="mission-title-row">
                          <strong>{m.title}</strong>
                          {m.completed && <span className="mission-done-tag">Done ✓</span>}
                        </div>
                        <p>{m.description}</p>
                      </div>
                    </div>

                    <div className="mission-right">
                      <span className="mission-xp">+{m.xp_reward} XP</span>
                      <div className="mission-track">
                        <div
                          className="mission-fill"
                          style={{ width: `${Math.min(100, (m.progress / m.target) * 100)}%` }}
                        />
                      </div>
                      <small className="mission-count">{m.progress} / {m.target}</small>
                    </div>
                  </div>
                ))}
              </div>

              <div className="panel-footer-action">
                <button type="button" className="action-card-button secondary" onClick={openPractice}>
                  Open Question Practice <span>→</span>
                </button>
              </div>
            </div>

            {/* TOPIC MASTERY & XP PROFILE */}
            <div className="panel topic-mastery-panel">
              <div className="panel-header">
                <div>
                  <span className="panel-badge">MASTERY TIERS</span>
                  <h2>Topic Mastery &amp; Rank</h2>
                  <p>Proficiency across technical interview competencies</p>
                </div>
                {practiceStats?.xp && (
                  <span className="rank-tag">
                    {practiceStats.xp.level_title}
                  </span>
                )}
              </div>

              {practiceStats?.xp && (
                <div className="xp-progress-card">
                  <div className="xp-card-meta">
                    <span className="level-badge">Level {practiceStats.xp.level}</span>
                    <span className="xp-fraction">
                      <strong>{practiceStats.xp.current_level_xp}</strong> / {practiceStats.xp.next_level_xp} XP to Lvl {practiceStats.xp.level + 1}
                    </span>
                  </div>
                  <div className="xp-bar-track">
                    <div
                      className="xp-bar-fill"
                      style={{ width: `${practiceStats.xp.progress_pct}%` }}
                    />
                  </div>
                </div>
              )}

              <div className="mastery-topics-compact">
                {practiceStats?.mastery?.top_topics && practiceStats.mastery.top_topics.length > 0 ? (
                  practiceStats.mastery.top_topics.slice(0, 4).map((tm) => (
                    <div key={tm.topic} className="compact-mastery-row">
                      <div className="compact-mastery-meta">
                        <span className="topic-name">{tm.topic}</span>
                        <span className={`status-badge-small status-${tm.status.toLowerCase()}`}>
                          {tm.status} ({tm.solved}/{tm.total})
                        </span>
                      </div>
                      <div className="compact-track">
                        <div
                          className="compact-fill"
                          style={{ width: `${tm.percentage}%` }}
                        />
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="empty-mastery-hint">
                    <p>Start solving questions in Question Practice to build topic mastery!</p>
                  </div>
                )}
              </div>
            </div>
          </section>

          {/* ==================================================
              PHASE 8B: CODING ARENA PERFORMANCE (100% REAL DB DATA)
          ================================================== */}
          <section className="two-column-action-grid coding-arena-dashboard-panel" id="coding-section">
            <div className="panel coding-stats-panel">
              <div className="panel-header">
                <div>
                  <span className="panel-badge">CODING ARENA</span>
                  <h2>Algorithm & Data Structure Performance</h2>
                  <p>Real-time submission analytics and problem solving metrics</p>
                </div>
                <button
                  type="button"
                  className="action-card-button secondary"
                  onClick={() => navigate("/coding")}
                  style={{ width: "auto", padding: "0.4rem 0.9rem" }}
                >
                  Enter Arena <span>→</span>
                </button>
              </div>

              <div className="coding-overview-metrics-grid">
                <div className="coding-metric-box">
                  <span className="coding-metric-num">{codingStats?.total_solved || 0}</span>
                  <span className="coding-metric-lbl">Solved / {codingStats?.total_attempted || 0} Attempted</span>
                  <div className="coding-difficulty-pills">
                    <span className="diff-pill easy">{codingStats?.easy_solved || 0} Easy</span>
                    <span className="diff-pill medium">{codingStats?.medium_solved || 0} Med</span>
                    <span className="diff-pill hard">{codingStats?.hard_solved || 0} Hard</span>
                  </div>
                </div>

                <div className="coding-metric-box">
                  <span className="coding-metric-num">{codingStats?.success_rate || 0}%</span>
                  <span className="coding-metric-lbl">Success Rate</span>
                  <small style={{ color: "#94a3b8" }}>
                    Avg Score: {Math.round(codingStats?.average_score || 0)} pts
                  </small>
                </div>

                <div className="coding-metric-box">
                  <span className="coding-metric-num">🔥 {codingStats?.current_streak || 0}</span>
                  <span className="coding-metric-lbl">Day Coding Streak</span>
                  <small style={{ color: "#94a3b8" }}>
                    Longest: {codingStats?.longest_streak || 0} Days
                  </small>
                </div>
              </div>

              {codingStats?.topic_breakdown && Object.keys(codingStats.topic_breakdown).length > 0 && (
                <div className="coding-topics-breakdown">
                  <span className="coding-breakdown-title">Topic Proficiency</span>
                  <div className="coding-topics-chips">
                    {Object.entries(codingStats.topic_breakdown).map(([top, info]) => {
                      const countText = typeof info === "object" && info !== null
                        ? `${(info as any).solved ?? 0}/${(info as any).attempted ?? 0}`
                        : `${info} solved`
                      return (
                        <div key={top} className="coding-topic-chip">
                          <span className="topic-name">{top}</span>
                          <span className="topic-count">{countText}</span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>

            <div className="panel coding-recent-panel">
              <div className="panel-header">
                <div>
                  <span className="panel-badge">ACTIVITY</span>
                  <h2>Recent Coding Submissions</h2>
                  <p>Latest evaluated code submissions and AI reviews</p>
                </div>
              </div>

              <div className="coding-recent-list">
                {codingStats?.recent_submissions && codingStats.recent_submissions.length > 0 ? (
                  codingStats.recent_submissions.slice(0, 4).map((sub) => (
                    <div
                      key={sub.id}
                      className="coding-recent-item"
                      onClick={() => navigate(`/coding/${sub.problem_id}`)}
                    >
                      <div className="recent-item-left">
                        <span className={`recent-status-dot ${sub.status === "Accepted" ? "accepted" : "failed"}`} />
                        <div>
                          <strong>{sub.status} ({sub.score} pts)</strong>
                          <small>{sub.language} • {sub.passed_tests}/{sub.total_tests} Tests Passed</small>
                        </div>
                      </div>
                      <div className="recent-item-right">
                        <span>{new Date(sub.created_at).toLocaleDateString()}</span>
                        <span>→</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="coding-empty-recent">
                    <p>No coding submissions recorded yet.</p>
                    <button
                      type="button"
                      className="action-card-button secondary"
                      onClick={() => navigate("/coding")}
                      style={{ marginTop: "0.5rem" }}
                    >
                      Solve Your First Challenge <span>→</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          </section>

          {/* ==================================================
              D & E. PERFORMANCE OVERVIEW & REAL ANALYTICS
          ================================================== */}
          <section className="main-grid" id="performance-section">
            {/* D. PERFORMANCE OVERVIEW */}
            <div className="panel performance-panel">
              <div className="panel-header">
                <div>
                  <h2>Performance Trajectory</h2>
                  <p>Score progression across completed interview sessions</p>
                </div>

                {completedInterviews.length > 0 && (
                  <select
                    className="period-select"
                    value={activePeriod}
                    onChange={(e) =>
                      setActivePeriod(e.target.value as "5" | "10" | "all")
                    }
                  >
                    <option value="5">Last 5 Sessions</option>
                    <option value="10">Last 10 Sessions</option>
                    <option value="all">All Sessions</option>
                  </select>
                )}
              </div>

              {completedInterviews.length >= 2 ? (
                <div className="chart-wrapper">
                  <div className="chart-y-axis">
                    <span>100%</span>
                    <span>75%</span>
                    <span>50%</span>
                    <span>25%</span>
                    <span>0%</span>
                  </div>

                  <div className="chart-area">
                    <div className="chart-lines">
                      <i /><i /><i /><i /><i />
                    </div>

                    <svg
                      viewBox="0 0 450 150"
                      preserveAspectRatio="none"
                      className="performance-svg"
                    >
                      <defs>
                        <linearGradient
                          id="chartGradient"
                          x1="0"
                          y1="0"
                          x2="0"
                          y2="1"
                        >
                          <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.4" />
                          <stop offset="100%" stopColor="#4c1d95" stopOpacity="0.0" />
                        </linearGradient>
                      </defs>

                      <polygon
                        points={`0,150 ${graphPoints} 450,150`}
                        fill="url(#chartGradient)"
                      />

                      <polyline
                        points={graphPoints}
                        fill="none"
                        stroke="#a855f7"
                        strokeWidth="3"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />

                      {performanceInterviews.map((item, index) => {
                        const x =
                          performanceInterviews.length === 1
                            ? 225
                            : (index / (performanceInterviews.length - 1)) * 450
                        const score = Number(item?.score || 0)
                        const y = Math.max(5, Math.min(150, 150 - score * 1.25))

                        return (
                          <g key={item.id || index}>
                            <circle
                              cx={x}
                              cy={y}
                              r="5"
                              fill="#c084fc"
                              stroke="#0f172a"
                              strokeWidth="2"
                            />
                          </g>
                        )
                      })}
                    </svg>

                    <div className="chart-x-axis">
                      {performanceInterviews.map((item) => (
                        <span key={item.id}>
                          {item.created_at
                            ? new Date(item.created_at).toLocaleDateString("en-US", {
                                month: "short",
                                day: "numeric",
                              })
                            : "—"}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="chart-empty-state">
                  <div className="chart-empty-icon">📈</div>
                  <strong>Need more interview data</strong>
                  <p>
                    Complete at least 2 interview sessions to visualize your score progression and performance trajectory over time.
                  </p>
                  <button type="button" onClick={startInterview}>
                    Start an Interview →
                  </button>
                </div>
              )}
            </div>

            {/* E. DOMAIN & ROLE ANALYTICS */}
            <div className="panel analytics-panel" id="analytics-section">
              <div className="panel-header">
                <div>
                  <h2>Domain & Difficulty Breakdown</h2>
                  <p>Real performance aggregated from your evaluations</p>
                </div>
              </div>

              {completedInterviews.length > 0 ? (
                <div className="breakdown-container">
                  {/* BY DIFFICULTY */}
                  <div className="breakdown-group">
                    <span className="breakdown-group-title">PERFORMANCE BY DIFFICULTY</span>
                    <div className="difficulty-bars">
                      {difficultyPerformance.map((item) => (
                        <div key={item.level} className="difficulty-row">
                          <div className="diff-header">
                            <span>{item.level}</span>
                            <strong>
                              {item.avg !== null ? `${item.avg}%` : "Not attempted"}
                            </strong>
                          </div>
                          <div className="diff-track">
                            <div
                              className={`diff-fill ${item.level.toLowerCase()}`}
                              style={{ width: `${item.avg ?? 0}%` }}
                            />
                          </div>
                          <small>{item.count} session{item.count === 1 ? "" : "s"}</small>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* BY ROLE */}
                  {rolePerformance.length > 0 && (
                    <div className="breakdown-group">
                      <span className="breakdown-group-title">TOP TARGET ROLES</span>
                      <div className="role-bars">
                        {rolePerformance.map((item) => (
                          <div key={item.role} className="role-row">
                            <div className="role-header">
                              <span className="role-name">{item.role}</span>
                              <span className="role-score">{item.average}% avg</span>
                            </div>
                            <div className="role-track">
                              <div
                                className="role-fill"
                                style={{ width: `${item.average}%` }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="analytics-empty-state">
                  <div className="empty-target-icon">📊</div>
                  <strong>No evaluated sessions yet</strong>
                  <p>
                    Complete your first mock interview to unlock breakdown analytics by job role and difficulty level.
                  </p>
                </div>
              )}
            </div>
          </section>

          {/* ==================================================
              F. RECENT SESSIONS TABLE
          ================================================== */}
          <section className="panel recent-sessions-panel" id="recent-section">
            <div className="panel-header">
              <div>
                <h2>Recent Interview Sessions</h2>
                <p>Complete history of your mock interviews with instant access to evaluations</p>
              </div>

              <button
                type="button"
                className="panel-header-btn"
                onClick={startInterview}
              >
                + New Interview
              </button>
            </div>

            {recentInterviews.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">♙</div>
                <h3>{search ? "No matching sessions found" : "No interviews taken yet"}</h3>
                <p>
                  {search
                    ? "Try searching for a different role or difficulty."
                    : "Launch your first mock interview session to see your activity, scores, and AI feedback here."}
                </p>
                {!search && (
                  <button type="button" onClick={startInterview}>
                    Start First Interview →
                  </button>
                )}
              </div>
            ) : (
              <>
                <div className="sessions-table-wrapper">
                  <table className="sessions-table">
                    <thead>
                      <tr>
                        <th>Target Role</th>
                        <th>Difficulty</th>
                        <th>Date</th>
                        <th>Status</th>
                        <th>Score</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recentInterviews.map((item) => {
                        const scoreNum = Number(item?.score)
                        const hasScore = Number.isFinite(scoreNum)
                        const isCompleted = item?.status === "completed"

                        return (
                          <tr key={item.id}>
                            <td>
                              <div className="table-role-cell">
                                <span className="table-role-icon">&lt;/&gt;</span>
                                <div>
                                  <strong>{item.job_role || "Interview"}</strong>
                                </div>
                              </div>
                            </td>
                            <td>
                              <span className={`diff-pill ${(item.difficulty || "medium").toLowerCase()}`}>
                                {item.difficulty || "Medium"}
                              </span>
                            </td>
                            <td>{formatDate(item.created_at)}</td>
                            <td>
                              <span className={`status-pill ${item.status || "created"}`}>
                                {formatStatus(item.status)}
                              </span>
                            </td>
                            <td>
                              {hasScore ? (
                                <span
                                  className={`score-badge ${
                                    scoreNum >= 80
                                      ? "score-high"
                                      : scoreNum >= 60
                                      ? "score-mid"
                                      : "score-low"
                                  }`}
                                >
                                  {Math.round(scoreNum)}%
                                </span>
                              ) : (
                                <span className="score-pending">—</span>
                              )}
                            </td>
                            <td>
                              {isCompleted ? (
                                <button
                                  type="button"
                                  className="table-action-btn view-result"
                                  onClick={() => navigate(`/results/${item.id}`)}
                                >
                                  View Result →
                                </button>
                              ) : (
                                <button
                                  type="button"
                                  className="table-action-btn resume-session"
                                  onClick={() => navigate(`/interview/${item.id}`)}
                                >
                                  Continue →
                                </button>
                              )}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>

                {filteredInterviews.length > 6 && (
                  <button
                    type="button"
                    className="sessions-toggle-btn"
                    onClick={() => setShowAllSessions((val) => !val)}
                  >
                    {showAllSessions ? "Show Fewer Sessions" : `View All ${filteredInterviews.length} Sessions`}
                  </button>
                )}
              </>
            )}
          </section>

          {/* ==================================================
              PHASE 11: PERSONALIZED LEARNING INTELLIGENCE
          ================================================== */}
          <section className="main-grid" id="learning-section">
            {/* WEAK TOPICS PANEL */}
            <div className="panel learning-weak-panel">
              <div className="panel-header">
                <div>
                  <span className="panel-badge">AI ANALYSIS</span>
                  <h2>Weak Topic Radar</h2>
                  <p>Topics needing the most improvement based on your performance</p>
                </div>
                <button
                  type="button"
                  className="action-card-button secondary"
                  onClick={() => navigate("/practice")}
                  style={{ width: "auto", padding: "0.4rem 0.9rem" }}
                >
                  Practice Now →
                </button>
              </div>

              {weakTopics.length === 0 ? (
                <div className="learning-empty-hint">
                  <span className="learning-empty-icon">🧠</span>
                  <p>Complete interviews or coding sessions to unlock your personalized weak-topic analysis.</p>
                </div>
              ) : (
                <div className="weak-topics-list">
                  {weakTopics.slice(0, 6).map((wt, idx) => {
                    const scoreNum = wt.combined_score ?? 0
                    const conf = Math.round(Math.min(Math.max(scoreNum, 0), 1) * 100)
                    const urgency = wt.priority ?? "low"
                    const urgencyColor =
                      urgency === "high" ? "#ef4444" :
                      urgency === "medium" ? "#f97316" : "#6366f1"
                    return (
                      <div key={`${wt.topic}-${idx}`} className="weak-topic-row">
                        <div className="weak-topic-meta">
                          <span className="weak-topic-name">{wt.topic}</span>
                          <span
                            className="weak-urgency-tag"
                            style={{ color: urgencyColor, borderColor: urgencyColor }}
                          >
                            {urgency.toUpperCase()} PRIORITY
                          </span>
                        </div>
                        <div className="weak-topic-bar-track">
                          <div
                            className="weak-topic-bar-fill"
                            style={{
                              width: `${conf}%`,
                              background: `linear-gradient(90deg, ${urgencyColor}88, ${urgencyColor})`,
                            }}
                          />
                        </div>
                        <small className="weak-topic-conf">{wt.reason || wt.category}</small>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            {/* DAILY PRACTICE PLAN PANEL */}
            <div className="panel learning-daily-panel">
              <div className="panel-header">
                <div>
                  <span className="panel-badge">TODAY&apos;S PLAN</span>
                  <h2>Daily Practice Plan</h2>
                  <p>Your AI-generated tasks for today</p>
                </div>
                {dailyPlan && (
                  <span className="daily-plan-date">
                    {new Date(dailyPlan.plan_date).toLocaleDateString("en-US", {
                      weekday: "short",
                      month: "short",
                      day: "numeric",
                    })}
                  </span>
                )}
              </div>

              {!dailyPlan || !Array.isArray(dailyPlan.items) || dailyPlan.items.length === 0 ? (
                <div className="learning-empty-hint">
                  <span className="learning-empty-icon">📅</span>
                  <p>Your daily practice plan generates after completing your first interview or coding session.</p>
                </div>
              ) : (
                <div className="daily-tasks-list">
                  {dailyPlan.items.map((task) => (
                    <div
                      key={task.id}
                      className={`daily-task-row ${task.is_completed ? "completed" : ""} ${togglingTask === task.id ? "toggling" : ""}`}
                    >
                      <button
                        type="button"
                        className="daily-task-check"
                        aria-label={task.is_completed ? "Mark incomplete" : "Mark complete"}
                        disabled={togglingTask === task.id}
                        onClick={async () => {
                          setTogglingTask(task.id)
                          try {
                            const updated = await toggleDailyPracticeTask(task.id)
                            setDailyPlan(updated)
                          } catch {
                            // silently ignore
                          } finally {
                            setTogglingTask(null)
                          }
                        }}
                      >
                        {task.is_completed ? "✓" : "○"}
                      </button>
                      <div className="daily-task-info">
                        <strong>{task.title}</strong>
                        {task.topic && <small>{task.topic}</small>}
                      </div>
                      {task.duration_mins > 0 && (
                        <span className="daily-task-duration">
                          {task.duration_mins}m
                        </span>
                      )}
                    </div>
                  ))}

                  {/* completion bar */}
                  {(() => {
                    const done = dailyPlan.items.filter(t => t.is_completed).length
                    const total = dailyPlan.items.length
                    const pct = total > 0 ? Math.round((done / total) * 100) : 0
                    return (
                      <div className="daily-plan-progress">
                        <div className="daily-plan-bar-track">
                          <div className="daily-plan-bar-fill" style={{ width: `${pct}%` }} />
                        </div>
                        <small>{done} / {total} tasks completed ({pct}%)</small>
                      </div>
                    )
                  })()}
                </div>
              )}
            </div>
          </section>

          {/* ==================================================
              G. REAL MILESTONES (NO FABRICATED BADGES)
          ================================================== */}
          <section className="panel milestones-panel" id="milestones-section">
            <div className="panel-header">
              <div>
                <h2>Preparation Milestones</h2>
                <p>Track your interview preparation consistency and score milestones</p>
              </div>

              <button
                type="button"
                className="panel-header-btn"
                onClick={() => navigate("/achievements")}
              >
                View All Achievements →
              </button>
            </div>

            <div className="milestones-grid">
              {milestones.map((m) => (
                <div
                  key={m.id}
                  className={`milestone-card ${m.unlocked ? "unlocked" : "locked"}`}
                >
                  <div className="milestone-top">
                    <span className="milestone-icon">{m.icon}</span>
                    <span className={`milestone-badge ${m.unlocked ? "unlocked" : "locked"}`}>
                      {m.unlocked ? "UNLOCKED" : "IN PROGRESS"}
                    </span>
                  </div>

                  <strong>{m.title}</strong>
                  <p>{m.desc}</p>

                  <div className="milestone-footer">
                    <small>Progress: {m.progress}</small>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </main>

      {/* REAL-TIME NOTIFICATION TOAST */}
      {realtimeToast && (
        <div className="realtime-toast-banner" onClick={() => setRealtimeToast(null)}>
          <span className="toast-icon">{realtimeToast.icon || "🔔"}</span>
          <div className="toast-body">
            <strong>{realtimeToast.title}</strong>
            <p>{realtimeToast.message}</p>
          </div>
          <button className="toast-close" onClick={(e) => { e.stopPropagation(); setRealtimeToast(null); }}>×</button>
        </div>
      )}

      {/* MOBILE DRAWER OVERLAY */}
      {mobileMenu && (
        <button
          type="button"
          className="dashboard-mobile-overlay"
          aria-label="Close navigation menu"
          onClick={() => setMobileMenu(false)}
        />
      )}
    </div>
  )
}

export default Dashboard