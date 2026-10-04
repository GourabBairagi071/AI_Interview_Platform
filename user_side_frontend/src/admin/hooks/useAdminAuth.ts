import { useEffect, useState, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { adminApi } from "../services/adminApi"
import type { AdminUser } from "../types"

export function useAdminAuth() {
  const [admin, setAdmin] = useState<AdminUser | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [permissions, setPermissions] = useState<string[]>([])
  const navigate = useNavigate()

  const fetchAdminProfile = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const token = localStorage.getItem("access_token")
      if (!token) {
        navigate("/admin/login")
        return
      }

      const user = await adminApi.getCurrentUser()
      if (!user) {
        throw new Error("Unable to fetch user profile")
      }

      const normalizedRole = (user.role || "").trim().toUpperCase().replace(/[\s-]/g, "_")
      const isExplicitAdmin = user.is_admin === true || normalizedRole === "SUPER_ADMIN"
      const hasAdminRole = normalizedRole !== "" && normalizedRole !== "CANDIDATE"
      const isAdmin = isExplicitAdmin || hasAdminRole

      if (!isAdmin) {
        setError("Access denied. Admin privileges required.")
        setLoading(false)
        return
      }

      setAdmin({
        id: user.id,
        email: user.email,
        full_name: user.full_name || user.email.split("@")[0],
        role: normalizedRole || "ADMIN",
        is_admin: isExplicitAdmin,
        is_active: user.is_active ?? true,
        is_verified: user.is_verified ?? true,
      })

      // Fetch active roles to get permissions
      try {
        const roles = await adminApi.getRBACRoles()
        const userRole = normalizedRole || "ADMIN"
        const matchedRole = roles.find((r: any) => (r.name || "").toUpperCase() === userRole)
        if (matchedRole && matchedRole.permissions) {
          setPermissions(matchedRole.permissions)
        } else if (userRole === "SUPER_ADMIN" || isExplicitAdmin) {
          setPermissions(["*"])
        }
      } catch {
        // Fallback for super admin or basic admin
        if (normalizedRole === "SUPER_ADMIN" || isExplicitAdmin) {
          setPermissions(["*"])
        }
      }
    } catch (err: any) {
      const msg = err?.message || ""
      if (msg.includes("401") || msg.toLowerCase().includes("unauthorized") || msg.toLowerCase().includes("token")) {
        localStorage.removeItem("access_token")
        navigate("/admin/login")
      } else {
        setError(msg || "Authentication verification failed")
      }
    } finally {
      setLoading(false)
    }
  }, [navigate])

  useEffect(() => {
    fetchAdminProfile()
  }, [fetchAdminProfile])

  const hasPermission = useCallback(
    (perm: string): boolean => {
      if (!admin) return false
      if (admin.role === "SUPER_ADMIN" || admin.is_admin) return true
      if (permissions.includes("*")) return true
      return permissions.includes(perm)
    },
    [admin, permissions]
  )

  const logout = () => {
    localStorage.removeItem("access_token")
    localStorage.removeItem("token_type")
    navigate("/admin/login")
  }

  return {
    admin,
    loading,
    error,
    permissions,
    hasPermission,
    logout,
    refresh: fetchAdminProfile,
  }
}
