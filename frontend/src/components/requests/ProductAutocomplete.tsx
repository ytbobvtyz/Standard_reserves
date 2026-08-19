import { Select, Spin } from 'antd'
import { useEffect, useRef, useState } from 'react'
import { referencesApi } from '../../api/references'
import type { ProductListItem } from '../../api/types'

interface ProductAutocompleteProps {
  value?: number
  onChange?: (code: number | undefined, product?: ProductListItem | null) => void
  disabled?: boolean
}

export function ProductAutocomplete({
  value,
  onChange,
  disabled,
}: ProductAutocompleteProps) {
  const [options, setOptions] = useState<ProductListItem[]>([])
  const [loading, setLoading] = useState(false)
  const timer = useRef<number | undefined>(undefined)

  const search = async (term?: string) => {
    setLoading(true)
    try {
      const { data } = await referencesApi.getProducts({
        search: term || undefined,
        is_active: true,
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
