import { Card, Col, Row, Statistic, Tooltip, Typography } from 'antd'
import { QuestionCircleOutlined } from '@ant-design/icons'
import type { DashboardMassUnit } from '../../api/types'
import {
  COVERAGE_AVAILABLE_HINT,
  COVERAGE_WITH_TRANSFERS_HINT,
  formatKpiMass,
} from './formatMass'

interface NorthStarRowProps {
  activeQuantity: number
  deficitQuantity: number
  coverageWithTransfers: number
  coverageAvailableOnly: number
  expiring30dQuantity: number
  unit: DashboardMassUnit
}

function MassStatistic({
  title,
  value,
  unit,
}: {
  title: string
  value: number
  unit: DashboardMassUnit
}) {
  return (
    <Statistic title={title} value={formatKpiMass(value)} suffix={unit} />
  )
}

export function NorthStarRow({
  activeQuantity,
  deficitQuantity,
  coverageWithTransfers,
  coverageAvailableOnly,
  expiring30dQuantity,
  unit,
}: NorthStarRowProps) {
  return (
    <Row gutter={[16, 16]}>
      <Col flex="1 1 200px">
        <Card>
          <MassStatistic title="Активных НЗ" value={activeQuantity} unit={unit} />
        </Card>
      </Col>
      <Col flex="1 1 200px">
        <Card>
          <MassStatistic title="Дефицит" value={deficitQuantity} unit={unit} />
        </Card>
      </Col>
      <Col flex="1 1 220px">
        <Card>
          <Statistic
            title={
              <span>
                Покрытие с учётом перемещений{' '}
                <Tooltip title={COVERAGE_WITH_TRANSFERS_HINT}>
                  <QuestionCircleOutlined aria-label="Что такое покрытие с учётом перемещений" />
                </Tooltip>
              </span>
            }
            value={coverageWithTransfers}
            suffix="%"
            precision={2}
          />
        </Card>
      </Col>
      <Col flex="1 1 220px">
        <Card>
          <Statistic
            title={
              <span>
                Покрытие доступным стоком{' '}
                <Tooltip title={COVERAGE_AVAILABLE_HINT}>
                  <QuestionCircleOutlined aria-label="Что такое покрытие доступным стоком" />
                </Tooltip>
              </span>
            }
            value={coverageAvailableOnly}
            suffix="%"
            precision={2}
          />
        </Card>
      </Col>
      <Col flex="1 1 200px">
        <Card>
          <MassStatistic title="Истекают 30д" value={expiring30dQuantity} unit={unit} />
        </Card>
      </Col>
      <Col span={24}>
        <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
          {COVERAGE_WITH_TRANSFERS_HINT} {COVERAGE_AVAILABLE_HINT}
        </Typography.Paragraph>
      </Col>
    </Row>
  )
}
