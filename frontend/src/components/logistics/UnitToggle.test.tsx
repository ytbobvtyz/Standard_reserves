import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { UnitToggle } from './UnitToggle'

describe('UnitToggle', () => {
  it('renders piece and ton options', () => {
    render(<UnitToggle value="шт" onChange={() => undefined} />)
    expect(screen.getByText('Единицы измерения:')).toBeTruthy()
    expect(screen.getByText('шт')).toBeTruthy()
    expect(screen.getByText('тонны')).toBeTruthy()
  })
})
