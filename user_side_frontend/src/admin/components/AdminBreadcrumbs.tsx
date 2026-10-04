import React from "react"
import { Link, useLocation } from "react-router-dom"
import { ChevronRightIcon } from "./AdminIcons"

export const AdminBreadcrumbs: React.FC = () => {
  const location = useLocation()
  const pathnames = location.pathname.split("/").filter((x) => x)

  const breadcrumbNameMap: Record<string, string> = {
    admin: "Admin",
    users: "User Directory",
    interviews: "Interviews",
    questions: "Practice Questions",
    coding: "Coding Arena",
    problems: "Problems Bank",
    companies: "Companies",
    resources: "Learning Resources",
    "ai-agents": "AI Agents",
    "resume-ats": "Resume & ATS",
    analytics: "Platform Analytics",
    subscriptions: "Subscriptions",
    payments: "Payments & Revenue",
    coupons: "Discount Coupons",
    invoices: "Invoices",
    support: "Support Tickets",
    feedback: "User Feedback",
    notifications: "Broadcasts",
    achievements: "Achievements",
    "audit-logs": "Audit Trail",
    settings: "System Settings",
    rbac: "Roles & RBAC",
    rag: "RAG & Vector DB",
    learning: "Learning Intelligence",
    contests: "Contests",
  }

  return (
    <nav style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.85rem", color: "#64748b", marginBottom: "1.25rem" }}>
      <Link to="/admin" style={{ color: "#94a3b8", textDecoration: "none" }}>
        Control Center
      </Link>
      {pathnames.slice(1).map((segment, index) => {
        const to = `/${pathnames.slice(0, index + 2).join("/")}`
        const isLast = index === pathnames.slice(1).length - 1
        const title = breadcrumbNameMap[segment] || segment

        return (
          <React.Fragment key={to}>
            <ChevronRightIcon size={14} className="text-slate-600" />
            {isLast ? (
              <span style={{ color: "#f8fafc", fontWeight: 500 }}>{title}</span>
            ) : (
              <Link to={to} style={{ color: "#94a3b8", textDecoration: "none" }}>
                {title}
              </Link>
            )}
          </React.Fragment>
        )
      })}
    </nav>
  )
}
