import { useState } from "react"
import type { FormEvent } from "react"
import { Link, useNavigate } from "react-router-dom"
import "./Login.css"

const API_BASE_URL = "http://127.0.0.1:8000/api/v1"

function Login() {
  const navigate = useNavigate()

  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [showPassword, setShowPassword] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    setLoading(true)
    setError("")

    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          email,
          password,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || "Login failed")
      }

      localStorage.setItem("access_token", data.access_token)

      navigate("/dashboard")
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Something went wrong",
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="login-page">

      {/* Animated background */}
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

      {/* LEFT SIDE */}
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

            {/* Floating cards */}
            <div className="floating-card code-card">
              <span className="mini-icon">&lt;/&gt;</span>
              <span>CODE</span>
            </div>

            <div className="floating-card ai-card">
              <span className="mini-icon">✦</span>
              <span>AI</span>
            </div>

            <div className="floating-card mic-card">
              <span className="mini-icon">◉</span>
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


      {/* RIGHT SIDE */}
      <section className="login-panel">

        <div className="login-card">

          <div className="card-top-line" />

          {/* Header */}
          <div className="login-header">

            <div className="welcome-icon">
              <span>👋</span>
            </div>

            <div>
              <h2>Welcome Back!</h2>
              <p>
                Sign in to continue your interview
                preparation journey.
              </p>
            </div>

          </div>

          {/* Social */}
          <button
            type="button"
            className="google-button"
            onClick={() => setError("Google login is coming soon.")}
          >
            <span className="google-g">G</span>
            Continue with Google
          </button>

          <div className="divider">
            <span />
            <p>OR CONTINUE WITH EMAIL</p>
            <span />
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit}>

            <div className="field">

              <label>Email address</label>

              <div className="input-box">

                <span className="field-icon">@</span>

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

            <div className="field">

              <label>Password</label>

              <div className="input-box">

                <span className="field-icon">◆</span>

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
                  placeholder="Enter your password"
                  required
                />

                <button
                  type="button"
                  className="password-toggle"
                  onClick={() =>
                    setShowPassword(!showPassword)
                  }
                  aria-label="Toggle password visibility"
                >
                  {showPassword ? "◉" : "○"}
                </button>

              </div>

            </div>

            <div className="form-row">

              <label className="remember">

                <input type="checkbox" />

                <span className="custom-checkbox" />

                <span>Remember me</span>

              </label>

              <button
                type="button"
                className="forgot"
                onClick={() =>
                  setError("Password reset is coming soon.")
                }
              >
                Forgot password?
              </button>

            </div>

            {error && (
              <div className="error-box">
                <span>!</span>
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="login-button"
            >
              <span>
                {loading
                  ? "Signing in..."
                  : "Sign In"}
              </span>

              {!loading && (
                <span className="button-arrow">
                  →
                </span>
              )}
            </button>

          </form>

          <div className="signup-line">
            Don't have an account?
            <Link to="/signup">
              Create an account
            </Link>
          </div>

          {/* Security */}
          <div className="security-card">

            <div className="security-check">
              ✓
            </div>

            <div>
              <strong>Secure Authentication</strong>
              <p>
                Your credentials are protected
                with industry-standard encryption.
              </p>
            </div>

          </div>

          <div className="terms">
            By continuing, you agree to our
            <span> Terms of Service</span>
            {" "}and{" "}
            <span>Privacy Policy</span>
          </div>

        </div>

      </section>

    </main>
  )
}

export default Login