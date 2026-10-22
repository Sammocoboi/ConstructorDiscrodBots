import { z } from 'zod'

export const emailSchema = z.string().trim().min(1, 'validation.required').email('validation.email')

export const passwordSchema = z
  .string()
  .min(8, 'validation.passwordMin')
  .max(128, 'validation.max')

export const loginSchema = z.object({
  email: emailSchema,
  password: passwordSchema,
})

export const registerSchema = z
  .object({
    name: z.string().trim().min(2, 'validation.nameMin').max(60, 'validation.max'),
    email: emailSchema,
    password: passwordSchema,
    passwordConfirm: z.string(),
    terms: z.literal(true, { errorMap: () => ({ message: 'validation.terms' }) }),
  })
  .refine((value) => value.password === value.passwordConfirm, {
    message: 'validation.passwordMatch',
    path: ['passwordConfirm'],
  })

export const forgotPasswordSchema = z.object({ email: emailSchema })

export const resetPasswordSchema = z
  .object({
    password: passwordSchema,
    passwordConfirm: z.string(),
  })
  .refine((value) => value.password === value.passwordConfirm, {
    message: 'validation.passwordMatch',
    path: ['passwordConfirm'],
  })

export const createBotSchema = z.object({
  name: z.string().trim().min(2, 'validation.nameMin').max(42, 'validation.max'),
  description: z.string().max(180, 'validation.max').optional().default(''),
  avatarColor: z.string().regex(/^#[0-9a-fA-F]{6}$/, 'validation.color'),
})

export const botProfileSchema = z.object({
  name: z.string().trim().min(2, 'validation.nameMin').max(42, 'validation.max'),
  description: z.string().max(180, 'validation.max'),
  avatarColor: z.string().regex(/^#[0-9a-fA-F]{6}$/, 'validation.color'),
  bannerColor: z.string().regex(/^#[0-9a-fA-F]{6}$/, 'validation.color'),
  activityType: z.enum(['playing', 'watching', 'listening', 'competing']),
  activityText: z.string().max(128, 'validation.max'),
})

export const accountProfileSchema = z.object({
  username: z.string().trim().min(2, 'validation.nameMin').max(60, 'validation.max'),
  email: emailSchema,
  locale: z.enum(['ru', 'en']),
  timezone: z.string(),
})

export const flowNameSchema = z.object({
  name: z.string().trim().min(2, 'validation.nameMin').max(80, 'validation.max'),
  description: z.string().max(240, 'validation.max').optional(),
})

export const templateExportSchema = z.object({
  schemaVersion: z.literal(1),
  name: z.string().min(1),
  description: z.string().default(''),
  category: z.enum([
    'community',
    'moderation',
    'gaming',
    'education',
    'commerce',
    'content',
    'roleplay',
    'minimal',
  ]),
  tags: z.array(z.string()).default([]),
  version: z.string().default('1.0.0'),
  modules: z.array(z.string()).default([]),
  commands: z.array(z.record(z.unknown())).default([]),
  flows: z
    .array(
      z.object({
        name: z.string(),
        description: z.string().default(''),
        nodes: z.array(z.record(z.unknown())).default([]),
        edges: z.array(z.record(z.unknown())).default([]),
      }),
    )
    .default([]),
  createdAt: z.string().default(() => new Date().toISOString()),
})

export type LoginFormValues = z.infer<typeof loginSchema>
export type RegisterFormValues = z.infer<typeof registerSchema>
export type CreateBotFormValues = z.infer<typeof createBotSchema>
export type BotProfileFormValues = z.infer<typeof botProfileSchema>
export type AccountProfileFormValues = z.infer<typeof accountProfileSchema>
