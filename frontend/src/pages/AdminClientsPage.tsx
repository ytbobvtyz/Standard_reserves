import {
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  PlusOutlined,
  UploadOutlined,
} from '@ant-design/icons'
import {
  Alert,
  Button,
  Input,
  Popconfirm,
  Space,
  Table,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { UploadFile } from 'antd/es/upload/interface'
import { useCallback, useEffect, useState } from 'react'
import { adminApi } from '../api/admin'
import { clientsApi } from '../api/clients'
import { getApiErrorMessage } from '../api/client'
import type { ClientListItem, ClientUploadResult, DepartmentListItem } from '../api/types'
import {
  ClientFormModal,
  createClientFromForm,
  departmentIdFromForm,
  type ClientFormValues,
} from '../components/clients/ClientFormModal'
import { downloadBlob } from '../utils/download'

export function AdminClientsPage() {
  const [items, setItems] = useState<ClientListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [departments, setDepartments] = useState<DepartmentListItem[]>([])
  const [createOpen, setCreateOpen] = useState(false)
  const [editing, setEditing] = useState<ClientListItem | null>(null)
  const [saving, setSaving] = useState(false)
  const [uploadResult, setUploadResult] = useState<ClientUploadResult | null>(null)
  const [fileList, setFileList] = useState<UploadFile[]>([])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await clientsApi.list({
        q: query || undefined,
        include_inactive: true,
        page,
        limit: 20,
      })
      setItems(data.data)
      setTotal(data.meta?.total ?? data.data.length)
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось загрузить клиентов'))
    } finally {
      setLoading(false)
    }
  }, [query, page])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    void adminApi
      .getDepartments()
      .then(({ data }) => setDepartments(data.data))
      .catch(() => setDepartments([]))
  }, [])

  const createClient = async (values: ClientFormValues) => {
    setSaving(true)
    try {
      await createClientFromForm(values, 'create-admin')
      message.success('Клиент создан')
      setCreateOpen(false)
      await load()
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Не удалось создать клиента')
    } finally {
      setSaving(false)
    }
  }

  const saveClient = async (values: ClientFormValues) => {
    if (!editing) {
      return
    }
    setSaving(true)
    try {
      await clientsApi.update(editing.id, {
        name: values.name.trim(),
        kpp: values.kpp?.trim() || null,
        is_active: Boolean(values.is_active),
        department_id: departmentIdFromForm(values.department_id),
      })
      message.success('Клиент обновлён')
      setEditing(null)
      await load()
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось обновить клиента'))
    } finally {
      setSaving(false)
    }
  }

  const removeClient = async (id: string) => {
    try {
      await clientsApi.remove(id)
      message.success('Клиент удалён')
      await load()
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось удалить клиента'))
    }
  }

  const downloadTemplate = async () => {
    try {
      const { data } = await clientsApi.downloadTemplate()
      downloadBlob(data, 'clients-template.xlsx')
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось скачать шаблон'))
    }
  }

  const exportExcel = async () => {
    try {
      const { data } = await clientsApi.exportExcel()
      downloadBlob(data, 'clients.xlsx')
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось выгрузить клиентов'))
    }
  }

  const uploadExcel = async () => {
    const file = fileList[0]?.originFileObj
    if (!file) {
      message.error('Выберите Excel-файл')
      return
    }
    setSaving(true)
    try {
      const { data } = await clientsApi.upload(file)
      setUploadResult(data.data)
      setFileList([])
      message.success(data.data.message)
      await load()
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось загрузить файл'))
    } finally {
      setSaving(false)
    }
  }

  const columns: ColumnsType<ClientListItem> = [
    { title: 'КССС', dataIndex: 'client_code', width: 140 },
    { title: 'ИНН', dataIndex: 'inn', width: 140 },
    { title: 'Наименование', dataIndex: 'name' },
    { title: 'КПП', dataIndex: 'kpp', width: 120, render: (value?: string | null) => value || '—' },
    {
      title: 'Управление продаж',
      dataIndex: 'department_name',
      render: (value?: string | null) => value || 'Без управления',
    },
    {
      title: 'Статус',
      dataIndex: 'is_active',
      width: 120,
      render: (value: boolean) => (
        <Tag color={value ? 'green' : 'default'}>{value ? 'Активен' : 'Неактивен'}</Tag>
      ),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 110,
      render: (_value, record) => {
        if (record.is_system) {
          return null
        }
        return (
          <Space>
            <Button
              type="text"
              aria-label={`Изменить ${record.name}`}
              icon={<EditOutlined aria-hidden />}
              onClick={() => setEditing(record)}
            />
            <Popconfirm
              title={`Удалить «${record.name}»?`}
              okText="Удалить"
              cancelText="Отмена"
              okButtonProps={{ danger: true }}
              onConfirm={() => void removeClient(record.id)}
            >
              <Button
                type="text"
                danger
                aria-label={`Удалить ${record.name}`}
                icon={<DeleteOutlined aria-hidden />}
              />
            </Popconfirm>
          </Space>
        )
      },
    },
  ]

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={3}>Клиенты</Typography.Title>
      <Space wrap>
        <Input.Search
          allowClear
          placeholder="КССС, ИНН или название"
          style={{ width: 320 }}
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          onSearch={(value) => {
            setPage(1)
            setQuery(value.trim())
          }}
        />
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
          Создать
        </Button>
        <Button icon={<DownloadOutlined />} onClick={() => void exportExcel()}>
          Выгрузить в Excel
        </Button>
        <Button icon={<DownloadOutlined />} onClick={() => void downloadTemplate()}>
          Скачать шаблон
        </Button>
      </Space>
      <Space wrap>
        <Upload
          accept=".xlsx"
          maxCount={1}
          fileList={fileList}
          beforeUpload={() => false}
          onChange={({ fileList: next }) => setFileList(next.slice(-1))}
        >
          <Button icon={<UploadOutlined />}>Выбрать Excel</Button>
        </Upload>
        <Button loading={saving} onClick={() => void uploadExcel()}>
          Загрузить из Excel
        </Button>
      </Space>
      {uploadResult ? (
        <Alert
          type={uploadResult.errors > 0 ? 'warning' : 'success'}
          message={`Загружено ${uploadResult.created}, ошибок ${uploadResult.errors}`}
          description={
            uploadResult.error_details.length > 0
              ? uploadResult.error_details
                  .map((item) => `Строка ${item.row}: ${item.message}`)
                  .join('\n')
              : undefined
          }
        />
      ) : null}
      <Table
        rowKey="id"
        loading={loading}
        dataSource={items}
        columns={columns}
        pagination={{
          current: page,
          pageSize: 20,
          total,
          showSizeChanger: false,
          onChange: (next) => setPage(next),
        }}
      />
      <ClientFormModal
        open={createOpen}
        mode="create-admin"
        canCreate
        departments={departments}
        confirmLoading={saving}
        onCancel={() => setCreateOpen(false)}
        onSubmit={createClient}
      />
      <ClientFormModal
        open={editing != null}
        mode="edit"
        client={editing}
        canCreate
        departments={departments}
        confirmLoading={saving}
        onCancel={() => setEditing(null)}
        onSubmit={saveClient}
      />
    </Space>
  )
}
