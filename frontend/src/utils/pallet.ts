export type PalletUnit = 'шт' | 'т'

const KG_IN_TON = 1000

export function ceilToPallet(
  quantity: number,
  palletQty?: number | null,
  unit: PalletUnit = 'шт',
  weightKg?: number | null,
): number {
  if (!Number.isFinite(quantity) || quantity <= 0) {
    return quantity
  }
  const stepPcs = palletQty != null && palletQty >= 1 ? palletQty : 1
  const qtyPcs = toPieces(quantity, unit, weightKg)
  const multiples = Math.max(1, Math.ceil(qtyPcs / stepPcs - 1e-8))
  const roundedPcs = multiples * stepPcs
  return fromPieces(roundedPcs, unit, weightKg)
}

function toPieces(quantity: number, unit: PalletUnit, weightKg?: number | null): number {
  if (unit !== 'т' || weightKg == null || weightKg <= 0) {
    return quantity
  }
  return (quantity * KG_IN_TON) / weightKg
}

function fromPieces(pieces: number, unit: PalletUnit, weightKg?: number | null): number {
  if (unit !== 'т' || weightKg == null || weightKg <= 0) {
    return pieces
  }
  return Number(((pieces * weightKg) / KG_IN_TON).toFixed(6))
}
