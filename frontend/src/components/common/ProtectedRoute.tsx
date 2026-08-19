import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '../../stores/auth'
import type { UserRole } from '../../api/types'

export function ProtectedRoute({ roles }: { roles?: UserRole[] }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const user = useAuthStore((state) => state.user)

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  if (roles && user && !roles.includes(user.role)) {
    return <Navigate to="/dashboard" replace />
  }

  return <Outlet />
}
