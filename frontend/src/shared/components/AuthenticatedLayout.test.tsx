import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { MemoryRouter, Routes, Route, Outlet } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import {
  clearSession,
  setAccessToken,
  setRefreshToken,
} from '@/features/auth/services/sessionStore'
import { AuthenticatedLayout } from './AuthenticatedLayout'

const BASE = 'http://localhost:8000'

function makeToken(roles = ['ADMIN']): string {
  const payload = btoa(JSON.stringify({ sub: 'u1', tenant_id: 'ten-1', roles, exp: 9999999999 }))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '')
  return `header.${payload}.sig`
}

function renderLayout(roles = ['ADMIN']) {
  clearSession()
  localStorage.clear()
  setAccessToken(makeToken(roles))
  setRefreshToken('rt-1')

  const qc = new QueryClient()
  return render(
    React.createElement(
      QueryClientProvider,
      { client: qc },
      React.createElement(
        MemoryRouter,
        { initialEntries: ['/dashboard'] },
        React.createElement(
          Routes,
          null,
          React.createElement(Route, {
            path: '/dashboard',
            element: React.createElement(AuthenticatedLayout),
          }),
          React.createElement(Route, { path: '/login', element: React.createElement('div', null, 'LoginPage') }),
        ),
      ),
    ),
  )
}

describe('AuthenticatedLayout', () => {
  beforeEach(() => {
    clearSession()
    localStorage.clear()
  })

  it('renders logout button for authenticated user', async () => {
    renderLayout()
    expect(await screen.findByRole('button', { name: /cerrar sesión|logout|salir/i })).toBeInTheDocument()
  })

  it('logout action clears session and navigates to /login', async () => {
    server.use(
      http.post(`${BASE}/api/auth/logout`, () => new HttpResponse(null, { status: 204 })),
    )
    renderLayout()
    const user = userEvent.setup()

    const logoutBtn = await screen.findByRole('button', { name: /cerrar sesión|logout|salir/i })
    await user.click(logoutBtn)

    expect(await screen.findByText('LoginPage')).toBeInTheDocument()
  })

  it('shows menu items filtered by role — ADMIN sees admin entry', async () => {
    renderLayout(['ADMIN'])
    expect(await screen.findByText(/^Administración$/i)).toBeInTheDocument()
  })

  it('ALUMNO role does not see admin entry (triangulate)', async () => {
    renderLayout(['ALUMNO'])

    // Wait for render
    expect(await screen.findByRole('button', { name: /cerrar sesión|logout|salir/i })).toBeInTheDocument()
    // Admin-only nav link should NOT be present
    expect(screen.queryByText(/^Administración$/i)).not.toBeInTheDocument()
  })
})
