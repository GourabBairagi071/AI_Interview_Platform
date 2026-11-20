import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { requestForgotPasswordOTP } from "../services/api"
import "./AuthFlow.css"

export default function ForgotPassword() {
  const [email, setEmail] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [successMessage, setSuccessMessage] = useState("")
  const navigate = useNavigate()

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!email.trim() || loading) return

    setLoading(true)
    setError("")
    setSuccessMessage("")

    try {
      const response = await requestForgotPasswordOTP(email.trim().toLowerCase())
      setSuccessMessage(response.message || "If an account exists for this email, a password reset OTP has been sent.")
      // Navigate to /verify-otp with email state after brief feedback
      setTimeout(() => {
        navigate("/verify-otp", {
          state: { email: email.trim().toLowerCase() },
        })
      }, 1200)
    } catch (err) {
      console.error("Forgot password request failed:", err)
      setError(
        err instanceof Error
          ? err.message
          : "Failed to request password reset. Please try again.",
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="auth-flow-container">
      <div className="auth-flow-bg">
        <div className="auth-flow-glow auth-glow-primary" />
        <div className="auth-flow-glow auth-glow-secondary" />
      </div>

      <section className="auth-card">
        <div className="auth-card-header">
          <div className="auth-badge-icon" role="img" aria-label="Lock">
            🔐
          </div>
          <h1 className="auth-card-title">Forgot Password?</h1>
          <p className="auth-card-subtitle">
            Enter your email address and we'll send a 6-digit verification code to reset your password.
          </p>
        </div>

        {error && (
          <div className="auth-alert auth-alert-error" role="alert">
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {successMessage && (
          <div className="auth-alert auth-alert-success" role="status">
            <span>✓</span>
            <span>{successMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="auth-field">
            <label className="auth-label" htmlFor="email-input">
              Email Address
            </label>
            <div className="auth-input-wrapper">
              <span className="auth-input-icon">@</span>
              <input
                id="email-input"
                type="email"
                className="auth-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                autoComplete="email"
                disabled={loading}
              />
            </div>
          </div>

          <button
            type="submit"
            className="auth-submit-btn"
            disabled={loading || !email.trim()}
          >
            {loading ? "Sending OTP..." : "Send Verification Code"}
          </button>
        </form>

        <div className="auth-footer">
          <Link to="/login" className="auth-back-link">
            ← Back to Login
          </Link>
        </div>
      </section>
    </main>
  )
}
