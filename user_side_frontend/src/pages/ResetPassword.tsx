import { useMemo, useState } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import { resetPasswordWithToken } from "../services/api"
import "./AuthFlow.css"

export default function ResetPassword() {
  const location = useLocation()
  const navigate = useNavigate()

  const resetToken = (location.state as { reset_token?: string })?.reset_token || ""

  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [isSuccess, setIsSuccess] = useState(false)

  // Password requirements calculation
  const requirements = useMemo(() => {
    return {
      minLength: newPassword.length >= 8,
      hasUpper: /[A-Z]/.test(newPassword),
      hasLower: /[a-z]/.test(newPassword),
      hasNumber: /\d/.test(newPassword),
      hasSpecial: /[!@#$%^&*(),.?":{}|<>\-_=+[\]/~`';]/.test(newPassword),
    }
  }, [newPassword])

  const strengthScore = useMemo(() => {
    let score = 0
    if (requirements.minLength) score += 1
    if (requirements.hasUpper && requirements.hasLower) score += 1
    if (requirements.hasNumber) score += 1
    if (requirements.hasSpecial) score += 1
    return score
  }, [requirements])

  const strengthLabel = useMemo(() => {
    if (!newPassword) return ""
    if (strengthScore <= 1) return "Weak"
    if (strengthScore === 2) return "Fair"
    if (strengthScore === 3) return "Good"
    return "Strong"
  }, [newPassword, strengthScore])

  const passwordsMatch = newPassword === confirmPassword && confirmPassword.length > 0
  const isFormValid = strengthScore >= 4 && passwordsMatch && resetToken

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!isFormValid || loading) return

    setLoading(true)
    setError("")

    try {
      await resetPasswordWithToken(resetToken, newPassword, confirmPassword)
      setIsSuccess(true)
    } catch (err) {
      console.error("Password reset error:", err)
      setError(
        err instanceof Error
          ? err.message
          : "Failed to reset password. Please try again.",
      )
    } finally {
      setLoading(false)
    }
  }

  // If token is missing, show session expired screen
  if (!resetToken && !isSuccess) {
    return (
      <main className="auth-flow-container">
        <div className="auth-flow-bg">
          <div className="auth-flow-glow auth-glow-primary" />
          <div className="auth-flow-glow auth-glow-secondary" />
        </div>

        <section className="auth-card">
          <div className="auth-card-header">
            <div className="auth-badge-icon" role="img" aria-label="Clock">
              ⏳
            </div>
            <h1 className="auth-card-title">Reset Session Expired</h1>
            <p className="auth-card-subtitle">
              Your password reset session has expired or is invalid. Please request a new verification code.
            </p>
          </div>

          <Link to="/forgot-password" style={{ textDecoration: "none" }}>
            <button type="button" className="auth-submit-btn">
              Request New OTP
            </button>
          </Link>

          <div className="auth-footer">
            <Link to="/login" className="auth-back-link">
              ← Return to Login
            </Link>
          </div>
        </section>
      </main>
    )
  }

  // Success state
  if (isSuccess) {
    return (
      <main className="auth-flow-container">
        <div className="auth-flow-bg">
          <div className="auth-flow-glow auth-glow-primary" />
          <div className="auth-flow-glow auth-glow-secondary" />
        </div>

        <section className="auth-card">
          <div className="auth-card-header">
            <div className="auth-badge-icon" style={{ background: "rgba(16, 185, 129, 0.2)", borderColor: "rgba(16, 185, 129, 0.4)" }} role="img" aria-label="Success">
              ✅
            </div>
            <h1 className="auth-card-title">Password Reset Complete!</h1>
            <p className="auth-card-subtitle">
              Your password has been securely updated. You can now sign in with your new credentials.
            </p>
          </div>

          <button
            type="button"
            className="auth-submit-btn"
            onClick={() => navigate("/login", { replace: true })}
          >
            Sign In with New Password
          </button>
        </section>
      </main>
    )
  }

  return (
    <main className="auth-flow-container">
      <div className="auth-flow-bg">
        <div className="auth-flow-glow auth-glow-primary" />
        <div className="auth-flow-glow auth-glow-secondary" />
      </div>

      <section className="auth-card">
        <div className="auth-card-header">
          <div className="auth-badge-icon" role="img" aria-label="Key">
            🔑
          </div>
          <h1 className="auth-card-title">Set New Password</h1>
          <p className="auth-card-subtitle">
            Choose a strong, secure password for your account.
          </p>
        </div>

        {error && (
          <div className="auth-alert auth-alert-error" role="alert">
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* NEW PASSWORD */}
          <div className="auth-field">
            <label className="auth-label" htmlFor="new-password-input">
              New Password
            </label>
            <div className="auth-input-wrapper">
              <span className="auth-input-icon">◆</span>
              <input
                id="new-password-input"
                type={showPassword ? "text" : "password"}
                className="auth-input"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Enter new password"
                required
                autoComplete="new-password"
                disabled={loading}
              />
              <button
                type="button"
                className="auth-password-toggle"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? "◉" : "○"}
              </button>
            </div>

            {/* STRENGTH METER */}
            {newPassword && (
              <div className="strength-meter">
                <div className="strength-bars">
                  {[1, 2, 3, 4].map((level) => (
                    <div
                      key={level}
                      className={`strength-bar ${level <= strengthScore ? `active level-${strengthScore}` : ""}`}
                    />
                  ))}
                </div>
                <div className="strength-text">
                  <span>Strength</span>
                  <span style={{ fontWeight: 600 }}>{strengthLabel}</span>
                </div>

                <div className="strength-reqs">
                  <div className={`req-item ${requirements.minLength ? "met" : ""}`}>
                    <span>{requirements.minLength ? "✓" : "○"}</span>
                    <span>At least 8 characters</span>
                  </div>
                  <div className={`req-item ${requirements.hasUpper && requirements.hasLower ? "met" : ""}`}>
                    <span>{requirements.hasUpper && requirements.hasLower ? "✓" : "○"}</span>
                    <span>Upper & lowercase letters</span>
                  </div>
                  <div className={`req-item ${requirements.hasNumber ? "met" : ""}`}>
                    <span>{requirements.hasNumber ? "✓" : "○"}</span>
                    <span>At least one number (0-9)</span>
                  </div>
                  <div className={`req-item ${requirements.hasSpecial ? "met" : ""}`}>
                    <span>{requirements.hasSpecial ? "✓" : "○"}</span>
                    <span>At least one special character (!@#$%^&*)</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* CONFIRM PASSWORD */}
          <div className="auth-field">
            <label className="auth-label" htmlFor="confirm-password-input">
              Confirm Password
            </label>
            <div className="auth-input-wrapper">
              <span className="auth-input-icon">◆</span>
              <input
                id="confirm-password-input"
                type={showConfirmPassword ? "text" : "password"}
                className="auth-input"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter new password"
                required
                autoComplete="new-password"
                disabled={loading}
              />
              <button
                type="button"
                className="auth-password-toggle"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                aria-label={showConfirmPassword ? "Hide password" : "Show password"}
              >
                {showConfirmPassword ? "◉" : "○"}
              </button>
            </div>
            {confirmPassword && !passwordsMatch && (
              <span style={{ fontSize: "12px", color: "#f87171", marginTop: "6px", display: "block" }}>
                Passwords do not match
              </span>
            )}
            {passwordsMatch && (
              <span style={{ fontSize: "12px", color: "#34d399", marginTop: "6px", display: "block" }}>
                ✓ Passwords match
              </span>
            )}
          </div>

          <button
            type="submit"
            className="auth-submit-btn"
            disabled={loading || !isFormValid}
          >
            {loading ? "Updating Password..." : "Reset Password"}
          </button>
        </form>

        <div className="auth-footer">
          <Link to="/login" className="auth-back-link">
            ← Cancel and Return to Login
          </Link>
        </div>
      </section>
    </main>
  )
}
