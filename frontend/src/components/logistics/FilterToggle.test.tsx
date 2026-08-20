import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { FilterToggle } from './FilterToggle'

describe('FilterToggle', () => {
  it('renders three filter modes', () => {
    render(<FilterToggle value="all" onChange={() => undefined} />)
    expect(screen.getByText('Все запасы')).toBeTruthy()
    expect(screen.getByText('Только с нормативами')).toBeTruthy()
    expect(screen.getByText('Требуют пополнения')).toBeTruthy()
  })
})
