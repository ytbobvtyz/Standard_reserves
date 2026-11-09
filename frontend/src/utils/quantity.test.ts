import { describe, expect, it } from 'vitest'
import { formatQuantity } from './quantity'

describe('formatQuantity', () => {
  it('formats tons with three decimals and pieces as integers', () => {
    expect(formatQuantity(1.2, 'т')).toBe('1.200')
    expect(formatQuantity(0.09, 'т')).toBe('0.090')
    expect(formatQuantity(90.5, 'шт')).toBe('91')
    expect(formatQuantity(800, 'шт')).toBe('800')
  })

  it('shows a dash when the value is missing', () => {
    expect(formatQuantity(null, 'т')).toBe('—')
    expect(formatQuantity(undefined, 'шт')).toBe('—')
  })
})