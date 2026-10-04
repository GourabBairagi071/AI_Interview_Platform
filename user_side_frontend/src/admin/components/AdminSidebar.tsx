import React from "react"
import { NavLink } from "react-router-dom"
import {
  DashboardIcon,
  UsersIcon,
  InterviewIcon,
  QuestionIcon,
  CodeIcon,
  ContestIcon,
  CompanyIcon,
  ResourceIcon,
  RobotIcon,
  ResumeIcon,
  AnalyticsIcon,
  SubscriptionIcon,
  PaymentIcon,
  CouponIcon,
  InvoiceIcon,
  SupportIcon,
  FeedbackIcon,
  NotificationIcon,
  AchievementIcon,
  AuditIcon,
  SettingsIcon,
  ShieldIcon,
  DatabaseIcon,
  SparklesIcon,
} from "./AdminIcons"
import { useAdminAuth } from "../hooks/useAdminAuth"

interface AdminSidebarProps {
  collapsed: boolean
  onToggle: () => void
}

interface NavItem {
  title: string
  path: string
  icon: React.ReactNode
  permission?: string
  badge?: string
}

interface NavSection {
  title: string
  items: NavItem[]
}

export const AdminSidebar: React.FC<AdminSidebarProps> = ({ collapsed }) => {
  const { hasPermission } = useAdminAuth()

  const sections: NavSection[] = [
    {
      title: "Core & Insights",
      items: [
        { title: "Control Center", path: "/admin", icon: <DashboardIcon /> },
        { title: "Platform Analytics", path: "/admin/analytics", icon: <AnalyticsIcon />, permission: "analytics.view" },
        { title: "Audit Trail", path: "/admin/audit-logs", icon: <AuditIcon />, permission: "audit_logs.view" },
      ],
    },
    {
      title: "Candidates & Prep",
      items: [
        { title: "User Directory", path: "/admin/users", icon: <UsersIcon />, permission: "users.view" },
        { title: "Interviews", path: "/admin/interviews", icon: <InterviewIcon />, permission: "interviews.view" },
        { title: "Resume & ATS", path: "/admin/resume-ats", icon: <ResumeIcon />, permission: "analytics.view" },
        { title: "Learning Intelligence", path: "/admin/learning", icon: <SparklesIcon />, permission: "analytics.view" },
      ],
    },
    {
      title: "Content & Arena",
      items: [
        { title: "Practice Questions", path: "/admin/questions", icon: <QuestionIcon />, permission: "questions.view" },
        { title: "1,000 Coding Problems", path: "/admin/coding-problems", icon: <CodeIcon />, permission: "questions.view" },
        { title: "Target Companies", path: "/admin/companies", icon: <CompanyIcon />, permission: "companies.view" },
        { title: "Learning Resources", path: "/admin/resources", icon: <ResourceIcon />, permission: "resources.view" },
        { title: "Live Contests", path: "/admin/contests", icon: <ContestIcon />, permission: "contests.view" },
      ],
    },
    {
      title: "AI & Infrastructure",
      items: [
        { title: "AI Agent Configs", path: "/admin/ai-agents", icon: <RobotIcon />, permission: "ai_agents.view" },
        { title: "RAG & Vector DB", path: "/admin/rag", icon: <DatabaseIcon />, permission: "rag.view" },
        { title: "System Settings", path: "/admin/settings", icon: <SettingsIcon />, permission: "settings.view" },
        { title: "RBAC Matrix", path: "/admin/rbac", icon: <ShieldIcon />, permission: "rbac.view" },
      ],
    },
    {
      title: "Monetization",
      items: [
        { title: "Subscriptions", path: "/admin/subscriptions", icon: <SubscriptionIcon />, permission: "subscriptions.view" },
        { title: "Payments & Revenue", path: "/admin/payments", icon: <PaymentIcon />, permission: "payments.view" },
        { title: "Discount Coupons", path: "/admin/coupons", icon: <CouponIcon />, permission: "coupons.manage" },
        { title: "Candidate Invoices", path: "/admin/invoices", icon: <InvoiceIcon />, permission: "invoices.view" },
      ],
    },
    {
      title: "Support & Growth",
      items: [
        { title: "Support Tickets", path: "/admin/support", icon: <SupportIcon />, permission: "support.view" },
        { title: "User Feedback", path: "/admin/feedback", icon: <FeedbackIcon />, permission: "feedback.view" },
        { title: "Broadcasts", path: "/admin/notifications", icon: <NotificationIcon />, permission: "notifications.manage" },
        { title: "Achievements", path: "/admin/achievements", icon: <AchievementIcon />, permission: "achievements.manage" },
      ],
    },
  ]

  return (
    <aside
      style={{
        width: collapsed ? "72px" : "260px",
        background: "rgba(10, 15, 29, 0.95)",
        backdropFilter: "blur(16px)",
        borderRight: "1px solid rgba(255, 255, 255, 0.08)",
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        position: "sticky",
        top: 0,
        transition: "width 0.25s ease-in-out",
        zIndex: 50,
        overflow: "hidden",
      }}
    >
      {/* Brand Header */}
      <div
        style={{
          padding: "1.25rem 1rem",
          display: "flex",
          alignItems: "center",
          gap: "0.75rem",
          borderBottom: "1px solid rgba(255, 255, 255, 0.06)",
        }}
      >
        <div
          style={{
            width: "36px",
            height: "36px",
            borderRadius: "10px",
            background: "linear-gradient(135deg, #6366f1 0%, #a855f7 100%)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#ffffff",
            fontWeight: 800,
            fontSize: "1.1rem",
            boxShadow: "0 4px 12px rgba(99, 102, 241, 0.4)",
            flexShrink: 0,
          }}
        >
          AI
        </div>
        {!collapsed && (
          <div style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>
            <span style={{ fontSize: "0.95rem", fontWeight: 700, color: "#f8fafc", whiteSpace: "nowrap" }}>
              InterviewAI
            </span>
            <span style={{ fontSize: "0.72rem", color: "#6366f1", fontWeight: 600, letterSpacing: "0.06em" }}>
              ADMIN CONSOLE
            </span>
          </div>
        )}
      </div>

      {/* Nav List */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "1rem 0.5rem",
          display: "flex",
          flexDirection: "column",
          gap: "1.25rem",
        }}
        className="admin-custom-scrollbar"
      >
        {sections.map((sec, secIdx) => {
          const visibleItems = sec.items.filter(
            (item) => !item.permission || hasPermission(item.permission)
          )
          if (visibleItems.length === 0) return null

          return (
            <div key={secIdx}>
              {!collapsed && (
                <div
                  style={{
                    padding: "0.25rem 0.75rem 0.5rem",
                    fontSize: "0.68rem",
                    fontWeight: 700,
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    color: "#64748b",
                  }}
                >
                  {sec.title}
                </div>
              )}
              <div style={{ display: "flex", flexDirection: "column", gap: "0.2rem" }}>
                {visibleItems.map((item) => (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    end={item.path === "/admin"}
                    title={collapsed ? item.title : undefined}
                    style={({ isActive }) => ({
                      display: "flex",
                      alignItems: "center",
                      gap: "0.75rem",
                      padding: collapsed ? "0.65rem" : "0.6rem 0.75rem",
                      justifyContent: collapsed ? "center" : "flex-start",
                      borderRadius: "8px",
                      textDecoration: "none",
                      fontSize: "0.85rem",
                      fontWeight: isActive ? 600 : 500,
                      color: isActive ? "#ffffff" : "#94a3b8",
                      background: isActive
                        ? "linear-gradient(90deg, rgba(99, 102, 241, 0.25) 0%, rgba(99, 102, 241, 0.08) 100%)"
                        : "transparent",
                      borderLeft: isActive ? "3px solid #6366f1" : "3px solid transparent",
                      transition: "all 0.15s ease",
                    })}
                  >
                    <span style={{ display: "flex", alignItems: "center" }}>{item.icon}</span>
                    {!collapsed && <span style={{ whiteSpace: "nowrap" }}>{item.title}</span>}
                  </NavLink>
                ))}
              </div>
            </div>
          )
        })}
      </div>

      {/* Switch back to candidate portal */}
      <div
        style={{
          padding: "0.75rem",
          borderTop: "1px solid rgba(255, 255, 255, 0.06)",
        }}
      >
        <NavLink
          to="/dashboard"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.65rem",
            padding: "0.6rem 0.75rem",
            justifyContent: collapsed ? "center" : "flex-start",
            borderRadius: "8px",
            textDecoration: "none",
            fontSize: "0.825rem",
            color: "#94a3b8",
            background: "rgba(255, 255, 255, 0.03)",
            border: "1px solid rgba(255, 255, 255, 0.05)",
          }}
          title="Switch to Candidate Portal"
        >
          <span style={{ fontSize: "1.1rem" }}>👤</span>
          {!collapsed && <span>Candidate Portal</span>}
        </NavLink>
      </div>
    </aside>
  )
}
