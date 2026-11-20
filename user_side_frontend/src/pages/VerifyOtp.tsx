import { useEffect, useRef, useState } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import { requestForgotPasswordOTP, verifyResetOTP } from "../services/api"
import "./AuthFlow.css"

export default function VerifyOtp() {
  const location = useLocation()
  const navigate = useNavigate()

  const initialEmail = (location.state as { email?: string })?.email || ""
  const [email, setEmail] = useState(initialEmail)
  const [otp, setOtp] = useState<string[]>(["", "", "", "", "", ""])
  const [loading, setLoading] = useState(false)
  const [resending, setResending] = useState(false)
  const [error, setError] = useState("")
  const [successMsg, setSuccessMsg] = useState("")
  const [cooldown, setCooldown] = useState(60)

  const inputRefs = useRef<(HTMLInputElement | null)[]>([])

  // Auto-focus first input on mount
  useEffect(() => {
    if (inputRefs.current[0]) {
      inputRefs.current[0].focus()
    }
  }, [])

  // Cooldown countdown timer
  useEffect(() => {
    if (cooldown <= 0) return
    const interval = setInterval(() => {
      setCooldown((prev) => (prev > 0 ? prev - 1 : 0))
    }, 1000)
    return () => clearInterval(interval)
  }, [cooldown])

  function handleOtpChange(index: number, value: string) {
    if (value.length > 1) {
      // Handle paste into single box
      handlePasteString(value)
      return
    }

    // Only allow single digit
    if (value && !/^\d$/.test(value)) return

    const newOtp = [...otp]
    newOtp[index] = value
    setOtp(newOtp)
    setError("")

    // Move to next box if digit entered
    if (value && index < 5 && inputRefs.current[index + 1]) {
      inputRefs.current[index + 1]?.focus()
    }
  }

  function handleKeyDown(index: number, e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Backspace" && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus()
    }
  }

  function handlePasteString(pasted: string) {
    const digits = pasted.replace(/\D/g, "").slice(0, 6).split("")
    if (digits.length === 0) return

    const newOtp = [...otp]
    digits.forEach((d, i) => {
      if (i < 6) newOtp[i] = d
    })
    setOtp(newOtp)
    setError("")

    const nextIndex = Math.min(digits.length, 5)
    inputRefs.current[nextIndex]?.focus()
  }

  function handlePaste(e: React.ClipboardEvent) {
    e.preventDefault()
    const pastedData = e.clipboardData.getData("text")
    handlePasteString(pastedData)
  }

  async function handleVerify(event: React.FormEvent) {
    event.preventDefault()
    const fullOtp = otp.join("")
    if (fullOtp.length !== 6 || !email.trim() || loading) return

    setLoading(true)
    setError("")
    setSuccessMsg("")

    try {
      const response = await verifyResetOTP(email.trim().toLowerCase(), fullOtp)
      setSuccessMsg(response.message || "OTP verified successfully.")

      // Navigate to /reset-password carrying the single-use reset token
      setTimeout(() => {
        navigate("/reset-password", {
          state: {
            reset_token: response.reset_token,
            email: email.trim().toLowerCase(),
          },
          replace: true,
        })
      }, 800)
    } catch (err) {
      console.error("OTP verification failed:", err)
      setError(
        err instanceof Error
          ? err.message
          : "Invalid or expired OTP. Please try again.",
      )
    } finally {
      setLoading(false)
    }
  }

  async function handleResend() {
    if (cooldown > 0 || resending || !email.trim()) return

    setResending(true)
    setError("")
    setSuccessMsg("")

    try {
      await requestForgotPasswordOTP(email.trim().toLowerCase())
      setSuccessMsg("A new verification code has been sent.")
      setCooldown(60)
      setOtp(["", "", "", "", "", ""])
      inputRefs.current[0]?.focus()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to resend code. Please try again later.",
      )
    } finally {
      setResending(false)
    }
  }

  const isOtpComplete = otp.every((d) => d.length === 1)

  return (
    <main className="auth-flow-container">
      <div className="auth-flow-bg">
        <div className="auth-flow-glow auth-glow-primary" />
        <div className="auth-flow-glow auth-glow-secondary" />
      </div>

      <section className="auth-card">
        <div className="auth-card-header">
          <div className="auth-badge-icon" role="img" aria-label="Shield">
            🛡️
          </div>
          <h1 className="auth-card-title">Enter Verification Code</h1>
          <p className="auth-card-subtitle">
            We sent a 6-digit code to <strong>{email || "your email"}</strong>
          </p>
        </div>

        {error && (
          <div className="auth-alert auth-alert-error" role="alert">
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="auth-alert auth-alert-success" role="status">
            <span>✓</span>
            <span>{successMsg}</span>
          </div>
        )}

        <form onSubmit={handleVerify}>
          {!initialEmail && (
            <div className="auth-field">
              <label className="auth-label" htmlFor="otp-email-input">
                Email Address
              </label>
              <div className="auth-input-wrapper">
                <span className="auth-input-icon">@</span>
                <input
                  id="otp-email-input"
                  type="email"
                  className="auth-input"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                />
              </div>
            </div>
          )}

          <div className="auth-field">
            <label className="auth-label">6-Digit Code</label>
            <div className="otp-inputs-grid" onPaste={handlePaste}>
              {otp.map((digit, idx) => (
                <input
                  key={idx}
                  ref={(el) => {
                    inputRefs.current[idx] = el
                  }}
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={1}
                  className="otp-box"
                  value={digit}
                  onChange={(e) => handleOtpChange(idx, e.target.value)}
                  onKeyDown={(e) => handleKeyDown(idx, e)}
                  disabled={loading}
                  aria-label={`Digit ${idx + 1}`}
                />
              ))}
            </div>
          </div>

          <button
            type="submit"
            className="auth-submit-btn"
            disabled={loading || !isOtpComplete || !email.trim()}
          >
            {loading ? "Verifying..." : "Verify Code"}
          </button>
        </form>

        <div className="resend-section">
          <span>Didn't receive the code?</span>
          {cooldown > 0 ? (
            <span className="cooldown-badge">
              ⏱ Resend in {cooldown}s
            </span>
          ) : (
            <button
              type="button"
              className="resend-btn"
              onClick={handleResend}
              disabled={resending}
            >
              {resending ? "Sending..." : "Resend OTP"}
            </button>
          )}
        </div>

        <div className="auth-footer">
          <Link to="/forgot-password" className="auth-back-link">
            ← Change Email
          </Link>
        </div>
      </section>
    </main>
  )
}
