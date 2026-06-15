import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { clearSession, getAccessToken } from '@/features/auth/services/sessionStore'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import TwoFactorPage from './TwoFactorPage'

const BASE = 'http://localhost:8000'

function makeToken(): string {
  const payload = btoa(
    JSON.stringify({ sub: 'u1', tenant_id: 'ten-1', roles: ['ADMIN'], exp: 9999999999 }),
  )
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '')
  return `header.${payload}.sig`
}

function renderTwoFactorPage() {
  const qc = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return render(
    React.createElement(
      QueryClientProvider,
      { client: qc },
      React.createElement(
        MemoryRouter,
        { initialEntries: [{ pathname: '/2fa', state: { challengeToken: 'ch-test' } }] },
        React.createElement(
          Routes,
          null,
          React.createElement(Route, {
            path: '/2fa',
            element: React.createElement(TwoFactorPage),
          }),
          React.createElement(Route, { path: '/dashboard', element: React.createElement('div', null, 'Dashboard') }),
        ),
      ),
    ),
  )
}

describe('TwoFactorPage', () => {
  beforeEach(() => {
    clearSession()
    localStorage.clear()
  })

  it('establishes session on valid TOTP code', async () => {
    const access = makeToken()
    server.use(
      http.post(`${BASE}/api/auth/2fa/verify-login`, () =>
        HttpResponse.json({ access_token: access, refresh_token: 'rt-2fa', token_type: 'bearer' }),
      ),
    )
    renderTwoFactorPage()
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText(/código|code/i), '123456')
    await user.click(screen.getByRole('button', { name: /verificar|verify|confirmar/i }))

    await waitFor(() => expect(getAccessToken()).toBe(access))
    expect(await screen.findByText('Dashboard')).toBeInTheDocument()
  })

  it('shows error on invalid code (triangulate)', async () => {
    server.use(
      http.post(`${BASE}/api/auth/2fa/verify-login`, () =>
        HttpResponse.json({ detail: 'Código inválido' }, { status: 400 }),
      ),
    )
    renderTwoFactorPage()
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText(/código|code/i), '000000')
    await user.click(screen.getByRole('button', { name: /verificar|verify|confirmar/i }))

    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(getAccessToken()).toBeNull()
  })
})
