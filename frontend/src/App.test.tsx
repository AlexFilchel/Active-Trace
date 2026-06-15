import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'
import { clearSession } from '@/features/auth/services/sessionStore'

describe('App root', () => {
  beforeEach(() => {
    clearSession()
    localStorage.clear()
  })

  it('mounts without runtime errors and renders login page', async () => {
    const { default: App } = await import('./App')
    render(React.createElement(App))
    expect(await screen.findByRole('button', { name: /ingresar|login|entrar/i })).toBeInTheDocument()
  })
})
