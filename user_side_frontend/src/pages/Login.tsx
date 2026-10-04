import { useState } from "react"
import type { FormEvent } from "react"
import { Link, useNavigate } from "react-router-dom"
import { GoogleLogin } from "@react-oauth/google"

import "./Login.css"

const API_BASE_URL = "http://127.0.0.1:8000/api/v1"

function Login() {
  const navigate = useNavigate()

  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [googleLoading, setGoogleLoading] = useState(false)
  const [error, setError] = useState("")
  const [showPassword, setShowPassword] = useState(false)

  // ============================================================
  // NORMAL EMAIL/PASSWORD LOGIN
  // ============================================================

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    if (loading || googleLoading) return

    setLoading(true)
    setError("")

    try {
      const response = await fetch(
        `${API_BASE_URL}/auth/login`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({
            email: email.trim(),
            password,
          }),
        },
      )

      let data: any = {}

      try {
        data = await response.json()
      } catch {
        data = {}
      }

      if (!response.ok) {
        throw new Error(
          data.detail ||
            data.message ||
            "Invalid email or password",
        )
      }

      if (!data.access_token) {
        throw new Error(
          "Login successful but access token was not received.",
        )
      }

      localStorage.setItem(
        "access_token",
        data.access_token,
      )

      const user = data.user || {}
      const role = (user.role || "").trim().toUpperCase().replace(/[\s-]/g, "_")
      const isAdmin = user.is_admin === true || (role !== "" && role !== "CANDIDATE")

      if (isAdmin) {
        navigate("/admin/dashboard", {
          replace: true,
        })
      } else {
        navigate("/dashboard", {
          replace: true,
        })
      }
    } catch (error) {
      console.error("Login error:", error)

      setError(
        error instanceof Error
          ? error.message
          : "Something went wrong. Please try again.",
      )
    } finally {
      setLoading(false)
    }
  }

  // ============================================================
  // GOOGLE LOGIN
  // ============================================================

  async function handleGoogleSuccess(
    credentialResponse: {
      credential?: string
    },
  ) {
    if (loading || googleLoading) return

    const idToken = credentialResponse.credential

    if (!idToken) {
      setError(
        "Google authentication failed. No credential received.",
      )
      return
    }

    setGoogleLoading(true)
    setError("")

    try {
      const response = await fetch(
        `${API_BASE_URL}/auth/google`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({
            credential: idToken,
          }),
        },
      )

      let data: any = {}

      try {
        data = await response.json()
      } catch {
        data = {}
      }

      if (!response.ok) {
        throw new Error(
          data.detail ||
            data.message ||
            "Google login failed",
        )
      }

      if (!data.access_token) {
        throw new Error(
          "Google login succeeded but access token was not received.",
        )
      }

      // Store YOUR backend JWT.
      // Do NOT store the Google client secret.
      localStorage.setItem(
        "access_token",
        data.access_token,
      )

      const gUser = data.user || {}
      const gRole = (gUser.role || "").trim().toUpperCase().replace(/[\s-]/g, "_")
      const isGoogleAdmin = gUser.is_admin === true || (gRole !== "" && gRole !== "CANDIDATE")

      if (isGoogleAdmin) {
        navigate("/admin/dashboard", {
          replace: true,
        })
      } else {
        navigate("/dashboard", {
          replace: true,
        })
      }
    } catch (error) {
      console.error(
        "Google authentication error:",
        error,
      )

      setError(
        error instanceof Error
          ? error.message
          : "Google login failed. Please try again.",
      )
    } finally {
      setGoogleLoading(false)
    }
  }

  // ============================================================
  // GOOGLE LOGIN ERROR
  // ============================================================

  function handleGoogleError() {
    setGoogleLoading(false)

    setError(
      "Google login was unsuccessful. Please try again.",
    )
  }

  // ============================================================
  // FORGOT PASSWORD
  // ============================================================

  function handleForgotPassword() {
    setError(
      "Password reset is coming soon.",
    )
  }

  // ============================================================
  // UI
  // ============================================================

  return (
    <main className="login-page">

      {/* ======================================================
          ANIMATED BACKGROUND
          ====================================================== */}

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


      {/* ======================================================
          LEFT SIDE
          ====================================================== */}

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


          {/* ==================================================
              ROBOT
              ================================================== */}

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


            {/* FLOATING CARDS */}

            <div className="floating-card code-card">

              <span className="mini-icon">
                &lt;/&gt;
              </span>

              <span>
                CODE
              </span>

            </div>


            <div className="floating-card ai-card">

              <span className="mini-icon">
                ✦
              </span>

              <span>
                AI
              </span>

            </div>


            <div className="floating-card mic-card">

              <span className="mini-icon">
                ◉
              </span>

              <span>
                VOICE
              </span>

            </div>


            <div className="floating-card score-card">

              <strong>
                94%
              </strong>

              <span>
                AI SCORE
              </span>

            </div>

          </div>


          {/* ==================================================
              STATS
              ================================================== */}

          <div className="stats">

            <div className="stat">

              <strong>
                50K+
              </strong>

              <span>
                Active Users
              </span>

            </div>


            <div className="stat-divider" />


            <div className="stat">

              <strong>
                100K+
              </strong>

              <span>
                Interviews
              </span>

            </div>


            <div className="stat-divider" />


            <div className="stat">

              <strong>
                4.8/5
              </strong>

              <span>
                User Rating
              </span>

            </div>

          </div>


          <div className="secure-line">

            <span>
              ✓
            </span>

            Your data is encrypted and secure

          </div>

        </div>

      </section>


      {/* ======================================================
          RIGHT SIDE
          ====================================================== */}

      <section className="login-panel">

        <div className="login-card">

          <div className="card-top-line" />


          {/* ==================================================
              HEADER
              ================================================== */}

          <div className="login-header">

            <div className="welcome-icon">
              <span>👋</span>
            </div>


            <div>

              <h2>
                Welcome Back!
              </h2>

              <p>
                Sign in to continue your interview
                preparation journey.
              </p>

            </div>

          </div>


          {/* ==================================================
              GOOGLE LOGIN
              ================================================== */}

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

                Signing in with Google...

              </button>

            ) : (

              <GoogleLogin
                onSuccess={handleGoogleSuccess}
                onError={handleGoogleError}
                useOneTap={false}
                theme="filled_black"
                size="large"
                text="continue_with"
                shape="rectangular"
                width="100%"
              />

            )}

          </div>


          {/* ==================================================
              DIVIDER
              ================================================== */}

          <div className="divider">

            <span />

            <p>
              OR CONTINUE WITH EMAIL
            </p>

            <span />

          </div>


          {/* ==================================================
              FORM
              ================================================== */}

          <form onSubmit={handleSubmit}>

            {/* EMAIL */}

            <div className="field">

              <label>
                Email address
              </label>


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
                  autoComplete="email"
                  required
                />

              </div>

            </div>


            {/* PASSWORD */}

            <div className="field">

              <label>
                Password
              </label>


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
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  required
                />


                <button
                  type="button"
                  className="password-toggle"
                  onClick={() =>
                    setShowPassword(
                      (previous) =>
                        !previous,
                    )
                  }
                  aria-label={
                    showPassword
                      ? "Hide password"
                      : "Show password"
                  }
                >

                  {showPassword
                    ? "◉"
                    : "○"}

                </button>

              </div>

            </div>


            {/* FORM OPTIONS */}

            <div className="form-row">

              <label className="remember">

                <input
                  type="checkbox"
                />

                <span className="custom-checkbox" />

                <span>
                  Remember me
                </span>

              </label>


              <button
                type="button"
                className="forgot"
                onClick={handleForgotPassword}
              >
                Forgot password?
              </button>

            </div>


            {/* ERROR */}

            {error && (

              <div className="error-box">

                <span>
                  !
                </span>

                {error}

              </div>

            )}


            {/* LOGIN BUTTON */}

            <button
              type="submit"
              disabled={
                loading ||
                googleLoading
              }
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


          {/* ==================================================
              SIGNUP
              ================================================== */}

          <div className="signup-line">

            Don't have an account?

            <Link to="/signup">
              Create an account
            </Link>

          </div>


          {/* ==================================================
              SECURITY
              ================================================== */}

          <div className="security-card">

            <div className="security-check">
              ✓
            </div>


            <div>

              <strong>
                Secure Authentication
              </strong>

              <p>
                Your credentials are protected
                with industry-standard encryption.
              </p>

            </div>

          </div>


          {/* ==================================================
              TERMS
              ================================================== */}

          <div className="terms">

            By continuing, you agree to our

            <span>
              Terms of Service
            </span>

            {" "}and{" "}

            <span>
              Privacy Policy
            </span>

          </div>

        </div>

      </section>

    </main>
  )
}

export default Login