import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { NotFoundPage } from './NotFoundPage'
import { ServerErrorPage } from './ServerErrorPage'

describe('error pages', () => {
  it('renders a 404 page', () => {
    render(
      <MemoryRouter>
        <NotFoundPage />
      </MemoryRouter>,
    )
    expect(screen.getByText('404')).toBeTruthy()
    expect(screen.getByText('Страница не найдена')).toBeTruthy()
  })

  it('renders a 500 page', () => {
    render(<ServerErrorPage />)
    expect(screen.getByText('500')).toBeTruthy()
    expect(screen.getByText(/Внутренняя ошибка сервера/)).toBeTruthy()
  })
})
