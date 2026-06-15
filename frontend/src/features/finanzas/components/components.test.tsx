import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'

afterEach(() => vi.clearAllMocks())

// ── 1.8 KPIsLiquidacion ───────────────────────────────────────────────────────
describe('KPIsLiquidacion', () => {
  it('renders KPI data when liquidacion is provided', async () => {
    const { KPIsLiquidacion } = await import('./KPIsLiquidacion')
    const liq = { id: 'l1', periodo: '2024-06', estado: 'ABIERTA' as const, total_honorarios: 5000, total_docentes: 3 }
    render(React.createElement(KPIsLiquidacion, { liquidacion: liq }))
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('ABIERTA')).toBeInTheDocument()
  })

  it('renders loading skeleton when isLoading (triangulate)', async () => {
    const { KPIsLiquidacion } = await import('./KPIsLiquidacion')
    const { container } = render(React.createElement(KPIsLiquidacion, { liquidacion: undefined, isLoading: true }))
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0)
  })

  it('renders no-data message when liquidacion is undefined (triangulate)', async () => {
    const { KPIsLiquidacion } = await import('./KPIsLiquidacion')
    render(React.createElement(KPIsLiquidacion, { liquidacion: undefined }))
    expect(screen.getByText(/sin datos/i)).toBeInTheDocument()
  })
})

// ── 1.9 TablaDetalleLiquidacion ──────────────────────────────────────────────
describe('TablaDetalleLiquidacion', () => {
  const detalles = [
    { id: 'd1', docente_nombre: 'Ana García', docente_email: 'ana@test.com', categoria: 'JTP', horas: 20, salario_base: 2000, total: 3000, segmento: 'general' as const },
    { id: 'd2', docente_nombre: 'Carlos Ruiz', docente_email: 'carlos@test.com', categoria: 'Titular', horas: 10, salario_base: 5000, total: 4500, segmento: 'nexo' as const },
  ]

  it('renders all rows when no segmento filter', async () => {
    const { TablaDetalleLiquidacion } = await import('./TablaDetalleLiquidacion')
    render(React.createElement(TablaDetalleLiquidacion, { detalles }))
    expect(screen.getByText('Ana García')).toBeInTheDocument()
    expect(screen.getByText('Carlos Ruiz')).toBeInTheDocument()
  })

  it('filters rows by segmento (triangulate)', async () => {
    const { TablaDetalleLiquidacion } = await import('./TablaDetalleLiquidacion')
    render(React.createElement(TablaDetalleLiquidacion, { detalles, segmento: 'general' }))
    expect(screen.getByText('Ana García')).toBeInTheDocument()
    expect(screen.queryByText('Carlos Ruiz')).not.toBeInTheDocument()
  })

  it('renders empty state when no detalles (triangulate)', async () => {
    const { TablaDetalleLiquidacion } = await import('./TablaDetalleLiquidacion')
    render(React.createElement(TablaDetalleLiquidacion, { detalles: [] }))
    expect(screen.getByText(/no hay registros/i)).toBeInTheDocument()
  })
})

// ── 1.10 HistorialLiquidaciones ──────────────────────────────────────────────
describe('HistorialLiquidaciones', () => {
  it('renders historial rows', async () => {
    const { HistorialLiquidaciones } = await import('./HistorialLiquidaciones')
    const historial = [
      { id: 'h1', periodo: '2024-05', estado: 'CERRADA' as const, total_honorarios: 4000, total_docentes: 2 },
    ]
    render(React.createElement(HistorialLiquidaciones, { historial }))
    expect(screen.getByText('2024-05')).toBeInTheDocument()
    expect(screen.getByText('CERRADA')).toBeInTheDocument()
  })

  it('renders empty state when historial is empty (triangulate)', async () => {
    const { HistorialLiquidaciones } = await import('./HistorialLiquidaciones')
    render(React.createElement(HistorialLiquidaciones, { historial: [] }))
    expect(screen.getByText(/no hay liquidaciones anteriores/i)).toBeInTheDocument()
  })
})

// ── 1.11 GrillaSalarial + FormularioGrilla ────────────────────────────────────
describe('GrillaSalarial', () => {
  const grillas = [{ id: 'g1', categoria: 'JTP', salario_base: 2000 }]

  it('renders rows with edit and delete buttons', async () => {
    const { GrillaSalarial } = await import('./GrillaSalarial')
    render(React.createElement(GrillaSalarial, {
      grillas,
      onCrear: vi.fn(),
      onEditar: vi.fn(),
      onEliminar: vi.fn(),
    }))
    expect(screen.getByText('JTP')).toBeInTheDocument()
    expect(screen.getByText('Editar')).toBeInTheDocument()
    expect(screen.getByText('Eliminar')).toBeInTheDocument()
  })

  it('renders empty state when no grillas (triangulate)', async () => {
    const { GrillaSalarial } = await import('./GrillaSalarial')
    render(React.createElement(GrillaSalarial, {
      grillas: [],
      onCrear: vi.fn(),
      onEditar: vi.fn(),
      onEliminar: vi.fn(),
    }))
    expect(screen.getByText(/no hay categorías/i)).toBeInTheDocument()
  })
})

describe('FormularioGrilla', () => {
  it('form validation blocks empty submit', async () => {
    const { FormularioGrilla } = await import('./FormularioGrilla')
    const onSubmit = vi.fn()
    render(React.createElement(FormularioGrilla, { onSubmit, onCancel: vi.fn() }))
    fireEvent.click(screen.getByRole('button', { name: /guardar/i }))
    await waitFor(() => {
      expect(screen.getByText(/categoría es requerida/i)).toBeInTheDocument()
    })
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('form calls onSubmit with valid data when pre-filled (triangulate)', async () => {
    const { FormularioGrilla } = await import('./FormularioGrilla')
    const onSubmit = vi.fn()
    const user = userEvent.setup()
    render(React.createElement(FormularioGrilla, {
      onSubmit,
      onCancel: vi.fn(),
      initial: { id: 'g1', categoria: 'Titular', salario_base: 3000 },
    }))
    await user.click(screen.getByRole('button', { name: /guardar/i }))
    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ categoria: 'Titular', salario_base: 3000 }),
      expect.anything(),
    ))
  })
})

// ── 1.12 TablaFacturas + FormularioFactura ────────────────────────────────────
describe('TablaFacturas', () => {
  const facturas = [
    { id: 'f1', proveedor: 'ACME', monto: 500, descripcion: 'Srv', estado: 'PENDIENTE' as const, fecha: '2024-06-01' },
  ]

  it('renders facturas with aprobar/rechazar buttons for PENDIENTE', async () => {
    const { TablaFacturas } = await import('./TablaFacturas')
    render(React.createElement(TablaFacturas, {
      facturas,
      onCrear: vi.fn(),
      onCambiarEstado: vi.fn(),
    }))
    expect(screen.getByText('ACME')).toBeInTheDocument()
    expect(screen.getByText('Aprobar')).toBeInTheDocument()
    expect(screen.getByText('Rechazar')).toBeInTheDocument()
  })

  it('calls onCambiarEstado with APROBADA when Aprobar clicked (triangulate)', async () => {
    const { TablaFacturas } = await import('./TablaFacturas')
    const onCambiarEstado = vi.fn()
    render(React.createElement(TablaFacturas, {
      facturas,
      onCrear: vi.fn(),
      onCambiarEstado,
    }))
    fireEvent.click(screen.getByText('Aprobar'))
    expect(onCambiarEstado).toHaveBeenCalledWith('f1', 'APROBADA')
  })

  it('renders empty state when no facturas (triangulate)', async () => {
    const { TablaFacturas } = await import('./TablaFacturas')
    render(React.createElement(TablaFacturas, {
      facturas: [],
      onCrear: vi.fn(),
      onCambiarEstado: vi.fn(),
    }))
    expect(screen.getByText(/no hay facturas/i)).toBeInTheDocument()
  })
})

describe('FormularioFactura', () => {
  it('form validation blocks empty submit', async () => {
    const { FormularioFactura } = await import('./FormularioFactura')
    const onSubmit = vi.fn()
    render(React.createElement(FormularioFactura, { onSubmit, onCancel: vi.fn() }))
    fireEvent.click(screen.getByRole('button', { name: /registrar/i }))
    await waitFor(() => {
      expect(screen.getByText(/proveedor es requerido/i)).toBeInTheDocument()
    })
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('submits with valid data when pre-filled (triangulate)', async () => {
    const { FormularioFactura } = await import('./FormularioFactura')
    const onSubmit = vi.fn()
    const user = userEvent.setup()
    render(React.createElement(FormularioFactura, {
      onSubmit,
      onCancel: vi.fn(),
      initial: { proveedor: 'XYZ Corp', monto: 1500, descripcion: 'Servicio de limpieza' },
    }))
    await user.click(screen.getByRole('button', { name: /registrar/i }))
    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ proveedor: 'XYZ Corp', monto: 1500, descripcion: 'Servicio de limpieza' }),
      expect.anything(),
    ))
  })
})
