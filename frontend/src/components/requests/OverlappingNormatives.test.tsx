import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { SendNormativeModal } from './OverlappingNormatives'

describe('SendNormativeModal', () => {
  it('starts with completion checked', () => {
    const onSubmit = vi.fn()
    render(
      <MemoryRouter>
        <SendNormativeModal
          open
          confirmLoading={false}
          requests={[
            {
              id: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
              created_at: '2026-10-01',
              expiry_date: '2026-12-31',
            },
          ]}
          onCancel={vi.fn()}
          onSubmit={onSubmit}
        />
      </MemoryRouter>,
    )

    const checkbox = screen.getByRole('checkbox')
    expect((checkbox as HTMLInputElement).checked).toBe(true)
    expect(
      screen.getByText(/Эти запросы завершатся в день утверждения экономистом/),
    ).toBeTruthy()
    expect(screen.queryByText(/Это увеличение по уже существующей позиции/)).toBeNull()

    fireEvent.click(checkbox)
    expect(
      screen.getByText(/Это увеличение по уже существующей позиции/),
    ).toBeTruthy()
    expect(
      screen.queryByText(/Эти запросы завершатся в день утверждения экономистом/),
    ).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: 'Отправить' }))
    expect(onSubmit).toHaveBeenCalledWith(false)
  })
})
