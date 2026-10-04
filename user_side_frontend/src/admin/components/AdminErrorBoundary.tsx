import React, { Component, type ErrorInfo, type ReactNode } from "react"

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class AdminErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Admin dashboard runtime error:", error, errorInfo)
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: "3rem",
          margin: "2rem auto",
          maxWidth: "700px",
          background: "#1e1b4b",
          border: "1px solid #4338ca",
          borderRadius: "16px",
          color: "#e0e7ff",
          textAlign: "center"
        }}>
          <h2 style={{ fontSize: "1.5rem", marginBottom: "0.75rem", color: "#a5b4fc" }}>
            Admin Component Error Encountered
          </h2>
          <p style={{ color: "#c7d2fe", fontSize: "0.95rem", marginBottom: "1.5rem" }}>
            {this.state.error?.message || "An unexpected error occurred in this view."}
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null })
              window.location.reload()
            }}
            style={{
              padding: "0.6rem 1.4rem",
              background: "#6366f1",
              color: "#fff",
              border: "none",
              borderRadius: "8px",
              cursor: "pointer",
              fontWeight: 500
            }}
          >
            Reload Module
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
