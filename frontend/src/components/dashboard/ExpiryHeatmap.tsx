import { Empty, Tooltip } from 'antd'
import type { ExpiryCalendarData } from '../../api/types'

interface ExpiryHeatmapProps {
  data: ExpiryCalendarData | null
}

function intensity(count: number, max: number): string {
  if (count <= 0 || max <= 0) {
    return '#f5f5f5'
  }
  const ratio = count / max
  if (ratio < 0.25) {
    return '#bae0ff'
  }
  if (ratio < 0.5) {
    return '#69b1ff'
  }
  if (ratio < 0.75) {
    return '#1677ff'
  }
  return '#003eb3'
}

export function ExpiryHeatmap({ data }: ExpiryHeatmapProps) {
  if (!data || data.days.length === 0) {
    return <Empty description="Нет истекающих нормативов в выбранном периоде" />
  }

  const max = Math.max(...data.days.map((day) => day.count))
  const byDate = new Map(data.days.map((day) => [day.date, day]))
  const start = new Date(`${data.date_from}T00:00:00`)
  const end = new Date(`${data.date_to}T00:00:00`)
  const cells: string[] = []
  for (let cursor = new Date(start); cursor <= end; cursor.setDate(cursor.getDate() + 1)) {
    const year = cursor.getFullYear()
    const month = String(cursor.getMonth() + 1).padStart(2, '0')
    const day = String(cursor.getDate()).padStart(2, '0')
    cells.push(`${year}-${month}-${day}`)
  }
  const leading = (start.getDay() + 6) % 7

  return (
    <div className="expiry-heatmap">
      {Array.from({ length: leading }, (_, index) => (
        <div key={`pad-${index}`} className="expiry-heatmap-cell is-empty" />
      ))}
      {cells.map((iso) => {
        const item = byDate.get(iso)
        const count = item?.count ?? 0
        const label = new Date(`${iso}T00:00:00`).toLocaleDateString('ru-RU')
        return (
          <Tooltip
            key={iso}
            title={`${label}: ${count} НЗ, ${item?.quantity ?? 0} ${data.unit}`}
          >
            <div
              className="expiry-heatmap-cell"
              style={{ background: intensity(count, max) }}
              data-date={iso}
            />
          </Tooltip>
        )
      })}
    </div>
  )
}
