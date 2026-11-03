import { Alert, Checkbox, Modal, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import type { OverlappingRequestRef } from '../../api/types'

export const COMPLETE_NOTICE =
  'Коммерсант завершает действующие запросы в день утверждения'

export const INCREASE_NOTICE =
  'Увеличение по действующей позиции, прежний норматив сохраняется. Количество прибавится к текущему'

const COMPLETE_HINT =
  'Эти запросы завершатся в день утверждения экономистом. Завершится каждый запрос целиком, включая позиции, которых нет в новом. До утверждения они действуют как сейчас. Новый норматив начнётся на следующий день.'

const INCREASE_HINT =
  'Это увеличение по уже существующей позиции. Прежние запросы и все их позиции остаются до своего срока. Количество нового запроса прибавится к действующему. Новый норматив тоже начнётся на следующий день, поэтому в день утверждения объём ещё прежний, со следующего дня объёмы складываются.'

function formatDate(value: string): string {
  const [year, month, day] = value.slice(0, 10).split('-')
  if (!year || !month || !day) {
    return value
  }
  return `${day}.${month}.${year}`
}

export function requestLinks(requests: OverlappingRequestRef[]) {
  return requests.map((item) => (
    <li key={item.id}>
      <Link
        to={`/requests/${item.id}`}
        target="_blank"
        rel="noopener noreferrer"
      >
        Запрос №{item.id.slice(0, 8)} от {formatDate(item.created_at)}
      </Link>
    </li>
  ))
}

export function OverlappingNormativesNotice({
  mode,
  requests,
}: {
  mode: 'complete' | 'increase'
  requests: OverlappingRequestRef[]
}) {
  return (
    <Alert
      type={mode === 'complete' ? 'warning' : 'info'}
      showIcon
      message={mode === 'complete' ? COMPLETE_NOTICE : INCREASE_NOTICE}
      description={
        requests.length > 0 ? <ul>{requestLinks(requests)}</ul> : null
      }
    />
  )
}

export function SendNormativeModal({
  open,
  requests,
  confirmLoading,
  onCancel,
  onSubmit,
}: {
  open: boolean
  requests: OverlappingRequestRef[]
  confirmLoading: boolean
  onCancel: () => void
  onSubmit: (completePrevious: boolean) => void
}) {
  const [completePrevious, setCompletePrevious] = useState(true)

  useEffect(() => {
    if (open) {
      setCompletePrevious(true)
    }
  }, [open])

  return (
    <Modal
      title="Действующие нормативы"
      open={open}
      okText="Отправить"
      cancelText="Отмена"
      confirmLoading={confirmLoading}
      onOk={() => onSubmit(completePrevious)}
      onCancel={onCancel}
      destroyOnHidden
    >
      <ul>{requestLinks(requests)}</ul>
      <Checkbox
        checked={completePrevious}
        onChange={(event) => setCompletePrevious(event.target.checked)}
      >
        Завершить эти запросы в день утверждения экономистом
      </Checkbox>
      <Typography.Paragraph style={{ marginTop: 12 }}>
        {completePrevious ? COMPLETE_HINT : INCREASE_HINT}
      </Typography.Paragraph>
    </Modal>
  )
}
