import type { ReactNode } from "react"
import { useAdminAuth } from "../hooks/useAdminAuth"

interface AdminRoleGuardProps {
  children: ReactNode
  permission: string
  fallback?: ReactNode
}

export function AdminRoleGuard({
  children,
  permission,
  fallback = null,
}: AdminRoleGuardProps) {
  const { hasPermission } = useAdminAuth()

  if (!hasPermission(permission)) {
    return <>{fallback}</>
  }

  return <>{children}</>
}
