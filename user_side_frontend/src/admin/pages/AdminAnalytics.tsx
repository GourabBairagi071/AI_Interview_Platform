import React, { useEffect, useState } from "react"
import { adminApi } from "../services/adminApi"

export const AdminAnalytics: React.FC = () => {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [timeRange, setTimeRange] = useState("30d")

  useEffect(() => {
    loadAnalytics()
  }, [timeRange])

  const loadAnalytics = async () => {
    try {
      setLoading(true)
      const res = await adminApi.getDashboardKPIs(timeRange)
      setData(res)
    } catch (err) {
      console.error("Failed to load analytics:", err)
    } finally {
      setLoading(false)
    }
  }

  const distributions = data?.distributions || {}
  const trends = data?.trends || {}

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Platform Intelligence & Analytics</h1>
          <p className="admin-page-subtitle">
            Longitudinal trends, distribution cohorts, and candidate conversion metrics
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          {["7d", "30d", "90d", "all"].map((t) => (
            <button
              key={t}
              onClick={() => setTimeRange(t)}
              className="admin-btn"
              style={{
                padding: "0.4rem 0.85rem",
                background: timeRange === t ? "#6366f1" : "rgba(255, 255, 255, 0.05)",
                color: timeRange === t ? "#ffffff" : "#94a3b8",
                border: "1px solid rgba(255, 255, 255, 0.1)",
                textTransform: "uppercase",
                fontSize: "0.75rem",
                fontWeight: 600,
              }}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div style={{ padding: "3rem", textAlign: "center", color: "#94a3b8" }}>
          Computing analytical aggregations...
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          {/* Revenue Trend Visualizer */}
          <div className="admin-card">
            <h3 style={{ fontSize: "1rem", fontWeight: 600, color: "#f8fafc", marginBottom: "1rem" }}>
              Revenue Inflow Progression (INR)
            </h3>
            {(!trends.revenue_daily || trends.revenue_daily.length === 0) ? (
              <p style={{ color: "#64748b", fontSize: "0.875rem" }}>No revenue points in this timeframe.</p>
            ) : (
              <div style={{ display: "flex", alignItems: "flex-end", gap: "0.75rem", height: "180px", paddingTop: "1rem" }}>
                {trends.revenue_daily.slice(-14).map((pt: any, idx: number) => {
                  const maxVal = Math.max(...trends.revenue_daily.map((p: any) => p.value), 1)
                  const height = Math.max(10, Math.round((pt.value / maxVal) * 100))
                  return (
                    <div key={idx} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: "0.4rem" }}>
                      <span style={{ fontSize: "0.7rem", color: "#34d399" }}>₹{pt.value}</span>
                      <div
                        style={{
                          width: "100%",
                          height: `${height}%`,
                          background: "linear-gradient(180deg, #10b981 0%, rgba(16, 185, 129, 0.2) 100%)",
                          borderRadius: "4px 4px 0 0",
                        }}
                      />
                      <span style={{ fontSize: "0.65rem", color: "#64748b" }}>{pt.date.slice(5)}</span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Cohorts Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1.25rem" }}>
            {/* Score Distribution */}
            <div className="admin-card">
              <h3 style={{ fontSize: "1rem", fontWeight: 600, color: "#f8fafc", marginBottom: "1rem" }}>
                Interview Score Cohorts
              </h3>
              {(distributions.interview_scores || []).length === 0 ? (
                <p style={{ color: "#64748b", fontSize: "0.875rem" }}>No completed scores yet.</p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                  {distributions.interview_scores.map((item: any, idx: number) => (
                    <div key={idx}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: "0.25rem" }}>
                        <span style={{ color: "#cbd5e1" }}>{item.name}</span>
                        <span style={{ fontWeight: 600, color: "#f8fafc" }}>{item.count} sessions</span>
                      </div>
                      <div style={{ height: "6px", background: "rgba(255,255,255,0.08)", borderRadius: "3px", overflow: "hidden" }}>
                        <div
                          style={{
                            width: `${Math.min(100, item.count * 10)}%`,
                            height: "100%",
                            background: idx === 0 ? "#34d399" : idx === 1 ? "#fbbf24" : "#f87171",
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Plan Distribution */}
            <div className="admin-card">
              <h3 style={{ fontSize: "1rem", fontWeight: 600, color: "#f8fafc", marginBottom: "1rem" }}>
                Active Subscription Tier Breakdown
              </h3>
              {(distributions.subscription_plans || []).length === 0 ? (
                <p style={{ color: "#64748b", fontSize: "0.875rem" }}>No active subscriptions.</p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                  {distributions.subscription_plans.map((item: any, idx: number) => (
                    <div key={idx}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: "0.25rem" }}>
                        <span style={{ color: "#cbd5e1" }}>{item.name}</span>
                        <span style={{ fontWeight: 600, color: "#6366f1" }}>{item.count} subscribers</span>
                      </div>
                      <div style={{ height: "6px", background: "rgba(255,255,255,0.08)", borderRadius: "3px", overflow: "hidden" }}>
                        <div
                          style={{
                            width: `${Math.min(100, item.count * 20)}%`,
                            height: "100%",
                            background: "#6366f1",
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
export default AdminAnalytics
