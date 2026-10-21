import { describe, expect, it } from 'vitest'
import {
  emailSchema,
  registerSchema,
  resetPasswordSchema,
  templateExportSchema,
} from './validation'

describe('validation schemas', () => {
  it('trims and accepts a valid email', () => {
    expect(emailSchema.parse('  user@example.com ')).toBe('user@example.com')
  })

  it('rejects an invalid email', () => {
    expect(emailSchema.safeParse('not-an-email').success).toBe(false)
  })

  it('requires matching passwords on registration', () => {
    const result = registerSchema.safeParse({
      name: 'Daniil',
      email: 'user@example.com',
      password: 'password123',
      passwordConfirm: 'password124',
      terms: true,
    })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues[0]?.path).toEqual(['passwordConfirm'])
    }
  })

  it('rejects short passwords on reset', () => {
    const result = resetPasswordSchema.safeParse({
      password: 'short',
      passwordConfirm: 'short',
    })
    expect(result.success).toBe(false)
  })

  it('validates the template export format', () => {
    const result = templateExportSchema.safeParse({
      schemaVersion: 1,
      name: 'Community starter',
      category: 'community',
      tags: ['welcome'],
      modules: ['moderation'],
      commands: [],
      flows: [],
    })
    expect(result.success).toBe(true)
  })

  it('rejects an unknown template schema version', () => {
    const result = templateExportSchema.safeParse({
      schemaVersion: 2,
      name: 'Old export',
      category: 'community',
    })
    expect(result.success).toBe(false)
  })
})
