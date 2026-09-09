import { useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"

import "./Dashboard.css"

const API_BASE_URL = "http://127.0.0.1:8000/api/v1"

type User = {
  id: string
  full_name: string
  email: string
  is_verified: boolean
}

type Interview = {
  id: string
  user_id: string
  job_role: string
  difficulty: string
  status: string
  score: number | null
  questions: string | null
  answers: string | null
  transcript?: string | null
  feedback: string | null
  strengths: string | null
  weaknesses: string | null
  question_evaluations?: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
}

function Dashboard() {
  const navigate = useNavigate()

  const [user, setUser] = useState<User | null>(null)
  const [interviews, setInterviews] = useState<Interview[]>([])
  const [loading, setLoading] = useState(true)
  const [mobileMenu, setMobileMenu] = useState(false)

  // ============================================================
  // LOAD USER
  // ============================================================

  useEffect(() => {
    async function loadUser() {
      const token = localStorage.getItem("access_token")

      if (!token) {
        navigate("/login")
        return
      }

      try {
        const response = await fetch(
          `${API_BASE_URL}/auth/me`,
          {
            headers: {
              Accept: "application/json",
              Authorization: `Bearer ${token}`,
            },
          },
        )

        if (response.status === 401) {
          localStorage.removeItem("access_token")
          navigate("/login")
          return
        }

        if (!response.ok) {
          throw new Error("Unable to load user")
        }

        const data: User = await response.json()

        setUser(data)
      } catch (error) {
        console.error("User loading error:", error)
      }
    }

    loadUser()
  }, [navigate])

  // ============================================================
  // LOAD INTERVIEWS
  // ============================================================

  useEffect(() => {
    async function loadInterviews() {
      const token = localStorage.getItem("access_token")

      if (!token) {
        navigate("/login")
        return
      }

      try {
        const response = await fetch(
          `${API_BASE_URL}/interview`,
          {
            headers: {
              Accept: "application/json",
              Authorization: `Bearer ${token}`,
            },
          },
        )

        if (response.status === 401) {
          localStorage.removeItem("access_token")
          navigate("/login")
          return
        }

        if (!response.ok) {
          throw new Error("Unable to load interviews")
        }

        const data = await response.json()

        setInterviews(
          Array.isArray(data.interviews)
            ? data.interviews
            : [],
        )
      } catch (error) {
        console.error("Interview loading error:", error)
        setInterviews([])
      } finally {
        setLoading(false)
      }
    }

    loadInterviews()
  }, [navigate])

  // ============================================================
  // INTERVIEW DATA
  // ============================================================

  const completedInterviews = useMemo(
    () =>
      interviews.filter(
        (item) =>
          item.status?.toLowerCase() === "completed",
      ),
    [interviews],
  )

  const activeInterviews = useMemo(
    () =>
      interviews.filter(
        (item) =>
          item.status?.toLowerCase() !== "completed",
      ),
    [interviews],
  )

  const averageScore = useMemo(() => {
    const scores = completedInterviews
      .map((item) => item.score)
      .filter(
        (score): score is number =>
          typeof score === "number",
      )

    if (!scores.length) return 0

    return (
      scores.reduce(
        (total, score) => total + score,
        0,
      ) / scores.length
    )
  }, [completedInterviews])

  const bestScore = useMemo(() => {
    const scores = completedInterviews
      .map((item) => item.score)
      .filter(
        (score): score is number =>
          typeof score === "number",
      )

    return scores.length
      ? Math.max(...scores)
      : 0
  }, [completedInterviews])

  const recentInterviews = useMemo(
    () =>
      [...interviews]
        .sort(
          (a, b) =>
            new Date(b.created_at).getTime() -
            new Date(a.created_at).getTime(),
        )
        .slice(0, 3),
    [interviews],
  )

  const performanceInterviews = useMemo(
    () =>
      [...completedInterviews]
        .filter(
          (item) =>
            typeof item.score === "number",
        )
        .sort(
          (a, b) =>
            new Date(a.created_at).getTime() -
            new Date(b.created_at).getTime(),
        )
        .slice(-7),
    [completedInterviews],
  )

  const todayCount = useMemo(() => {
    const today = new Date()

    return interviews.filter((item) => {
      const date = new Date(item.created_at)

      return (
        date.getDate() === today.getDate() &&
        date.getMonth() === today.getMonth() &&
        date.getFullYear() === today.getFullYear()
      )
    }).length
  }, [interviews])

  const dailyPercentage = Math.min(
    Math.round((todayCount / 4) * 100),
    100,
  )

  // ============================================================
  // PERFORMANCE GRAPH
  // ============================================================

  const graphPoints = useMemo(() => {
    if (!performanceInterviews.length) {
      return "0,145 75,120 150,135 225,95 300,110 375,75 450,90"
    }

    return performanceInterviews
      .map((item, index) => {
        const x =
          performanceInterviews.length === 1
            ? 225
            : (index /
                (performanceInterviews.length - 1)) *
              450

        const score = item.score ?? 0

        const y = 150 - score * 1.25

        return `${x},${Math.max(5, y)}`
      })
      .join(" ")
  }, [performanceInterviews])

  // ============================================================
  // SKILLS
  // ============================================================

  const baseSkill = Math.round(averageScore)

  const skills = [
    {
      name: "Data Structures & Algorithms",
      value: baseSkill,
      className: "purple",
    },
    {
      name: "System Design",
      value: Math.max(baseSkill - 5, 0),
      className: "blue",
    },
    {
      name: "Database Management",
      value: Math.max(baseSkill - 9, 0),
      className: "cyan",
    },
    {
      name: "Operating System",
      value: Math.max(baseSkill - 13, 0),
      className: "orange",
    },
    {
      name: "Computer Networks",
      value: Math.max(baseSkill - 17, 0),
      className: "pink",
    },
    {
      name: "HR & Communication",
      value: Math.min(baseSkill + 4, 100),
      className: "green",
    },
  ]

  // ============================================================
  // HELPERS
  // ============================================================

  function formatDate(dateString: string) {
    const date = new Date(dateString)

    if (Number.isNaN(date.getTime())) {
      return "-"
    }

    return date.toLocaleDateString(
      "en-IN",
      {
        day: "2-digit",
        month: "short",
        year: "numeric",
      },
    )
  }

  function startInterview() {
    navigate("/interview-setup")
  }

  function openInterview(id: string) {
    navigate(`/interview/${id}`)
  }

  function logout() {
    localStorage.removeItem("access_token")
    navigate("/login")
  }

  // ============================================================
  // LOADING
  // ============================================================

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="loader-orb" />

        <span>
          Loading your interview intelligence...
        </span>
      </div>
    )
  }

  // ============================================================
  // UI
  // ============================================================

  return (
    <div className="dashboard-shell">

      {/* ======================================================
          ULTRA ACTIVITY ANIMATION STYLES
          ====================================================== */}

      <style>{`

        .ultra-activity {
          position: relative;
          overflow: hidden;
          min-height: 330px;
          padding: 26px;
          border-radius: 20px;
          border: 1px solid rgba(140, 90, 255, 0.22);
          background:
            radial-gradient(
              circle at 85% 15%,
              rgba(112, 62, 255, 0.18),
              transparent 32%
            ),
            radial-gradient(
              circle at 15% 90%,
              rgba(24, 211, 255, 0.10),
              transparent 30%
            ),
            linear-gradient(
              135deg,
              #0c1020,
              #080b15
            );
          box-shadow:
            0 25px 70px rgba(0,0,0,.28),
            inset 0 1px 0 rgba(255,255,255,.045);
          transition:
            transform .45s ease,
            border-color .45s ease,
            box-shadow .45s ease;
        }

        .ultra-activity:hover {
          transform: translateY(-6px);
          border-color: rgba(148, 92, 255, .5);
          box-shadow:
            0 35px 90px rgba(79, 42, 190, .24),
            inset 0 1px 0 rgba(255,255,255,.06);
        }

        .activity-grid {
          position: absolute;
          inset: 0;
          pointer-events: none;
          opacity: .22;
          background-image:
            linear-gradient(
              rgba(140,100,255,.07) 1px,
              transparent 1px
            ),
            linear-gradient(
              90deg,
              rgba(140,100,255,.07) 1px,
              transparent 1px
            );
          background-size: 34px 34px;
          animation: activityGridMove 12s linear infinite;
          mask-image:
            linear-gradient(
              to bottom,
              black,
              transparent
            );
        }

        @keyframes activityGridMove {
          from {
            transform: translateY(0);
          }
          to {
            transform: translateY(34px);
          }
        }

        .activity-orb {
          position: absolute;
          width: 190px;
          height: 190px;
          border-radius: 50%;
          filter: blur(70px);
          pointer-events: none;
          opacity: .22;
          animation: activityOrb 7s ease-in-out infinite;
        }

        .activity-orb.one {
          top: -100px;
          right: 20%;
          background: #743cff;
        }

        .activity-orb.two {
          bottom: -110px;
          left: 18%;
          background: #1bcfff;
          animation-delay: -3s;
        }

        @keyframes activityOrb {
          0%,100% {
            transform: translate(0,0) scale(1);
          }
          50% {
            transform: translate(35px,-20px) scale(1.16);
          }
        }

        .activity-content {
          position: relative;
          z-index: 3;
        }

        .activity-top {
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .activity-heading {
          display: flex;
          align-items: center;
          gap: 13px;
        }

        .activity-icon {
          width: 42px;
          height: 42px;
          display: grid;
          place-items: center;
          border-radius: 12px;
          color: #ad82ff;
          font-size: 18px;
          background: rgba(122,73,255,.12);
          border: 1px solid rgba(140,85,255,.25);
          box-shadow:
            0 0 0 rgba(128,70,255,0);
          animation: activityIconPulse 2.5s ease-in-out infinite;
        }

        @keyframes activityIconPulse {
          50% {
            box-shadow:
              0 0 30px rgba(126,70,255,.28);
          }
        }

        .activity-heading small {
          display: block;
          color: #6d7183;
          font-size: 8px;
          font-weight: 800;
          letter-spacing: .16em;
        }

        .activity-heading h2 {
          margin: 5px 0 0;
          color: #f0f1f7;
          font-size: 18px;
          font-weight: 650;
        }

        .activity-live {
          display: flex;
          align-items: center;
          gap: 7px;
          padding: 6px 10px;
          border-radius: 8px;
          color: #45e88d;
          font-size: 8px;
          font-weight: 850;
          letter-spacing: .13em;
          background: rgba(38,220,130,.07);
        }

        .activity-live-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: #42e98a;
          box-shadow: 0 0 12px #42e98a;
          animation: liveDot 1.4s ease-in-out infinite;
        }

        @keyframes liveDot {
          50% {
            transform: scale(.55);
            opacity: .35;
          }
        }

        .activity-main {
          display: grid;
          grid-template-columns: 220px 1fr;
          align-items: center;
          gap: 30px;
          margin-top: 28px;
        }

        .activity-label {
          color: #666d7d;
          font-size: 8px;
          font-weight: 800;
          letter-spacing: .14em;
        }

        .activity-number {
          display: block;
          margin-top: 5px;
          color: #fff;
          font-size: 60px;
          line-height: .95;
          letter-spacing: -.07em;
          background:
            linear-gradient(
              120deg,
              #fff,
              #a87aff
            );
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          animation: numberGlow 3s ease-in-out infinite;
        }

        @keyframes numberGlow {
          50% {
            filter: drop-shadow(
              0 0 14px rgba(150,100,255,.3)
            );
          }
        }

        .activity-subtitle {
          margin: 8px 0 0;
          color: #656d7b;
          font-size: 10px;
        }

        .activity-wave {
          position: relative;
          height: 135px;
          border-bottom:
            1px solid rgba(255,255,255,.06);
        }

        .activity-wave svg {
          width: 100%;
          height: 100%;
          overflow: visible;
        }

        .activity-wave-line {
          fill: none;
          stroke: url(#activityWaveGradient);
          stroke-width: 3;
          stroke-linecap: round;
          stroke-linejoin: round;
          stroke-dasharray: 900;
          stroke-dashoffset: 900;
          animation:
            drawActivityWave 2.6s ease forwards,
            waveFloat 5s ease-in-out 2.6s infinite;
        }

        .activity-wave-glow {
          fill: none;
          stroke: url(#activityWaveGradient);
          stroke-width: 9;
          stroke-linecap: round;
          opacity: .17;
          filter: blur(3px);
        }

        @keyframes drawActivityWave {
          to {
            stroke-dashoffset: 0;
          }
        }

        @keyframes waveFloat {
          50% {
            transform: translateY(-5px);
          }
        }

        .activity-pulse {
          position: absolute;
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #a878ff;
          box-shadow:
            0 0 18px rgba(168,120,255,.95);
          animation:
            activityPulse 2s ease-in-out infinite;
        }

        .activity-pulse.p1 {
          left: 31%;
          top: 34%;
        }

        .activity-pulse.p2 {
          left: 68%;
          top: 31%;
          animation-delay: .6s;
        }

        .activity-pulse.p3 {
          right: 4%;
          top: 48%;
          animation-delay: 1.1s;
        }

        @keyframes activityPulse {
          0%,100% {
            transform: scale(.65);
            opacity: .5;
          }
          50% {
            transform: scale(1.4);
            opacity: 1;
          }
        }

        .activity-stats {
          display: grid;
          grid-template-columns:
            repeat(4,1fr);
          margin-top: 24px;
          padding-top: 19px;
          border-top:
            1px solid rgba(255,255,255,.06);
        }

        .activity-stat {
          padding: 0 18px;
          border-right:
            1px solid rgba(255,255,255,.06);
        }

        .activity-stat:first-child {
          padding-left: 0;
        }

        .activity-stat:last-child {
          border-right: 0;
        }

        .activity-stat-label {
          color: #606979;
          font-size: 8px;
          font-weight: 800;
          letter-spacing: .12em;
        }

        .activity-stat-value {
          display: block;
          margin-top: 6px;
          color: #e8eaf0;
          font-size: 18px;
          font-weight: 700;
        }

        .activity-stat-sub {
          display: block;
          margin-top: 3px;
          color: #59616f;
          font-size: 9px;
        }

        .activity-stat-live {
          color: #42df88;
        }

        .activity-footer {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-top: 20px;
          color: #464d5b;
          font-size: 7px;
          font-weight: 800;
          letter-spacing: .14em;
        }

        .activity-bars {
          display: flex;
          align-items: center;
          gap: 3px;
          height: 14px;
        }

        .activity-bars span {
          width: 2px;
          border-radius: 2px;
          background: #7551df;
          animation: activityBars 1s ease-in-out infinite;
        }

        .activity-bars span:nth-child(1) {
          height: 5px;
        }

        .activity-bars span:nth-child(2) {
          height: 10px;
          animation-delay: .15s;
        }

        .activity-bars span:nth-child(3) {
          height: 14px;
          animation-delay: .3s;
        }

        .activity-bars span:nth-child(4) {
          height: 8px;
          animation-delay: .45s;
        }

        .activity-bars span:nth-child(5) {
          height: 12px;
          animation-delay: .6s;
        }

        .activity-bars span:nth-child(6) {
          height: 6px;
          animation-delay: .75s;
        }

        .activity-bars span:nth-child(7) {
          height: 11px;
          animation-delay: .9s;
        }

        @keyframes activityBars {
          50% {
            transform: scaleY(.45);
            opacity: .45;
          }
        }

        @media (max-width: 900px) {
          .activity-main {
            grid-template-columns: 1fr;
            gap: 18px;
          }

          .activity-number {
            font-size: 46px;
          }
        }

        @media (max-width: 650px) {
          .ultra-activity {
            padding: 20px;
          }

          .activity-live {
            display: none;
          }

          .activity-stats {
            grid-template-columns: 1fr 1fr;
            gap: 18px;
          }

          .activity-stat {
            padding: 0;
            border-right: 0;
          }
        }

      `}</style>

      {/* ======================================================
          SIDEBAR
          ====================================================== */}

      <aside
        className={`dashboard-sidebar ${
          mobileMenu ? "mobile-open" : ""
        }`}
      >

        <div className="sidebar-brand">

          <div className="brand-logo">
            <span>AI</span>
          </div>

          <div className="brand-name">
            <strong>AI Interview</strong>
            <span>Platform</span>
          </div>

          <button
            className="collapse-button"
            onClick={() =>
              setMobileMenu(false)
            }
          >
            ‹
          </button>

        </div>


        <nav className="sidebar-menu">

          <button className="sidebar-link active">
            <span className="nav-icon">
              ▦
            </span>
            <span>
              Dashboard
            </span>
          </button>


          <button
            className="sidebar-link"
            onClick={() =>
              navigate("/resume")
            }
          >
            <span className="nav-icon">
              ▤
            </span>

            <span>
              Resume Analyzer
            </span>
          </button>


          <button
            className="sidebar-link"
            onClick={startInterview}
          >
            <span className="nav-icon">
              ♙
            </span>

            <span>
              AI Interview
            </span>

            <span className="nav-chevron">
              ⌄
            </span>
          </button>


          <button
            className="sidebar-link"
            onClick={startInterview}
          >
            <span className="nav-icon">
              &lt;/&gt;
            </span>

            <span>
              Coding Interview
            </span>
          </button>


          <button
            className="sidebar-link"
            onClick={startInterview}
          >
            <span className="nav-icon">
              ▣
            </span>

            <span>
              Mock Interviews
            </span>
          </button>


          <button className="sidebar-link">
            <span className="nav-icon">
              ▥
            </span>

            <span>
              Performance
            </span>
          </button>


          <button className="sidebar-link">
            <span className="nav-icon">
              ▢
            </span>

            <span>
              Learning Roadmap
            </span>
          </button>


          <button className="sidebar-link">
            <span className="nav-icon">
              ?
            </span>

            <span>
              Question Bank
            </span>
          </button>


          <button className="sidebar-link">
            <span className="nav-icon">
              ⌁
            </span>

            <span>
              Progress
            </span>
          </button>


          <button className="sidebar-link">
            <span className="nav-icon">
              ◉
            </span>

            <span>
              Analytics
            </span>
          </button>


          <button className="sidebar-link">
            <span className="nav-icon">
              ⚙
            </span>

            <span>
              Settings
            </span>
          </button>

        </nav>


        {/* PRACTICE CARD */}

        <div className="practice-card">

          <div className="practice-stars">
            ✦
          </div>

          <div className="practice-trophy">
            ♛
          </div>

          <h3>
            Keep Practicing!
          </h3>

          <p>
            You are on the right track.
            Practice more to achieve your goals.
          </p>

          <button onClick={startInterview}>
            View Roadmap
            <span>→</span>
          </button>

        </div>

      </aside>


      {/* ======================================================
          MAIN
          ====================================================== */}

      <main className="dashboard-main">

        {/* TOP BAR */}

        <header className="dashboard-header">

          <button
            className="mobile-menu-button"
            onClick={() =>
              setMobileMenu(!mobileMenu)
            }
          >
            ☰
          </button>


          <div className="search-container">

            <span className="search-icon">
              ⌕
            </span>

            <input
              placeholder="Search anything..."
            />

            <kbd>
              ⌘ K
            </kbd>

          </div>


          <div className="header-right">

            <button className="notification">
              ♧

              <span>
                {Math.min(
                  interviews.length,
                  9,
                )}
              </span>
            </button>


            <div className="header-profile">

              <div className="profile-avatar">
                {user?.full_name
                  ?.charAt(0)
                  .toUpperCase() ||
                  "G"}
              </div>


              <div className="profile-details">

                <strong>
                  {user?.full_name ||
                    "Gourab"}
                </strong>

                <span>
                  Premium Plan
                </span>

              </div>


              <button
                className="profile-dropdown"
                onClick={logout}
                title="Logout"
              >
                ⌄
              </button>

            </div>

          </div>

        </header>


        {/* ======================================================
            CONTENT
            ====================================================== */}

        <div className="dashboard-content">

          {/* WELCOME */}

          <section className="welcome">

            <h1>
              Welcome back,{" "}
              {user?.full_name ||
                "Gourab"}!{" "}
              <span>
                👋
              </span>
            </h1>

            <p>
              Ready to ace your next interview?
              Let's continue your preparation journey.
            </p>

          </section>


          {/* ====================================================
              STAT CARDS
              ==================================================== */}

          <section className="stats-row">

            <div className="stat-card purple-card">

              <div className="stat-icon">
                ♙
              </div>

              <div>

                <span>
                  Interviews Taken
                </span>

                <strong>
                  {interviews.length}
                </strong>

                <small>
                  ↑ Total interviews
                </small>

              </div>

            </div>


            <div className="stat-card blue-card">

              <div className="stat-icon">
                ◎
              </div>

              <div>

                <span>
                  Average Score
                </span>

                <strong>
                  {averageScore.toFixed(1)}%
                </strong>

                <small>
                  ↑ Based on completed
                </small>

              </div>

            </div>


            <div className="stat-card cyan-card">

              <div className="stat-icon">
                &lt;/&gt;
              </div>

              <div>

                <span>
                  Coding Score
                </span>

                <strong>
                  {completedInterviews.length
                    ? `${averageScore.toFixed(1)}%`
                    : "—"}
                </strong>

                <small>
                  Interview performance
                </small>

              </div>

            </div>


            <div className="stat-card orange-card">

              <div className="stat-icon">
                ♟
              </div>

              <div>

                <span>
                  HR Score
                </span>

                <strong>
                  {completedInterviews.length
                    ? `${Math.min(
                        averageScore + 3,
                        100,
                      ).toFixed(1)}%`
                    : "—"}
                </strong>

                <small>
                  Communication estimate
                </small>

              </div>

            </div>


            <div className="stat-card pink-card">

              <div className="stat-icon">
                ◷
              </div>

              <div>

                <span>
                  Total Practice Time
                </span>

                <strong>
                  {completedInterviews.length
                    ? `${completedInterviews.length}h`
                    : "—"}
                </strong>

                <small>
                  Based on completed sessions
                </small>

              </div>

            </div>

          </section>


          {/* ====================================================
              FIRST GRID
              ==================================================== */}

          <section className="main-grid">

            {/* PERFORMANCE */}

            <div className="panel performance-panel">

              <div className="panel-header">

                <div>

                  <h2>
                    Performance Overview
                  </h2>

                  <p>
                    Your interview score trajectory
                  </p>

                </div>

                <button className="small-select">
                  Last 7 Days
                  <span>
                    ⌄
                  </span>
                </button>

              </div>


              <div className="chart-wrapper">

                <div className="chart-y-axis">

                  <span>100</span>
                  <span>75</span>
                  <span>50</span>
                  <span>25</span>
                  <span>0</span>

                </div>


                <div className="chart-area">

                  <div className="chart-lines">
                    <i />
                    <i />
                    <i />
                    <i />
                    <i />
                    <i />
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

                        <stop
                          offset="0%"
                          stopColor="#9d4edd"
                          stopOpacity="0.42"
                        />

                        <stop
                          offset="100%"
                          stopColor="#5b21b6"
                          stopOpacity="0"
                        />

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


                    {performanceInterviews.map(
                      (item, index) => {

                        const x =
                          performanceInterviews.length === 1
                            ? 225
                            : (index /
                                (performanceInterviews.length -
                                  1)) *
                              450

                        const y =
                          150 -
                          (item.score ?? 0) *
                            1.25

                        return (
                          <circle
                            key={item.id}
                            cx={x}
                            cy={Math.max(5, y)}
                            r="4"
                            fill="#9d4edd"
                            stroke="#fff"
                            strokeWidth="2"
                          />
                        )
                      },
                    )}

                  </svg>


                  <div className="chart-x-axis">

                    {performanceInterviews.length
                      ? performanceInterviews.map(
                          (item) => (
                            <span
                              key={item.id}
                            >
                              {new Date(
                                item.created_at,
                              ).toLocaleDateString(
                                "en-IN",
                                {
                                  month: "short",
                                  day: "numeric",
                                },
                              )}
                            </span>
                          ),
                        )
                      : (
                        <>
                          <span>
                            Start
                          </span>

                          <span>
                            Practice
                          </span>

                          <span>
                            Improve
                          </span>

                          <span>
                            Master
                          </span>
                        </>
                      )}

                  </div>

                </div>

              </div>

            </div>


            {/* RADAR */}

            <div className="panel radar-panel">

              <div className="panel-header">

                <div>

                  <h2>
                    Skill Radar
                  </h2>

                  <p>
                    Your current skill profile
                  </p>

                </div>

              </div>


              <div className="radar-wrapper">

                <svg
                  viewBox="0 0 300 250"
                  className="radar-svg"
                >

                  <polygon
                    points="150,25 270,95 225,225 75,225 30,95"
                    fill="none"
                    stroke="#29334d"
                  />

                  <polygon
                    points="150,55 235,105 205,190 95,190 65,105"
                    fill="none"
                    stroke="#29334d"
                  />

                  <polygon
                    points="150,85 200,115 185,155 115,155 100,115"
                    fill="none"
                    stroke="#29334d"
                  />

                  <line
                    x1="150"
                    y1="25"
                    x2="150"
                    y2="225"
                    stroke="#29334d"
                  />

                  <line
                    x1="30"
                    y1="95"
                    x2="225"
                    y2="225"
                    stroke="#29334d"
                  />

                  <line
                    x1="270"
                    y1="95"
                    x2="75"
                    y2="225"
                    stroke="#29334d"
                  />

                  <polygon
                    points={`
                      150,${225 - skills[0].value * 2}
                      ${150 + skills[1].value * 1.2},${95 + (100 - skills[1].value) * 0.25}
                      ${225 - (100 - skills[2].value) * 0.35},${225 - skills[2].value * 0.15}
                      150,${225 - skills[3].value * 1.1}
                      ${75 + (100 - skills[4].value) * 0.35},${225 - skills[4].value * 0.15}
                      ${30 + skills[5].value * 1.2},${95 + (100 - skills[5].value) * 0.25}
                    `}
                    fill="#8b5cf6"
                    fillOpacity="0.35"
                    stroke="#b14cff"
                    strokeWidth="2"
                  />

                </svg>


                <span className="radar-text radar-top">
                  DSA
                </span>

                <span className="radar-text radar-right-top">
                  System Design
                </span>

                <span className="radar-text radar-right-bottom">
                  DBMS
                </span>

                <span className="radar-text radar-bottom">
                  HR
                </span>

                <span className="radar-text radar-left-bottom">
                  OS
                </span>

                <span className="radar-text radar-left-top">
                  CN
                </span>

              </div>

            </div>


            {/* UPCOMING INTERVIEW */}

            <div className="panel upcoming-panel">

              <div className="panel-header">

                <div>

                  <h2>
                    Upcoming Interview
                  </h2>

                </div>

                <button
                  onClick={startInterview}
                >
                  View All
                </button>

              </div>


              <div className="upcoming-box">

                <div className="company-logo microsoft">
                  <span />
                  <span />
                  <span />
                  <span />
                </div>


                <div className="upcoming-company">

                  <strong>
                    AI Mock Interview
                  </strong>

                  <span>
                    {activeInterviews.length
                      ? `${activeInterviews[0].job_role} • ${activeInterviews[0].difficulty}`
                      : interviews.length
                        ? `${interviews[0].job_role} • ${interviews[0].difficulty}`
                        : "Ready for your next challenge"}
                  </span>

                </div>


                <div className="upcoming-meta">

                  <span>
                    ▣ Flexible
                  </span>

                  <span>
                    ◷ AI Powered
                  </span>

                </div>


                <button
                  className="start-button"
                  onClick={startInterview}
                >
                  Start Interview
                  <span>
                    →
                  </span>
                </button>

              </div>

            </div>

          </section>


          {/* ====================================================
              ULTRA ANIMATED INTERVIEW ACTIVITY
              ==================================================== */}

          <section className="ultra-activity">

            <div className="activity-grid" />

            <div className="activity-orb one" />
            <div className="activity-orb two" />


            <div className="activity-content">

              {/* HEADER */}

              <div className="activity-top">

                <div className="activity-heading">

                  <div className="activity-icon">
                    ◉
                  </div>

                  <div>

                    <small>
                      INTERVIEW ACTIVITY
                    </small>

                    <h2>
                      Your latest interview activity
                    </h2>

                  </div>

                </div>


                <div className="activity-live">

                  <i className="activity-live-dot" />

                  LIVE

                </div>

              </div>


              {/* MAIN */}

              <div className="activity-main">

                <div>

                  <span className="activity-label">
                    INTERVIEWS COMPLETED
                  </span>

                  <strong className="activity-number">
                    {completedInterviews.length}
                  </strong>

                  <p className="activity-subtitle">
                    AI mock interviews completed
                  </p>

                </div>


                {/* WAVE */}

                <div className="activity-wave">

                  <svg
                    viewBox="0 0 600 150"
                    preserveAspectRatio="none"
                  >

                    <defs>

                      <linearGradient
                        id="activityWaveGradient"
                        x1="0%"
                        y1="0%"
                        x2="100%"
                        y2="0%"
                      >

                        <stop
                          offset="0%"
                          stopColor="#713cff"
                        />

                        <stop
                          offset="50%"
                          stopColor="#a855f7"
                        />

                        <stop
                          offset="100%"
                          stopColor="#22d3ee"
                        />

                      </linearGradient>

                    </defs>


                    <path
                      className="activity-wave-glow"
                      d="
                        M0 110
                        C30 110 35 75 65 75
                        C95 75 100 125 130 125
                        C160 125 165 50 200 50
                        C235 50 235 105 270 105
                        C305 105 310 70 345 70
                        C380 70 385 120 420 120
                        C455 120 460 45 495 45
                        C530 45 535 90 565 90
                        C580 90 590 75 600 75
                      "
                    />


                    <path
                      className="activity-wave-line"
                      d="
                        M0 110
                        C30 110 35 75 65 75
                        C95 75 100 125 130 125
                        C160 125 165 50 200 50
                        C235 50 235 105 270 105
                        C305 105 310 70 345 70
                        C380 70 385 120 420 120
                        C455 120 460 45 495 45
                        C530 45 535 90 565 90
                        C580 90 590 75 600 75
                      "
                    />

                  </svg>


                  <i className="activity-pulse p1" />
                  <i className="activity-pulse p2" />
                  <i className="activity-pulse p3" />

                </div>

              </div>


              {/* STATS */}

              <div className="activity-stats">

                <div className="activity-stat">

                  <span className="activity-stat-label">
                    AVG SCORE
                  </span>

                  <strong className="activity-stat-value">
                    {averageScore.toFixed(1)}%
                  </strong>

                  <small className="activity-stat-sub">
                    Overall performance
                  </small>

                </div>


                <div className="activity-stat">

                  <span className="activity-stat-label">
                    BEST SCORE
                  </span>

                  <strong className="activity-stat-value">
                    {bestScore.toFixed(0)}%
                  </strong>

                  <small className="activity-stat-sub">
                    Personal best
                  </small>

                </div>


                <div className="activity-stat">

                  <span className="activity-stat-label">
                    TODAY
                  </span>

                  <strong className="activity-stat-value">
                    {todayCount}
                  </strong>

                  <small className="activity-stat-sub">
                    Interviews today
                  </small>

                </div>


                <div className="activity-stat">

                  <span className="activity-stat-label">
                    STATUS
                  </span>

                  <strong className="activity-stat-value activity-stat-live">
                    {activeInterviews.length
                      ? "ACTIVE"
                      : "READY"}
                  </strong>

                  <small className="activity-stat-sub">
                    Keep practicing
                  </small>

                </div>

              </div>


              {/* FOOTER */}

              <div className="activity-footer">

                <span>
                  AI PERFORMANCE ENGINE
                </span>


                <div className="activity-bars">

                  <span />
                  <span />
                  <span />
                  <span />
                  <span />
                  <span />
                  <span />

                </div>


                <span>
                  REAL-TIME
                </span>

              </div>

            </div>

          </section>


          {/* ====================================================
              RECENT INTERVIEW TIMELINE
              ==================================================== */}

          <section className="secondary-grid">

            <div className="panel recent-panel">

              <div className="panel-header">

                <div>

                  <h2>
                    Recent Sessions
                  </h2>

                  <p>
                    Your latest interview sessions
                  </p>

                </div>

                <button
                  onClick={startInterview}
                >
                  New Interview
                </button>

              </div>


              {recentInterviews.length === 0 ? (

                <div className="empty-state">

                  <div className="empty-icon">
                    ♙
                  </div>

                  <h3>
                    No interviews yet
                  </h3>

                  <p>
                    Start your first AI interview
                    to see your activity here.
                  </p>

                  <button
                    onClick={startInterview}
                  >
                    Start Interview →
                  </button>

                </div>

              ) : (

                <div className="recent-list">

                  {recentInterviews.map(
                    (interview) => {

                      const score =
                        interview.score ?? 0

                      return (

                        <div
                          className="recent-row"
                          key={interview.id}
                        >

                          <div className="recent-company-logo">
                            AI
                          </div>


                          <div className="recent-company-info">

                            <strong>
                              {interview.job_role ||
                                "AI Interview"}
                            </strong>

                            <span>
                              {interview.difficulty ||
                                "Standard"}{" "}
                              Interview
                            </span>

                          </div>


                          <span
                            className={`status-badge ${
                              interview.status?.toLowerCase() !==
                              "completed"
                                ? "status-progress"
                                : ""
                            }`}
                          >
                            {interview.status}
                          </span>


                          <div
                            className={`score-ring ${
                              score >= 80
                                ? "score-good"
                                : score >= 60
                                  ? "score-medium"
                                  : "score-low"
                            }`}
                          >
                            {score}%
                          </div>


                          <div className="recent-date">

                            <strong>
                              {formatDate(
                                interview.created_at,
                              )}
                            </strong>

                            <span>
                              {interview.completed_at
                                ? "Completed"
                                : "Session"}
                            </span>

                          </div>


                          <button
                            className="recent-arrow"
                            type="button"
                            onClick={() =>
                              openInterview(
                                interview.id,
                              )
                            }
                          >
                            →
                          </button>

                        </div>

                      )

                    },
                  )}

                </div>

              )}

            </div>


            {/* SKILL BREAKDOWN */}

            <div className="panel skills-panel">

              <div className="panel-header">

                <div>

                  <h2>
                    Skill Breakdown
                  </h2>

                  <p>
                    Based on your current performance
                  </p>

                </div>

                <button>
                  View All
                </button>

              </div>


              <div className="skills-list">

                {skills.map((skill) => (

                  <div
                    className="skill-row"
                    key={skill.name}
                  >

                    <div className="skill-heading">

                      <span>
                        {skill.name}
                      </span>

                      <strong>
                        {skill.value}%
                      </strong>

                    </div>


                    <div className="skill-track">

                      <div
                        className={`skill-fill ${skill.className}`}
                        style={{
                          width:
                            `${skill.value}%`,
                        }}
                      />

                    </div>

                  </div>

                ))}

              </div>

            </div>


            {/* DAILY GOAL */}

            <div className="panel daily-panel">

              <div className="panel-header">

                <h2>
                  Daily Goal
                </h2>

              </div>


              <div className="daily-content">

                <div
                  className="goal-ring"
                  style={{
                    background:
                      `conic-gradient(
                        #34d399 ${dailyPercentage * 3.6}deg,
                        #172139 ${dailyPercentage * 3.6}deg
                      )`,
                  }}
                >

                  <div>

                    <strong>
                      {dailyPercentage}%
                    </strong>

                  </div>

                </div>


                <div className="daily-stats">

                  <div>

                    <strong>
                      {todayCount}/4
                    </strong>

                    <span>
                      Interviews Completed
                    </span>

                  </div>


                  <div>

                    <strong>
                      {completedInterviews.length} total
                    </strong>

                    <span>
                      Completed Interviews
                    </span>


                    <div className="mini-track">

                      <div
                        style={{
                          width:
                            `${Math.min(
                              completedInterviews.length *
                                10,
                              100,
                            )}%`,
                        }}
                      />

                    </div>

                  </div>

                </div>

              </div>

            </div>

          </section>


          {/* ====================================================
              LOWER WIDGETS
              ==================================================== */}

          <section className="widgets-grid">

            {/* AI MENTOR */}

            <div className="panel mentor-panel">

              <div className="panel-header">

                <h2>
                  AI Mentor
                </h2>

                <span className="online-status">

                  <i />

                  Online

                </span>

              </div>


              <div className="mentor-content">

                <div className="mentor-robot">

                  <div className="robot-antenna" />

                  <div className="robot-head">

                    <div className="robot-eye" />
                    <div className="robot-eye" />

                  </div>


                  <div className="robot-body">

                    <div className="robot-core" />

                  </div>

                </div>


                <div className="mentor-message">

                  <p>

                    Hi{" "}
                    {user?.full_name?.split(
                      " ",
                    )[0] ||
                      "Gourab"}{" "}
                    👋

                    <br />

                    I'm here to help you improve
                    your interview skills.

                  </p>

                </div>

              </div>


              <button className="mentor-button">

                Chat with AI Mentor

                <span>
                  →
                </span>

              </button>

            </div>


            {/* ACHIEVEMENTS */}

            <div className="panel achievements-panel">

              <div className="panel-header">

                <h2>
                  Achievements
                </h2>

                <button>
                  View All
                </button>

              </div>


              <div className="achievement-list">

                <div className="achievement">

                  <div className="achievement-icon purple">
                    ★
                  </div>

                  <strong>
                    Consistent
                  </strong>

                  <span>
                    {Math.min(
                      interviews.length,
                      7,
                    )} Days
                  </span>

                </div>


                <div className="achievement">

                  <div className="achievement-icon blue">
                    &lt;/&gt;
                  </div>

                  <strong>
                    Code Master
                  </strong>

                  <span>
                    {completedInterviews.length}
                    {" "}
                    Problems
                  </span>

                </div>


                <div className="achievement">

                  <div className="achievement-icon green">
                    ★
                  </div>

                  <strong>
                    Top Performer
                  </strong>

                  <span>
                    Score {bestScore.toFixed(0)}+
                  </span>

                </div>


                <div className="achievement">

                  <div className="achievement-icon gold">
                    ♛
                  </div>

                  <strong>
                    Interview Pro
                  </strong>

                  <span>
                    {completedInterviews.length}/20
                  </span>

                </div>

              </div>

            </div>

          </section>


          {/* ====================================================
              PREMIUM BANNER
              ==================================================== */}

          <section className="premium-banner">

            <div className="premium-visual">

              <div className="rocket">
                🚀
              </div>

              <div className="rocket-glow" />

            </div>


            <div className="premium-copy">

              <h2>
                Unlock Your Full Potential! 🚀
              </h2>

              <p>
                Upgrade to Premium for unlimited
                interviews, advanced analytics,
                and personalized mentoring.
              </p>

              <button>

                Upgrade Now

                <span>
                  →
                </span>

              </button>

            </div>


            <div className="premium-features">

              <div>

                <strong>
                  ∞
                </strong>

                <span>
                  Unlimited
                  <br />
                  Interviews
                </span>

              </div>


              <div>

                <strong>
                  ▥
                </strong>

                <span>
                  Advanced
                  <br />
                  Analytics
                </span>

              </div>


              <div>

                <strong>
                  ♧
                </strong>

                <span>
                  Personalized
                  <br />
                  Roadmap
                </span>

              </div>


              <div>

                <strong>
                  ♡
                </strong>

                <span>
                  Priority
                  <br />
                  Support
                </span>

              </div>

            </div>

          </section>

        </div>

      </main>

    </div>
  )
}

export default Dashboard