import { describe, expect, it } from 'vitest'
import { ceilToPallet } from './pallet'

describe('ceilToPallet', () => {
  it('rounds up to the pallet step', () => {
    expect(ceilToPallet(10, 48)).toBe(48)
    expect(ceilToPallet(48, 48)).toBe(48)
    expect(ceilToPallet(49, 48)).toBe(96)
  })

  it('treats missing pallet qty as 1 piece', () => {
    expect(ceilToPallet(10, null)).toBe(10)
    expect(ceilToPallet(10.1, undefined)).toBe(11)
  })

  it('rounds tons up using piece weight and pallet qty', () => {
    expect(ceilToPallet(1, 756, 'т', 0.82)).toBe(1.23984)
    expect(ceilToPallet(1.23984, 756, 'т', 0.82)).toBe(1.23984)
    expect(ceilToPallet(0.0001, 1, 'т', 0.82)).toBe(0.00082)
  })
})
