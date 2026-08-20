import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { DeficitIndicator } from './DeficitIndicator'

describe('DeficitIndicator', () => {
  it('renders warning deficit in red', () => {
    render(<DeficitIndicator deficit={400} status="warning" unit="шт" />)
    expect(screen.getByText(/400/)).toBeTruthy()
  })

  it('renders zero deficit as ok', () => {
    render(<DeficitIndicator deficit={0} />)
    expect(screen.getByText('0')).toBeTruthy()
  })
})
