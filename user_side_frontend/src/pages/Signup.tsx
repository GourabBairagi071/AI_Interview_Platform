import { useState } from "react"
import type { FormEvent } from "react"
import { Link, useNavigate } from "react-router-dom"
import { GoogleLogin } from "@react-oauth/google"
import "./Login.css"

const API_BASE_URL = "http://127.0.0.1:8000/api/v1"

type GoogleCredentialResponse = {
  credential?: string
  clientId?: string
  select_by?: string
}

function Signup() {
  const navigate = useNavigate()

  const [fullName, setFullName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")

  const [loading, setLoading] = useState(false)
  const [googleLoading, setGoogleLoading] = useState(false)
  const [error, setError] = useState("")

  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] =
    useState(false)

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    setError("")

    if (!fullName.trim()) {
      setError("Please enter your full name.")
      return
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.")
      return
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters long.")
      return
    }

    setLoading(true)

    try {
      const response = await fetch(
        `${API_BASE_URL}/auth/register`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({
            full_name: fullName.trim(),
            email: email.trim(),
            password,
          }),
        },
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          data.detail || "Registration failed",
        )
      }

      navigate("/login")
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong",
      )
    } finally {
      setLoading(false)
    }
  }

  async function handleGoogleSuccess(
    response: GoogleCredentialResponse,
  ) {
    setError("")

    if (!response.credential) {
      setError("Google authentication failed.")
      return
    }

    setGoogleLoading(true)

    try {
      /*
       * IMPORTANT:
       * Your backend must provide this endpoint.
       *
       * Example:
       * POST /api/v1/auth/google
       *
       * with:
       * {
       *   "credential": "GOOGLE_ID_TOKEN"
       * }
       */

      const backendResponse = await fetch(
        `${API_BASE_URL}/auth/google`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({
            credential: response.credential,
          }),
        },
      )

      const data = await backendResponse.json()

      if (!backendResponse.ok) {
        throw new Error(
          data.detail || "Google registration failed",
        )
      }

      /*
       * Adjust these keys according to your backend response.
       */

      if (data.access_token) {
        localStorage.setItem(
          "access_token",
          data.access_token,
        )
      }

      if (data.token) {
        localStorage.setItem(
          "token",
          data.token,
        )
      }

      navigate("/dashboard")
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Google registration failed.",
      )
    } finally {
      setGoogleLoading(false)
    }
  }

  function handleGoogleError() {
    setGoogleLoading(false)
    setError(
      "Google authentication failed. Please try again.",
    )
  }

  return (
    <main className="login-page">

      {/* BACKGROUND */}

      <div className="background-effects">
        <div className="glow glow-one" />
        <div className="glow glow-two" />
        <div className="grid-lines" />

        <span className="particle p1" />
        <span className="particle p2" />
        <span className="particle p3" />
        <span className="particle p4" />
        <span className="particle p5" />
        <span className="particle p6" />
      </div>

      {/* LEFT HERO */}

      <section className="login-hero">

        <div className="brand">

          <div className="brand-logo">
            <span>AI</span>
          </div>

          <div>
            <h1>AI Interview</h1>
            <p>PLATFORM</p>
          </div>

        </div>

        <div className="hero-content">

          <div className="eyebrow">
            <span className="status-dot" />
            AI-POWERED INTERVIEW PRACTICE
          </div>

          <h2>
            Practice
            <span> Smarter.</span>
            <br />
            Get Hired
            <span> Faster.</span>
          </h2>

          <p className="hero-description">
            Master your interviews with AI-powered
            <br />
            practice, instant feedback, and personalized
            <br />
            preparation.
          </p>

          {/* ROBOT */}

          <div className="robot-stage">

            <div className="orbit orbit-1" />
            <div className="orbit orbit-2" />
            <div className="orbit orbit-3" />

            <div className="robot-glow" />

            <div className="robot">

              <div className="antenna">
                <span />
              </div>

              <div className="robot-head">

                <div className="ear ear-left" />
                <div className="ear ear-right" />

                <div className="robot-eyes">
                  <span />
                  <span />
                </div>

                <div className="robot-mouth" />

              </div>

              <div className="robot-neck" />

              <div className="robot-body">

                <div className="body-core">
                  <div className="core-inner" />
                </div>

                <div className="body-line line-one" />
                <div className="body-line line-two" />

              </div>

              <div className="robot-arm arm-left">
                <span />
              </div>

              <div className="robot-arm arm-right">
                <span />
              </div>

            </div>

            <div className="floating-card code-card">
              <span className="mini-icon">
                &lt;/&gt;
              </span>
              <span>CODE</span>
            </div>

            <div className="floating-card ai-card">
              <span className="mini-icon">
                ✦
              </span>
              <span>AI</span>
            </div>

            <div className="floating-card mic-card">
              <span className="mini-icon">
                ◉
              </span>
              <span>VOICE</span>
            </div>

            <div className="floating-card score-card">
              <strong>94%</strong>
              <span>AI SCORE</span>
            </div>

          </div>

          {/* STATS */}

          <div className="stats">

            <div className="stat">
              <strong>50K+</strong>
              <span>Active Users</span>
            </div>

            <div className="stat-divider" />

            <div className="stat">
              <strong>100K+</strong>
              <span>Interviews</span>
            </div>

            <div className="stat-divider" />

            <div className="stat">
              <strong>4.8/5</strong>
              <span>User Rating</span>
            </div>

          </div>

          <div className="secure-line">
            <span>✓</span>
            Your data is encrypted and secure
          </div>

        </div>

      </section>

      {/* RIGHT PANEL */}

      <section className="login-panel">

        <div className="login-card">

          <div className="card-top-line" />

          {/* HEADER */}

          <div className="login-header">

            <div className="welcome-icon">
              <span>👋</span>
            </div>

            <div>
              <h2>Create Your Account</h2>

              <p>
                Join AI Interview and start your
                interview preparation journey.
              </p>
            </div>

          </div>

          {/* GOOGLE */}

          <div className="google-login-wrapper">

            {googleLoading ? (
              <button
                type="button"
                className="google-button"
                disabled
              >
                <span className="google-g">
                  G
                </span>

                Creating account...
              </button>
            ) : (
              <GoogleLogin
                onSuccess={handleGoogleSuccess}
                onError={handleGoogleError}
                useOneTap={false}
                theme="outline"
                size="large"
                text="continue_with"
                shape="rectangular"
                width="100%"
              />
            )}

          </div>

          <div className="divider">
            <span />
            <p>OR CREATE ACCOUNT WITH EMAIL</p>
            <span />
          </div>

          {/* FORM */}

          <form onSubmit={handleSubmit}>

            {/* FULL NAME */}

            <div className="field">

              <label>Full name</label>

              <div className="input-box">

                <span className="field-icon">
                  👤
                </span>

                <input
                  type="text"
                  value={fullName}
                  onChange={(event) =>
                    setFullName(event.target.value)
                  }
                  placeholder="Enter your full name"
                  required
                />

              </div>

            </div>

            {/* EMAIL */}

            <div className="field">

              <label>Email address</label>

              <div className="input-box">

                <span className="field-icon">
                  @
                </span>

                <input
                  type="email"
                  value={email}
                  onChange={(event) =>
                    setEmail(event.target.value)
                  }
                  placeholder="you@example.com"
                  required
                />

              </div>

            </div>

            {/* PASSWORD */}

            <div className="field">

              <label>Password</label>

              <div className="input-box">

                <span className="field-icon">
                  ◆
                </span>

                <input
                  type={
                    showPassword
                      ? "text"
                      : "password"
                  }
                  value={password}
                  onChange={(event) =>
                    setPassword(event.target.value)
                  }
                  placeholder="Create a password"
                  required
                  minLength={8}
                />

                <button
                  type="button"
                  className="password-toggle"
                  onClick={() =>
                    setShowPassword(
                      (value) => !value,
                    )
                  }
                  aria-label="Toggle password visibility"
                >
                  {showPassword ? "◉" : "○"}
                </button>

              </div>

            </div>

            {/* CONFIRM PASSWORD */}

            <div className="field">

              <label>
                Confirm password
              </label>

              <div className="input-box">

                <span className="field-icon">
                  ◆
                </span>

                <input
                  type={
                    showConfirmPassword
                      ? "text"
                      : "password"
                  }
                  value={confirmPassword}
                  onChange={(event) =>
                    setConfirmPassword(
                      event.target.value,
                    )
                  }
                  placeholder="Confirm your password"
                  required
                  minLength={8}
                />

                <button
                  type="button"
                  className="password-toggle"
                  onClick={() =>
                    setShowConfirmPassword(
                      (value) => !value,
                    )
                  }
                  aria-label="Toggle password visibility"
                >
                  {showConfirmPassword
                    ? "◉"
                    : "○"}
                </button>

              </div>

            </div>

            {/* ERROR */}

            {error && (
              <div className="error-box">
                <span>!</span>
                {error}
              </div>
            )}

            {/* SUBMIT */}

            <button
              type="submit"
              disabled={loading}
              className="login-button"
            >
              <span>
                {loading
                  ? "Creating account..."
                  : "Create Account"}
              </span>

              {!loading && (
                <span className="button-arrow">
                  →
                </span>
              )}

            </button>

          </form>

          {/* LOGIN */}

          <div className="signup-line">
            Already have an account?

            <Link to="/login">
              Sign in
            </Link>
          </div>

          {/* SECURITY */}

          <div className="security-card">

            <div className="security-check">
              ✓
            </div>

            <div>

              <strong>
                Secure Registration
              </strong>

              <p>
                Your credentials are protected
                with industry-standard encryption.
              </p>

            </div>

          </div>

          <div className="terms">
            By creating an account, you agree to our
            <span> Terms of Service</span>
            {" "}and{" "}
            <span>Privacy Policy</span>
          </div>

        </div>

      </section>

    </main>
  )
}

export default Signup