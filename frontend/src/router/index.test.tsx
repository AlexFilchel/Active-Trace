import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from 'react-router-dom'
import React from 'react'
import { clearSession, setAccessToken } from '@/features/auth/services/sessionStore'
import { createAppRouter } from './index'

function makeToken(): string {
  const payload = btoa(
    JSON.stringify({ sub: 'u1', tenant_id: 'ten-1', roles: ['ADMIN'], exp: 9999999999 }),
  )
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '')
  return `header.${payload}.sig`
}

describe('App router', () => {
  beforeEach(() => {
    clearSession()
    localStorage.clear()
  })

  it('private route without session redirects to /login', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const router = createAppRouter({ initialPath: '/dashboard' })
    render(
      React.createElement(
        QueryClientProvider,
        { client: qc },
        React.createElement(RouterProvider, { router }),
      ),
    )

    // Should redirect to login and render the login form
    expect(await screen.findByRole('button', { name: /ingresar|login|entrar/i }, { timeout: 8000 })).toBeInTheDocument()
  })

  it('public /login route renders without redirect', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const router = createAppRouter({ initialPath: '/login' })
    render(
      React.createElement(
        QueryClientProvider,
        { client: qc },
        React.createElement(RouterProvider, { router }),
      ),
    )

    expect(await screen.findByRole('button', { name: /ingresar|login|entrar/i }, { timeout: 8000 })).toBeInTheDocument()
  })
})
