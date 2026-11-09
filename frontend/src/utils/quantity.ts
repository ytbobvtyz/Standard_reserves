export function formatQuantity(
  value: number | null | undefined,
  unit: string,
): string {
  if (value === null || value === undefined) {
    return '—'
  }
  if (unit === 'т') {
    return value.toFixed(3)
  }
  return Math.round(value).toString()
}
