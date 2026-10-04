import { useCallback, useEffect, useState } from "react"
import type { FormEvent } from "react"
import { useNavigate } from "react-router-dom"

import {
  getCurrentUser,
  getPracticeStats,
  getUserProfile,
  updateUserProfile,
  type PracticeStatsResponse,
} from "../services/api"
import type { Profile, User } from "../services/api"

import "./Settings.css"

export default function Settings() {
  const navigate = useNavigate()

  const [loading, setLoading] = useState(true)
  const [savingProfile, setSavingProfile] = useState(false)
  const [savingPreferences, setSavingPreferences] = useState(false)
  const [alert, setAlert] = useState<{ type: "success" | "error"; message: string } | null>(null)
  const [practiceStats, setPracticeStats] = useState<PracticeStatsResponse | null>(null)

  // User & Profile State
  const [user, setUser] = useState<User | null>(null)
  const [fullName, setFullName] = useState("")
  const [email, setEmail] = useState("")
  const [phone, setPhone] = useState("")
  const [bio, setBio] = useState("")
  const [experienceYears, setExperienceYears] = useState<number | "">("")
  const [education, setEducation] = useState("")

  // Preferences State
  const [targetRole, setTargetRole] = useState(
    () => localStorage.getItem("preferred_role") || "Software Engineer",
  )
  const [difficulty, setDifficulty] = useState(
    () => localStorage.getItem("preferred_difficulty") || "medium",
  )
  const [voiceFeedback, setVoiceFeedback] = useState(
    () => localStorage.getItem("pref_voice_feedback") !== "false",
  )
  const [realtimeTranscription, setRealtimeTranscription] = useState(
    () => localStorage.getItem("pref_transcription") !== "false",
  )

  // ------------------------------------------------------------
  // LOAD DATA
  // ------------------------------------------------------------

  const loadData = useCallback(async () => {
    try {
      const [userData, profileData, statsData] = await Promise.all([
        getCurrentUser().catch(() => null),
        getUserProfile().catch(() => null),
        getPracticeStats().catch(() => null),
      ])

      if (statsData) {
        setPracticeStats(statsData)
      }

      if (userData) {
        setUser(userData)
        setFullName(userData.full_name || "")
        setEmail(userData.email || "")
      }

      if (profileData) {
        setPhone(profileData.phone || "")
        setBio(profileData.bio || "")
        setExperienceYears(
          profileData.experience_years !== null && profileData.experience_years !== undefined
            ? profileData.experience_years
            : "",
        )
        setEducation(profileData.education || "")
      }
    } catch (err) {
      console.error("Failed to load settings data:", err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  // ------------------------------------------------------------
  // SAVE PROFILE
  // ------------------------------------------------------------

  async function handleSaveProfile(e: FormEvent) {
    e.preventDefault()
    setSavingProfile(true)
    setAlert(null)

    try {
      const payload: Partial<Profile> = {
        phone: phone.trim() || null,
        bio: bio.trim() || null,
        experience_years: experienceYears === "" ? null : Number(experienceYears),
        education: education.trim() || null,
      }

      await updateUserProfile(payload)
      setAlert({ type: "success", message: "Profile details updated successfully!" })
    } catch (err: any) {
      setAlert({
        type: "error",
        message: err.message || "Failed to update profile. Please try again.",
      })
    } finally {
      setSavingProfile(false)
    }
  }

  // ------------------------------------------------------------
  // SAVE PREFERENCES
  // ------------------------------------------------------------

  function handleSavePreferences(e: FormEvent) {
    e.preventDefault()
    setSavingPreferences(true)
    setAlert(null)

    try {
      localStorage.setItem("preferred_role", targetRole)
      localStorage.setItem("preferred_difficulty", difficulty)
      localStorage.setItem("pref_voice_feedback", String(voiceFeedback))
      localStorage.setItem("pref_transcription", String(realtimeTranscription))

      setAlert({ type: "success", message: "Interview preferences saved successfully!" })
    } catch {
      setAlert({ type: "error", message: "Could not save preferences locally." })
    } finally {
      setSavingPreferences(false)
    }
  }

  // ------------------------------------------------------------
  // LOGOUT (Dedicated handler)
  // ------------------------------------------------------------

  function handleLogout() {
    localStorage.removeItem("access_token")
    navigate("/login", { replace: true })
  }

  if (loading) {
    return (
      <div className="settings-loading">
        <div className="settings-loader-orb" />
        <span>Loading your preferences...</span>
      </div>
    )
  }

  return (
    <div className="settings-page">
      {/* BACKGROUND ACCENTS */}
      <div className="settings-background">
        <div className="settings-glow glow-top" />
        <div className="settings-glow glow-bottom" />
        <div className="settings-grid-overlay" />
      </div>

      <div className="settings-wrapper">
        {/* TOP NAVIGATION */}
        <div className="settings-nav">
          <button
            type="button"
            className="settings-back-btn"
            onClick={() => navigate("/dashboard")}
          >
            ← Back to Dashboard
          </button>

          <div className="session-indicator">
            <span className="session-pulse" />
            <span>Session Active</span>
          </div>
        </div>

        {/* HEADER */}
        <div className="settings-header">
          <span className="settings-eyebrow">Platform Preferences</span>
          <h1 className="settings-title">Account &amp; System Settings</h1>
          <p className="settings-subtitle">
            Configure your personal details, AI interview customizations, and account security.
          </p>
        </div>

        {/* TOAST ALERT */}
        {alert && (
          <div className={`settings-alert ${alert.type}`}>
            <span>{alert.type === "success" ? "✓" : "⚠"}</span>
            <span>{alert.message}</span>
          </div>
        )}

        <div className="settings-grid">
          {/* PREPARATION MASTERY & LEVEL CARD */}
          {practiceStats?.xp && (
            <section className="settings-card prep-mastery-card">
              <div className="card-header">
                <div className="card-icon">⚡</div>
                <div className="card-title-group">
                  <div className="prep-title-row">
                    <h2>Preparation Rank &amp; XP</h2>
                    <span className="prep-rank-tag">{practiceStats.xp.level_title}</span>
                  </div>
                  <p>Track your level progression, consecutive practice streak, and mastery.</p>
                </div>
              </div>

              <div className="prep-stats-grid">
                <div className="prep-stat-item">
                  <span className="prep-label">Current Level</span>
                  <strong className="prep-val">Level {practiceStats.xp.level}</strong>
                  <small>{practiceStats.xp.level_title}</small>
                </div>

                <div className="prep-stat-item">
                  <span className="prep-label">Total Experience</span>
                  <strong className="prep-val">{practiceStats.xp.total_xp} XP</strong>
                  <small>{practiceStats.xp.current_level_xp} / {practiceStats.xp.next_level_xp} to Lvl {practiceStats.xp.level + 1}</small>
                </div>

                <div className="prep-stat-item">
                  <span className="prep-label">Practice Streak</span>
                  <strong className="prep-val">🔥 {practiceStats.streak.current_streak} Day{practiceStats.streak.current_streak === 1 ? "" : "s"}</strong>
                  <small>{practiceStats.streak.is_active_today ? "Active today" : "Longest: " + practiceStats.streak.longest_streak + " days"}</small>
                </div>

                <div className="prep-stat-item">
                  <span className="prep-label">Topic Mastery</span>
                  <strong className="prep-val">{practiceStats.mastery.overall_percentage}%</strong>
                  <small>{practiceStats.mastery.mastered_topics} mastered / {practiceStats.mastery.total_topics} topics</small>
                </div>
              </div>

              <div className="prep-xp-bar-wrap">
                <div className="prep-xp-bar-track">
                  <div
                    className="prep-xp-bar-fill"
                    style={{ width: `${practiceStats.xp.progress_pct}%` }}
                  />
                </div>
              </div>

              <div className="prep-card-actions">
                <button
                  type="button"
                  className="settings-save-btn"
                  style={{ width: "auto", padding: "10px 20px" }}
                  onClick={() => navigate("/practice")}
                >
                  Go to Question Practice →
                </button>
                <button
                  type="button"
                  className="settings-save-btn"
                  style={{ width: "auto", padding: "10px 20px", marginLeft: "10px", background: "rgba(124, 58, 237, 0.2)", border: "1px solid rgba(124, 58, 237, 0.4)" }}
                  onClick={() => navigate("/achievements")}
                >
                  View Achievements 🏆
                </button>
              </div>
            </section>
          )}

          {/* PROFILE CARD */}
          <section className="settings-card">
            <div className="card-header">
              <div className="card-icon">👤</div>
              <div className="card-title-group">
                <h2>Personal Profile</h2>
                <p>Manage your account identity and professional background.</p>
              </div>
            </div>

            <form onSubmit={handleSaveProfile}>
              <div className="form-grid">
                <div className="form-field">
                  <label className="form-label" htmlFor="fullName">
                    Full Name
                  </label>
                  <input
                    id="fullName"
                    type="text"
                    className="form-input"
                    value={fullName}
                    disabled
                    title="Name registered with account"
                  />
                </div>

                <div className="form-field">
                  <label className="form-label" htmlFor="email">
                    Email Address
                    {user?.is_verified && <span className="verified-pill">Verified</span>}
                  </label>
                  <input
                    id="email"
                    type="email"
                    className="form-input"
                    value={email}
                    disabled
                    title="Account email address"
                  />
                </div>

                <div className="form-field">
                  <label className="form-label" htmlFor="phone">
                    Phone Number
                  </label>
                  <input
                    id="phone"
                    type="tel"
                    className="form-input"
                    placeholder="+1 (555) 000-0000"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                  />
                </div>

                <div className="form-field">
                  <label className="form-label" htmlFor="experience">
                    Years of Experience
                  </label>
                  <input
                    id="experience"
                    type="number"
                    min="0"
                    max="50"
                    className="form-input"
                    placeholder="e.g. 3"
                    value={experienceYears}
                    onChange={(e) =>
                      setExperienceYears(e.target.value === "" ? "" : Number(e.target.value))
                    }
                  />
                </div>

                <div className="form-field full-width">
                  <label className="form-label" htmlFor="education">
                    Education / Degree
                  </label>
                  <input
                    id="education"
                    type="text"
                    className="form-input"
                    placeholder="B.S. in Computer Science, etc."
                    value={education}
                    onChange={(e) => setEducation(e.target.value)}
                  />
                </div>

                <div className="form-field full-width">
                  <label className="form-label" htmlFor="bio">
                    Professional Bio
                  </label>
                  <textarea
                    id="bio"
                    className="form-textarea"
                    placeholder="Tell AI interviewers a summary of your expertise and career goals..."
                    value={bio}
                    onChange={(e) => setBio(e.target.value)}
                  />
                </div>
              </div>

              <div className="card-actions">
                <button type="submit" className="btn-primary" disabled={savingProfile}>
                  {savingProfile ? "Saving Profile..." : "Save Profile Details"}
                </button>
              </div>
            </form>
          </section>

          {/* INTERVIEW PREFERENCES CARD */}
          <section className="settings-card">
            <div className="card-header">
              <div className="card-icon">⚙</div>
              <div className="card-title-group">
                <h2>Interview Preferences</h2>
                <p>Default configurations applied when starting new mock sessions.</p>
              </div>
            </div>

            <form onSubmit={handleSavePreferences}>
              <div className="form-grid">
                <div className="form-field">
                  <label className="form-label" htmlFor="targetRole">
                    Default Target Role
                  </label>
                  <select
                    id="targetRole"
                    className="form-select"
                    value={targetRole}
                    onChange={(e) => setTargetRole(e.target.value)}
                  >
                    <option value="Software Engineer">Software Engineer</option>
                    <option value="Frontend Developer">Frontend Developer</option>
                    <option value="Backend Developer">Backend Developer</option>
                    <option value="Full Stack Developer">Full Stack Developer</option>
                    <option value="AI / ML Engineer">AI / ML Engineer</option>
                    <option value="DevOps Engineer">DevOps Engineer</option>
                    <option value="Data Scientist">Data Scientist</option>
                  </select>
                </div>

                <div className="form-field">
                  <label className="form-label" htmlFor="difficulty">
                    Default Difficulty
                  </label>
                  <select
                    id="difficulty"
                    className="form-select"
                    value={difficulty}
                    onChange={(e) => setDifficulty(e.target.value)}
                  >
                    <option value="easy">Easy (Entry Level)</option>
                    <option value="medium">Medium (Mid-Level)</option>
                    <option value="hard">Hard (Senior / Lead)</option>
                  </select>
                </div>
              </div>

              <div className="toggle-group">
                <div className="toggle-row">
                  <div className="toggle-info">
                    <h4>AI Voice &amp; Speech Feedback</h4>
                    <p>Enable AI voice text-to-speech reading questions aloud during active interview rounds.</p>
                  </div>
                  <label className="toggle-switch">
                    <input
                      type="checkbox"
                      checked={voiceFeedback}
                      onChange={(e) => setVoiceFeedback(e.target.checked)}
                    />
                    <span className="toggle-slider" />
                  </label>
                </div>

                <div className="toggle-row">
                  <div className="toggle-info">
                    <h4>Real-Time Audio Transcription</h4>
                    <p>Display live speech-to-text transcription as you answer questions.</p>
                  </div>
                  <label className="toggle-switch">
                    <input
                      type="checkbox"
                      checked={realtimeTranscription}
                      onChange={(e) => setRealtimeTranscription(e.target.checked)}
                    />
                    <span className="toggle-slider" />
                  </label>
                </div>
              </div>

              <div className="card-actions">
                <button type="submit" className="btn-primary" disabled={savingPreferences}>
                  {savingPreferences ? "Saving Preferences..." : "Save Preferences"}
                </button>
              </div>
            </form>
          </section>

          {/* MEMBERSHIP & SUBSCRIPTION CARD */}
          <section className="settings-card subscription-settings-card">
            <div className="card-header">
              <div className="card-icon">💎</div>
              <div className="card-title-group">
                <h2>Subscription &amp; Membership</h2>
                <p>View your active tier limits, upgrade plans, and download GST tax invoices.</p>
              </div>
            </div>

            <div className="security-row">
              <div className="security-info">
                <h4>Plan &amp; Usage Telemetry</h4>
                <p>
                  Manage your interview limits, coding problem quotas, and billing details.
                </p>
              </div>

              <button
                type="button"
                className="btn-primary"
                onClick={() => navigate("/subscription")}
              >
                Manage Subscription →
              </button>
            </div>
          </section>

          {/* HELP & SUPPORT CARD (PHASE 15) */}
          <section className="settings-card support-settings-card">
            <div className="card-header">
              <div className="card-icon">🎧</div>
              <div className="card-title-group">
                <h2>Help, Support &amp; Feedback</h2>
                <p>Browse FAQs, create support inquiries, track open tickets, or share platform feedback.</p>
              </div>
            </div>

            <div className="security-row">
              <div className="security-info">
                <h4>Help Center &amp; Support Tickets</h4>
                <p>
                  Get technical assistance, browse knowledge base articles, and manage your conversation history.
                </p>
              </div>

              <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
                <button
                  type="button"
                  onClick={() => navigate("/support/tickets")}
                  style={{
                    padding: "0.6rem 1.1rem",
                    borderRadius: "8px",
                    background: "#1e293b",
                    color: "#f1f5f9",
                    border: "1px solid rgba(255, 255, 255, 0.12)",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  My Tickets
                </button>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => navigate("/support")}
                >
                  Help Center →
                </button>
              </div>
            </div>
          </section>

          {/* SECURITY & SESSION CARD */}
          <section className="settings-card danger-zone">
            <div className="card-header">
              <div className="card-icon">🔒</div>
              <div className="card-title-group">
                <h2>Account Session &amp; Security</h2>
                <p>Manage your active JWT authentication tokens and session state.</p>
              </div>
            </div>

            <div className="security-row">
              <div className="security-info">
                <h4>Sign Out of Your Account</h4>
                <p>
                  Terminates your current browser session, clears stored tokens, and redirects you
                  to the login page.
                </p>
              </div>

              <button
                type="button"
                className="settings-logout-btn"
                onClick={handleLogout}
              >
                ⇥ Log Out
              </button>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
