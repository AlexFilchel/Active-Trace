import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import ForgotPasswordPage from './ForgotPasswordPage'

const BASE = 'http://localhost:8000'

function renderForgotPage() {
  const qc = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return render(
    React.createElement(
      QueryClientProvider,
      { client: qc },
      React.createElement(
        MemoryRouter,
        { initialEntries: ['/forgot'] },
        React.createElement(
          Routes,
          null,
          React.createElement(Route, {
            path: '/forgot',
            element: React.createElement(ForgotPasswordPage),
          }),
        ),
      ),
    ),
  )
}

describe('ForgotPasswordPage', () => {
  it('shows neutral confirmation after submit regardless of email existence', async () => {
    server.use(
      http.post(`${BASE}/api/auth/forgot`, () => new HttpResponse(null, { status: 202 })),
    )
    renderForgotPage()
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText(/email/i), 'any@example.com')
    await user.click(screen.getByRole('button', { name: /enviar|send|recuperar/i }))

    expect(await screen.findByRole('heading', { name: /revis.* tu email|check your email/i })).toBeInTheDocument()
  })
})
