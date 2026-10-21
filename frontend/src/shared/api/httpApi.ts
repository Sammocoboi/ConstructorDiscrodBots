import type { MockApi } from './mockApi'
import type {
  AuthSession,
  BillingOverview,
  Bot,
  BotActivityEvent,
  Command,
  CreateBotInput,
  DashboardStats,
  Flow,
  FlowIssue,
  FlowSaveInput,
  FlowTestResult,
  Guild,
  LibraryCommand,
  MessageDraft,
  ModuleManifest,
  ModuleState,
  Notification,
  Template,
  TemplateExport,
  UpdateBotInput,
  User,
} from './types'
import { API_BASE, http } from './http'

interface RawAuthSession {
  user: User
  access_token?: string
  accessToken?: string
}

interface AccountResponse {
  user: User
  sessions: {
    id: string
    device: string
    browser: string
    ip: string
    location: string
    last_active_at: string
    current: boolean
  }[]
  notifications: {
    botErrors: boolean
    payments: boolean
    productUpdates: boolean
    weeklyDigest: boolean
  }
}

const toSession = (raw: RawAuthSession): AuthSession => ({
  user: raw.user,
  accessToken: raw.access_token ?? raw.accessToken ?? '',
})

export const httpApi: MockApi = {
  auth: {
    async login(input) {
      return toSession(await http.post<RawAuthSession>('/auth/login', input))
    },
    async register(input) {
      return toSession(await http.post<RawAuthSession>('/auth/register', input))
    },
    async loginWithDiscord() {
      const next = encodeURIComponent(`${window.location.pathname}${window.location.search}`)
      window.location.assign(`${API_BASE}/auth/discord?next=${next}`)
      return new Promise<AuthSession>(() => undefined)
    },
    async forgotPassword(email) {
      await http.post('/auth/password/forgot', { email })
    },
    async resetPassword(password) {
      await http.post('/auth/password/reset', { password })
    },
    async verifyEmail(code) {
      await http.post('/auth/email/verify', { code })
    },
    async me() {
      return http.get<User>('/me')
    },
    async logout() {
      await http.post('/auth/logout')
    },
  },

  dashboard: {
    async stats() {
      return http.get<DashboardStats>('/dashboard/stats')
    },
  },

  bots: {
    async list() {
      return http.get<Bot[]>('/bots')
    },
    async get(botId) {
      return http.get<Bot>(`/bots/${botId}`)
    },
    async create(input: CreateBotInput) {
      return http.post<Bot>('/bots', input)
    },
    async update(botId, patch: UpdateBotInput) {
      return http.patch<Bot>(`/bots/${botId}`, patch)
    },
    async remove(botId) {
      await http.delete(`/bots/${botId}`)
    },
    async start(botId) {
      return http.post<Bot>(`/bots/${botId}/start`)
    },
    async stop(botId) {
      return http.post<Bot>(`/bots/${botId}/stop`)
    },
    async restart(botId) {
      return http.post<Bot>(`/bots/${botId}/restart`)
    },
    async validateToken(token) {
      return http.post<{
        valid: boolean
        username: string
        applicationId: string
        avatarColor: string
        guildsCount: number
      }>('/bots/validate-token', { token })
    },
    async replaceToken(botId, token) {
      return http.post<Bot>(`/bots/${botId}/token`, { token })
    },
    async availableGuilds() {
      return http.get<Guild[]>('/me/discord-guilds')
    },
    async guilds(botId) {
      return http.get<Guild[]>(`/bots/${botId}/guilds`)
    },
    async events(botId) {
      return http.get<BotActivityEvent[]>(`/bots/${botId}/events`)
    },
    async copySettings(botId, input) {
      await http.post(`/bots/${botId}/settings/copy`, input)
    },
    async saveAsTemplate(botId, input) {
      return http.post<Template>(`/bots/${botId}/save-as-template`, input)
    },
  },

  modules: {
    async list() {
      return http.get<ModuleManifest[]>('/modules')
    },
    async forBot(botId) {
      return http.get<{ manifest: ModuleManifest; state: ModuleState }[]>(
        `/bots/${botId}/modules`,
      )
    },
    async get(botId, moduleId) {
      return http.get<{ manifest: ModuleManifest; state: ModuleState }>(
        `/bots/${botId}/modules/${moduleId}`,
      )
    },
    async toggle(botId, moduleId, enabled) {
      return http.patch<ModuleState>(`/bots/${botId}/modules/${moduleId}`, { enabled })
    },
    async updateSettings(botId, moduleId, guildId, settings) {
      return http.put<ModuleState>(
        `/bots/${botId}/modules/${moduleId}/settings/${guildId}`,
        settings,
      )
    },
  },

  commands: {
    async list(botId) {
      return http.get<Command[]>(`/bots/${botId}/commands`)
    },
    async library() {
      return http.get<LibraryCommand[]>('/commands-library')
    },
    async install(botId, libraryId) {
      return http.post<Command>(`/bots/${botId}/commands/install`, { libraryId })
    },
    async create(botId, input: Partial<Command>) {
      return http.post<Command>(`/bots/${botId}/commands`, input)
    },
    async update(botId, commandId, patch: Partial<Command>) {
      return http.patch<Command>(`/bots/${botId}/commands/${commandId}`, patch)
    },
    async remove(botId, commandId) {
      await http.delete(`/bots/${botId}/commands/${commandId}`)
    },
    async sync(botId) {
      return http.post<{ count: number; syncedAt: string }>(
        `/bots/${botId}/commands/sync`,
      )
    },
    async test(botId, input) {
      return http.post<FlowTestResult>(`/bots/${botId}/commands/test`, input)
    },
  },

  flows: {
    async list(botId) {
      return http.get<Flow[]>(`/bots/${botId}/flows`)
    },
    async get(botId, flowId) {
      return http.get<Flow>(`/bots/${botId}/flows/${flowId}`)
    },
    async create(botId, input) {
      return http.post<Flow>(`/bots/${botId}/flows`, input)
    },
    async save(botId, flowId, input: FlowSaveInput) {
      return http.put<Flow>(`/bots/${botId}/flows/${flowId}`, input)
    },
    async remove(botId, flowId) {
      await http.delete(`/bots/${botId}/flows/${flowId}`)
    },
    async validate(botId, flowId, input) {
      return http.post<FlowIssue[]>(`/bots/${botId}/flows/${flowId}/validate`, input)
    },
    async test(botId, flowId, input) {
      return http.post<FlowTestResult>(`/bots/${botId}/flows/${flowId}/test`, input)
    },
    async publish(botId, flowId, comment) {
      return http.post<Flow>(`/bots/${botId}/flows/${flowId}/publish`, { comment })
    },
    async rollback(botId, flowId, versionId) {
      return http.post<Flow>(`/bots/${botId}/flows/${flowId}/rollback`, { versionId })
    },
  },

  templates: {
    async list() {
      return http.get<Template[]>('/templates')
    },
    async mine() {
      return http.get<Template[]>('/templates/mine')
    },
    async get(templateId) {
      return http.get<Template>(`/templates/${templateId}`)
    },
    async createFromBot(botId, input) {
      return http.post<Template>(`/bots/${botId}/save-as-template`, input)
    },
    async import(payload: TemplateExport) {
      return http.post<Template>('/templates/import', payload)
    },
    async remove(templateId) {
      await http.delete(`/templates/${templateId}`)
    },
    async export(templateId) {
      return http.get<TemplateExport>(`/templates/${templateId}/export`)
    },
    async share(templateId) {
      return http.post<{ shareId: string; url: string }>(
        `/templates/${templateId}/share`,
      )
    },
  },

  billing: {
    async overview() {
      return http.get<BillingOverview>('/billing')
    },
    async checkout(planId) {
      return http.post<{ url: string }>('/billing/checkout', { planId })
    },
    async portal() {
      return http.post<{ url: string }>('/billing/portal')
    },
    async cancel() {
      return http.post<BillingOverview>('/billing/cancel')
    },
    async downloadInvoice(invoiceId) {
      return http.post<{ url: string }>(`/billing/invoices/${invoiceId}/download`)
    },
  },

  account: {
    async get() {
      const raw = await http.get<AccountResponse>('/me/account')
      return {
        user: raw.user,
        sessions: raw.sessions.map((session) => ({
          id: session.id,
          device: session.device,
          browser: session.browser,
          ip: session.ip,
          location: session.location,
          lastActiveAt: session.last_active_at,
          current: session.current,
        })),
        notifications: raw.notifications,
      }
    },
    async updateProfile(patch) {
      return http.patch<User>('/me', patch)
    },
    async updateNotifications(patch) {
      return http.put<{
        botErrors: boolean
        payments: boolean
        productUpdates: boolean
        weeklyDigest: boolean
      }>('/me/notifications', patch)
    },
    async revokeSession(sessionId) {
      await http.delete(`/me/sessions/${sessionId}`)
    },
    async logoutEverywhere() {
      await http.post('/me/sessions/logout-all')
    },
    async deleteAccount() {
      await http.delete('/me')
    },
  },

  notifications: {
    async list() {
      return http.get<Notification[]>('/notifications')
    },
    async markRead(notificationId) {
      await http.post(`/notifications/${notificationId}/read`)
    },
    async markAllRead() {
      await http.post('/notifications/read-all')
    },
  },

  messages: {
    async list() {
      return http.get<MessageDraft[]>('/messages')
    },
    async save(draft) {
      return http.put<MessageDraft>(`/messages/${draft.id}`, draft)
    },
    async sendTest(draft) {
      return http.post<{ ok: boolean }>('/messages/test', draft)
    },
  },
}
