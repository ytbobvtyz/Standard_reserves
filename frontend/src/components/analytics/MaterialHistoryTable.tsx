import { Checkbox, Table, Tag } from 'antd'
import { toggleCode } from './clientAnalytics'
import type { MaterialHistoryItem } from './materialHistory'

const KIND_LABEL: Record<MaterialHistoryItem['kind'], string> = {
  current: 'Текущий',
  parent: 'Родительский',
  child: 'Дочерний',
}

interface MaterialHistoryTableProps {
  items: MaterialHistoryItem[]
  selectedCodes: number[] | null
  onChange: (codes: number[] | null) => void
}

export function MaterialHistoryTable({
  items,
  selectedCodes,
  onChange,
}: MaterialHistoryTableProps) {
  const codes = items.map((item) => item.code)
  const selected = selectedCodes ?? codes
  const allChecked = selected.length === codes.length && codes.length > 0
  const someChecked = selected.length > 0 && !allChecked

  return (
    <Table
      data-testid="material-history"
      size="small"
      pagination={false}
      rowKey="code"
      dataSource={items}
      columns={[
        {
          title: (
            <Checkbox
              aria-label="Все материалы цепочки"
              checked={allChecked}
              indeterminate={someChecked}
              onChange={(event) => onChange(event.target.checked ? null : [])}
            />
          ),
          width: 48,
          render: (_value, row: MaterialHistoryItem) => (
            <Checkbox
              aria-label={`Материал ${row.code}`}
              checked={selected.includes(row.code)}
              onChange={(event) =>
                onChange(toggleCode(selectedCodes, codes, row.code, event.target.checked))
              }
            />
          ),
        },
        {
          title: 'Артикул',
          dataIndex: 'code',
          width: 120,
        },
        {
          title: 'Название',
          dataIndex: 'name',
          render: (name: string, row: MaterialHistoryItem) => (
            <>
              {name} <Tag>{KIND_LABEL[row.kind]}</Tag>
              {row.isActive ? null : <Tag color="red">Не активен</Tag>}
            </>
          ),
        },
      ]}
    />
  )
}
