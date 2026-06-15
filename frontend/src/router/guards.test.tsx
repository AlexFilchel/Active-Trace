import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import {
  clearSession,
  setAccessToken,
} from '@/features/auth/services/sessionStore'

function makeToken(roles = ['ADMIN'], exp = 9999999999): string {
  const payload = btoa(JSON.stringify({ sub: 'u1', tenant_id: 'ten-1', roles, exp }))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '')
  return `header.${payload}.sig`
}

function wrapper(children: React.ReactNode) {
  const qc = new QueryClient()
  return render(
    React.createElement(
      QueryClientProvider,
      { client: qc },
      children,
    ),
  )
}

describe('RequireAuth guard', () => {
  beforeEach(() => {
    clearSession()
    localStorage.clear()
  })

  it('redirects to /login when no session exists', async () => {
    const { RequireAuth } = await import('./guards')

    wrapper(
      React.createElement(
        MemoryRouter,
        { initialEntries: ['/dashboard'] },
        React.createElement(
          Routes,
          null,
          React.createElement(Route, { path: '/login', element: React.createElement('div', null, 'LoginPage') }),
          React.createElement(
            Route,
            {
              path: '/dashboard',
              element: React.createElement(
                RequireAuth,
                null,
                React.createElement('div', null, 'Protected Content'),
              ),
            },
          ),
        ),
      ),
    )

    expect(await screen.findByText('LoginPage')).toBeInTheDocument()
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
  })

  it('renders content when session exists (triangulate)', async () => {
    setAccessToken(makeToken())
    const { RequireAuth } = await import('./guards')

    wrapper(
      React.createElement(
        MemoryRouter,
        { initialEntries: ['/dashboard'] },
        React.createElement(
          Routes,
          null,
          React.createElement(Route, { path: '/login', element: React.createElement('div', null, 'LoginPage') }),
          React.createElement(
            Route,
            {
              path: '/dashboard',
              element: React.createElement(
                RequireAuth,
                null,
                React.createElement('div', null, 'Protected Content'),
              ),
            },
          ),
        ),
      ),
    )

    expect(await screen.findByText('Protected Content')).toBeInTheDocument()
    expect(screen.queryByText('LoginPage')).not.toBeInTheDocument()
  })
})

describe('RequireRole guard', () => {
  beforeEach(() => {
    clearSession()
    localStorage.clear()
  })

  it('shows no-access when session lacks required role', async () => {
    setAccessToken(makeToken(['ALUMNO']))
    const { RequireRole } = await import('./guards')

    wrapper(
      React.createElement(
        MemoryRouter,
        { initialEntries: ['/admin'] },
        React.createElement(
          Routes,
          null,
          React.createElement(
            Route,
            {
              path: '/admin',
              element: React.createElement(
                RequireRole,
                { roles: ['ADMIN'] },
                React.createElement('div', null, 'Admin Panel'),
              ),
            },
          ),
        ),
      ),
    )

    await waitFor(() => {
      expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
    })
    expect(screen.getByRole('heading', { name: /sin acceso|no access|acceso denegado/i })).toBeInTheDocument()
  })

  it('renders content when session has required role (triangulate)', async () => {
    setAccessToken(makeToken(['ADMIN', 'COORDINADOR']))
    const { RequireRole } = await import('./guards')

    wrapper(
      React.createElement(
        MemoryRouter,
        { initialEntries: ['/admin'] },
        React.createElement(
          Routes,
          null,
          React.createElement(
            Route,
            {
              path: '/admin',
              element: React.createElement(
                RequireRole,
                { roles: ['ADMIN'] },
                React.createElement('div', null, 'Admin Panel'),
              ),
            },
          ),
        ),
      ),
    )

    expect(await screen.findByText('Admin Panel')).toBeInTheDocument()
  })
})
