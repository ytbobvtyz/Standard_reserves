import {
  Button,
  Checkbox,
  Input,
  Pagination,
  Select,
  Space,
  Typography,
  message,
} from 'antd'
import { DownloadOutlined, PlusOutlined } from '@ant-design/icons'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { requestsApi } from '../api/requests'
import { getApiErrorMessage } from '../api/client'
import type { RequestListItem, RequestStatus, RequestType } from '../api/types'
import { RequestCard } from '../components/requests/RequestCard'
import { useAuthStore } from '../stores/auth'
import { downloadBlob, filenameFromContentDisposition } from '../utils/download'
import { canDeleteByStatus } from '../utils/requestActions'

const STATUS_OPTIONS: Array<{ value: RequestStatus; label: string }> = [
  { value: 'draft', label: 'Черновик' },
  { value: 'pp_approved', label: 'Ожидает ПП' },
  { value: 'economy_check', label: 'Ожидает экономиста' },
  { value: 'active', label: 'Активен' },
  { value: 'approved', label: 'Согласован' },
  { value: 'rejected', label: 'Отклонен' },
  { value: 'expired', label: 'Просрочен' },
  { value: 'executed', label: 'Исполнен' },
]

export function MyRequestsPage() {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const canCreate = user?.role === 'commercial' || user?.role === 'logistics'
  const title =
    user?.role === 'pp' || user?.role === 'economist' || user?.role === 'logistics'
      ? 'Запросы'
      : 'Мои запросы'

  const [items, setItems] = useState<RequestListItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<RequestStatus | undefined>()
  const [type, setType] = useState<RequestType | undefined>()
  const [clientName, setClientName] = useState('')
  const [page, setPage] = useState(1)
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [exporting, setExporting] = useState(false)
  const [selectingAll, setSelectingAll] = useState(false)
  const selectionRequest = useRef(0)
  const limit = 10
  const canExport = user?.role === 'commercial' || user?.role === 'logistics'
  const allSelected = total > 0 && selectedIds.length >= total
  const someSelected = selectedIds.length > 0 && !allSelected

  const clearSelection = () => {
    selectionRequest.current += 1
    setSelectingAll(false)
    setSelectedIds([])
  }

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await requestsApi.list({
        status,
        type,
        client_name: clientName || undefined,
        page,
        limit,
      })
      setItems(data.data)
      setTotal(data.meta?.total ?? data.data.length)
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось загрузить запросы'))
    } finally {
      setLoading(false)
    }
  }, [status, type, clientName, page])

  useEffect(() => {
    void load()
  }, [load])

  const toggleAll = async (checked: boolean) => {
    const requestId = ++selectionRequest.current
    if (!checked) {
      setSelectedIds([])
      return
    }
    if (total > 0 && items.length >= total) {
      setSelectedIds(items.map((item) => item.id))
      return
    }
    setSelectingAll(true)
    try {
      const ids: string[] = []
      let pageNumber = 1
      let expected = 0
      do {
        const { data } = await requestsApi.list({
          status,
          type,
          client_name: clientName || undefined,
          page: pageNumber,
          limit: 200,
        })
        expected = data.meta?.total ?? data.data.length
        if (data.data.length === 0) {
          break
        }
        ids.push(...data.data.map((item) => item.id))
        pageNumber += 1
      } while (ids.length < expected)
      if (selectionRequest.current !== requestId) {
        return
      }
      setSelectedIds([...new Set(ids)])
    } catch (error) {
      if (selectionRequest.current === requestId) {
        message.error(getApiErrorMessage(error, 'Не удалось выбрать запросы'))
      }
    } finally {
      if (selectionRequest.current === requestId) {
        setSelectingAll(false)
      }
    }
  }

  const exportSelected = async () => {
    if (selectedIds.length === 0) {
      return
    }
    setExporting(true)
    try {
      const { data, headers } = await requestsApi.exportExcel(selectedIds)
      const filename =
        filenameFromContentDisposition(headers['content-disposition']) ??
        `requests_export_${new Date().toISOString().slice(0, 10)}.xlsx`
      downloadBlob(data, filename)
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось выгрузить запросы'))
    } finally {
      setExporting(false)
    }
  }

  const remove = async (id: string) => {
    try {
      await requestsApi.remove(id)
      message.success('Запрос удален')
      await load()
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Не удалось удалить запрос'))
    }
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Space style={{ justifyContent: 'space-between', width: '100%' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>
          {title}
        </Typography.Title>
        <Space>
          {canExport ? (
            <Button
              icon={<DownloadOutlined />}
              disabled={selectedIds.length === 0}
              loading={exporting}
              onClick={() => void exportSelected()}
            >
              Выгрузить в Excel
            </Button>
          ) : null}
          {canCreate ? (
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => navigate('/requests/create')}
            >
              Создать запрос
            </Button>
          ) : null}
        </Space>
      </Space>
      <Space wrap>
        <Select
          allowClear
          placeholder="Статус"
          style={{ width: 200 }}
          value={status}
          onChange={(value) => {
            setPage(1)
            clearSelection()
            setStatus(value)
          }}
          options={STATUS_OPTIONS}
        />
        <Select
          allowClear
          placeholder="Тип"
          style={{ width: 180 }}
          value={type}
          onChange={(value) => {
            setPage(1)
            clearSelection()
            setType(value)
          }}
          options={[
            { value: 'normative', label: 'Норматив' },
            { value: 'one_time', label: 'Разовое' },
          ]}
        />
        <Input.Search
          allowClear
          placeholder="Клиент"
          style={{ width: 240 }}
          onSearch={(value) => {
            setPage(1)
            clearSelection()
            setClientName(value)
          }}
        />
      </Space>
      {canExport && items.length > 0 ? (
        <Checkbox
          indeterminate={someSelected}
          checked={allSelected}
          disabled={selectingAll}
          onChange={(event) => void toggleAll(event.target.checked)}
        >
          Выбрать все
        </Checkbox>
      ) : null}
      {loading ? <Typography.Text type="secondary">Загрузка...</Typography.Text> : null}
      {!loading && items.length === 0 ? (
        <Typography.Text type="secondary">Запросы не найдены</Typography.Text>
      ) : null}
      {items.map((item) => (
        <RequestCard
          key={item.id}
          request={item}
          canDelete={
            Boolean(user && user.id === item.initiator.id && canDeleteByStatus(item.status))
          }
          onDelete={() => void remove(item.id)}
          selected={selectedIds.includes(item.id)}
          onSelectedChange={
            canExport
              ? (checked) =>
                  setSelectedIds((current) =>
                    checked
                      ? [...current, item.id]
                      : current.filter((id) => id !== item.id),
                  )
              : undefined
          }
        />
      ))}
      <Pagination
        current={page}
        pageSize={limit}
        total={total}
        onChange={setPage}
        hideOnSinglePage
      />
    </Space>
  )
}
