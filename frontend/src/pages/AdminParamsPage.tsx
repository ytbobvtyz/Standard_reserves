import {
  Button,
  Card,
  Form,
  InputNumber,
  Modal,
  Space,
  Switch,
  Typography,
  message,
} from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { adminApi } from '../api/admin'
import { getApiErrorMessage } from '../api/client'
import type { SystemParams } from '../api/types'
import { formatDateTime } from '../utils/format'

interface ParamsForm {
  category_a: number
  category_b: number
  category_c: number
  remote_warehouse: number
  pallet_multiple: boolean
}

const COEFF_CONFIRM =
  'Вы меняете коэфициент категории, это приведёт к изменению потребности на складах. Вы уверены?'

function coeffsChanged(saved: SystemParams, next: ParamsForm): boolean {
  return (
    Number(saved.category_a) !== Number(next.category_a) ||
    Number(saved.category_b) !== Number(next.category_b) ||
    Number(saved.category_c) !== Number(next.category_c) ||
    Number(saved.remote_warehouse) !== Number(next.remote_warehouse)
  )
}

export function AdminParamsPage() {
  const [form] = Form.useForm<ParamsForm>()
  const [saved, setSaved] = useState<SystemParams | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await adminApi.getParams()
      const params = data.data
      setSaved(params)
      form.setFieldsValue({
        category_a: Number(params.category_a),
        category_b: Number(params.category_b),
        category_c: Number(params.category_c),
        remote_warehouse: Number(params.remote_warehouse),
        pallet_multiple: params.pallet_multiple,
      })
    } catch (err) {
      message.error(getApiErrorMessage(err, 'Не удалось загрузить параметры'))
    } finally {
      setLoading(false)
    }
  }, [form])

  useEffect(() => {
    void load()
  }, [load])

  const persist = async (values: ParamsForm) => {
    setSaving(true)
    try {
      const { data } = await adminApi.updateParams(values)
      setSaved(data.data)
      message.success('Параметры сохранены')
    } catch (err) {
      message.error(getApiErrorMessage(err, 'Не удалось сохранить параметры'))
    } finally {
      setSaving(false)
    }
  }

  const submit = async () => {
    const values = await form.validateFields()
    if (saved && coeffsChanged(saved, values)) {
      Modal.confirm({
        title: 'Подтверждение',
        content: COEFF_CONFIRM,
        okText: 'Да',
        cancelText: 'Отмена',
        onOk: () => persist(values),
      })
      return
    }
    await persist(values)
  }

  const lastBy = saved?.last_modified_by
  const lastAt = saved?.last_modified_at

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={3}>Параметры</Typography.Title>
      <Card loading={loading}>
        <Form form={form} layout="vertical" style={{ maxWidth: 480 }}>
          <Typography.Title level={5}>Коэффициенты категорий</Typography.Title>
          <Form.Item
            name="category_a"
            label="Категория A"
            rules={[{ required: true, message: 'Укажите коэффициент' }]}
          >
            <InputNumber min={1} max={3} step={0.1} precision={1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="category_b"
            label="Категория B"
            rules={[{ required: true, message: 'Укажите коэффициент' }]}
          >
            <InputNumber min={1} max={3} step={0.1} precision={1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="category_c"
            label="Категория C"
            rules={[{ required: true, message: 'Укажите коэффициент' }]}
          >
            <InputNumber min={1} max={3} step={0.1} precision={1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="remote_warehouse"
            label="Удалённые склады"
            rules={[{ required: true, message: 'Укажите коэффициент' }]}
          >
            <InputNumber min={1} max={3} step={0.1} precision={1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="pallet_multiple"
            label="Запросы кратно паллетной норме"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
          <Typography.Paragraph type="secondary">
            Последнее изменение:{' '}
            {lastBy || lastAt
              ? `${lastBy ? `${lastBy.username} (${lastBy.full_name})` : '—'}, ${formatDateTime(lastAt)}`
              : 'ещё не изменялись'}
          </Typography.Paragraph>
          <Button type="primary" loading={saving} onClick={() => void submit()}>
            Сохранить
          </Button>
        </Form>
      </Card>
    </Space>
  )
}
