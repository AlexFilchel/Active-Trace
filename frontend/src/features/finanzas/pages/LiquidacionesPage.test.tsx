import { describe, it, expect, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import React from 'react'
import { LiquidacionesPage } from './LiquidacionesPage'

const BASE = 'http://localhost:8000'

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children)
}

afterEach(() => server.resetHandlers())

const mockLiquidacion = {
  id: 'l1',
  periodo: '2024-06',
  estado: 'ABIERTA',
  total_honorarios: 5000,
  total_docentes: 3,
  detalles: [],
}

function setupDefaultHandlers() {
  server.use(
    http.get(`${BASE}/api/liquidaciones`, () => HttpResponse.json([mockLiquidacion])),
    http.get(`${BASE}/api/liquidaciones/historial`, () => HttpResponse.json([])),
    http.get(`${BASE}/api/salarios/grilla`, () => HttpResponse.json([])),
    http.get(`${BASE}/api/facturas`, () => HttpResponse.json([])),
  )
}

describe('LiquidacionesPage', () => {
  it('renders page title', async () => {
    setupDefaultHandlers()
    const Wrapper = makeWrapper()
    render(React.createElement(Wrapper, null, React.createElement(LiquidacionesPage)))
    expect(screen.getByText('Liquidaciones')).toBeInTheDocument()
  })

  it('shows KPI data after loading', async () => {
    setupDefaultHandlers()
    const Wrapper = makeWrapper()
    render(React.createElement(Wrapper, null, React.createElement(LiquidacionesPage)))
    await waitFor(() => {
      expect(screen.getByText('3')).toBeInTheDocument()
      expect(screen.getByText('ABIERTA')).toBeInTheDocument()
    })
  })

  it('shows Cerrar liquidacion button when liquidacion is ABIERTA', async () => {
    setupDefaultHandlers()
    const Wrapper = makeWrapper()
    render(React.createElement(Wrapper, null, React.createElement(LiquidacionesPage)))
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /cerrar liquidación/i })).toBeInTheDocument()
    }, { timeout: 5000 })
  })

  it('switches to Historial tab on click (triangulate)', async () => {
    setupDefaultHandlers()
    const Wrapper = makeWrapper()
    render(React.createElement(Wrapper, null, React.createElement(LiquidacionesPage)))
    fireEvent.click(screen.getByRole('button', { name: 'Historial' }))
    await waitFor(() => {
      expect(screen.getByText(/no hay liquidaciones anteriores/i)).toBeInTheDocument()
    })
  })

  it('switches to Grilla Salarial tab (triangulate)', async () => {
    setupDefaultHandlers()
    const Wrapper = makeWrapper()
    render(React.createElement(Wrapper, null, React.createElement(LiquidacionesPage)))
    fireEvent.click(screen.getByRole('button', { name: 'Grilla Salarial' }))
    await waitFor(() => {
      expect(screen.getByText(/no hay categorías/i)).toBeInTheDocument()
    })
  })
})
