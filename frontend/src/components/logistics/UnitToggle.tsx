import { Radio, Space, Typography } from 'antd'
import type { Unit } from '../../api/types'

interface UnitToggleProps {
  value: Unit
  onChange: (unit: Unit) => void
}

export function UnitToggle({ value, onChange }: UnitToggleProps) {
  return (
    <Space>
      <Typography.Text>Единицы измерения:</Typography.Text>
      <Radio.Group
        value={value}
        onChange={(event) => onChange(event.target.value)}
        optionType="button"
        buttonStyle="solid"
        options={[
          { value: 'шт', label: 'шт' },
          { value: 'т', label: 'тонны' },
        ]}
      />
    </Space>
  )
}
