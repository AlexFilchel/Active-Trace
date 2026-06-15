import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { clearSession, getAccessToken } from '@/features/auth/services/sessionStore'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import LoginPage from './LoginPage'

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

function renderLoginPage(initialEntry = '/login') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(
    React.createElement(
      QueryClientProvider,
      { client: qc },
      React.createElement(
        MemoryRouter,
        { initialEntries: [initialEntry] },
        React.createElement(
          Routes,
          null,
          React.createElement(Route, {
            path: '/login',
            element: React.createElement(LoginPage),
          }),
          React.createElement(Route, { path: '/dashboard', element: React.createElement('div', null, 'Dashboard') }),
          React.createElement(Route, { path: '/2fa', element: React.createElement('div', null, 'TwoFactor') }),
        ),
      ),
    ),
  )
}

describe('LoginPage — render', () => {
  beforeEach(() => {
    clearSession()
    localStorage.clear()
  })

  it('renders email, password fields and submit button', async () => {
    renderLoginPage()
    expect(await screen.findByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/contraseña|password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /ingresar|login|entrar/i })).toBeInTheDocument()
  })
})

describe('LoginPage — login flow', () => {
  beforeEach(() => {
    clearSession()
    localStorage.clear()
  })

  it('establishes session and navigates to dashboard on valid credentials', async () => {
    const access = makeToken()
    server.use(
      http.post(`${BASE}/api/auth/login`, () =>
        HttpResponse.json({ access_token: access, refresh_token: 'rt-ok', token_type: 'bearer' }),
      ),
    )
    renderLoginPage()
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText(/email/i), 'user@test.com')
    await user.type(screen.getByLabelText(/contraseña|password/i), 'Password1!')
    await user.click(screen.getByRole('button', { name: /ingresar|login|entrar/i }))

    await waitFor(() => expect(getAccessToken()).toBe(access))
    expect(await screen.findByText('Dashboard')).toBeInTheDocument()
  })

  it('shows error message on invalid credentials (triangulate)', async () => {
    server.use(
      http.post(`${BASE}/api/auth/login`, () =>
        HttpResponse.json({ detail: 'Credenciales incorrectas' }, { status: 401 }),
      ),
    )
    renderLoginPage()
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText(/email/i), 'wrong@test.com')
    await user.type(screen.getByLabelText(/contraseña|password/i), 'wrongpass')
    await user.click(screen.getByRole('button', { name: /ingresar|login|entrar/i }))

    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(getAccessToken()).toBeNull()
  })

  it('navigates to 2FA page on requires_two_factor response (triangulate)', async () => {
    server.use(
      http.post(`${BASE}/api/auth/login`, () =>
        HttpResponse.json({
          requires_two_factor: true,
          challenge_token: 'ch-tok-abc',
          expires_in: 300,
        }),
      ),
    )
    renderLoginPage()
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText(/email/i), 'user2fa@test.com')
    await user.type(screen.getByLabelText(/contraseña|password/i), 'Pass1!')
    await user.click(screen.getByRole('button', { name: /ingresar|login|entrar/i }))

    expect(await screen.findByText('TwoFactor')).toBeInTheDocument()
    expect(getAccessToken()).toBeNull()
  })
})
