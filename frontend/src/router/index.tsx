import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from '../components/common/Layout'
import { ProtectedRoute } from '../components/common/ProtectedRoute'
import { LoginPage } from '../pages/LoginPage'
import { DashboardPage } from '../pages/DashboardPage'
import { MyRequestsPage } from '../pages/MyRequestsPage'
import { CreateRequestPage } from '../pages/CreateRequestPage'
import { RequestDetailPage } from '../pages/RequestDetailPage'
import { ApprovalsPage } from '../pages/ApprovalsPage'
import { LogisticsDashboardPage } from '../pages/LogisticsDashboardPage'
import { OneTimeRequestsPage } from '../pages/OneTimeRequestsPage'
import { NormativesPage } from '../pages/NormativesPage'
import { ProductsPage } from '../pages/ProductsPage'
import { ObjectsPage } from '../pages/ObjectsPage'
import { ReferencesPage } from '../pages/ReferencesPage'

export function AppRouter() {
  return (
    <BrowserRouter
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/requests/my" element={<MyRequestsPage />} />
            <Route element={<ProtectedRoute roles={['commercial', 'logistics']} />}>
              <Route path="/requests/create" element={<CreateRequestPage />} />
            </Route>
            <Route path="/requests/:id" element={<RequestDetailPage />} />
            <Route element={<ProtectedRoute roles={['pp']} />}>
              <Route path="/approvals/pp" element={<ApprovalsPage />} />
            </Route>
            <Route element={<ProtectedRoute roles={['economist']} />}>
              <Route path="/approvals/economy" element={<ApprovalsPage />} />
            </Route>
            <Route element={<ProtectedRoute roles={['logistics']} />}>
              <Route path="/logistics/dashboard" element={<LogisticsDashboardPage />} />
              <Route path="/logistics/one-time" element={<OneTimeRequestsPage />} />
            </Route>
            <Route path="/normatives" element={<NormativesPage />} />
            <Route path="/references/products" element={<ProductsPage />} />
            <Route path="/references/objects" element={<ObjectsPage />} />
            <Route path="/references/users" element={<ReferencesPage />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
