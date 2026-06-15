import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'

// ── 5.1 SelectorActividades ──────────────────────────────────────────────────
describe('SelectorActividades', () => {
  it('renders list of actividades with checkboxes', async () => {
    const { SelectorActividades } = await import('./SelectorActividades')
    const actividades = [
      { id: 'a1', nombre: 'TP1', tipo: 'tp' },
      { id: 'a2', nombre: 'Quiz', tipo: 'quiz' },
    ]
    render(
      React.createElement(SelectorActividades, {
        actividades,
        selected: [],
        onChange: vi.fn(),
      }),
    )
    expect(screen.getByLabelText(/TP1/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Quiz/i)).toBeInTheDocument()
  })

  it('shows empty state when no actividades (triangulate)', async () => {
    const { SelectorActividades } = await import('./SelectorActividades')
    render(
      React.createElement(SelectorActividades, {
        actividades: [],
        selected: [],
        onChange: vi.fn(),
      }),
    )
    expect(screen.getByText(/No hay actividades/i)).toBeInTheDocument()
  })

  it('calls onChange when a checkbox is toggled (triangulate)', async () => {
    const { SelectorActividades } = await import('./SelectorActividades')
    const onChange = vi.fn()
    const actividades = [{ id: 'a1', nombre: 'TP1', tipo: 'tp' }]
    render(
      React.createElement(SelectorActividades, {
        actividades,
        selected: [],
        onChange,
      }),
    )
    const user = userEvent.setup()
    await user.click(screen.getByLabelText(/TP1/i))
    expect(onChange).toHaveBeenCalledWith(['a1'])
  })
})

// ── 5.2 ImportadorCalificaciones ─────────────────────────────────────────────
describe('ImportadorCalificaciones', () => {
  it('submit button is disabled without file and actividad selected', async () => {
    const { ImportadorCalificaciones } = await import('./ImportadorCalificaciones')
    const actividades = [{ id: 'a1', nombre: 'TP1', tipo: 'tp' }]
    render(
      React.createElement(ImportadorCalificaciones, {
        actividades,
        onImport: vi.fn(),
      }),
    )
    expect(screen.getByRole('button', { name: /importar/i })).toBeDisabled()
  })

  it('shows success message after import (triangulate)', async () => {
    const { ImportadorCalificaciones } = await import('./ImportadorCalificaciones')
    const actividades = [{ id: 'a1', nombre: 'TP1', tipo: 'tp' }]
    const onImport = vi.fn().mockResolvedValue({ importados: 5, errores: 0 })
    render(
      React.createElement(ImportadorCalificaciones, {
        actividades,
        onImport,
      }),
    )
    // Simulate file selection
    const fileInput = screen.getByLabelText(/archivo/i, { exact: false })
    const file = new File(['data'], 'test.csv', { type: 'text/csv' })
    await userEvent.upload(fileInput, file)

    // Select actividad
    await userEvent.click(screen.getByLabelText(/TP1/i))

    // Submit
    await userEvent.click(screen.getByRole('button', { name: /^importar$/i }))
    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent(/Importación exitosa/i),
    )
  })

  it('shows error message on import failure (triangulate)', async () => {
    const { ImportadorCalificaciones } = await import('./ImportadorCalificaciones')
    const actividades = [{ id: 'a1', nombre: 'TP1', tipo: 'tp' }]
    const onImport = vi.fn().mockRejectedValue(new Error('Server error'))
    render(
      React.createElement(ImportadorCalificaciones, {
        actividades,
        onImport,
      }),
    )
    const fileInput = screen.getByLabelText(/archivo/i, { exact: false })
    const file = new File(['bad'], 'bad.csv', { type: 'text/csv' })
    await userEvent.upload(fileInput, file)
    await userEvent.click(screen.getByLabelText(/TP1/i))
    await userEvent.click(screen.getByRole('button', { name: /^importar$/i }))
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent(/Error al importar/i),
    )
  })
})

// ── 5.3 ConfiguradorUmbral ───────────────────────────────────────────────────
describe('ConfiguradorUmbral', () => {
  it('shows current umbral value', async () => {
    const { ConfiguradorUmbral } = await import('./ConfiguradorUmbral')
    const current = { comision_id: 'c1', umbral_pct: 70, valores_aprobatorios: [7] }
    render(
      React.createElement(ConfiguradorUmbral, {
        current,
        onSave: vi.fn(),
      }),
    )
    expect(screen.getByText(/70%/i)).toBeInTheDocument()
  })

  it('calls onSave with new value (triangulate)', async () => {
    const { ConfiguradorUmbral } = await import('./ConfiguradorUmbral')
    const onSave = vi.fn()
    const current = { comision_id: 'c1', umbral_pct: 70, valores_aprobatorios: [7] }
    render(
      React.createElement(ConfiguradorUmbral, {
        current,
        onSave,
      }),
    )
    const input = screen.getByLabelText(/umbral/i)
    await userEvent.clear(input)
    await userEvent.type(input, '65')
    await userEvent.click(screen.getByRole('button', { name: /guardar/i }))
    await waitFor(() => expect(onSave).toHaveBeenCalledWith(65))
  })

  it('shows validation error for out-of-range value (triangulate)', async () => {
    const { ConfiguradorUmbral } = await import('./ConfiguradorUmbral')
    render(
      React.createElement(ConfiguradorUmbral, {
        onSave: vi.fn(),
      }),
    )
    const input = screen.getByLabelText(/umbral/i)
    await userEvent.clear(input)
    await userEvent.type(input, '200')
    await userEvent.click(screen.getByRole('button', { name: /guardar/i }))
    await waitFor(() => expect(screen.getByText(/Máximo 100/i)).toBeInTheDocument())
  })
})

// ── 6.1 TablaAtrasados ────────────────────────────────────────────────────────
describe('TablaAtrasados', () => {
  it('renders table with atrasados data', async () => {
    const { TablaAtrasados } = await import('./TablaAtrasados')
    const data = [
      { alumno_id: 'u1', nombre: 'Juan', apellido: 'Doe', legajo: '123', actividades_pendientes: ['TP1'], motivo: 'Sin entregar' },
    ]
    render(React.createElement(TablaAtrasados, { atrasados: data }))
    expect(screen.getByText(/Doe/i)).toBeInTheDocument()
    expect(screen.getByText(/Sin entregar/i)).toBeInTheDocument()
  })

  it('shows empty state message (triangulate)', async () => {
    const { TablaAtrasados } = await import('./TablaAtrasados')
    render(React.createElement(TablaAtrasados, { atrasados: [] }))
    expect(screen.getByText(/Sin alumnos atrasados/i)).toBeInTheDocument()
  })
})

// ── 6.2 TablaRanking ──────────────────────────────────────────────────────────
describe('TablaRanking', () => {
  it('renders ranking ordered by position', async () => {
    const { TablaRanking } = await import('./TablaRanking')
    const ranking = [
      { alumno_id: 'u2', nombre: 'Ana', apellido: 'Gomez', legajo: '99', promedio: 9.5, posicion: 1 },
      { alumno_id: 'u1', nombre: 'Bob', apellido: 'Smith', legajo: '88', promedio: 7.0, posicion: 2 },
    ]
    render(React.createElement(TablaRanking, { ranking }))
    const rows = screen.getAllByRole('row').slice(1) // skip header
    expect(rows[0]).toHaveTextContent('Gomez')
    expect(rows[1]).toHaveTextContent('Smith')
  })

  it('shows empty state (triangulate)', async () => {
    const { TablaRanking } = await import('./TablaRanking')
    render(React.createElement(TablaRanking, { ranking: [] }))
    expect(screen.getByText(/Sin datos de ranking/i)).toBeInTheDocument()
  })
})

// ── 6.4 ReporteRapido ─────────────────────────────────────────────────────────
describe('ReporteRapido', () => {
  it('renders metrics with data', async () => {
    const { ReporteRapido } = await import('./ReporteRapido')
    const data = { total_alumnos: 20, aprobados: 15, reprobados: 3, sin_nota: 2, atrasados: 5, promedio_general: 7.2 }
    render(React.createElement(ReporteRapido, { reporte: data }))
    expect(screen.getByText('20')).toBeInTheDocument()
    expect(screen.getByText('15')).toBeInTheDocument()
    expect(screen.getByText('7.20')).toBeInTheDocument()
  })

  it('shows informative state when no data (triangulate)', async () => {
    const { ReporteRapido } = await import('./ReporteRapido')
    render(React.createElement(ReporteRapido, { reporte: undefined }))
    expect(screen.getByText(/Sin datos disponibles/i)).toBeInTheDocument()
  })
})

// ── 6.5 TablaEntregasSinCorregir ─────────────────────────────────────────────
describe('TablaEntregasSinCorregir', () => {
  it('renders entregas list with export button', async () => {
    const { TablaEntregasSinCorregir } = await import('./TablaEntregasSinCorregir')
    const entregas = [
      { alumno_id: 'u1', nombre: 'P', apellido: 'Q', legajo: '1', actividad_id: 'a1', actividad_nombre: 'TP1', fecha_entrega: '2024-01-01' },
    ]
    render(React.createElement(TablaEntregasSinCorregir, { entregas, onExport: vi.fn() }))
    expect(screen.getByText(/TP1/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Exportar/i })).not.toBeDisabled()
  })

  it('disables export button when empty (triangulate)', async () => {
    const { TablaEntregasSinCorregir } = await import('./TablaEntregasSinCorregir')
    render(React.createElement(TablaEntregasSinCorregir, { entregas: [] }))
    expect(screen.getByRole('button', { name: /Exportar/i })).toBeDisabled()
  })
})

// ── 6.7 MonitorSeguimiento ────────────────────────────────────────────────────
describe('MonitorSeguimiento', () => {
  const atrasados = [
    { alumno_id: 'u1', nombre: 'Juan', apellido: 'Perez', legajo: '1', actividades_pendientes: ['TP1', 'TP2'], motivo: 'Sin entregar' },
    { alumno_id: 'u2', nombre: 'Ana', apellido: 'Gomez', legajo: '2', actividades_pendientes: ['TP1'], motivo: 'Tardio' },
  ]

  it('renders all atrasados initially', async () => {
    const { MonitorSeguimiento } = await import('./MonitorSeguimiento')
    render(React.createElement(MonitorSeguimiento, { atrasados }))
    expect(screen.getByText(/Perez/i)).toBeInTheDocument()
    expect(screen.getByText(/Gomez/i)).toBeInTheDocument()
  })

  it('filters by nombre (triangulate)', async () => {
    const { MonitorSeguimiento } = await import('./MonitorSeguimiento')
    render(React.createElement(MonitorSeguimiento, { atrasados }))
    const input = screen.getByPlaceholderText(/Buscar por nombre/i)
    await userEvent.type(input, 'perez')
    expect(screen.getByText(/Perez/i)).toBeInTheDocument()
    expect(screen.queryByText(/Gomez/i)).not.toBeInTheDocument()
  })

  it('filters by minimo actividades pendientes (triangulate)', async () => {
    const { MonitorSeguimiento } = await import('./MonitorSeguimiento')
    render(React.createElement(MonitorSeguimiento, { atrasados }))
    const minimoInput = screen.getByLabelText(/Mínimo actividades/i)
    fireEvent.change(minimoInput, { target: { value: '2' } })
    // Only Perez has 2 pending activities
    expect(screen.getByText(/Perez/i)).toBeInTheDocument()
    expect(screen.queryByText(/Gomez/i)).not.toBeInTheDocument()
  })
})

// ── 7.1 PreviewComunicacion ───────────────────────────────────────────────────
describe('PreviewComunicacion', () => {
  it('renders preview asunto and cuerpo', async () => {
    const { PreviewComunicacion } = await import('./PreviewComunicacion')
    const preview = { asunto: 'Alerta', cuerpo: 'Estás atrasado', destinatarios_count: 3 }
    render(React.createElement(PreviewComunicacion, { preview }))
    expect(screen.getByText(/Alerta/i)).toBeInTheDocument()
    expect(screen.getByText(/Estás atrasado/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Enviar/i })).not.toBeDisabled()
  })

  it('shows error state and disables send (triangulate)', async () => {
    const { PreviewComunicacion } = await import('./PreviewComunicacion')
    render(React.createElement(PreviewComunicacion, { error: 'Servicio no disponible' }))
    expect(screen.getByRole('alert')).toHaveTextContent(/Servicio no disponible/i)
    expect(screen.queryByRole('button', { name: /Enviar/i })).not.toBeInTheDocument()
  })
})

// ── 7.2 PanelEnvioComunicacion ────────────────────────────────────────────────
describe('PanelEnvioComunicacion', () => {
  it('confirm button is disabled without preview', async () => {
    const { PanelEnvioComunicacion } = await import('./PanelEnvioComunicacion')
    render(React.createElement(PanelEnvioComunicacion, { onConfirm: vi.fn() }))
    expect(screen.getByRole('button', { name: /Confirmar envío/i })).toBeDisabled()
  })

  it('calls onConfirm when preview is present and confirmed (triangulate)', async () => {
    const { PanelEnvioComunicacion } = await import('./PanelEnvioComunicacion')
    const onConfirm = vi.fn()
    const preview = { asunto: 'A', cuerpo: 'B', destinatarios_count: 1 }
    render(React.createElement(PanelEnvioComunicacion, { preview, onConfirm }))
    await userEvent.click(screen.getByRole('button', { name: /Confirmar envío/i }))
    expect(onConfirm).toHaveBeenCalledWith(undefined)
  })

  it('passes mensaje_personalizado when provided (triangulate)', async () => {
    const { PanelEnvioComunicacion } = await import('./PanelEnvioComunicacion')
    const onConfirm = vi.fn()
    const preview = { asunto: 'A', cuerpo: 'B', destinatarios_count: 1 }
    render(React.createElement(PanelEnvioComunicacion, { preview, onConfirm }))
    const textarea = screen.getByPlaceholderText(/Agregar texto/i)
    await userEvent.type(textarea, 'Recordatorio adicional')
    await userEvent.click(screen.getByRole('button', { name: /Confirmar envío/i }))
    expect(onConfirm).toHaveBeenCalledWith('Recordatorio adicional')
  })
})

// ── 7.3 PanelEstadoComunicaciones ────────────────────────────────────────────
describe('PanelEstadoComunicaciones', () => {
  it('renders estado list with badges', async () => {
    const { PanelEstadoComunicaciones } = await import('./PanelEstadoComunicaciones')
    const estados = [
      { alumno_id: 'u1', nombre: 'A', apellido: 'B', legajo: '1', estado: 'OK' as const },
      { alumno_id: 'u2', nombre: 'C', apellido: 'D', legajo: '2', estado: 'Pendiente' as const },
    ]
    render(React.createElement(PanelEstadoComunicaciones, { estados }))
    expect(screen.getByText('OK')).toBeInTheDocument()
    expect(screen.getByText('Pendiente')).toBeInTheDocument()
  })

  it('shows empty state when no comunicaciones (triangulate)', async () => {
    const { PanelEstadoComunicaciones } = await import('./PanelEstadoComunicaciones')
    render(React.createElement(PanelEstadoComunicaciones, { estados: [] }))
    expect(screen.getByText(/Sin comunicaciones/i)).toBeInTheDocument()
  })
})
