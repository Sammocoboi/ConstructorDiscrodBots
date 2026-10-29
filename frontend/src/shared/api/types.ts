export type Locale = 'ru' | 'en'
export type ThemePreference = 'auto' | 'light' | 'dark'
export type PlanId = 'free' | 'pro' | 'business'
export type BotStatus = 'online' | 'starting' | 'stopped' | 'error' | 'suspended'
export type BotDesiredState = 'running' | 'stopped'
export type ActivityType = 'playing' | 'watching' | 'listening' | 'competing'
export type ModuleCategory = 'community' | 'moderation' | 'roles' | 'utility' | 'engagement' | 'logs'
export type CommandType = 'slash' | 'message' | 'user'
export type CommandSource = 'library' | 'custom'
export type TemplateCategory =
  | 'community'
  | 'moderation'
  | 'gaming'
  | 'education'
  | 'commerce'
  | 'content'
  | 'roleplay'
  | 'minimal'

export interface User {
  id: string
  username: string
  email: string
  avatarColor: string
  locale: Locale
  timezone: string
  theme: ThemePreference
  plan: PlanId
  isStaff: boolean
  twoFactorEnabled: boolean
  createdAt: string
  avatarUrl?: string
  isEmailVerified?: boolean
}

export interface AuthSession {
  user: User
  accessToken: string
}

export interface Channel {
  id: string
  name: string
  type: 'text' | 'voice' | 'category' | 'forum'
}

export interface Role {
  id: string
  name: string
  color: string
  position: number
  managed?: boolean
}

export interface Guild {
  id: string
  name: string
  iconColor: string
  memberCount: number
  botAdded: boolean
  owner: boolean
  canManage: boolean
  channels: Channel[]
  roles: Role[]
}

export interface BotActivity {
  type: ActivityType
  text: string
}

export interface Bot {
  id: string
  name: string
  description: string
  templateId?: string
  status: BotStatus
  desiredState: BotDesiredState
  ping: number
  uptimeSeconds: number
  guilds: Guild[]
  lastError?: string
  tokenMasked: string
  applicationId: string
  inviteUrl: string
  avatarColor: string
  bannerColor: string
  activity: BotActivity
  createdAt: string
  updatedAt: string
  version: string
  runtimeVersion: string
  ownerId: string
}

export interface BotActivityEvent {
  id: string
  botId: string
  type: 'runtime' | 'config' | 'command' | 'module' | 'error'
  message: string
  createdAt: string
}

export interface JsonSchemaEnumOption {
  value: string | number
  label: string
}

export interface JsonSchemaProperty {
  type: 'string' | 'number' | 'integer' | 'boolean' | 'array'
  title: string
  description?: string
  default?: unknown
  enum?: JsonSchemaEnumOption[]
  format?: 'text' | 'textarea' | 'channel' | 'role' | 'color' | 'duration' | 'secret'
  items?: { type: 'string' | 'number' }
  minimum?: number
  maximum?: number
}

export interface JsonSchema {
  type: 'object'
  title?: string
  description?: string
  properties: Record<string, JsonSchemaProperty>
  required?: string[]
}

export interface ModuleManifest {
  id: string
  title: string
  description: string
  category: ModuleCategory
  icon: string
  permissions: string[]
  intents: string[]
  enabledByDefault: boolean
  popular?: boolean
  settingsSchema: JsonSchema
}

export interface ModuleState {
  botId: string
  moduleId: string
  enabled: boolean
  settings: Record<string, Record<string, unknown>>
  warnings: string[]
  updatedAt: string
}

export interface Command {
  id: string
  botId: string
  name: string
  description: string
  type: CommandType
  enabled: boolean
  source: CommandSource
  category: string
  libraryId?: string
  requiredRoleId?: string
  responseText: string
  embed?: {
    title: string
    description: string
    color: string
  }
  updatedAt: string
  syncedAt?: string
}

export interface LibraryCommand {
  id: string
  name: string
  description: string
  category: 'moderation' | 'utility' | 'community' | 'fun' | 'roles' | 'economy'
  type: CommandType
  permissions: string[]
  parameters: { name: string; type: string; required: boolean; description: string }[]
  preview: string
  author: string
  installs: number
  flowSummary: string[]
}

export interface FlowNodeData extends Record<string, unknown> {
  blockId: string
  label: string
  config: Record<string, unknown>
  validationMessage?: string
  traceState?: 'pending' | 'ok' | 'error' | 'skipped'
}

export interface FlowNode {
  id: string
  type: 'block'
  position: { x: number; y: number }
  data: FlowNodeData
}

export interface FlowEdge {
  id: string
  source: string
  target: string
  sourceHandle?: string | null
  targetHandle?: string | null
  animated?: boolean
}

export interface FlowSnapshot {
  nodes: FlowNode[]
  edges: FlowEdge[]
}

export interface FlowVersion {
  id: string
  version: number
  comment: string
  author: string
  createdAt: string
  status: 'draft' | 'published' | 'archived'
  nodeCount: number
  edgeCount: number
  snapshot: FlowSnapshot
}

export interface Flow {
  id: string
  botId: string
  name: string
  description: string
  status: 'draft' | 'published'
  version: number
  updatedAt: string
  nodes: FlowNode[]
  edges: FlowEdge[]
  versions: FlowVersion[]
}

export interface FlowIssue {
  id: string
  code: string
  severity: 'error' | 'warning'
  nodeId?: string
  message: string
}

export interface FlowTraceStep {
  id: string
  nodeId?: string
  title: string
  status: 'ok' | 'skipped' | 'error'
  detail: string
  variables?: Record<string, unknown>
}

export interface FlowTestResult {
  success: boolean
  durationMs: number
  steps: FlowTraceStep[]
  variables: Record<string, unknown>
  output: string
}

export interface Template {
  id: string
  name: string
  description: string
  category: TemplateCategory
  tags: string[]
  iconColor: string
  featured: boolean
  system: boolean
  version: string
  minPlan: PlanId
  modules: string[]
  commandsCount: number
  flowsCount: number
  botsCount: number
  author: string
  ownerId?: string
  shareId?: string
  createdAt: string
}

export interface Notification {
  id: string
  type: 'info' | 'success' | 'warning' | 'error' | 'billing'
  title: string
  message: string
  read: boolean
  createdAt: string
  link?: string
}

export interface Plan {
  id: PlanId
  name: string
  priceMonthly: number
  description: string
  features: string[]
  limits: { bots: number; executions: number; guilds: number; members: number }
  highlighted?: boolean
}

export interface Usage {
  bots: number
  executions: number
  guilds: number
  members: number
  periodStart: string
  periodEnd: string
}

export interface Subscription {
  planId: PlanId
  status: 'active' | 'trialing' | 'past_due' | 'canceled'
  renewsAt?: string
  trialEndsAt?: string
  cancelAtPeriodEnd: boolean
}

export interface Invoice {
  id: string
  number: string
  amount: number
  currency: string
  status: 'paid' | 'open' | 'void'
  createdAt: string
  period: string
  downloadUrl?: string
}

export interface PaymentMethod {
  brand: 'visa' | 'mastercard'
  last4: string
  expires: string
}

export interface BillingOverview {
  subscription: Subscription
  usage: Usage
  invoices: Invoice[]
  paymentMethod?: PaymentMethod
  plans?: Plan[]
}

export interface Session {
  id: string
  device: string
  browser: string
  ip: string
  location: string
  lastActiveAt: string
  current: boolean
}

export interface AccountSettings {
  user: User
  sessions: Session[]
  notifications: {
    botErrors: boolean
    payments: boolean
    productUpdates: boolean
    weeklyDigest: boolean
  }
}

export interface MessageField {
  id: string
  name: string
  value: string
  inline: boolean
}

export interface Embed {
  id: string
  title: string
  description: string
  url: string
  color: string
  authorName: string
  authorIconUrl: string
  footerText: string
  footerIconUrl: string
  thumbnailUrl: string
  imageUrl: string
  fields: MessageField[]
}

export type ButtonStyle = 'primary' | 'secondary' | 'success' | 'danger' | 'link'

export interface MessageButton {
  id: string
  label: string
  style: ButtonStyle
  emoji: string
  url: string
  disabled: boolean
}

export interface SelectOption {
  id: string
  label: string
  value: string
  description: string
  emoji: string
}

export interface MessageSelect {
  enabled: boolean
  placeholder: string
  options: SelectOption[]
}

export interface MessageDraft {
  id: string
  name: string
  content: string
  embeds: Embed[]
  buttons: MessageButton[]
  select: MessageSelect
  updatedAt: string
}

export interface DashboardStats {
  bots: number
  online: number
  guilds: number
  unreadNotifications: number
}

export interface CreateBotInput {
  name: string
  description: string
  templateId?: string
  token: string
  guildIds: string[]
  avatarColor: string
}

export interface UpdateBotInput {
  name?: string
  description?: string
  avatarColor?: string
  bannerColor?: string
  activity?: BotActivity
}

export interface FlowSaveInput {
  nodes: FlowNode[]
  edges: FlowEdge[]
  name?: string
  description?: string
}

export interface TemplateExport {
  schemaVersion: 1
  name: string
  description: string
  category: TemplateCategory
  tags: string[]
  version: string
  modules: string[]
  commands: Omit<Command, 'botId' | 'id' | 'updatedAt' | 'syncedAt'>[]
  flows: { name: string; description: string; nodes: FlowNode[]; edges: FlowEdge[] }[]
  createdAt: string
}
