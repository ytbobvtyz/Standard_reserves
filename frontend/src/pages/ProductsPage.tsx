import { Input, Select, Space, Table, Typography } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { referencesApi } from '../api/references'
import { getApiErrorMessage } from '../api/client'
import type { ProductListItem } from '../api/types'

export function ProductsPage() {
  const navigate = useNavigate()
  const [items, setItems] = useState<ProductListItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState<'A' | 'B' | 'C' | undefined>()
  const [page, setPage] = useState(1)
  const [error, setError] = useState<string | null>(null)
  const limit = 10

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await referencesApi.getProducts({
        search: search || undefined,
        category,
        page,
        limit,
      })
      setItems(data.data)
      setTotal(data.meta?.total ?? data.data.length)
    } catch (err) {
      setError(getApiErrorMessage(err, 'Не удалось загрузить продукты'))
    } finally {
      setLoading(false)
    }
  }, [search, category, page])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={3}>Справочник: продукты</Typography.Title>
      <Space wrap>
        <Input.Search
          allowClear
          placeholder="Поиск по артикулу или названию"
          style={{ width: 320 }}
          onSearch={(value) => {
            setPage(1)
            setSearch(value)
          }}
        />
        <Select
          allowClear
          placeholder="Категория"
          style={{ width: 140 }}
          value={category}
          onChange={(value) => {
            setPage(1)
            setCategory(value)
          }}
          options={[
            { value: 'A', label: 'A' },
            { value: 'B', label: 'B' },
            { value: 'C', label: 'C' },
          ]}
        />
      </Space>
      {error ? <Typography.Text type="danger">{error}</Typography.Text> : null}
      <Table
        rowKey="code"
        loading={loading}
        dataSource={items}
        onRow={(record) => ({
          onClick: () => navigate(`/references/products/${record.code}`),
          style: { cursor: 'pointer' },
        })}
        pagination={{
          current: page,
          pageSize: limit,
          total,
          onChange: setPage,
        }}
        columns={[
          { title: 'Артикул', dataIndex: 'code', width: 120 },
          { title: 'Название', dataIndex: 'name' },
          { title: 'Категория', dataIndex: 'category', width: 110 },
          { title: 'Завод', dataIndex: 'plant_name' },
          { title: 'Вес, кг', dataIndex: 'weight_kg', width: 110 },
          {
            title: 'Активен',
            dataIndex: 'is_active',
            width: 110,
            render: (value: boolean) => (value ? 'Да' : 'Нет'),
          },
        ]}
      />
    </Space>
  )
}
