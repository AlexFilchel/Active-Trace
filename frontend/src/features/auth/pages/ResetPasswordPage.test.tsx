import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import ResetPasswordPage from './ResetPasswordPage'

const BASE = 'http://localhost:8000'

function renderResetPage(search = '?token=valid-tok') {
  const qc = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return render(
    React.createElement(
      QueryClientProvider,
      { client: qc },
      React.createElement(
        MemoryRouter,
        { initialEntries: [`/reset${search}`] },
        React.createElement(
          Routes,
          null,
          React.createElement(Route, {
            path: '/reset',
            element: React.createElement(ResetPasswordPage),
          }),
          React.createElement(Route, { path: '/login', element: React.createElement('div', null, 'LoginPage') }),
        ),
      ),
    ),
  )
}

describe('ResetPasswordPage', () => {
  it('resets password with valid token and navigates to login', async () => {
    server.use(
      http.post(`${BASE}/api/auth/reset`, () => HttpResponse.json({ ok: true })),
    )
    renderResetPage('?token=valid-tok')
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText(/nueva contraseña|new password/i), 'NewPass1!')
    await user.click(screen.getByRole('button', { name: /restablecer|reset|guardar/i }))

    expect(await screen.findByText('LoginPage')).toBeInTheDocument()
  })

  it('shows error on invalid token (triangulate)', async () => {
    server.use(
      http.post(`${BASE}/api/auth/reset`, () =>
        HttpResponse.json({ detail: 'Token inválido' }, { status: 400 }),
      ),
    )
    renderResetPage('?token=bad-tok')
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText(/nueva contraseña|new password/i), 'NewPass1!')
    await user.click(screen.getByRole('button', { name: /restablecer|reset|guardar/i }))

    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })
})
