import { Select, Space, Spin } from 'antd'
import { useCallback, useEffect, useRef, useState } from 'react'
import { clientsApi } from '../../api/clients'
import type { ClientListItem } from '../../api/types'

interface ClientAutocompleteProps {
  value?: string
  onChange?: (id: string | undefined) => void
  disabled?: boolean
  pinned?: ClientListItem | null
}

function labelOf(client: ClientListItem): string {
  return `${client.client_code} — ${client.name}`
}

export function ClientAutocomplete({
  value,
  onChange,
  disabled,
  pinned,
}: ClientAutocompleteProps) {
  const [options, setOptions] = useState<ClientListItem[]>([])
  const [loading, setLoading] = useState(false)
  const timer = useRef<number | undefined>(undefined)

  const merge = useCallback(
    (items: ClientListItem[]) => {
      const next = pinned ? [pinned, ...items.filter((item) => item.id !== pinned.id)] : items
      setOptions(next)
    },
    [pinned],
  )

  const search = useCallback(
    async (term?: string) => {
      setLoading(true)
      try {
        const { data } = await clientsApi.list({
          q: term || undefined,
          is_active: true,
          limit: 20,
        })
        merge(data.data)
      } catch {
        merge([])
      } finally {
        setLoading(false)
      }
    },
    [merge],
  )

  useEffect(() => {
    void search()
  }, [search])

  useEffect(() => {
    if (!value) {
      return
    }
    let cancelled = false
    void clientsApi
      .get(value)
      .then(({ data }) => {
        if (cancelled) {
          return
        }
        setOptions((prev) => {
          if (prev.some((item) => item.id === data.data.id)) {
            return prev
          }
          return [data.data, ...prev]
        })
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [value])

  return (
    <Select
      showSearch
      allowClear
      value={value}
      disabled={disabled}
      placeholder="Код КССС, ИНН или название"
      filterOption={false}
      loading={loading}
      style={{ minWidth: 280, width: '100%' }}
      notFoundContent={loading ? <Spin size="small" /> : 'Ничего не найдено'}
      optionLabelProp="label"
      options={options.map((client) => ({
        value: client.id,
        label: labelOf(client),
        client,
      }))}
      optionRender={(option) => {
        const client = option.data.client as ClientListItem
        return (
          <Space size={8}>
            <span>
              {client.client_code} — {client.name}
            </span>
            <span style={{ color: '#8c8c8c' }}>ИНН {client.inn}</span>
          </Space>
        )
      }}
      onSearch={(term) => {
        window.clearTimeout(timer.current)
        timer.current = window.setTimeout(() => {
          void search(term)
        }, 300)
      }}
      onChange={(id: string | undefined) => onChange?.(id)}
    />
  )
}
