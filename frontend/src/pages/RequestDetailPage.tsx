import { Typography } from 'antd'
import { useParams } from 'react-router-dom'

export function RequestDetailPage() {
  const { id } = useParams()
  return <Typography.Title level={3}>Запрос {id}</Typography.Title>
}
