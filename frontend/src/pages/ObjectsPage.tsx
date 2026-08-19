import { Select, Space, Table, Typography } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { referencesApi } from '../api/references'
import { getApiErrorMessage } from '../api/client'
import type { ObjectListItem, ObjectType } from '../api/types'

const TYPE_LABEL: Record<ObjectType, string> = {
  plant: 'Завод',
  warehouse: 'Склад',
}

export function ObjectsPage() {
  const [items, setItems] = useState<ObjectListItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [type, setType] = useState<ObjectType | undefined>()
  const [page, setPage] = useState(1)
  const [error, setError] = useState<string | null>(null)
  const limit = 10

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await referencesApi.getObjects({ type, page, limit })
      setItems(data.data)
      setTotal(data.meta?.total ?? data.data.length)
    } catch (err) {
      setError(getApiErrorMessage(err, 'Не удалось загрузить объекты'))
    } finally {
      setLoading(false)
    }
  }, [type, page])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={3}>Справочник: объекты</Typography.Title>
      <Select
        allowClear
        placeholder="Тип объекта"
        style={{ width: 200 }}
        value={type}
        onChange={(value) => {
          setPage(1)
          setType(value)
        }}
        options={[
          { value: 'plant', label: 'Заводы' },
          { value: 'warehouse', label: 'Склады' },
        ]}
      />
      {error ? <Typography.Text type="danger">{error}</Typography.Text> : null}
      <Table
        rowKey="code"
        loading={loading}
        dataSource={items}
        pagination={{
          current: page,
          pageSize: limit,
          total,
          onChange: setPage,
        }}
        columns={[
          { title: 'Код', dataIndex: 'code', width: 100 },
          { title: 'Название', dataIndex: 'name' },
          {
            title: 'Тип',
            dataIndex: 'type',
            width: 120,
            render: (value: ObjectType) => TYPE_LABEL[value] ?? value,
          },
          { title: 'Город', dataIndex: 'city' },
          { title: 'Регион', dataIndex: 'region' },
        ]}
      />
    </Space>
  )
}
