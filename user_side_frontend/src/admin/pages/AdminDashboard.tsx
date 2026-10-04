import React, { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { adminApi } from "../services/adminApi"
import { AdminStatCard } from "../components/AdminStatCard"
import {
  UsersIcon,
  InterviewIcon,
  SubscriptionIcon,
  SupportIcon,
  CodeIcon,
  DatabaseIcon,
  ResumeIcon,
  QuestionIcon,
} from "../components/AdminIcons"

export const AdminDashboard: React.FC = () => {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [timeRange, setTimeRange] = useState("30d")
  const [activeChartTab, setActiveChartTab] = useState<"interviews" | "users" | "revenue">("interviews")

  useEffect(() => {
    loadData()
  }, [timeRange])

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      const res = await adminApi.getDashboardKPIs(timeRange)
      setData(res)
    } catch (err: any) {
      setError(err?.message || "Failed to load dashboard KPIs")
    } finally {
      setLoading(false)
    }
  }

  const kpis = data?.kpis || data || {}
  const trends = data?.trends || {}
  const recentActivities = data?.recent_activities || []

  const timeRangeOptions = [
    { key: "today", label: "Today" },
    { key: "7d", label: "7 Days" },
    { key: "30d", label: "30 Days" },
    { key: "90d", label: "90 Days" },
    { key: "year", label: "This Year" },
    { key: "all", label: "All Time" },
  ]

  // Determine active chart series
  const activeSeries: Array<{ date: string; value: number; count?: number }> =
    activeChartTab === "interviews"
      ? trends.interviews_daily || data?.interview_activity_chart || []
      : activeChartTab === "users"
      ? trends.user_registrations_daily || data?.user_growth_chart || []
      : trends.revenue_daily || data?.revenue_chart || []

  const maxVal = Math.max(...activeSeries.map((p) => Number(p.value) || 0), 1)

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Page Title & Time Range Filter */}
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Executive Control Center</h1>
          <p className="admin-page-subtitle">
            Real-time PostgreSQL aggregates and platform telemetry
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
          {timeRangeOptions.map((opt) => (
            <button
              key={opt.key}
              onClick={() => setTimeRange(opt.key)}
              className="admin-btn"
              style={{
                padding: "0.4rem 0.85rem",
                background: timeRange === opt.key ? "#6366f1" : "rgba(255, 255, 255, 0.05)",
                color: timeRange === opt.key ? "#ffffff" : "#94a3b8",
                border: "1px solid rgba(255, 255, 255, 0.1)",
                fontSize: "0.75rem",
                fontWeight: 600,
                cursor: "pointer",
                borderRadius: "6px",
                transition: "all 0.2s ease",
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div
          style={{
            padding: "1rem",
            background: "rgba(239, 68, 68, 0.15)",
            border: "1px solid #ef4444",
            borderRadius: "8px",
            color: "#fca5a5",
          }}
        >
          {error}
        </div>
      )}

      {/* KPI Cards Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: "1rem",
        }}
      >
        <AdminStatCard
          title="Total Candidates"
          value={loading ? "..." : (kpis.total_users ?? 0).toLocaleString()}
          icon={<UsersIcon />}
          subtitle={`${kpis.active_users ?? 0} active accounts`}
          trend={{
            value: `${kpis.new_users ?? kpis.new_users_30d ?? 0} new in window`,
            isPositive: true,
          }}
          colorVariant="indigo"
        />
        <AdminStatCard
          title="Interviews Conducted"
          value={loading ? "..." : (kpis.total_interviews ?? 0).toLocaleString()}
          icon={<InterviewIcon />}
          subtitle={`${kpis.completed_interviews ?? 0} completed`}
          trend={{
            value:
              kpis.average_interview_score != null
                ? `${Number(kpis.average_interview_score).toFixed(1)} avg score`
                : "No score data",
            isPositive: kpis.average_interview_score != null,
          }}
          colorVariant="purple"
        />
        <AdminStatCard
          title="Average ATS Score"
          value={
            loading
              ? "..."
              : kpis.average_ats_score != null
              ? `${Number(kpis.average_ats_score).toFixed(1)}%`
              : "No data"
          }
          icon={<ResumeIcon />}
          subtitle="Persisted resume analyses"
          trend={
            kpis.average_ats_score != null
              ? { value: "PostgreSQL verified", isPositive: true }
              : undefined
          }
          colorVariant="cyan"
        />
        <AdminStatCard
          title="Gross Revenue"
          value={
            loading
              ? "..."
              : `₹${(kpis.total_revenue_inr ?? 0).toLocaleString("en-IN", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}`
          }
          icon={<SubscriptionIcon />}
          subtitle={`${kpis.active_subscriptions ?? 0} active subscriptions`}
          trend={{
            value: `${kpis.successful_payments ?? 0} captured payments`,
            isPositive: true,
          }}
          colorVariant="emerald"
        />
        <AdminStatCard
          title="Support Tickets"
          value={loading ? "..." : (kpis.pending_support_tickets ?? 0).toString()}
          icon={<SupportIcon />}
          subtitle={`${kpis.open_support_tickets ?? 0} open, ${kpis.in_progress_support_tickets ?? 0} in progress`}
          trend={{
            value: `${kpis.total_support_tickets ?? 0} total tickets`,
            isPositive: false,
          }}
          colorVariant="rose"
        />
        <AdminStatCard
          title="Technical Questions"
          value={loading ? "..." : (kpis.technical_questions ?? 0).toLocaleString()}
          icon={<QuestionIcon />}
          subtitle="Practice questions repository"
          trend={{ value: "Dynamic DB count", isPositive: true }}
          colorVariant="indigo"
        />
        <AdminStatCard
          title="Coding Problems"
          value={loading ? "..." : (kpis.coding_problems ?? 0).toLocaleString()}
          icon={<CodeIcon />}
          subtitle={`${(kpis.total_coding_submissions ?? 0).toLocaleString()} submissions`}
          trend={{ value: `${kpis.contests ?? 0} contests`, isPositive: true }}
          colorVariant="cyan"
        />
        <AdminStatCard
          title="RAG Indexed Vectors"
          value={
            loading
              ? "..."
              : (kpis.rag_indexed_questions ?? kpis.rag_question_count ?? 0).toLocaleString()
          }
          icon={<DatabaseIcon />}
          subtitle="Qdrant / PGVector embeddings"
          trend={{ value: "Semantic sync active", isPositive: true }}
          colorVariant="amber"
        />
      </div>

      {/* Charts & Breakdown Row */}
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "1.25rem", flexWrap: "wrap" }}>
        {/* Trend Bar Chart */}
        <div className="admin-card">
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "1.25rem",
              flexWrap: "wrap",
              gap: "0.5rem",
            }}
          >
            <div>
              <h3 style={{ fontSize: "1rem", fontWeight: 600, color: "#f8fafc" }}>
                {activeChartTab === "interviews"
                  ? "Interview Activity Timeline"
                  : activeChartTab === "users"
                  ? "Candidate Registrations Timeline"
                  : "Gross Revenue Timeline"}
              </h3>
              <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
                PostgreSQL date aggregation
              </span>
            </div>

            {/* Chart Metric Switcher */}
            <div style={{ display: "flex", gap: "0.3rem" }}>
              <button
                onClick={() => setActiveChartTab("interviews")}
                className="admin-btn"
                style={{
                  padding: "0.3rem 0.6rem",
                  fontSize: "0.7rem",
                  background: activeChartTab === "interviews" ? "#6366f1" : "rgba(255,255,255,0.05)",
                  color: activeChartTab === "interviews" ? "#fff" : "#94a3b8",
                  borderRadius: "4px",
                  border: "none",
                  cursor: "pointer",
                }}
              >
                Interviews
              </button>
              <button
                onClick={() => setActiveChartTab("users")}
                className="admin-btn"
                style={{
                  padding: "0.3rem 0.6rem",
                  fontSize: "0.7rem",
                  background: activeChartTab === "users" ? "#6366f1" : "rgba(255,255,255,0.05)",
                  color: activeChartTab === "users" ? "#fff" : "#94a3b8",
                  borderRadius: "4px",
                  border: "none",
                  cursor: "pointer",
                }}
              >
                Candidates
              </button>
              <button
                onClick={() => setActiveChartTab("revenue")}
                className="admin-btn"
                style={{
                  padding: "0.3rem 0.6rem",
                  fontSize: "0.7rem",
                  background: activeChartTab === "revenue" ? "#6366f1" : "rgba(255,255,255,0.05)",
                  color: activeChartTab === "revenue" ? "#fff" : "#94a3b8",
                  borderRadius: "4px",
                  border: "none",
                  cursor: "pointer",
                }}
              >
                Revenue
              </button>
            </div>
          </div>

          {loading ? (
            <div
              style={{
                height: "200px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#64748b",
              }}
            >
              Loading telemetry...
            </div>
          ) : activeSeries.length === 0 ? (
            <div
              style={{
                height: "200px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#64748b",
              }}
            >
              No activity recorded in the selected window.
            </div>
          ) : (
            <div
              style={{
                display: "flex",
                alignItems: "flex-end",
                gap: "0.4rem",
                height: "200px",
                paddingTop: "1rem",
                overflowX: "auto",
              }}
            >
              {activeSeries.slice(-14).map((pt: any, idx: number) => {
                const val = Number(pt.value) || 0
                const heightPercent = val > 0 ? Math.max(12, Math.round((val / maxVal) * 100)) : 4
                const isRevenue = activeChartTab === "revenue"
                const displayVal = isRevenue ? `₹${val.toFixed(0)}` : val

                return (
                  <div
                    key={idx}
                    style={{
                      flex: 1,
                      minWidth: "28px",
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      gap: "0.4rem",
                      height: "100%",
                      justifyContent: "flex-end",
                    }}
                  >
                    <span style={{ fontSize: "0.65rem", color: val > 0 ? "#94a3b8" : "#475569" }}>
                      {displayVal}
                    </span>
                    <div
                      style={{
                        width: "100%",
                        height: `${heightPercent}%`,
                        background:
                          val > 0
                            ? isRevenue
                              ? "linear-gradient(180deg, #10b981 0%, rgba(16, 185, 129, 0.3) 100%)"
                              : "linear-gradient(180deg, #6366f1 0%, rgba(99, 102, 241, 0.3) 100%)"
                            : "rgba(255, 255, 255, 0.05)",
                        borderRadius: "4px 4px 0 0",
                        transition: "height 0.3s ease",
                      }}
                      title={`${pt.date}: ${isRevenue ? `₹${val.toFixed(2)}` : val}`}
                    />
                    <span
                      style={{
                        fontSize: "0.65rem",
                        color: "#64748b",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {pt.date ? pt.date.slice(5) : ""}
                    </span>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Quick Operations Shortcuts */}
        <div className="admin-card" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <h3 style={{ fontSize: "1rem", fontWeight: 600, color: "#f8fafc" }}>
            Operational Shortcuts
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
            <Link
              to="/admin/users"
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "0.75rem",
                borderRadius: "8px",
                background: "rgba(255, 255, 255, 0.03)",
                border: "1px solid rgba(255, 255, 255, 0.06)",
                color: "#e2e8f0",
                textDecoration: "none",
                fontSize: "0.875rem",
              }}
            >
              <span>Manage User Clearance</span>
              <span style={{ color: "#6366f1" }}>→</span>
            </Link>
            <Link
              to="/admin/questions"
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "0.75rem",
                borderRadius: "8px",
                background: "rgba(255, 255, 255, 0.03)",
                border: "1px solid rgba(255, 255, 255, 0.06)",
                color: "#e2e8f0",
                textDecoration: "none",
                fontSize: "0.875rem",
              }}
            >
              <span>Create Practice Question</span>
              <span style={{ color: "#6366f1" }}>→</span>
            </Link>
            <Link
              to="/admin/notifications"
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "0.75rem",
                borderRadius: "8px",
                background: "rgba(255, 255, 255, 0.03)",
                border: "1px solid rgba(255, 255, 255, 0.06)",
                color: "#e2e8f0",
                textDecoration: "none",
                fontSize: "0.875rem",
              }}
            >
              <span>Broadcast Announcement</span>
              <span style={{ color: "#6366f1" }}>→</span>
            </Link>
            <Link
              to="/admin/support"
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "0.75rem",
                borderRadius: "8px",
                background: "rgba(255, 255, 255, 0.03)",
                border: "1px solid rgba(255, 255, 255, 0.06)",
                color: "#e2e8f0",
                textDecoration: "none",
                fontSize: "0.875rem",
              }}
            >
              <span>Resolve Support Tickets</span>
              <span style={{ color: "#6366f1" }}>→</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Recent Audit Activities */}
      <div className="admin-card">
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "1rem",
          }}
        >
          <h3 style={{ fontSize: "1rem", fontWeight: 600, color: "#f8fafc" }}>
            Real-time Administrative Activity Trail
          </h3>
          <Link
            to="/admin/audit-logs"
            style={{ fontSize: "0.825rem", color: "#6366f1", textDecoration: "none" }}
          >
            View All Logs →
          </Link>
        </div>

        {recentActivities.length === 0 ? (
          <p style={{ color: "#64748b", fontSize: "0.875rem" }}>No recent audit events logged.</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {recentActivities.slice(0, 5).map((act: any) => (
              <div
                key={act.id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "0.6rem 0.85rem",
                  background: "rgba(255, 255, 255, 0.02)",
                  borderRadius: "8px",
                  fontSize: "0.85rem",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                  <span
                    style={{
                      fontFamily: "monospace",
                      fontSize: "0.75rem",
                      padding: "0.15rem 0.4rem",
                      background: "rgba(99, 102, 241, 0.15)",
                      color: "#a5b4fc",
                      borderRadius: "4px",
                    }}
                  >
                    {act.action}
                  </span>
                  <span style={{ color: "#e2e8f0" }}>
                    <strong>{act.actor_email}</strong> on <em>{act.resource_type || act.resource}</em>
                  </span>
                </div>
                <span style={{ color: "#64748b", fontSize: "0.75rem" }}>
                  {new Date(act.timestamp || act.created_at).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default AdminDashboard
