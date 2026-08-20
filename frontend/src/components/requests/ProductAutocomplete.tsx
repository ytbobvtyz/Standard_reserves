import { Select, Spin } from 'antd'
import { useEffect, useRef, useState } from 'react'
import { referencesApi } from '../../api/references'
import type { ProductListItem } from '../../api/types'

interface ProductAutocompleteProps {
  value?: number
  onChange?: (code: number | undefined, product?: ProductListItem | null) => void
  disabled?: boolean
  activeOnly?: boolean
}

export function ProductAutocomplete({
  value,
  onChange,
  disabled,
  activeOnly = true,
}: ProductAutocompleteProps) {
  const [options, setOptions] = useState<ProductListItem[]>([])
  const [loading, setLoading] = useState(false)
  const timer = useRef<number | undefined>(undefined)

  const search = async (term?: string) => {
    setLoading(true)
    try {
      const { data } = await referencesApi.getProducts({
        search: term || undefined,
        is_active: activeOnly ? true : undefined,
        limit: 20,
      })
      setOptions(data.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void search()
  }, [])

  useEffect(() => {
    if (!value) {
      return
    }
    void referencesApi.getProduct(value).then(({ data }) => {
      setOptions((prev) => {
        if (prev.some((item) => item.code === data.data.code)) {
          return prev
        }
        return [data.data, ...prev]
      })
    })
  }, [value])

  return (
    <Select
      showSearch
      allowClear
      value={value}
      disabled={disabled}
      placeholder="Артикул или название"
      filterOption={false}
      loading={loading}
      notFoundContent={loading ? <Spin size="small" /> : 'Ничего не найдено'}
      options={options.map((product) => ({
        value: product.code,
        label: `${product.code} — ${product.name}`,
      }))}
      onSearch={(term) => {
        window.clearTimeout(timer.current)
        timer.current = window.setTimeout(() => {
          void search(term)
        }, 300)
      }}
      onChange={(code: number | undefined) => {
        const product = options.find((item) => item.code === code) ?? null
        onChange?.(code, product)
      }}
    />
  )
}
