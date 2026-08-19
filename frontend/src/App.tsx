import { useEffect } from 'react'
import { AppRouter } from './router'
import { useAuthStore } from './stores/auth'

export default function App() {
  const fetchProfile = useAuthStore((state) => state.fetchProfile)

  useEffect(() => {
    void fetchProfile()
  }, [fetchProfile])

  return <AppRouter />
}
