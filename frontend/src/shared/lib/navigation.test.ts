import { describe, expect, it } from 'vitest'
import { getBotSection } from './navigation'

describe('getBotSection', () => {
  it('returns the section for bot routes', () => {
    expect(getBotSection('/app/bots/bot_community/modules')).toBe('modules')
    expect(getBotSection('/app/bots/bot_community/commands/new')).toBe('commands')
    expect(getBotSection('/app/bots/bot_community/flows/flow_1/versions')).toBe('flows')
  })

  it('defaults to overview for the bot root', () => {
    expect(getBotSection('/app/bots/bot_community')).toBe('overview')
    expect(getBotSection('/app/bots/bot_community/')).toBe('overview')
  })

  it('defaults to overview outside bot routes', () => {
    expect(getBotSection('/app')).toBe('overview')
    expect(getBotSection('/app/templates')).toBe('overview')
  })
})
