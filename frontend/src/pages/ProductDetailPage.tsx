import { Card, Descriptions, Space, Table, Tag, Typography, message } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getApiErrorMessage } from '../api/client'
import { referencesApi } from '../api/references'
import type { ProductDetail, RelatedProduct } from '../api/types'

const RELATION_LABEL: Record<RelatedProduct['relation'], string> = {
  parent: 'Родительский',
  child: 'Дочерний',
}

export function ProductDetailPage() {
  const { code } = useParams()
  const productCode = Number(code)
  const [product, setProduct] = useState<ProductDetail | null>(null)
  const [related, setRelated] = useState<RelatedProduct[]>([])
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    if (!Number.isFinite(productCode)) {
      return
    }
    setLoading(true)
    try {
      const [productResp, relatedResp] = await Promise.all([
        referencesApi.getProduct(productCode),
        referencesApi.getRelated(productCode),
      ])
      setProduct(productResp.data.data)
      setRelated(relatedResp.data.data.related_products)
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось загрузить продукт'))
    } finally {
      setLoading(false)
    }
  }, [productCode])

  useEffect(() => {
    void load()
  }, [load])

  if (!product) {
    return (
      <Typography.Text type="secondary">
        {loading ? 'Загрузка...' : 'Продукт не найден'}
      </Typography.Text>
    )
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={3}>
        {product.code} — {product.name}
      </Typography.Title>
      <Card loading={loading}>
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="Категория">{product.category}</Descriptions.Item>
          <Descriptions.Item label="Завод">{product.plant_name}</Descriptions.Item>
          <Descriptions.Item label="Вес, кг">{product.weight_kg}</Descriptions.Item>
          <Descriptions.Item label="Мес. потребление">
            {product.monthly_consumption ?? '—'}
          </Descriptions.Item>
          <Descriptions.Item label="Активен">
            {product.is_active ? 'Да' : 'Нет'}
          </Descriptions.Item>
          <Descriptions.Item label="Описание">
            {product.description || '—'}
          </Descriptions.Item>
        </Descriptions>
      </Card>
      <Card title="Родственные артикулы">
        <Table
          rowKey="code"
          pagination={false}
          dataSource={related}
          locale={{ emptyText: 'Родственных артикулов нет' }}
          columns={[
            {
              title: 'Артикул',
              dataIndex: 'code',
              width: 120,
              render: (value: number) => (
                <Link to={`/references/products/${value}`}>{value}</Link>
              ),
            },
            { title: 'Название', dataIndex: 'name' },
            {
              title: 'Связь',
              dataIndex: 'relation',
              width: 160,
              render: (value: RelatedProduct['relation']) =>
                RELATION_LABEL[value] ?? value,
            },
            {
              title: 'Активен',
              dataIndex: 'is_active',
              width: 120,
              render: (value: boolean) => (
                <Tag color={value ? 'green' : 'default'}>{value ? 'Да' : 'Нет'}</Tag>
              ),
            },
          ]}
        />
      </Card>
    </Space>
  )
}
