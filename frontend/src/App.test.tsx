import { MantineProvider } from '@mantine/core'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { App } from './App'

describe('App', () => {
  it('renders the product name', () => {
    render(
      <MantineProvider>
        <App />
      </MantineProvider>,
    )

    expect(screen.getByText('BotForge')).toBeInTheDocument()
  })
})
