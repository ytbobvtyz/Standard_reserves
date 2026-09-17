import { Card, Col, Row, Statistic, Tooltip, Typography } from 'antd'
import { QuestionCircleOutlined } from '@ant-design/icons'
import type { DashboardMassUnit } from '../../api/types'
import { COVERAGE_HINT, formatMass } from './formatMass'

interface NorthStarRowProps {
  activeCount: number
  deficitQuantity: number
  coveragePct: number
  expiring30d: number
  avgRemainingDays: number | null
  unit: DashboardMassUnit
}

export function NorthStarRow({
  activeCount,
  deficitQuantity,
  coveragePct,
  expiring30d,
  avgRemainingDays,
  unit,
}: NorthStarRowProps) {
  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} sm={12} lg={4}>
        <Card>
          <Statistic title="Активных НЗ" value={activeCount} />
        </Card>
      </Col>
      <Col xs={24} sm={12} lg={5}>
        <Card>
          <Statistic
            title="Дефицит"
            value={formatMass(deficitQuantity, unit)}
            suffix={unit}
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} lg={5}>
        <Card>
          <Statistic
            title={
              <span>
                Покрытие{' '}
                <Tooltip title={COVERAGE_HINT}>
                  <QuestionCircleOutlined aria-label="Что такое покрытие" />
                </Tooltip>
              </span>
            }
            value={coveragePct}
            suffix="%"
            precision={0}
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} lg={5}>
        <Card>
          <Statistic title="Истекают 30д" value={expiring30d} />
        </Card>
      </Col>
      <Col xs={24} sm={12} lg={5}>
        <Card>
          <Statistic
            title="Средний срок"
            value={avgRemainingDays ?? 0}
            suffix="дней"
            precision={0}
            formatter={avgRemainingDays == null ? () => '—' : undefined}
          />
        </Card>
      </Col>
      <Col span={24}>
        <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
          {COVERAGE_HINT}
        </Typography.Paragraph>
      </Col>
    </Row>
  )
}
