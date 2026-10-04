import { useCallback, useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  getComprehensiveProfile,
  updateComprehensiveProfile,
  type ComprehensiveProfileResponse,
  type ProfileUpdateRequest,
} from "../services/api"
import "./Profile.css"

export default function Profile() {
  const navigate = useNavigate()

  // Layout states
  const [mobileMenu, setMobileMenu] = useState(false)
  const [data, setData] = useState<ComprehensiveProfileResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  // Edit Profile modal state
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [editForm, setEditForm] = useState<ProfileUpdateRequest>({})
  const [formErrors, setFormErrors] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [saveError, setSaveError] = useState("")

  // ------------------------------------------------------------
  // LOAD REAL DATA FROM BACKEND
  // ------------------------------------------------------------
  const fetchProfile = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const response = await getComprehensiveProfile()
      setData(response)
    } catch (err: unknown) {
      console.error("Failed to load profile:", err)
      setError("Couldn't load your profile. Please check your network and try again.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void fetchProfile()
  }, [fetchProfile])

  // ------------------------------------------------------------
  // MODAL HANDLERS
  // ------------------------------------------------------------
  const openEditModal = () => {
    if (!data) return
    const p = data.profile
    setEditForm({
      full_name: p.full_name || "",
      headline: p.headline || "",
      bio: p.bio || "",
      target_role: p.target_role || "",
      experience_level: p.experience_level || "",
      college: p.college || "",
      degree: p.degree || "",
      graduation_year: p.graduation_year || undefined,
      location: p.location || "",
      phone: p.phone || "",
      github_url: p.github_url || "",
      linkedin_url: p.linkedin_url || "",
      portfolio_url: p.portfolio_url || "",
      avatar_url: p.avatar_url || "",
    })
    setFormErrors({})
    setSaveError("")
    setSaveSuccess(false)
    setIsEditModalOpen(true)
  }

  const closeEditModal = () => {
    if (saving) return
    setIsEditModalOpen(false)
  }

  // ------------------------------------------------------------
  // FORM VALIDATION & SUBMISSION
  // ------------------------------------------------------------
  const validateForm = (): boolean => {
    const errors: Record<string, string> = {}

    if (!editForm.full_name || !editForm.full_name.trim()) {
      errors.full_name = "Full name is required"
    } else if (editForm.full_name.trim().length > 100) {
      errors.full_name = "Full name cannot exceed 100 characters"
    }

    if (editForm.headline && editForm.headline.length > 255) {
      errors.headline = "Headline cannot exceed 255 characters"
    }

    if (editForm.bio && editForm.bio.length > 1000) {
      errors.bio = "Bio cannot exceed 1000 characters"
    }

    if (editForm.graduation_year !== undefined && editForm.graduation_year !== null) {
      const year = Number(editForm.graduation_year)
      if (isNaN(year) || year < 1970 || year > 2040) {
        errors.graduation_year = "Graduation year must be between 1970 and 2040"
      }
    }

    const urlFields: Array<keyof ProfileUpdateRequest> = [
      "github_url",
      "linkedin_url",
      "portfolio_url",
      "avatar_url",
    ]

    const urlRegex = /^https?:\/\/[^\s/$.?#].[^\s]*$/i
    for (const key of urlFields) {
      const val = editForm[key]
      if (typeof val === "string" && val.trim()) {
        if (!val.startsWith("http://") && !val.startsWith("https://")) {
          errors[key] = "URL must start with http:// or https://"
        } else if (!urlRegex.test(val.trim())) {
          errors[key] = "Please enter a valid URL"
        }
      }
    }

    setFormErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validateForm()) return

    setSaving(true)
    setSaveError("")
    setSaveSuccess(false)

    try {
      const payload: ProfileUpdateRequest = {
        full_name: editForm.full_name?.trim() || undefined,
        headline: editForm.headline?.trim() || null,
        bio: editForm.bio?.trim() || null,
        target_role: editForm.target_role?.trim() || null,
        experience_level: editForm.experience_level?.trim() || null,
        college: editForm.college?.trim() || null,
        degree: editForm.degree?.trim() || null,
        graduation_year: editForm.graduation_year ? Number(editForm.graduation_year) : null,
        location: editForm.location?.trim() || null,
        phone: editForm.phone?.trim() || null,
        github_url: editForm.github_url?.trim() || null,
        linkedin_url: editForm.linkedin_url?.trim() || null,
        portfolio_url: editForm.portfolio_url?.trim() || null,
        avatar_url: editForm.avatar_url?.trim() || null,
      }

      const updated = await updateComprehensiveProfile(payload)
      setData(updated)
      setSaveSuccess(true)
      setTimeout(() => {
        setIsEditModalOpen(false)
        setSaveSuccess(false)
      }, 900)
    } catch (err: any) {
      console.error("Profile update failed:", err)
      setSaveError(err.message || "Failed to update profile. Please verify your inputs.")
    } finally {
      setSaving(false)
    }
  }

  // ------------------------------------------------------------
  // INITIALS AVATAR HELPER
  // ------------------------------------------------------------
  const getInitials = (name?: string): string => {
    if (!name) return "U"
    const parts = name.trim().split(" ")
    if (parts.length >= 2) {
      return `${parts[0].charAt(0)}${parts[1].charAt(0)}`.toUpperCase()
    }
    return name.slice(0, 2).toUpperCase()
  }

  // ------------------------------------------------------------
  // SKELETON LOADING
  // ------------------------------------------------------------
  if (loading && !data) {
    return (
      <div className="profile-shell">
        <aside className="profile-sidebar">
          <div className="profile-brand">
            <div className="brand-logo">AI</div>
            <div className="brand-name">
              <strong>AI Interview</strong>
              <span>Platform</span>
            </div>
          </div>
        </aside>
        <main className="profile-main">
          <div className="profile-skeleton-container">
            <div className="skeleton-hero" />
            <div className="skeleton-grid">
              <div className="skeleton-card" />
              <div className="skeleton-card" />
              <div className="skeleton-card" />
              <div className="skeleton-card" />
            </div>
          </div>
        </main>
      </div>
    )
  }

  // ------------------------------------------------------------
  // ERROR STATE
  // ------------------------------------------------------------
  if (error && !data) {
    return (
      <div className="profile-shell">
        <aside className="profile-sidebar">
          <div className="profile-brand">
            <div className="brand-logo">AI</div>
            <div className="brand-name">
              <strong>AI Interview</strong>
              <span>Platform</span>
            </div>
          </div>
        </aside>
        <main className="profile-main">
          <div className="profile-error-box">
            <div className="error-icon">⚠️</div>
            <h2>Couldn&apos;t load your profile</h2>
            <p>{error}</p>
            <button type="button" className="profile-btn-primary" onClick={fetchProfile}>
              Retry Connection
            </button>
          </div>
        </main>
      </div>
    )
  }

  const profile = data!.profile
  const account = data!.account
  const practice = data!.practice_summary
  const achievements = data!.achievement_summary
  const interview = data!.interview_summary
  const resume = data!.resume_status

  return (
    <div className="profile-shell">
      {/* ======================================================
          SIDEBAR NAVIGATION
      ====================================================== */}
      <aside className={`profile-sidebar ${mobileMenu ? "mobile-open" : ""}`}>
        <div className="profile-brand">
          <div className="brand-logo">AI</div>
          <div className="brand-name">
            <strong>AI Interview</strong>
            <span>Platform</span>
          </div>
          <button
            type="button"
            className="profile-collapse-btn"
            onClick={() => setMobileMenu(false)}
            aria-label="Close navigation menu"
          >
            ✕
          </button>
        </div>

        <nav className="profile-nav" aria-label="Main Navigation">
          <button
            type="button"
            className="profile-nav-link"
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
            className="profile-nav-link"
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
            className="profile-nav-link"
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
            className="profile-nav-link"
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
            className="profile-nav-link"
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
            className="profile-nav-link"
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
            className="profile-nav-link"
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
            className="profile-nav-link active"
            onClick={() => setMobileMenu(false)}
            aria-current="page"
          >
            <span className="nav-icon">👤</span>
            <span>Profile</span>
          </button>

          <button
            type="button"
            className="profile-nav-link"
            onClick={() => {
              setMobileMenu(false)
              navigate("/settings")
            }}
          >
            <span className="nav-icon">⚙</span>
            <span>Settings</span>
          </button>
        </nav>

        {/* SIDEBAR PRACTICE WIDGET */}
        <div className="profile-sidebar-widget">
          <div className="widget-header">
            <span className="widget-icon">⚡</span>
            <span>Level {practice.current_level}</span>
          </div>
          <p className="widget-title">{practice.level_title}</p>
          <div className="widget-progress-bar">
            <div
              className="widget-progress-fill"
              style={{ width: `${Math.min(100, Math.max(5, practice.progress_pct))}%` }}
            />
          </div>
          <span className="widget-xp">{practice.total_xp.toLocaleString()} XP earned</span>
        </div>
      </aside>

      {/* ======================================================
          MAIN PROFILE CONTENT
      ====================================================== */}
      <main className="profile-main">
        {/* TOP BAR */}
        <header className="profile-top-bar">
          <div className="top-bar-left">
            <button
              type="button"
              className="profile-mobile-toggle"
              onClick={() => setMobileMenu(true)}
              aria-label="Open navigation menu"
            >
              ☰
            </button>
            <button
              type="button"
              className="profile-back-btn"
              onClick={() => navigate("/dashboard")}
            >
              ← Back to Dashboard
            </button>
          </div>

          <div className="top-bar-right">
            <div className="profile-stat-pill xp-pill">
              <span>⚡ Level {practice.current_level}</span>
              <span>{practice.total_xp.toLocaleString()} XP</span>
            </div>
            {practice.current_streak > 0 && (
              <div className="profile-stat-pill streak-pill">
                <span>🔥 {practice.current_streak} Day Streak</span>
              </div>
            )}
          </div>
        </header>

        <div className="profile-content-scroll">
          {/* ==================================================
              1. PROFILE HERO SECTION
          ================================================== */}
          <section className="profile-hero-card" aria-label="Candidate Profile Header">
            <div className="hero-avatar-wrap">
              {profile.avatar_url ? (
                <img
                  src={profile.avatar_url}
                  alt={`${profile.full_name}'s avatar`}
                  className="hero-avatar-img"
                  onError={(e) => {
                    // Fallback to initials if image link breaks
                    e.currentTarget.style.display = "none"
                    const fallback = e.currentTarget.parentElement?.querySelector(
                      ".hero-avatar-fallback",
                    )
                    if (fallback) (fallback as HTMLElement).style.display = "flex"
                  }}
                />
              ) : null}
              <div
                className="hero-avatar-fallback"
                style={{ display: profile.avatar_url ? "none" : "flex" }}
              >
                {getInitials(profile.full_name)}
              </div>
            </div>

            <div className="hero-info">
              <div className="hero-name-row">
                <h1 className="hero-name">{profile.full_name}</h1>
                {account.is_verified && (
                  <span className="verified-badge" title="Verified Account">
                    ✓ Verified
                  </span>
                )}
              </div>

              <p className="hero-headline">
                {profile.headline || "Technical Candidate & Software Engineer"}
              </p>

              <div className="hero-meta-row">
                <span className="meta-item">
                  <span className="meta-icon">✉</span> {profile.email}
                </span>

                {profile.location && (
                  <span className="meta-item">
                    <span className="meta-icon">📍</span> {profile.location}
                  </span>
                )}

                {profile.target_role && (
                  <span className="meta-badge role-badge">
                    💼 {profile.target_role}
                  </span>
                )}

                {profile.experience_level && (
                  <span className="meta-badge level-badge">
                    ⭐ {profile.experience_level}
                  </span>
                )}
              </div>

              {/* SOCIAL / PORTFOLIO LINKS */}
              <div className="hero-social-row">
                {profile.github_url && (
                  <a
                    href={profile.github_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="social-chip"
                    aria-label="GitHub Profile"
                  >
                    <span className="chip-icon">⌥</span> GitHub
                  </a>
                )}
                {profile.linkedin_url && (
                  <a
                    href={profile.linkedin_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="social-chip"
                    aria-label="LinkedIn Profile"
                  >
                    <span className="chip-icon">in</span> LinkedIn
                  </a>
                )}
                {profile.portfolio_url && (
                  <a
                    href={profile.portfolio_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="social-chip"
                    aria-label="Portfolio Website"
                  >
                    <span className="chip-icon">🌐</span> Portfolio
                  </a>
                )}
                {!profile.github_url && !profile.linkedin_url && !profile.portfolio_url && (
                  <span className="social-hint">No public links added yet.</span>
                )}
              </div>
            </div>

            <div className="hero-actions">
              <button
                type="button"
                className="profile-btn-primary edit-btn"
                onClick={openEditModal}
                aria-label="Edit Profile Details"
              >
                <span>✎</span> Edit Profile
              </button>
            </div>
          </section>

          {/* ==================================================
              2. PROFILE SUMMARY & ACADEMIC INFO
          ================================================== */}
          <section className="profile-grid-two" aria-label="Profile Summary and Education">
            {/* ABOUT / BIO */}
            <div className="profile-glass-card">
              <div className="card-header-row">
                <div className="card-title-group">
                  <span className="card-header-icon">📝</span>
                  <h2>About &amp; Background</h2>
                </div>
              </div>
              <div className="card-body">
                {profile.bio ? (
                  <p className="bio-text">{profile.bio}</p>
                ) : (
                  <div className="empty-inline-state">
                    <p>No bio added yet. Add a brief technical summary to highlight your strengths.</p>
                    <button type="button" className="btn-link" onClick={openEditModal}>
                      + Add Bio
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* EDUCATION & DETAILS */}
            <div className="profile-glass-card">
              <div className="card-header-row">
                <div className="card-title-group">
                  <span className="card-header-icon">🎓</span>
                  <h2>Education &amp; Details</h2>
                </div>
              </div>
              <div className="card-body">
                <div className="info-keyval-grid">
                  <div className="keyval-item">
                    <span className="keyval-label">College / University</span>
                    <strong className="keyval-value">{profile.college || "Not specified"}</strong>
                  </div>
                  <div className="keyval-item">
                    <span className="keyval-label">Degree</span>
                    <strong className="keyval-value">{profile.degree || "Not specified"}</strong>
                  </div>
                  <div className="keyval-item">
                    <span className="keyval-label">Graduation Year</span>
                    <strong className="keyval-value">
                      {profile.graduation_year || "Not specified"}
                    </strong>
                  </div>
                  <div className="keyval-item">
                    <span className="keyval-label">Account Created</span>
                    <strong className="keyval-value">
                      {new Date(account.created_at).toLocaleDateString("en-US", {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                      })}
                    </strong>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* ==================================================
              3. PREPARATION & PROGRESS OVERVIEW
          ================================================== */}
          <section className="profile-section" aria-label="Preparation Overview">
            <div className="section-title-row">
              <div className="section-title-group">
                <span className="section-icon">⚡</span>
                <h2>Preparation Overview</h2>
              </div>
              <span className="section-subtitle">Real metrics backed by PostgreSQL data</span>
            </div>

            <div className="stats-five-grid">
              {/* Level & Rank */}
              <div className="stat-card">
                <div className="stat-card-icon level-glow">⚡</div>
                <div className="stat-card-data">
                  <span className="stat-label">Level &amp; Rank</span>
                  <strong className="stat-value">Level {practice.current_level}</strong>
                  <span className="stat-detail">{practice.level_title}</span>
                </div>
              </div>

              {/* Total XP */}
              <div className="stat-card">
                <div className="stat-card-icon xp-glow">✨</div>
                <div className="stat-card-data">
                  <span className="stat-label">Total Experience</span>
                  <strong className="stat-value">{practice.total_xp.toLocaleString()} XP</strong>
                  <div className="stat-progress-bar">
                    <div
                      className="stat-progress-fill"
                      style={{ width: `${Math.min(100, Math.max(5, practice.progress_pct))}%` }}
                    />
                  </div>
                  <span className="stat-detail">{practice.progress_pct}% to next level</span>
                </div>
              </div>

              {/* Practice Streak */}
              <div className="stat-card">
                <div className="stat-card-icon streak-glow">🔥</div>
                <div className="stat-card-data">
                  <span className="stat-label">Current Streak</span>
                  <strong className="stat-value">{practice.current_streak} Days</strong>
                  <span className="stat-detail">Longest: {practice.longest_streak} Days</span>
                </div>
              </div>

              {/* Questions Solved */}
              <div className="stat-card">
                <div className="stat-card-icon solved-glow">✎</div>
                <div className="stat-card-data">
                  <span className="stat-label">Questions Solved</span>
                  <strong className="stat-value">
                    {practice.questions_solved}
                    <small> / {practice.total_questions.toLocaleString()}</small>
                  </strong>
                  <span className="stat-detail">{practice.completion_percentage}% completed</span>
                </div>
              </div>

              {/* Topics Mastered */}
              <div className="stat-card">
                <div className="stat-card-icon mastery-glow">🎯</div>
                <div className="stat-card-data">
                  <span className="stat-label">Topics Mastered</span>
                  <strong className="stat-value">{practice.topics_mastered}</strong>
                  <span className="stat-detail">Based on solve thresholds</span>
                </div>
              </div>
            </div>
          </section>

          {/* ==================================================
              4. SKILLS & TECHNOLOGIES PRACTICED
          ================================================== */}
          <section className="profile-section" aria-label="Practiced Technologies">
            <div className="section-title-row">
              <div className="section-title-group">
                <span className="section-icon">💻</span>
                <h2>Practiced Technologies</h2>
              </div>
              <button
                type="button"
                className="section-link-btn"
                onClick={() => navigate("/practice")}
              >
                Go to Question Practice <span>→</span>
              </button>
            </div>

            {practice.technologies_practiced.length === 0 ? (
              <div className="profile-empty-panel">
                <div className="empty-panel-icon">💻</div>
                <h3>Start practicing to build your technical profile.</h3>
                <p>
                  Explore 5,738+ questions across 47 technologies like Python, SQL, DSA, React, and System Design.
                </p>
                <button
                  type="button"
                  className="profile-btn-primary"
                  onClick={() => navigate("/practice")}
                >
                  Start Practicing
                </button>
              </div>
            ) : (
              <div className="tech-matrix-grid">
                {practice.technologies_practiced.map((tech) => (
                  <div
                    key={tech.slug}
                    className="tech-card"
                    onClick={() => navigate(`/practice/${tech.slug}`)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        navigate(`/practice/${tech.slug}`)
                      }
                    }}
                  >
                    <div className="tech-card-header">
                      <strong className="tech-name">{tech.technology}</strong>
                      <span className="tech-solved-pill">{tech.solved} solved</span>
                    </div>
                    <div className="tech-bar-container">
                      <div
                        className="tech-bar-fill"
                        style={{ width: `${Math.min(100, Math.max(8, tech.mastery_percentage))}%` }}
                      />
                    </div>
                    <div className="tech-card-footer">
                      <span>{tech.mastery_percentage}% mastery</span>
                      <span className="tech-arrow">→</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* ==================================================
              5. ACHIEVEMENTS SHOWCASE
          ================================================== */}
          <section className="profile-section" aria-label="Achievements">
            <div className="section-title-row">
              <div className="section-title-group">
                <span className="section-icon">🏆</span>
                <h2>Achievements</h2>
              </div>
              <button
                type="button"
                className="section-link-btn"
                onClick={() => navigate("/achievements")}
              >
                View All Achievements ({achievements.unlocked_count}/{achievements.total_achievements}) <span>→</span>
              </button>
            </div>

            {achievements.unlocked_count === 0 ? (
              <div className="profile-empty-panel">
                <div className="empty-panel-icon">🏆</div>
                <h3>Start practicing to unlock your first achievement.</h3>
                <p>
                  Earn milestone badges for streaks, technical mastery, problem-solving speed, and interview preparation.
                </p>
                <button
                  type="button"
                  className="profile-btn-primary"
                  onClick={() => navigate("/practice")}
                >
                  Earn First Badge
                </button>
              </div>
            ) : (
              <div className="ach-badge-grid">
                {achievements.recent_unlocks.map((ach) => (
                  <div key={ach.id} className={`ach-card rarity-${ach.rarity.toLowerCase()}`}>
                    <div className="ach-icon-circle">{ach.icon || "🏆"}</div>
                    <div className="ach-details">
                      <div className="ach-title-row">
                        <strong className="ach-name">{ach.name}</strong>
                        <span className="ach-rarity-tag">{ach.rarity}</span>
                      </div>
                      <p className="ach-desc">{ach.description}</p>
                      <div className="ach-footer">
                        <span className="ach-reward">+{ach.xp_reward} XP</span>
                        {ach.unlocked_at && (
                          <span className="ach-date">
                            Unlocked {new Date(ach.unlocked_at).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* ==================================================
              6. INTERVIEWS & RESUME TWIN SECTION
          ================================================== */}
          <section className="profile-grid-two" aria-label="Interview Readiness and Resume">
            {/* INTERVIEW PERFORMANCE */}
            <div className="profile-glass-card">
              <div className="card-header-row">
                <div className="card-title-group">
                  <span className="card-header-icon">🎙️</span>
                  <h2>Interview Performance</h2>
                </div>
                <button
                  type="button"
                  className="btn-link"
                  onClick={() => navigate("/performance")}
                >
                  View Performance →
                </button>
              </div>

              <div className="card-body">
                {interview.completed_interviews === 0 ? (
                  <div className="empty-inline-state">
                    <p>No interviews completed yet. Test your readiness with our AI interviewer.</p>
                    <button
                      type="button"
                      className="profile-btn-primary"
                      onClick={() => navigate("/interview-setup")}
                      style={{ marginTop: "12px" }}
                    >
                      Start AI Interview
                    </button>
                  </div>
                ) : (
                  <div className="interview-stats-wrap">
                    <div className="interview-metrics-row">
                      <div className="metric-box">
                        <span className="metric-label">Completed</span>
                        <strong className="metric-value">{interview.completed_interviews}</strong>
                      </div>
                      <div className="metric-box">
                        <span className="metric-label">Average Score</span>
                        <strong className="metric-value">{interview.average_score}%</strong>
                      </div>
                      <div className="metric-box">
                        <span className="metric-label">Best Score</span>
                        <strong className="metric-value">{interview.best_score}%</strong>
                      </div>
                    </div>

                    {interview.recent_interview && (
                      <div className="recent-interview-item">
                        <div className="recent-interview-header">
                          <span className="recent-role">{interview.recent_interview.job_role}</span>
                          <span className={`diff-pill ${interview.recent_interview.difficulty.toLowerCase()}`}>
                            {interview.recent_interview.difficulty}
                          </span>
                        </div>
                        <div className="recent-interview-footer">
                          <span>
                            Score: <strong>{interview.recent_interview.score ?? "N/A"}%</strong>
                          </span>
                          {interview.recent_interview.completed_at && (
                            <span>
                              {new Date(interview.recent_interview.completed_at).toLocaleDateString()}
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* RESUME INTEGRATION */}
            <div className="profile-glass-card">
              <div className="card-header-row">
                <div className="card-title-group">
                  <span className="card-header-icon">📄</span>
                  <h2>Resume Integration</h2>
                </div>
                <button
                  type="button"
                  className="btn-link"
                  onClick={() => navigate("/resume")}
                >
                  {resume.has_resume ? "Analyze Resume →" : "Upload Resume →"}
                </button>
              </div>

              <div className="card-body">
                {resume.has_resume ? (
                  <div className="resume-ready-box">
                    <div className="resume-icon-circle">✓</div>
                    <div className="resume-meta">
                      <strong>Resume Uploaded</strong>
                      <span className="resume-filename">{resume.filename || "Uploaded Resume Document"}</span>
                      {resume.uploaded_at && (
                        <span className="resume-date">
                          Uploaded on {new Date(resume.uploaded_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                    <button
                      type="button"
                      className="profile-btn-secondary"
                      onClick={() => navigate("/resume")}
                    >
                      View &amp; Analyze
                    </button>
                  </div>
                ) : (
                  <div className="empty-inline-state">
                    <p>Upload your resume to analyze your profile and tailor mock interview sessions.</p>
                    <button
                      type="button"
                      className="profile-btn-primary"
                      onClick={() => navigate("/resume")}
                      style={{ marginTop: "12px" }}
                    >
                      Upload Resume
                    </button>
                  </div>
                )}
              </div>
            </div>
          </section>
        </div>
      </main>

      {/* ======================================================
          EDIT PROFILE MODAL
      ====================================================== */}
      {isEditModalOpen && (
        <div
          className="profile-modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-labelledby="edit-profile-title"
          onClick={(e) => {
            if (e.target === e.currentTarget) closeEditModal()
          }}
        >
          <div className="profile-modal-container">
            <div className="modal-header">
              <div className="modal-title-group">
                <span className="modal-icon">✎</span>
                <h2 id="edit-profile-title">Edit Candidate Profile</h2>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={closeEditModal}
                disabled={saving}
                aria-label="Close edit profile dialog"
              >
                ✕
              </button>
            </div>

            {saveSuccess && (
              <div className="modal-alert-success" role="status">
                ✓ Profile updated successfully!
              </div>
            )}

            {saveError && (
              <div className="modal-alert-error" role="alert">
                ⚠️ {saveError}
              </div>
            )}

            <form onSubmit={handleSaveProfile} className="modal-form">
              <div className="modal-scroll-body">
                {/* Full Name & Headline */}
                <div className="form-row-two">
                  <div className="form-group">
                    <label htmlFor="edit_full_name">
                      Full Name <span className="req">*</span>
                    </label>
                    <input
                      id="edit_full_name"
                      type="text"
                      value={editForm.full_name || ""}
                      onChange={(e) =>
                        setEditForm((prev) => ({ ...prev, full_name: e.target.value }))
                      }
                      placeholder="e.g. Alex Chen"
                      maxLength={100}
                      disabled={saving}
                    />
                    {formErrors.full_name && (
                      <span className="field-error">{formErrors.full_name}</span>
                    )}
                  </div>

                  <div className="form-group">
                    <label htmlFor="edit_headline">Headline</label>
                    <input
                      id="edit_headline"
                      type="text"
                      value={editForm.headline || ""}
                      onChange={(e) =>
                        setEditForm((prev) => ({ ...prev, headline: e.target.value }))
                      }
                      placeholder="e.g. Senior Backend & AI Systems Engineer"
                      maxLength={255}
                      disabled={saving}
                    />
                    {formErrors.headline && (
                      <span className="field-error">{formErrors.headline}</span>
                    )}
                  </div>
                </div>

                {/* Target Role & Experience Level */}
                <div className="form-row-two">
                  <div className="form-group">
                    <label htmlFor="edit_target_role">Target Role</label>
                    <input
                      id="edit_target_role"
                      type="text"
                      value={editForm.target_role || ""}
                      onChange={(e) =>
                        setEditForm((prev) => ({ ...prev, target_role: e.target.value }))
                      }
                      placeholder="e.g. Full-Stack Engineer, ML Engineer"
                      maxLength={100}
                      disabled={saving}
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="edit_experience_level">Experience Level</label>
                    <select
                      id="edit_experience_level"
                      value={editForm.experience_level || ""}
                      onChange={(e) =>
                        setEditForm((prev) => ({ ...prev, experience_level: e.target.value }))
                      }
                      disabled={saving}
                    >
                      <option value="">Select Level</option>
                      <option value="Entry Level / Student">Entry Level / Student</option>
                      <option value="Junior (1-2 yrs)">Junior (1-2 yrs)</option>
                      <option value="Mid-Level (3-5 yrs)">Mid-Level (3-5 yrs)</option>
                      <option value="Senior (5-8 yrs)">Senior (5-8 yrs)</option>
                      <option value="Lead / Staff (8+ yrs)">Lead / Staff (8+ yrs)</option>
                    </select>
                  </div>
                </div>

                {/* Bio */}
                <div className="form-group">
                  <label htmlFor="edit_bio">Bio / About</label>
                  <textarea
                    id="edit_bio"
                    rows={4}
                    value={editForm.bio || ""}
                    onChange={(e) => setEditForm((prev) => ({ ...prev, bio: e.target.value }))}
                    placeholder="Briefly describe your technical background, core technologies, and career ambitions..."
                    maxLength={1000}
                    disabled={saving}
                  />
                  <div className="field-hint-row">
                    <span>Markdown supported. Max 1000 characters.</span>
                    <span>{(editForm.bio || "").length} / 1000</span>
                  </div>
                  {formErrors.bio && <span className="field-error">{formErrors.bio}</span>}
                </div>

                {/* Education */}
                <div className="form-row-three">
                  <div className="form-group">
                    <label htmlFor="edit_college">College / University</label>
                    <input
                      id="edit_college"
                      type="text"
                      value={editForm.college || ""}
                      onChange={(e) =>
                        setEditForm((prev) => ({ ...prev, college: e.target.value }))
                      }
                      placeholder="e.g. UC Berkeley"
                      maxLength={255}
                      disabled={saving}
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="edit_degree">Degree</label>
                    <input
                      id="edit_degree"
                      type="text"
                      value={editForm.degree || ""}
                      onChange={(e) =>
                        setEditForm((prev) => ({ ...prev, degree: e.target.value }))
                      }
                      placeholder="e.g. B.S. in Computer Science"
                      maxLength={255}
                      disabled={saving}
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="edit_grad_year">Graduation Year</label>
                    <input
                      id="edit_grad_year"
                      type="number"
                      value={editForm.graduation_year ?? ""}
                      onChange={(e) =>
                        setEditForm((prev) => ({
                          ...prev,
                          graduation_year: e.target.value ? Number(e.target.value) : undefined,
                        }))
                      }
                      placeholder="e.g. 2024"
                      min={1970}
                      max={2040}
                      disabled={saving}
                    />
                    {formErrors.graduation_year && (
                      <span className="field-error">{formErrors.graduation_year}</span>
                    )}
                  </div>
                </div>

                {/* Location & Phone */}
                <div className="form-row-two">
                  <div className="form-group">
                    <label htmlFor="edit_location">Location</label>
                    <input
                      id="edit_location"
                      type="text"
                      value={editForm.location || ""}
                      onChange={(e) =>
                        setEditForm((prev) => ({ ...prev, location: e.target.value }))
                      }
                      placeholder="e.g. San Francisco, CA"
                      maxLength={255}
                      disabled={saving}
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="edit_phone">Phone</label>
                    <input
                      id="edit_phone"
                      type="tel"
                      value={editForm.phone || ""}
                      onChange={(e) =>
                        setEditForm((prev) => ({ ...prev, phone: e.target.value }))
                      }
                      placeholder="e.g. +1 555-0199"
                      maxLength={30}
                      disabled={saving}
                    />
                  </div>
                </div>

                {/* Social & Portfolio URLs */}
                <div className="form-group">
                  <label htmlFor="edit_github">GitHub URL</label>
                  <input
                    id="edit_github"
                    type="url"
                    value={editForm.github_url || ""}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, github_url: e.target.value }))
                    }
                    placeholder="https://github.com/username"
                    disabled={saving}
                  />
                  {formErrors.github_url && (
                    <span className="field-error">{formErrors.github_url}</span>
                  )}
                </div>

                <div className="form-group">
                  <label htmlFor="edit_linkedin">LinkedIn URL</label>
                  <input
                    id="edit_linkedin"
                    type="url"
                    value={editForm.linkedin_url || ""}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, linkedin_url: e.target.value }))
                    }
                    placeholder="https://linkedin.com/in/username"
                    disabled={saving}
                  />
                  {formErrors.linkedin_url && (
                    <span className="field-error">{formErrors.linkedin_url}</span>
                  )}
                </div>

                <div className="form-group">
                  <label htmlFor="edit_portfolio">Portfolio URL</label>
                  <input
                    id="edit_portfolio"
                    type="url"
                    value={editForm.portfolio_url || ""}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, portfolio_url: e.target.value }))
                    }
                    placeholder="https://myportfolio.dev"
                    disabled={saving}
                  />
                  {formErrors.portfolio_url && (
                    <span className="field-error">{formErrors.portfolio_url}</span>
                  )}
                </div>

                <div className="form-group">
                  <label htmlFor="edit_avatar">Avatar Image URL (Optional)</label>
                  <input
                    id="edit_avatar"
                    type="url"
                    value={editForm.avatar_url || ""}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, avatar_url: e.target.value }))
                    }
                    placeholder="https://images.example.com/avatar.jpg"
                    disabled={saving}
                  />
                  {formErrors.avatar_url && (
                    <span className="field-error">{formErrors.avatar_url}</span>
                  )}
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="profile-btn-secondary"
                  onClick={closeEditModal}
                  disabled={saving}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="profile-btn-primary"
                  disabled={saving}
                >
                  {saving ? "Saving Changes..." : "Save Changes"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
