import React, { useState } from "react"
import { Outlet } from "react-router-dom"
import { AdminSidebar } from "../components/AdminSidebar"
import { AdminHeader } from "../components/AdminHeader"
import { AdminBreadcrumbs } from "../components/AdminBreadcrumbs"
import { AdminErrorBoundary } from "../components/AdminErrorBoundary"
import "./AdminLayout.css"

export const AdminLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div className="admin-layout-container">
      <AdminSidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />
      <div className="admin-layout-main">
        <AdminHeader
          collapsed={collapsed}
          onToggleSidebar={() => setCollapsed(!collapsed)}
        />
        <main className="admin-layout-content">
          <AdminBreadcrumbs />
          <AdminErrorBoundary>
            <Outlet />
          </AdminErrorBoundary>
        </main>
      </div>
    </div>
  )
}
export default AdminLayout
