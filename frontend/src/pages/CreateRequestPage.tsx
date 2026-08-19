import {
  Button,
  Card,
  DatePicker,
  Form,
  Input,
  InputNumber,
  Radio,
  Select,
  Space,
  Typography,
  message,
} from 'antd'
import { MinusCircleOutlined, PlusOutlined } from '@ant-design/icons'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getApiErrorMessage } from '../api/client'
import { referencesApi } from '../api/references'
import { requestsApi } from '../api/requests'
import type { ObjectListItem, RequestCreatePayload, RequestType } from '../api/types'
import { ProductAutocomplete } from '../components/requests/ProductAutocomplete'
import { useAuthStore } from '../stores/auth'

interface ItemFormValue {
  product_code?: number
  warehouse_code?: number
  quantity_requested?: number
  unit?: 'шт' | 'т'
}

interface FormValues {
  request_type: RequestType
  client_name: string
  expiry_date?: { format: (value: string) => string }
  comment?: string
  items: ItemFormValue[]
}

export function CreateRequestPage() {
  const [form] = Form.useForm<FormValues>()
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const [warehouses, setWarehouses] = useState<ObjectListItem[]>([])
  const [submitting, setSubmitting] = useState(false)
  const requestType = Form.useWatch('request_type', form)
  const isLogistics = user?.role === 'logistics'

  useEffect(() => {
    void referencesApi
      .getObjects({ type: 'warehouse', is_active: true, limit: 100 })
      .then(({ data }) => setWarehouses(data.data))
      .catch((error) => {
        message.error(getApiErrorMessage(error, 'Не удалось загрузить склады'))
      })
  }, [])

  const buildPayload = (values: FormValues): RequestCreatePayload => ({
    request_type: values.request_type,
    client_name: values.client_name,
    expiry_date:
      values.request_type === 'normative'
        ? values.expiry_date?.format('YYYY-MM-DD')
        : undefined,
    comment: values.comment,
    items: values.items.map((item) => ({
      product_code: Number(item.product_code),
      warehouse_code: Number(item.warehouse_code),
      quantity_requested: Number(item.quantity_requested),
      unit: item.unit ?? 'шт',
    })),
  })

  const submit = async (send: boolean) => {
    try {
      const values = await form.validateFields()
      setSubmitting(true)
      const { data } = await requestsApi.create(buildPayload(values))
      const requestId = data.data.id
      if (send) {
        await requestsApi.submit(requestId)
        message.success('Запрос отправлен на согласование')
      } else {
        message.success('Черновик сохранен')
      }
      navigate(`/requests/${requestId}`)
    } catch (error) {
      if (error && typeof error === 'object' && 'errorFields' in error) {
        return
      }
      message.error(getApiErrorMessage(error, 'Не удалось сохранить запрос'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={3}>Создать запрос</Typography.Title>
      <Card>
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            request_type: isLogistics ? 'one_time' : 'normative',
            items: [{}],
          }}
        >
          <Form.Item
            name="request_type"
            label="Тип запроса"
            rules={[{ required: true, message: 'Выберите тип' }]}
          >
            <Radio.Group disabled={isLogistics}>
              <Radio.Button value="normative">Нормативный</Radio.Button>
              <Radio.Button value="one_time">Разовое перемещение</Radio.Button>
            </Radio.Group>
          </Form.Item>
          <Form.Item
            name="client_name"
            label="Клиент"
            rules={[{ required: true, message: 'Укажите клиента' }]}
          >
            <Input placeholder="ООО Ромашка" />
          </Form.Item>
          {requestType === 'normative' ? (
            <Form.Item
              name="expiry_date"
              label="Срок действия"
              rules={[{ required: true, message: 'Укажите срок действия' }]}
            >
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          ) : null}
          <Typography.Title level={5}>Позиции</Typography.Title>
          <Form.List
            name="items"
            rules={[
              {
                validator: async (_, items: ItemFormValue[]) => {
                  if (!items || items.length < 1) {
                    return Promise.reject(new Error('Добавьте хотя бы одну позицию'))
                  }
                },
              },
            ]}
          >
            {(fields, { add, remove }) => (
              <>
                {fields.map((field) => (
                  <Space
                    key={field.key}
                    align="baseline"
                    style={{ display: 'flex', marginBottom: 8 }}
                    wrap
                  >
                    <Form.Item
                      {...field}
                      name={[field.name, 'product_code']}
                      rules={[{ required: true, message: 'Выберите продукт' }]}
                      style={{ minWidth: 280, marginBottom: 8 }}
                    >
                      <ProductAutocomplete />
                    </Form.Item>
                    <Form.Item
                      {...field}
                      name={[field.name, 'warehouse_code']}
                      rules={[{ required: true, message: 'Выберите склад' }]}
                      style={{ minWidth: 220, marginBottom: 8 }}
                    >
                      <Select
                        placeholder="Склад"
                        options={warehouses.map((item) => ({
                          value: item.code,
                          label: `${item.name} (${item.city})`,
                        }))}
                      />
                    </Form.Item>
                    <Form.Item
                      {...field}
                      name={[field.name, 'quantity_requested']}
                      rules={[{ required: true, message: 'Укажите количество' }]}
                      style={{ width: 140, marginBottom: 8 }}
                    >
                      <InputNumber min={0.01} placeholder="Кол-во" style={{ width: '100%' }} />
                    </Form.Item>
                    <Form.Item
                      {...field}
                      name={[field.name, 'unit']}
                      initialValue="шт"
                      style={{ width: 90, marginBottom: 8 }}
                    >
                      <Select
                        options={[
                          { value: 'шт', label: 'шт' },
                          { value: 'т', label: 'т' },
                        ]}
                      />
                    </Form.Item>
                    {fields.length > 1 ? (
                      <MinusCircleOutlined onClick={() => remove(field.name)} />
                    ) : null}
                  </Space>
                ))}
                <Button
                  type="dashed"
                  onClick={() => add()}
                  icon={<PlusOutlined />}
                  style={{ marginBottom: 16 }}
                >
                  Добавить позицию
                </Button>
              </>
            )}
          </Form.List>
          <Form.Item name="comment" label="Комментарий">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Space>
            <Button onClick={() => navigate('/requests/my')}>Отмена</Button>
            <Button loading={submitting} onClick={() => void submit(false)}>
              Сохранить черновик
            </Button>
            <Button
              type="primary"
              loading={submitting}
              onClick={() => void submit(true)}
            >
              Отправить
            </Button>
          </Space>
        </Form>
      </Card>
    </Space>
  )
}
