import { Typography } from 'antd'
import { useLocation } from 'react-router-dom'

export function ApprovalsPage() {
  const location = useLocation()
  const title = location.pathname.includes('economy')
    ? 'Согласование экономиста'
    : 'Согласование ПП'
  return <Typography.Title level={3}>{title}</Typography.Title>
}
