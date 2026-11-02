import { Card, Col, Row, Statistic } from 'antd'
import { formatKpiMass } from './formatMass'

interface CompanyStockRowProps {
  fullStock: number
  available: number
}

export function CompanyStockRow({ fullStock, available }: CompanyStockRowProps) {
  return (
    <Row gutter={[16, 16]} data-testid="company-stock-row">
      <Col flex="1 1 280px">
        <Card>
          <Statistic
            title="Фактический остаток"
            value={formatKpiMass(fullStock)}
            suffix="т"
          />
        </Card>
      </Col>
      <Col flex="1 1 280px">
        <Card>
          <Statistic
            title="Доступный остаток"
            value={formatKpiMass(available)}
            suffix="т"
          />
        </Card>
      </Col>
    </Row>
  )
}
