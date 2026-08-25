import { render, screen } from '@testing-library/react'
import { afterEach, describe, it, expect } from 'vitest'
import App from './App'

describe('App', () => {
  afterEach(() => {
    window.history.pushState({}, '', '/')
  })

  it('renders login page for unauthenticated user', () => {
    render(<App />)
    expect(screen.getByText('Standart Reserve')).toBeTruthy()
  })

  it('renders a 404 page for unknown routes', () => {
    window.history.pushState({}, '', '/unknown-route')
    render(<App />)
    expect(screen.getByText('404')).toBeTruthy()
    expect(screen.getByText('Страница не найдена')).toBeTruthy()
  })
})
