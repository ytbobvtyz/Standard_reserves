import { describe, expect, it } from 'vitest'
import {
  calculateRequirement,
  categoryLabel,
  distanceLabel,
  requirementTooltip,
} from './requirement'

describe('requirement helpers', () => {
  it('multiplies quantity by category and distance factors', () => {
    expect(calculateRequirement(1000, 'A', false)).toBe(1000)
    expect(calculateRequirement(1000, 'B', false)).toBe(1500)
    expect(calculateRequirement(500, 'B', true)).toBe(1125)
  })

  it('formats category and distance labels', () => {
    expect(categoryLabel('A')).toBe('A (×1,0)')
    expect(categoryLabel('B')).toBe('B (×1,5)')
    expect(distanceLabel(false)).toBe('Нет (×1,0)')
    expect(distanceLabel(true)).toBe('Да (×1,5)')
  })

  it('builds a calculation tooltip', () => {
    const text = requirementTooltip(1000, 'шт', 'B', true)
    expect(text).toContain('категория B')
    expect(text).toContain('удалённый склад')
    expect(text).toContain('1,5')
    expect(text).toContain('шт')
  })
})
