export function ceilToPallet(quantity: number, palletQty?: number | null): number {
  if (!Number.isFinite(quantity) || quantity <= 0) {
    return quantity
  }
  const step = palletQty != null && palletQty >= 1 ? palletQty : 1
  return Math.ceil(quantity / step) * step
}
