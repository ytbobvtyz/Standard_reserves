import { Typography } from 'antd'
import { useLocation } from 'react-router-dom'

const titles: Record<string, string> = {
  '/references/products': 'Справочник: продукты',
  '/references/objects': 'Справочник: объекты',
  '/references/users': 'Справочник: пользователи',
}

export function ReferencesPage() {
  const location = useLocation()
  return (
    <Typography.Title level={3}>
      {titles[location.pathname] ?? 'Справочники'}
    </Typography.Title>
  )
}
