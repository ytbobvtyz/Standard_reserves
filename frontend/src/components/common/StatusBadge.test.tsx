import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { StatusBadge } from './StatusBadge'

describe('StatusBadge', () => {
  it('renders draft status label', () => {
    render(<StatusBadge status="draft" />)
    expect(screen.getByText('Черновик')).toBeTruthy()
  })

  it('renders submitted status label', () => {
    render(<StatusBadge status="pp_approved" />)
    expect(screen.getByText('Ожидает ПП')).toBeTruthy()
  })
})
