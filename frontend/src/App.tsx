import { useEffect } from 'react'
import { ErrorBoundary } from './components/common/ErrorBoundary'
import { AppRouter } from './router'
import { useAuthStore } from './stores/auth'

export default function App() {
  const fetchProfile = useAuthStore((state) => state.fetchProfile)

  useEffect(() => {
    void fetchProfile()
  }, [fetchProfile])

  return (
    <ErrorBoundary>
      <AppRouter />
    </ErrorBoundary>
  )
}
