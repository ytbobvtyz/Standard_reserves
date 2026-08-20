import { Radio, Space, Typography } from 'antd'
import type { FilterMode } from '../../api/types'

interface FilterToggleProps {
  value: FilterMode
  onChange: (value: FilterMode) => void
}

export function FilterToggle({ value, onChange }: FilterToggleProps) {
  return (
    <Space wrap>
      <Typography.Text>Показать:</Typography.Text>
      <Radio.Group
        value={value}
        onChange={(event) => onChange(event.target.value)}
        optionType="button"
        buttonStyle="solid"
        options={[
          { value: 'all', label: 'Все запасы' },
          { value: 'with_normatives', label: 'Только с нормативами' },
          { value: 'deficit_only', label: 'Требуют пополнения' },
        ]}
      />
    </Space>
  )
}
