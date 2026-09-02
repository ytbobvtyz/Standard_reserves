import {
  Alert,
  Button,
  Card,
  DatePicker,
  Form,
  Input,
  InputNumber,
  Radio,
  Select,
  Space,
  Tooltip,
  Typography,
  message,
} from 'antd'
import type { FormListFieldData } from 'antd'
import { MinusCircleOutlined, PlusOutlined } from '@ant-design/icons'
import { type Dayjs } from 'dayjs'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getApiErrorMessage } from '../api/client'
import { referencesApi } from '../api/references'
import { requestsApi } from '../api/requests'
import type { ObjectListItem, RequestCreatePayload, RequestType } from '../api/types'
import { ProductAutocomplete } from '../components/requests/ProductAutocomplete'
import { useAuthStore } from '../stores/auth'
import {
  EXPIRY_ERROR,
  EXPIRY_HINT,
  EXPIRY_TOO_SOON,
  defaultExpiryDate,
  isExpiryTooFar,
  isExpiryTooSoon,
  maxExpiryDate,
  minExpiryDate,
} from '../utils/expiryDate'
import { formatInitiator } from '../utils/format'
import {
  calculateRequirement,
  categoryLabel,
  distanceLabel,
  formatRequirementQty,
  requirementTooltip,
} from '../utils/requirement'

const PALLET_NORM_HINT =
  'Пополнение возможно только кратно поддонной норме. Если вы укажете количество не кратное поддонной норме, перемещение будет выдано с округлением вашей потребности до поддонной нормы'

interface ItemFormValue {
  product_code?: number
  product_name?: string
  warehouse_code?: number
  quantity_requested?: number
  unit?: 'шт' | 'т'
  category?: string
}

interface FormValues {
  request_type: RequestType
  client_name: string
  expiry_date?: Dayjs
  comment?: string
  items: ItemFormValue[]
}

const ITEM_GRID =
  'minmax(220px, 1.5fr) minmax(140px, 1.1fr) minmax(180px, 1.2fr) 110px 80px 110px 120px 150px 28px'

function RequestItemRow({
  field,
  warehouses,
  canRemove,
  onRemove,
}: {
  field: FormListFieldData
  warehouses: ObjectListItem[]
  canRemove: boolean
  onRemove: () => void
}) {
  const form = Form.useFormInstance<FormValues>()
  const productName = Form.useWatch(['items', field.name, 'product_name'], form)
  const category = Form.useWatch(['items', field.name, 'category'], form)
  const quantity = Form.useWatch(['items', field.name, 'quantity_requested'], form)
  const unit = Form.useWatch(['items', field.name, 'unit'], form) ?? 'шт'
  const warehouseCode = Form.useWatch(['items', field.name, 'warehouse_code'], form)
  const warehouse = warehouses.find((item) => item.code === warehouseCode)
  const longDistance = warehouse == null ? undefined : Boolean(warehouse.long_distance)
  const requirement = calculateRequirement(quantity, category, longDistance)

  return (
    <>
      <div style={{ display: 'none' }}>
        <Form.Item name={[field.name, 'product_name']}>
          <Input />
        </Form.Item>
        <Form.Item name={[field.name, 'category']}>
          <Input />
        </Form.Item>
      </div>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: ITEM_GRID,
          gap: 8,
          alignItems: 'start',
          marginBottom: 8,
          minWidth: 1100,
        }}
      >
        <Form.Item
          {...field}
          name={[field.name, 'product_code']}
          rules={[{ required: true, message: 'Выберите продукт' }]}
          style={{ marginBottom: 0 }}
        >
        <ProductAutocomplete
          includeAnalogs
          onChange={(_code, product) => {
            form.setFieldValue(['items', field.name, 'product_name'], product?.name)
            form.setFieldValue(['items', field.name, 'category'], product?.category)
          }}
        />
      </Form.Item>
      <Typography.Text style={{ paddingTop: 5 }} ellipsis>
        {productName || '—'}
      </Typography.Text>
      <Form.Item
        {...field}
        name={[field.name, 'warehouse_code']}
        rules={[{ required: true, message: 'Выберите склад' }]}
        style={{ marginBottom: 0 }}
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
        style={{ marginBottom: 0 }}
      >
        <InputNumber min={0.01} placeholder="Кол-во" style={{ width: '100%' }} />
      </Form.Item>
      <Form.Item
        {...field}
        name={[field.name, 'unit']}
        initialValue="шт"
        style={{ marginBottom: 0 }}
      >
        <Select
          options={[
            { value: 'шт', label: 'шт' },
            { value: 'т', label: 'т' },
          ]}
        />
      </Form.Item>
      <Typography.Text style={{ paddingTop: 5 }}>{categoryLabel(category)}</Typography.Text>
      <Typography.Text style={{ paddingTop: 5 }}>
        {warehouseCode == null ? '—' : distanceLabel(Boolean(longDistance))}
      </Typography.Text>
      {requirement == null || !unit ? (
        <Typography.Text type="secondary" style={{ paddingTop: 5 }}>
          —
        </Typography.Text>
      ) : (
        <Tooltip title={requirementTooltip(quantity ?? 0, unit, category, Boolean(longDistance))}>
          <Typography.Text style={{ paddingTop: 5 }}>
            {formatRequirementQty(requirement)} {unit}
          </Typography.Text>
        </Tooltip>
      )}
      {canRemove ? (
        <MinusCircleOutlined style={{ marginTop: 8 }} onClick={onRemove} />
      ) : (
        <span />
      )}
      </div>
    </>
  )
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
            expiry_date: defaultExpiryDate(),
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
          {user ? (
            <Form.Item label="Инициатор">
              <Typography.Text>
                {formatInitiator(user.full_name, user.department)}
              </Typography.Text>
            </Form.Item>
          ) : null}
          {requestType === 'normative' ? (
            <Form.Item
              name="expiry_date"
              label="Срок действия"
              extra={EXPIRY_HINT}
              rules={[
                { required: true, message: 'Укажите срок действия' },
                {
                  validator: async (_, value: Dayjs | undefined) => {
                    if (isExpiryTooSoon(value)) {
                      return Promise.reject(new Error(EXPIRY_TOO_SOON))
                    }
                    if (isExpiryTooFar(value)) {
                      return Promise.reject(new Error(EXPIRY_ERROR))
                    }
                  },
                },
              ]}
            >
              <DatePicker
                style={{ width: '100%' }}
                disabledDate={(current) =>
                  Boolean(
                    current &&
                      (current.isBefore(minExpiryDate(), 'day') ||
                        current.isAfter(maxExpiryDate(), 'day')),
                  )
                }
              />
            </Form.Item>
          ) : null}
          <Typography.Title level={5}>Позиции</Typography.Title>
          <Alert
            type="info"
            showIcon
            message={PALLET_NORM_HINT}
            style={{ marginBottom: 12 }}
          />
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
              <div style={{ overflowX: 'auto' }}>
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: ITEM_GRID,
                    gap: 8,
                    marginBottom: 8,
                    fontWeight: 600,
                    minWidth: 1100,
                  }}
                >
                  <span>Артикул</span>
                  <span>Название</span>
                  <span>Склад</span>
                  <span>Кол-во</span>
                  <span>Ед</span>
                  <span>Категория</span>
                  <span>Удалённость</span>
                  <span>Потребность</span>
                  <span />
                </div>
                {fields.map((field) => (
                  <RequestItemRow
                    key={field.key}
                    field={field}
                    warehouses={warehouses}
                    canRemove={fields.length > 1}
                    onRemove={() => remove(field.name)}
                  />
                ))}
                <Button
                  type="dashed"
                  onClick={() => add({ unit: 'шт' })}
                  icon={<PlusOutlined />}
                  style={{ marginBottom: 16 }}
                >
                  Добавить позицию
                </Button>
              </div>
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
