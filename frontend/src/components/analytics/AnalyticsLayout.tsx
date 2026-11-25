import { Tabs } from 'antd'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'

export function AnalyticsLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const active = location.pathname.startsWith('/analytics/client') ? 'client' : 'product'

  return (
    <>
      <Tabs
        activeKey={active}
        onChange={(key) => {
          navigate(key === 'client' ? '/analytics/client' : '/analytics')
        }}
        items={[
          { key: 'product', label: 'По артикулу' },
          { key: 'client', label: 'По клиенту' },
        ]}
      />
      <Outlet />
    </>
  )
}
