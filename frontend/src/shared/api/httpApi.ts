import type { MockApi } from './mockApi'
import type {
  AuthSession,
  BillingOverview,
  Bot,
  BotActivityEvent,
  BotStatus,
  Command,
  CreateBotInput,
  CreateGuildResourceInput,
  DashboardStats,
  Flow,
  FlowIssue,
  FlowSaveInput,
  FlowTestResult,
  Guild,
  GuildResources,
  Invoice,
  JsonSchema,
  JsonSchemaProperty,
  LibraryCommand,
  MessageDraft,
  ModuleCategory,
  ModuleManifest,
  ModuleState,
  Notification,
  Plan,
  PlanId,
  Subscription,
  Template,
  TemplateCategory,
  TemplateExport,
  UpdateBotInput,
  Usage,
  User,
} from './types'
import { API_BASE, http } from './http'
import { ApiError } from './errors'
import { getAccessToken, useAuthStore } from '../stores/authStore'

interface Page<T> {
  results: T[]
  next?: string | null
  previous?: string | null
}

interface RawUser {
  id: string
  email: string
  display_name?: string
  avatar_url?: string
  locale?: string
  timezone?: string
  is_staff?: boolean
  is_email_verified?: boolean
  created_at?: string
}

interface RawAuthSession {
  access?: string
  access_token?: string
  accessToken?: string
  user: RawUser
}

interface RawRegisterResponse {
  user: RawUser
  message?: string
}

interface RawBot {
  id: string
  name: string
  discord_application_id?: string
  discord_bot_user_id?: string
  status?: string
  desired_state?: string
  active_version_number?: number | null
  profile?: Record<string, unknown>
  intents?: string[]
  has_token?: boolean
  token_masked?: string
  avatar_url?: string | null
  last_error?: string
  last_error_at?: string | null
  created_at: string
  updated_at: string
}

interface RawRuntimeState {
  worker_id?: string
  status?: string
  latency_ms?: number | null
  guild_count?: number | null
  uptime_seconds?: number | null
  version_number?: number | null
  heartbeat_at?: string | null
  is_alive?: boolean
}

interface RawBotStatus {
  bot_id: string
  status?: string
  desired_state?: string
  runtime?: RawRuntimeState | null
}

interface RawLifecycle {
  bot: RawBot
  runtime_command: RawRuntimeCommand
}

interface RawRuntimeCommand {
  id: string
  command: string
  status: string
  processed_at?: string | null
  error?: string
  created_at: string
}

interface RawBotGuild {
  id: string
  guild_id: string
  guild_name?: string
  joined_at?: string | null
  left_at?: string | null
  settings?: Record<string, unknown>
  enabled_modules?: string[]
}

interface RawModule {
  id?: string
  slug: string
  title?: string
  description?: string
  manifest?: Record<string, unknown>
  settings_schema?: Record<string, unknown>
  is_premium?: boolean
  min_plan?: string
}

interface RawBotModule {
  manifest: Record<string, unknown>
  enabled: boolean
  current_settings: Record<string, unknown>
}

interface RawBotModules {
  bot_id: string
  guild_id?: string | null
  modules: RawBotModule[]
}

interface RawModuleUpdate {
  status: string
  bot_id: string
  guild_id: string
  module_slug: string
  enabled: boolean
  settings?: Record<string, unknown>
  validation?: { warnings?: string[] }
}

interface RawCommandLibrary {
  id: string
  slug: string
  category?: string
  title?: string
  description?: string
  type?: string
  options?: { name?: string; description?: string; type?: number; required?: boolean }[]
  required_permissions?: number | string[]
  required_intents?: string[]
  dependencies?: unknown
  popularity?: number
  is_active?: boolean
}

interface RawInstalledCommand {
  slug?: string
  name?: string
  title?: string
  category?: string
  description?: string
  type?: string
  required_module?: string
  required_permissions?: number | string[]
  cooldown?: { type?: string; seconds?: number }
  preview?: { embed?: { title?: string; description?: string; color?: number | string } }
  access_rules?: {
    allowed_roles?: string[]
    denied_roles?: string[]
  }
  installed_at?: string
}

interface RawTemplateVersion {
  id: string
  version: string
  changelog?: string
  content?: Record<string, unknown> | null
  created_at: string
}

interface RawTemplate {
  id: string
  title: string
  description?: string
  category?: string
  visibility?: string
  tags?: string[]
  is_system?: boolean
  popularity?: number
  author_email?: string | null
  latest_version?: RawTemplateVersion | null
  created_at: string
  updated_at: string
}

interface RawTemplateExport {
  title: string
  description?: string
  category?: string
  version?: string
  content?: Record<string, unknown>
}

interface RawNotification {
  id: string
  type: string
  payload?: Record<string, unknown>
  read_at?: string | null
  created_at: string
}

interface RawPlan {
  id: string
  code: string
  name: string
  price_monthly: number | string
  currency?: string
  limits?: Record<string, unknown>
  sort_order?: number
}

interface RawSubscription {
  id: string
  plan?: RawPlan | null
  status?: string
  current_period_start?: string | null
  current_period_end?: string | null
  cancel_at_period_end?: boolean
  trial_end?: string | null
  created_at?: string
}

interface RawUsage {
  period_start: string
  period_end: string
  executions: number
  limits?: Record<string, unknown>
  plan?: RawPlan | null
  bots_used: number
  executions_limit?: number | null
  warnings?: string[]
}

interface RawInvoice {
  id: string
  number: string
  amount: number | string
  currency?: string
  status?: string
  issued_at: string
  paid_at?: string | null
  pdf_url?: string
}

interface RawSession {
  id: string
  device_info?: string
  ip?: string | null
  created_at: string
  expires_at: string
  revoked_at?: string | null
  is_active?: boolean
}

const UNSUPPORTED =
  'Эта функция пока недоступна в текущей версии backend. Мы работаем над ней.'

function unsupported(): never {
  throw new ApiError(501, 'not_implemented', UNSUPPORTED)
}

function hashColor(seed: string): string {
  const palette = ['#5865f2', '#3ba55d', '#faa81a', '#ed4245', '#00a8fc', '#9b59b6']
  let hash = 0
  for (let index = 0; index < seed.length; index += 1) {
    hash = (hash * 31 + seed.charCodeAt(index)) >>> 0
  }
  return palette[hash % palette.length]
}

function toPlanId(value: unknown): PlanId {
  return value === 'pro' || value === 'business' ? value : 'free'
}

function toBotStatus(value: unknown): BotStatus {
  if (
    value === 'online' ||
    value === 'starting' ||
    value === 'stopped' ||
    value === 'error' ||
    value === 'suspended'
  ) {
    return value
  }
  return 'stopped'
}

async function fetchPlanCodeWithToken(token: string): Promise<PlanId> {
  try {
    const response = await fetch(`${API_BASE}/me/usage`, {
      credentials: 'include',
      headers: { Accept: 'application/json', Authorization: `Bearer ${token}` },
    })
    if (!response.ok) return 'free'
    const payload = (await response.json()) as RawUsage
    return toPlanId(payload.plan?.code)
  } catch {
    return 'free'
  }
}

function mapUser(raw: RawUser): User {
  return {
    id: raw.id,
    username: raw.display_name?.trim() || raw.email.split('@')[0],
    email: raw.email,
    avatarColor: hashColor(raw.id),
    locale: raw.locale === 'en' ? 'en' : 'ru',
    timezone: raw.timezone || 'Europe/Moscow',
    theme: 'auto',
    plan: 'free',
    isStaff: Boolean(raw.is_staff),
    twoFactorEnabled: false,
    createdAt: raw.created_at ?? new Date().toISOString(),
    avatarUrl: raw.avatar_url || undefined,
    isEmailVerified: Boolean(raw.is_email_verified),
  }
}

function mapPlan(raw: RawPlan): Plan {
  const limits = raw.limits ?? {}
  const bots = Number(limits.bots ?? 0)
  const executions = Number(limits.executions_per_month ?? 0)
  const guilds = Number(limits.guilds_per_bot ?? 0)
  return {
    id: toPlanId(raw.code),
    name: raw.name,
    priceMonthly: Number(raw.price_monthly ?? 0),
    description: '',
    features: [],
    limits: { bots, executions, guilds, members: 0 },
    highlighted: raw.code === 'pro',
  }
}

function profileString(profile: Record<string, unknown>, key: string, fallback: string): string {
  const value = profile[key]
  return typeof value === 'string' && value.trim() ? value : fallback
}

function profileActivity(profile: Record<string, unknown>): Bot['activity'] {
  const activity = profile.activity
  if (activity && typeof activity === 'object') {
    const record = activity as Record<string, unknown>
    const type = record.type
    const text = record.text
    if (
      (type === 'playing' || type === 'watching' || type === 'listening' || type === 'competing') &&
      typeof text === 'string'
    ) {
      return { type, text }
    }
  }
  return { type: 'playing', text: '' }
}

function mapGuild(raw: RawBotGuild): Guild {
  const id = raw.guild_id || raw.id
  return {
    id,
    name: raw.guild_name || id,
    iconColor: hashColor(id),
    memberCount: 0,
    botAdded: !raw.left_at,
    enabledModules: raw.enabled_modules,
    owner: false,
    canManage: true,
    channels: [],
    roles: [],
  }
}

function mapBot(
  raw: RawBot,
  guilds: Guild[] = [],
  status?: RawBotStatus | null,
  inviteUrl = '',
): Bot {
  const profile = raw.profile ?? {}
  const runtime = status?.runtime
  const resolvedStatus = toBotStatus(status?.status ?? raw.status)
  const appId = raw.discord_application_id || raw.discord_bot_user_id || ''
  return {
    id: raw.id,
    name: raw.name,
    description: profileString(profile, 'description', ''),
    status: resolvedStatus,
    desiredState: raw.desired_state === 'running' ? 'running' : 'stopped',
    ping: runtime?.latency_ms ?? 0,
    uptimeSeconds: runtime?.uptime_seconds ?? 0,
    guilds,
    lastError: raw.last_error || (runtime?.is_alive === false ? 'Runtime недоступен' : undefined),
    tokenMasked: raw.token_masked || '',
    applicationId: appId,
    inviteUrl,
    avatarUrl: raw.avatar_url || undefined,
    avatarColor: profileString(profile, 'avatar_color', '#5865f2'),
    bannerColor: profileString(profile, 'banner_color', '#1f2160'),
    activity: profileActivity(profile),
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
    version: raw.active_version_number ? `v${raw.active_version_number}` : '—',
    runtimeVersion: runtime?.version_number ? `runtime v${runtime.version_number}` : '—',
    ownerId: useAuthStore.getState().user?.id ?? '',
  }
}

async function fetchGuilds(botId: string): Promise<Guild[]> {
  try {
    const guilds = await http.get<RawBotGuild[]>(`/bots/${botId}/guilds`)
    return guilds.map(mapGuild)
  } catch {
    return []
  }
}

async function fetchStatus(botId: string): Promise<RawBotStatus | null> {
  try {
    return await http.get<RawBotStatus>(`/bots/${botId}/status`)
  } catch {
    return null
  }
}

async function fetchBot(botId: string): Promise<Bot> {
  const [raw, status, guilds, invite] = await Promise.all([
    http.get<RawBot>(`/bots/${botId}`),
    fetchStatus(botId),
    fetchGuilds(botId),
    http.get<{ url: string }>(`/bots/${botId}/invite-url`).catch(() => null),
  ])
  return mapBot(raw, guilds, status, invite?.url)
}

async function listBots(): Promise<Bot[]> {
  const page = await http.get<Page<RawBot>>('/bots?limit=100')
  return Promise.all(
    page.results.map(async (raw) => mapBot(raw, await fetchGuilds(raw.id))),
  )
}

async function listNotificationsRaw(): Promise<RawNotification[]> {
  const page = await http.get<Page<RawNotification>>('/notifications?limit=100')
  return page.results
}

function permissionsFromMask(mask: number | string[] | undefined): string[] {
  if (Array.isArray(mask)) return mask.map(String)
  if (!mask) return []
  const flags: Record<number, string> = {
    1: 'Kick Members',
    2: 'Ban Members',
    3: 'Administrator',
    4: 'Manage Channels',
    5: 'Manage Server',
    6: 'Add Reactions',
    7: 'View Audit Log',
    10: 'View Channels',
    11: 'Send Messages',
    13: 'Manage Messages',
    14: 'Embed Links',
    15: 'Attach Files',
    16: 'Read History',
    17: 'Mention Everyone',
    28: 'Manage Roles',
    31: 'Use Application Commands',
    40: 'Moderate Members',
  }
  return Object.entries(flags)
    .filter(([bit]) => Math.floor(mask / 2 ** Number(bit)) % 2 === 1)
    .map(([, label]) => label)
}

function commandType(value: unknown): Command['type'] {
  return value === 'message' || value === 'user' ? value : 'slash'
}

function commandCategory(value: unknown): LibraryCommand['category'] {
  if (
    value === 'moderation' ||
    value === 'utility' ||
    value === 'community' ||
    value === 'fun' ||
    value === 'roles' ||
    value === 'economy'
  ) {
    return value
  }
  if (value === 'automation' || value === 'tickets') return 'utility'
  if (value === 'giveaways' || value === 'levels') return 'fun'
  if (value === 'social') return 'community'
  return 'utility'
}

function optionType(value: number | undefined): string {
  switch (value) {
    case 3:
      return 'string'
    case 4:
      return 'integer'
    case 5:
      return 'boolean'
    case 6:
      return 'user'
    case 7:
      return 'channel'
    case 8:
      return 'role'
    case 10:
      return 'number'
    default:
      return 'string'
  }
}

function colorToHex(value: number | string | undefined): string {
  if (typeof value === 'string') return value.startsWith('#') ? value : `#${value}`
  if (typeof value === 'number') return `#${value.toString(16).padStart(6, '0')}`
  return '#5865F2'
}

function mapLibraryCommand(raw: RawCommandLibrary): LibraryCommand {
  return {
    id: raw.slug,
    name: raw.slug,
    description: raw.description || '',
    category: commandCategory(raw.category),
    type: commandType(raw.type),
    permissions: permissionsFromMask(raw.required_permissions),
    parameters: (raw.options ?? []).map((option) => ({
      name: option.name ?? '',
      type: optionType(option.type),
      required: Boolean(option.required),
      description: option.description || '',
    })),
    preview: raw.description || '',
    author: 'BotForge',
    installs: raw.popularity ?? 0,
    flowSummary: [],
  }
}

function mapInstalledCommand(botId: string, raw: RawInstalledCommand, updatedAt: string): Command {
  const category = commandCategory(raw.category)
  return {
    id: raw.name || raw.slug || 'command',
    botId,
    name: raw.name || raw.slug || 'command',
    description: raw.description || '',
    type: commandType(raw.type),
    enabled: true,
    source: 'library',
    category,
    libraryId: raw.slug,
    requiredRoleId: raw.access_rules?.allowed_roles?.[0],
    responseText: raw.preview?.embed?.description || '',
    embed: raw.preview?.embed
      ? {
          title: raw.preview.embed.title || '',
          description: raw.preview.embed.description || '',
          color: colorToHex(raw.preview.embed.color),
        }
      : undefined,
    updatedAt: raw.installed_at || updatedAt,
    syncedAt: undefined,
  }
}

const moduleIcons: Record<string, string> = {
  welcomes: 'userPlus',
  moderation: 'shield',
  antispam: 'shieldMinus',
  tickets: 'ticket',
  levels: 'award',
  economy: 'coins',
  logging: 'list',
  roles: 'users',
  fun: 'dice',
  automation: 'bolt',
  giveaways: 'gift',
}

function moduleCategory(value: unknown, slug: string): ModuleCategory {
  if (
    value === 'community' ||
    value === 'moderation' ||
    value === 'roles' ||
    value === 'utility' ||
    value === 'engagement' ||
    value === 'logs'
  ) {
    return value
  }
  switch (value) {
    case 'Автоматизация':
    case 'Утилиты':
      return 'utility'
    case 'Модерация':
    case 'Безопасность':
      return 'moderation'
    case 'Роли':
      return 'roles'
    case 'Социальное':
    case 'Поддержка':
      return 'community'
    case 'Экономика':
    case 'Развлечения':
      return 'engagement'
    case 'Логирование':
      return 'logs'
    default:
      break
  }
  if (slug === 'logging') return 'logs'
  if (slug === 'roles') return 'roles'
  if (slug === 'moderation' || slug === 'antispam') return 'moderation'
  if (slug === 'levels' || slug === 'tickets') return 'community'
  if (slug === 'fun' || slug === 'giveaways' || slug === 'economy') return 'engagement'
  return 'utility'
}

function inferFormat(key: string, property: Record<string, unknown>): JsonSchemaProperty['format'] {
  const explicit = property.format
  if (
    explicit === 'text' ||
    explicit === 'textarea' ||
    explicit === 'channel' ||
    explicit === 'role' ||
    explicit === 'color' ||
    explicit === 'duration' ||
    explicit === 'secret'
  ) {
    return explicit
  }
  const lower = key.replace(/([a-z])([A-Z])/g, '$1_$2').toLowerCase()
  if (/(?:^|_)role_ids?$/.test(lower)) return 'role'
  if (/(?:^|_)channel_ids?$/.test(lower) || lower === 'category_id') return 'channel'
  if (lower.includes('color')) return 'color'
  if (lower.includes('token') || lower.includes('password') || lower.includes('secret')) {
    return 'secret'
  }
  if (lower.includes('message') || lower.includes('text') || lower.includes('description')) {
    return 'textarea'
  }
  return undefined
}

function normalizeSchema(raw: Record<string, unknown> | undefined): JsonSchema {
  const propertiesRaw =
    raw && typeof raw.properties === 'object' && raw.properties
      ? (raw.properties as Record<string, unknown>)
      : {}
  const properties: Record<string, JsonSchemaProperty> = {}
  for (const [key, value] of Object.entries(propertiesRaw)) {
    if (!value || typeof value !== 'object') continue
    properties[key] = normalizeSchemaProperty(key, value as Record<string, unknown>)
  }
  return {
    type: 'object',
    title: typeof raw?.title === 'string' ? raw.title : undefined,
    description: typeof raw?.description === 'string' ? raw.description : undefined,
    properties,
    required: Array.isArray(raw?.required)
      ? raw.required.filter((item): item is string => typeof item === 'string')
      : [],
  }
}

function normalizeSchemaProperty(key: string, property: Record<string, unknown>): JsonSchemaProperty {
  const declared = Array.isArray(property.type)
    ? property.type.find((item) => typeof item === 'string' && item !== 'null')
    : property.type
  const type =
    declared === 'number' ||
    declared === 'integer' ||
    declared === 'boolean' ||
    declared === 'array' ||
    declared === 'object'
      ? declared
      : 'string'
  const normalized: JsonSchemaProperty = {
    type,
    title:
      typeof property.title === 'string'
        ? property.title
        : key.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase()),
  }
  if (typeof property.description === 'string') normalized.description = property.description
  if (property.default !== undefined) normalized.default = property.default
  if (Array.isArray(property.enum)) {
    normalized.enum = property.enum.map((option) => {
      if (option && typeof option === 'object') {
        const record = option as Record<string, unknown>
        const optionValue =
          typeof record.value === 'string' || typeof record.value === 'number'
            ? record.value
            : String(record.value ?? '')
        return { value: optionValue, label: String(record.label ?? optionValue) }
      }
      return {
        value: typeof option === 'number' ? option : String(option),
        label: String(option),
      }
    })
  }
  if (typeof property.minimum === 'number') normalized.minimum = property.minimum
  if (typeof property.maximum === 'number') normalized.maximum = property.maximum
  if (type === 'array' && property.items && typeof property.items === 'object') {
    normalized.items = normalizeSchemaProperty(key, property.items as Record<string, unknown>)
  }
  if (type === 'object') {
    const schema = normalizeSchema(property)
    normalized.properties = schema.properties
    normalized.required = schema.required
  }
  const format = inferFormat(key, property)
  if (format) normalized.format = format
  return normalized
}

function mapManifest(raw: RawModule): ModuleManifest {
  const manifest = raw.manifest ?? {}
  const slug = String(manifest.slug ?? raw.slug ?? raw.id ?? 'module')
  return {
    id: slug,
    title: String(manifest.title ?? raw.title ?? slug),
    description: String(manifest.description ?? raw.description ?? ''),
    category: moduleCategory(manifest.category, slug),
    icon: moduleIcons[slug] ?? 'layout',
    permissions: permissionsFromMask(manifest.required_permissions as number | string[] | undefined),
    intents: Array.isArray(manifest.required_intents)
      ? manifest.required_intents.map(String)
      : [],
    enabledByDefault: false,
    popular: Boolean(raw.is_premium),
    settingsSchema: normalizeSchema(
      (manifest.settings_schema ?? raw.settings_schema) as Record<string, unknown> | undefined,
    ),
  }
}

function mapModuleState(
  botId: string,
  guildId: string | undefined,
  slug: string,
  enabled: boolean,
  settings: Record<string, unknown>,
  warnings: string[] = [],
): ModuleState {
  return {
    botId,
    moduleId: slug,
    enabled,
    settings: guildId ? { [guildId]: settings } : {},
    warnings,
    updatedAt: new Date().toISOString(),
  }
}

function templateCategory(value: unknown): TemplateCategory {
  if (
    value === 'community' ||
    value === 'moderation' ||
    value === 'gaming' ||
    value === 'education' ||
    value === 'commerce' ||
    value === 'content' ||
    value === 'roleplay' ||
    value === 'minimal'
  ) {
    return value
  }
  if (value === 'support' || value === 'social') return 'community'
  if (value === 'economy' || value === 'shop') return 'commerce'
  if (value === 'games' || value === 'fun') return 'gaming'
  if (value === 'utility' || value === 'roles') return 'minimal'
  return 'minimal'
}

function contentRecord(content: Record<string, unknown> | null | undefined): Record<string, unknown> {
  return content && typeof content === 'object' ? content : {}
}

function mapTemplate(raw: RawTemplate): Template {
  const content = contentRecord(raw.latest_version?.content)
  const modules = Array.isArray(content.modules) ? content.modules.map(String) : []
  const commands = Array.isArray(content.commands) ? content.commands : []
  const flows = Array.isArray(content.flows) ? content.flows : []
  const profile =
    content.profile && typeof content.profile === 'object'
      ? (content.profile as Record<string, unknown>)
      : {}
  const installed =
    profile.installed_commands && typeof profile.installed_commands === 'object'
      ? Object.keys(profile.installed_commands as Record<string, unknown>)
      : []
  const author = raw.author_email || 'BotForge'
  return {
    id: raw.id,
    name: raw.title,
    description: raw.description || '',
    category: templateCategory(raw.category),
    tags: Array.isArray(raw.tags) ? raw.tags.map(String) : [],
    iconColor: hashColor(raw.id),
    featured: Boolean(raw.is_system),
    system: Boolean(raw.is_system),
    version: raw.latest_version?.version || '1.0.0',
    minPlan: 'free',
    modules,
    commandsCount: commands.length || installed.length,
    flowsCount: flows.length,
    botsCount: raw.popularity ?? 0,
    author,
    createdAt: raw.created_at,
  }
}

async function createTemplateFromBot(
  botId: string,
  input: { name: string; description: string },
): Promise<Template> {
  const bot = await http.get<RawBot>(`/bots/${botId}`)
  const created = await http.post<RawTemplate>('/templates', {
    title: input.name,
    description: input.description,
    category: '',
    visibility: 'private',
    tags: [],
    content: {
      profile: bot.profile ?? {},
      intents: bot.intents ?? [],
    },
  })
  return mapTemplate(created)
}

function mapNotification(raw: RawNotification): Notification {
  const payload = raw.payload ?? {}
  const type = raw.type || 'info'
  const kind: Notification['type'] = type.includes('limit') || type.includes('billing') || type.includes('invoice')
    ? 'billing'
    : type.includes('error')
      ? 'error'
      : type.includes('success')
        ? 'success'
        : type.includes('warning')
          ? 'warning'
          : 'info'
  const title =
    typeof payload.title === 'string'
      ? payload.title
      : type.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())
  const pieces: string[] = []
  if (typeof payload.message === 'string') pieces.push(payload.message)
  if (typeof payload.used === 'number' && typeof payload.limit === 'number') {
    pieces.push(`${payload.used} / ${payload.limit}`)
  }
  if (typeof payload.percent === 'number') pieces.push(`${payload.percent}%`)
  return {
    id: raw.id,
    type: kind,
    title,
    message: pieces.join(' · ') || title,
    read: Boolean(raw.read_at),
    createdAt: raw.created_at,
    link:
      typeof payload.link === 'string'
        ? payload.link
        : kind === 'billing'
          ? '/app/billing'
          : undefined,
  }
}

function mapInvoice(raw: RawInvoice): Invoice {
  const status = raw.status === 'paid' || raw.status === 'void' ? raw.status : 'open'
  return {
    id: raw.id,
    number: raw.number,
    amount: Number(raw.amount ?? 0),
    currency: (raw.currency || 'usd').toUpperCase(),
    status,
    createdAt: raw.issued_at,
    period: raw.issued_at.slice(0, 10),
    downloadUrl: raw.pdf_url || undefined,
  }
}

function mapSession(raw: RawSession, index: number) {
  const deviceInfo = raw.device_info?.trim() || ''
  return {
    id: raw.id,
    device: deviceInfo || 'Устройство',
    browser: '—',
    ip: raw.ip || '—',
    location: '—',
    lastActiveAt: raw.created_at,
    current: index === 0,
  }
}

function mapSubscription(raw: RawSubscription | null, usage?: RawUsage): Subscription {
  const planCode = raw?.plan?.code ?? usage?.plan?.code
  return {
    planId: toPlanId(planCode),
    status:
      raw?.status === 'trialing' ||
      raw?.status === 'past_due' ||
      raw?.status === 'canceled'
        ? raw.status
        : 'active',
    renewsAt: raw?.current_period_end ?? undefined,
    trialEndsAt: raw?.trial_end ?? undefined,
    cancelAtPeriodEnd: Boolean(raw?.cancel_at_period_end),
  }
}

function mapUsage(raw: RawUsage): Usage {
  return {
    bots: raw.bots_used ?? 0,
    executions: raw.executions ?? 0,
    guilds: 0,
    members: 0,
    periodStart: raw.period_start,
    periodEnd: raw.period_end,
  }
}

function mapExport(raw: RawTemplateExport): TemplateExport {
  const content = contentRecord(raw.content)
  if (content.schemaVersion === 1) {
    return content as unknown as TemplateExport
  }
  return {
    schemaVersion: 1,
    name: raw.title,
    description: raw.description || '',
    category: templateCategory(raw.category),
    tags: [],
    version: raw.version || '1.0.0',
    modules: Array.isArray(content.modules) ? content.modules.map(String) : [],
    commands: Array.isArray(content.commands)
      ? (content.commands as TemplateExport['commands'])
      : [],
    flows: Array.isArray(content.flows) ? (content.flows as TemplateExport['flows']) : [],
    createdAt: new Date().toISOString(),
  }
}

const invoiceDownloads = new Map<string, string>()

export const httpApi: MockApi = {
  auth: {
    async login(input): Promise<AuthSession> {
      const raw = await http.post<RawAuthSession>('/auth/login', input)
      const accessToken = raw.access ?? raw.access_token ?? raw.accessToken ?? ''
      const user = mapUser(raw.user)
      if (accessToken) user.plan = await fetchPlanCodeWithToken(accessToken)
      return { user, accessToken }
    },
    async register(input): Promise<AuthSession> {
      const raw = await http.post<RawRegisterResponse>('/auth/register', {
        email: input.email,
        password: input.password,
        display_name: input.name,
      })
      return { user: mapUser(raw.user), accessToken: '' }
    },
    async loginWithDiscord() {
      window.location.assign(`${API_BASE}/auth/discord/login`)
      return new Promise<AuthSession>(() => undefined)
    },
    async exchangeDiscordCode(code: string): Promise<AuthSession> {
      const raw = await http.post<RawAuthSession>('/auth/discord/exchange', { code })
      const accessToken = raw.access ?? raw.access_token ?? raw.accessToken ?? ''
      const user = mapUser(raw.user)
      if (accessToken) user.plan = await fetchPlanCodeWithToken(accessToken)
      return { user, accessToken }
    },
    async forgotPassword(email) {
      await http.post('/auth/password/reset/request', { email })
    },
    async resetPassword(password, token?) {
      if (!token) throw new ApiError(400, 'missing_token', 'Ссылка сброса пароля недействительна.')
      await http.post('/auth/password/reset/confirm', { token, new_password: password })
    },
    async verifyEmail(token) {
      await http.post('/auth/email/verify', { token })
    },
    async me() {
      const raw = await http.get<RawUser>('/me')
      const user = mapUser(raw)
      try {
        const usage = await http.get<RawUsage>('/me/usage')
        user.plan = toPlanId(usage.plan?.code)
      } catch {
        // Plan is a cosmetic detail here; /me must still work without billing access.
      }
      return user
    },
    async logout() {
      await http.post('/auth/logout')
    },
  },

  dashboard: {
    async stats(): Promise<DashboardStats> {
      const [bots, notifications] = await Promise.all([
        listBots(),
        listNotificationsRaw().catch(() => [] as RawNotification[]),
      ])
      return {
        bots: bots.length,
        online: bots.filter((bot) => bot.status === 'online').length,
        guilds: bots.reduce((sum, bot) => sum + bot.guilds.length, 0),
        unreadNotifications: notifications.filter((item) => !item.read_at).length,
      }
    },
  },

  bots: {
    async list() {
      return listBots()
    },
    async get(botId) {
      return fetchBot(botId)
    },
    async create(input: CreateBotInput) {
      const created = await http.post<RawBot>('/bots', {
        name: input.name,
        discord_application_id: '',
        token: input.token,
        profile: {
          description: input.description,
          avatar_color: input.avatarColor,
          banner_color: '#1f2160',
          activity: { type: 'playing', text: '' },
        },
        intents: [],
      })
      return fetchBot(created.id)
    },
    async update(botId, patch: UpdateBotInput) {
      const current = await http.get<RawBot>(`/bots/${botId}`)
      const profile: Record<string, unknown> = { ...(current.profile ?? {}) }
      if (patch.description !== undefined) profile.description = patch.description
      if (patch.avatarColor !== undefined) profile.avatar_color = patch.avatarColor
      if (patch.bannerColor !== undefined) profile.banner_color = patch.bannerColor
      if (patch.activity !== undefined) profile.activity = patch.activity
      await http.patch(`/bots/${botId}`, {
        name: patch.name ?? current.name,
        profile,
      })
      return fetchBot(botId)
    },
    async updateAvatar(botId: string, file: File): Promise<void> {
      const form = new FormData()
      form.append('avatar', file)
      await http.post(`/bots/${botId}/avatar`, form)
    },
    async remove(botId) {
      await http.delete(`/bots/${botId}`)
    },
    async start(botId) {
      await http.post<RawLifecycle>(`/bots/${botId}/start`)
      return fetchBot(botId)
    },
    async stop(botId) {
      await http.post<RawLifecycle>(`/bots/${botId}/stop`)
      return fetchBot(botId)
    },
    async restart(botId) {
      await http.post<RawLifecycle>(`/bots/${botId}/restart`)
      return fetchBot(botId)
    },
    async validateToken() {
      unsupported()
    },
    async replaceToken() {
      unsupported()
    },
    async availableGuilds(): Promise<Guild[]> {
      return http.get<Guild[]>('/me/discord-guilds')
    },
    async discordGuilds(botId: string): Promise<Pick<Guild, 'id' | 'name' | 'iconUrl'>[]> {
      return http.get<Pick<Guild, 'id' | 'name' | 'iconUrl'>[]>(`/bots/${botId}/discord-guilds`)
    },
    async guildResources(botId: string, guildId: string): Promise<GuildResources> {
      return http.get(`/bots/${botId}/guilds/${guildId}/resources`)
    },
    async createGuildResource(
      botId: string,
      guildId: string,
      input: CreateGuildResourceInput,
    ): Promise<{ id: string }> {
      return http.post(`/bots/${botId}/guilds/${guildId}/resources`, {
        kind: input.kind,
        name: input.name,
        channel_type: input.channelType,
      })
    },
    async guilds(botId) {
      const guilds = await http.get<RawBotGuild[]>(`/bots/${botId}/guilds`)
      return guilds.map(mapGuild)
    },
    async events(botId): Promise<BotActivityEvent[]> {
      const commands = await http.get<RawRuntimeCommand[]>(`/bots/${botId}/commands`)
      return commands.map((command) => ({
        id: command.id,
        botId,
        type: command.error ? 'error' : 'runtime',
        message: `${command.command} → ${command.status}${command.error ? `: ${command.error}` : ''}`,
        createdAt: command.processed_at || command.created_at,
      }))
    },
    async copySettings() {
      unsupported()
    },
    async saveAsTemplate(botId, input) {
      return createTemplateFromBot(botId, input)
    },
  },

  modules: {
    async list(): Promise<ModuleManifest[]> {
      const page = await http.get<Page<RawModule>>('/modules?limit=100')
      return page.results.map(mapManifest)
    },
    async forBot(botId, guildId?: string) {
      const query = guildId ? `?guild_id=${encodeURIComponent(guildId)}` : ''
      const raw = await http.get<RawBotModules>(`/bots/${botId}/modules${query}`)
      return raw.modules.map((item) => {
        const manifest = mapManifest({
          slug: String(item.manifest.slug ?? item.manifest.id ?? ''),
          manifest: item.manifest,
        })
        return {
          manifest,
          state: mapModuleState(
            botId,
            guildId,
            manifest.id,
            item.enabled,
            item.current_settings ?? {},
          ),
        }
      })
    },
    async get(botId, moduleId, guildId?: string) {
      const query = guildId ? `?guild_id=${encodeURIComponent(guildId)}` : ''
      const raw = await http.get<RawBotModules>(`/bots/${botId}/modules${query}`)
      const found = raw.modules.find(
        (item) => item.manifest.slug === moduleId || item.manifest.id === moduleId,
      )
      if (!found) throw new ApiError(404, 'module_not_found', 'Модуль не найден.')
      const manifest = mapManifest({
        slug: String(found.manifest.slug ?? found.manifest.id ?? moduleId),
        manifest: found.manifest,
      })
      return {
        manifest,
        state: mapModuleState(
          botId,
          guildId,
          manifest.id,
          found.enabled,
          found.current_settings ?? {},
        ),
      }
    },
    async toggle(botId, moduleId, enabled, guildId?: string) {
      if (!guildId) {
        throw new ApiError(
          400,
          'guild_required',
          'Выберите сервер: настройки модулей хранятся отдельно для каждого сервера.',
        )
      }
      const response = await http.put<RawModuleUpdate>(
        `/bots/${botId}/modules/${moduleId}`,
        { guild_id: guildId, enabled, settings: {} },
      )
      return mapModuleState(
        botId,
        guildId,
        moduleId,
        response.enabled,
        response.settings ?? {},
        response.validation?.warnings ?? [],
      )
    },
    async updateSettings(botId, moduleId, guildId, settings) {
      const current = await http.get<RawBotModules>(
        `/bots/${botId}/modules?guild_id=${encodeURIComponent(guildId)}`,
      )
      const found = current.modules.find(
        (item) => item.manifest.slug === moduleId || item.manifest.id === moduleId,
      )
      const response = await http.put<RawModuleUpdate>(
        `/bots/${botId}/modules/${moduleId}`,
        {
          guild_id: guildId,
          enabled: found?.enabled ?? true,
          settings,
        },
      )
      return mapModuleState(
        botId,
        guildId,
        moduleId,
        response.enabled,
        response.settings ?? settings,
        response.validation?.warnings ?? [],
      )
    },
  },

  commands: {
    async list(botId): Promise<Command[]> {
      const bot = await http.get<RawBot>(`/bots/${botId}`)
      const installed = bot.profile?.installed_commands
      if (!installed || typeof installed !== 'object') return []
      return Object.values(installed as Record<string, RawInstalledCommand>)
        .map((command) => mapInstalledCommand(botId, command, bot.updated_at))
        .sort((a, b) => a.name.localeCompare(b.name))
    },
    async library(): Promise<LibraryCommand[]> {
      const page = await http.get<Page<RawCommandLibrary>>('/commands-library?limit=100')
      return page.results.map(mapLibraryCommand)
    },
    async install(botId, libraryId): Promise<Command> {
      const library = await http.get<Page<RawCommandLibrary>>(
        `/commands-library?limit=100&search=${encodeURIComponent(libraryId)}`,
      )
      const source = library.results.find((item) => item.slug === libraryId)
      await http.post(`/bots/${botId}/commands/install`, {
        slugs: [libraryId],
        action_on_conflict: 'skip',
      })
      if (source) {
        return mapInstalledCommand(botId, source, new Date().toISOString())
      }
      return mapInstalledCommand(
        botId,
        { slug: libraryId, name: libraryId },
        new Date().toISOString(),
      )
    },
    async create() {
      unsupported()
    },
    async update() {
      unsupported()
    },
    async remove() {
      unsupported()
    },
    async sync() {
      unsupported()
    },
    async test(): Promise<FlowTestResult> {
      unsupported()
    },
  },

  flows: {
    async list(botId: string): Promise<Flow[]> {
      return http.get<Flow[]>(`/bots/${botId}/flows`)
    },
    async get(botId: string, flowId: string): Promise<Flow> {
      return http.get<Flow>(`/bots/${botId}/flows/${flowId}`)
    },
    async create(botId: string, input?: { name?: string; description?: string }): Promise<Flow> {
      return http.post<Flow>(`/bots/${botId}/flows`, input ?? {})
    },
    async save(botId: string, flowId: string, input: FlowSaveInput): Promise<Flow> {
      return http.put<Flow>(`/bots/${botId}/flows/${flowId}`, input)
    },
    async remove(botId: string, flowId: string): Promise<void> {
      return http.delete(`/bots/${botId}/flows/${flowId}`)
    },
    async setEnabled(botId: string, flowId: string, enabled: boolean): Promise<Flow> {
      return http.post<Flow>(`/bots/${botId}/flows/${flowId}/enabled`, { enabled })
    },
    async rename(botId: string, flowId: string, name: string): Promise<Flow> {
      return http.patch<Flow>(`/bots/${botId}/flows/${flowId}`, { name })
    },
    async validate(botId: string, flowId: string, input?: FlowSaveInput): Promise<FlowIssue[]> {
      return http.post<FlowIssue[]>(`/bots/${botId}/flows/${flowId}/validate`, input ?? {})
    },
    async test(botId: string, flowId: string, input?: FlowSaveInput): Promise<FlowTestResult> {
      return http.post<FlowTestResult>(`/bots/${botId}/flows/${flowId}/test`, input ?? {})
    },
    async publish(botId: string, flowId: string, comment: string): Promise<Flow> {
      return http.post<Flow>(`/bots/${botId}/flows/${flowId}/publish`, { comment })
    },
    async rollback(botId: string, flowId: string, versionId: string): Promise<Flow> {
      return http.post<Flow>(`/bots/${botId}/flows/${flowId}/rollback`, { versionId })
    },
  },

  templates: {
    async list(): Promise<Template[]> {
      const page = await http.get<Page<RawTemplate>>('/templates?limit=100')
      return page.results.map(mapTemplate)
    },
    async mine(): Promise<Template[]> {
      const templates = await httpApi.templates.list()
      const email = useAuthStore.getState().user?.email
      return email ? templates.filter((template) => template.author === email) : templates
    },
    async get(templateId) {
      const raw = await http.get<RawTemplate>(`/templates/${templateId}`)
      return mapTemplate(raw)
    },
    async createFromBot(botId, input) {
      return createTemplateFromBot(botId, input)
    },
    async import(payload: TemplateExport) {
      const raw = await http.post<RawTemplate>('/templates/import', {
        title: payload.name,
        description: payload.description,
        category: payload.category,
        version: payload.version,
        content: payload,
      })
      return mapTemplate(raw)
    },
    async remove(templateId) {
      await http.delete(`/templates/${templateId}`)
    },
    async export(templateId): Promise<TemplateExport> {
      const raw = await http.get<RawTemplateExport>(`/templates/${templateId}/export`)
      return mapExport(raw)
    },
    async share(templateId) {
      const result = await http.post<{ url: string }>(`/templates/${templateId}/share_link`)
      return { shareId: templateId, url: result.url }
    },
  },

  billing: {
    async overview(): Promise<BillingOverview> {
      const [subscriptionRaw, usageRaw, invoicesRaw, plansRaw] = await Promise.all([
        http.get<RawSubscription | null>('/me/subscription').catch(() => null),
        http.get<RawUsage>('/me/usage'),
        http.get<Page<RawInvoice>>('/billing/invoices?limit=100').catch(() => ({ results: [] })),
        http.get<RawPlan[]>('/plans').catch(() => [] as RawPlan[]),
      ])
      const invoices = invoicesRaw.results.map((invoice) => {
        const mapped = mapInvoice(invoice)
        if (mapped.downloadUrl) invoiceDownloads.set(mapped.id, mapped.downloadUrl)
        return mapped
      })
      return {
        subscription: mapSubscription(subscriptionRaw, usageRaw),
        usage: mapUsage(usageRaw),
        invoices,
        plans: plansRaw.map(mapPlan),
      }
    },
    async checkout(planId) {
      return http.post<{ url: string }>('/billing/checkout', { plan_code: planId })
    },
    async portal() {
      return http.post<{ url: string }>('/billing/portal', {})
    },
    async cancel() {
      return unsupported() as BillingOverview
    },
    async downloadInvoice(invoiceId) {
      const url = invoiceDownloads.get(invoiceId)
      if (!url) {
        throw new ApiError(404, 'invoice_pdf_missing', 'Для этого счёта PDF пока не сформирован.')
      }
      return { url }
    },
  },

  account: {
    async get() {
      const [raw, sessions, subscriptionRaw] = await Promise.all([
        http.get<RawUser>('/me'),
        http.get<RawSession[]>('/me/sessions').catch(() => [] as RawSession[]),
        http.get<RawSubscription | null>('/me/subscription').catch(() => null),
      ])
      const user = mapUser(raw)
      user.plan = toPlanId(subscriptionRaw?.plan?.code)
      return {
        user,
        sessions: sessions.map((session, index) => mapSession(session, index)),
        notifications: {
          botErrors: true,
          payments: true,
          productUpdates: true,
          weeklyDigest: false,
        },
      }
    },
    async updateProfile(patch: Partial<User>): Promise<User> {
      const raw = await http.patch<RawUser>('/me', {
        display_name: patch.username,
        avatar_url: patch.avatarUrl,
        locale: patch.locale,
        timezone: patch.timezone,
      })
      const user = mapUser(raw)
      if (patch.plan) user.plan = patch.plan
      return user
    },
    async updateNotifications(patch) {
      const current = {
        botErrors: true,
        payments: true,
        productUpdates: true,
        weeklyDigest: false,
      }
      return { ...current, ...patch }
    },
    async revokeSession(sessionId) {
      await http.delete(`/me/sessions/${sessionId}`)
    },
    async logoutEverywhere() {
      await http.post('/auth/logout-all')
    },
    async deleteAccount() {
      await http.delete('/me')
    },
  },

  notifications: {
    async list(): Promise<Notification[]> {
      const notifications = await listNotificationsRaw()
      return notifications.map(mapNotification)
    },
    async markRead(notificationId) {
      await http.post(`/notifications/${notificationId}/read`)
    },
    async markAllRead() {
      await http.post('/notifications/read_all')
    },
  },

  messages: {
    async list(): Promise<MessageDraft[]> {
      return unsupported() as MessageDraft[]
    },
    async save() {
      return unsupported() as MessageDraft
    },
    async sendTest() {
      return unsupported() as { ok: boolean }
    },
  },
}

// Keep Flow/FlowSaveInput referenced so the adapter type stays aligned with MockApi.
export type HttpApiFlowTypes = Flow | FlowSaveInput

export function hasAccessToken(): boolean {
  return Boolean(getAccessToken())
}
