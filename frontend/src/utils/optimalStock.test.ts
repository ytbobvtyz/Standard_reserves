import { describe, expect, it } from 'vitest'
import { kgToRequestQuantity } from './optimalStock'

describe('kgToRequestQuantity', () => {
  it('converts kilograms to tons and pieces', () => {
    expect(kgToRequestQuantity(90.5, 'т', 0.25)).toBe(0.0905)
    expect(kgToRequestQuantity(90, 'шт', 0.25)).toBe(360)
  })

  it('returns null when piece weight is missing', () => {
    expect(kgToRequestQuantity(90, 'шт', 0)).toBeNull()
    expect(kgToRequestQuantity(90, 'шт', null)).toBeNull()
  })
})
