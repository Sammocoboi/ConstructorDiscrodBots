import type {
  Bot,
  BotActivityEvent,
  BillingOverview,
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
  Session,
  Template,
  TemplateExport,
  UpdateBotInput,
  User,
} from './types'
import { ApiError } from './errors'
import { validateFlowGraph, simulateFlow } from '../lib/flowGraph'
import { schemaDefaults } from '../lib/jsonSchema'
import { getDb, persistDb } from '../mocks/db'

const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T
const randomDelay = (min = 180, max = 480) =>
  new Promise<void>((resolve) => {
    window.setTimeout(resolve, min + Math.random() * (max - min))
  })

const nowIso = () => new Date().toISOString()

function logEvent(
  botId: string,
  type: BotActivityEvent['type'],
  message: string,
) {
  const db = getDb()
  db.botEvents.unshift({
    id: `evt_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
    botId,
    type,
    message,
    createdAt: nowIso(),
  })
  db.botEvents = db.botEvents.slice(0, 120)
}

function addNotification(notification: Omit<Notification, 'id' | 'read' | 'createdAt'>) {
  const db = getDb()
  db.notifications.unshift({
    ...notification,
    id: `ntf_${Date.now()}`,
    read: false,
    createdAt: nowIso(),
  })
}

function findBot(botId: string): Bot {
  const bot = getDb().bots.find((item) => item.id === botId)
  if (!bot) throw new ApiError(404, 'bot_not_found', 'Бот не найден.')
  return bot
}

function findFlow(flowId: string): Flow {
  const flow = getDb().flows.find((item) => item.id === flowId)
  if (!flow) throw new ApiError(404, 'flow_not_found', 'Сценарий не найден.')
  return flow
}

function findModule(moduleId: string): ModuleManifest {
  const module = getDb().modules.find((item) => item.id === moduleId)
  if (!module) throw new ApiError(404, 'module_not_found', 'Модуль не найден.')
  return module
}

function findTemplate(templateId: string): Template {
  const template = getDb().templates.find((item) => item.id === templateId)
  if (!template) throw new ApiError(404, 'template_not_found', 'Шаблон не найден.')
  return template
}

function createSession(user: User) {
  return {
    user: clone(user),
    accessToken: `mock-access-${Date.now()}`,
  }
}

function moduleStateFor(
  bot: Bot,
  module: ModuleManifest,
  enabled: boolean,
): ModuleState {
  const settings: Record<string, Record<string, unknown>> = {}
  for (const guild of bot.guilds) {
    settings[guild.id] = {
      ...schemaDefaults(module.settingsSchema),
      channelId:
        guild.channels.find((channel) => channel.name === 'welcome')?.id ??
        guild.channels[0]?.id ??
        '',
      logChannelId:
        guild.channels.find((channel) => channel.name === 'logs')?.id ??
        guild.channels[0]?.id ??
        '',
      autoRoleId: guild.roles.find((role) => role.id === 'role_member')?.id ?? '',
      supportRoleId: guild.roles.find((role) => role.id === 'role_mod')?.id ?? '',
    }
  }
  return {
    botId: bot.id,
    moduleId: module.id,
    enabled,
    settings,
    warnings: [],
    updatedAt: nowIso(),
  }
}

export const mockApi = {
  auth: {
    async login(input: { email: string; password: string }) {
      await randomDelay(300, 600)
      const db = getDb()
      db.user.email = input.email
      persistDb()
      return createSession(db.user)
    },
    async register(input: { name: string; email: string; password: string }) {
      await randomDelay(350, 650)
      const db = getDb()
      db.user.username = input.name
      db.user.email = input.email
      persistDb()
      return createSession(db.user)
    },
    async loginWithDiscord() {
      await randomDelay(450, 800)
      return createSession(getDb().user)
    },
    async forgotPassword(_email: string) {
      await randomDelay()
    },
    async resetPassword(_password: string) {
      await randomDelay()
    },
    async verifyEmail(_code: string) {
      await randomDelay()
    },
    async me() {
      await randomDelay(80, 160)
      return clone(getDb().user)
    },
    async logout() {
      await randomDelay(80, 140)
    },
  },

  dashboard: {
    async stats(): Promise<DashboardStats> {
      await randomDelay(80, 180)
      const db = getDb()
      return {
        bots: db.bots.length,
        online: db.bots.filter((bot) => bot.status === 'online').length,
        guilds: db.bots.reduce((sum, bot) => sum + bot.guilds.length, 0),
        unreadNotifications: db.notifications.filter((item) => !item.read).length,
      }
    },
  },

  bots: {
    async list(): Promise<Bot[]> {
      await randomDelay(120, 280)
      return clone(getDb().bots)
    },
    async get(botId: string): Promise<Bot> {
      await randomDelay(100, 220)
      return clone(findBot(botId))
    },
    async create(input: CreateBotInput): Promise<Bot> {
      await randomDelay(450, 700)
      const db = getDb()
      const guilds = db.guilds.filter((guild) => input.guildIds.includes(guild.id))
      const template = input.templateId
        ? db.templates.find((item) => item.id === input.templateId)
        : undefined
      const bot: Bot = {
        id: `bot_${Date.now()}`,
        name: input.name,
        description: input.description,
        templateId: input.templateId,
        status: 'stopped',
        desiredState: 'stopped',
        ping: 0,
        uptimeSeconds: 0,
        guilds: guilds.map((guild) => ({ ...guild, botAdded: true })),
        tokenMasked: `${input.token.slice(0, 10)}.***.***${input.token.slice(-4)}`,
        applicationId: `${Math.floor(1e17 + Math.random() * 8e17)}`,
        inviteUrl: `https://discord.com/oauth2/authorize?client_id=${Math.floor(1e17 + Math.random() * 8e17)}&scope=bot%20applications.commands&permissions=1099511627776`,
        avatarColor: input.avatarColor,
        bannerColor: '#1f2160',
        activity: { type: 'playing', text: 'с участниками' },
        createdAt: nowIso(),
        updatedAt: nowIso(),
        version: '1.0.0',
        runtimeVersion: 'runtime-0.9.7',
        ownerId: db.user.id,
      }
      db.bots.push(bot)
      db.guilds = db.guilds.map((guild) =>
        input.guildIds.includes(guild.id) ? { ...guild, botAdded: true } : guild,
      )
      for (const module of db.modules) {
        db.moduleStates.push(
          moduleStateFor(bot, module, template?.modules.includes(module.id) ?? false),
        )
      }
      if (template) {
        const triggerId = `n_${Date.now()}_trigger`
        const actionId = `n_${Date.now()}_action`
        const nodes = [
          {
            id: triggerId,
            type: 'block' as const,
            position: { x: 40, y: 40 },
            data: {
              blockId: 'trigger.slash',
              label: 'Slash-команда',
              config: { commandName: 'start' },
            },
          },
          {
            id: actionId,
            type: 'block' as const,
            position: { x: 40, y: 220 },
            data: {
              blockId: 'action.send_message',
              label: 'Ответить приветствием',
              config: {
                channelId: guilds[0]?.channels[0]?.id ?? '',
                text: `Привет! Я ${bot.name}, готов помогать серверу.`,
              },
            },
          },
        ]
        db.flows.push({
          id: `flow_${Date.now()}`,
          botId: bot.id,
          name: 'Первый сценарий',
          description: 'Стартовый сценарий из шаблона.',
          status: 'draft',
          version: 1,
          updatedAt: nowIso(),
          nodes,
          edges: [{ id: `edge_${Date.now()}`, source: triggerId, target: actionId }],
          versions: [
            {
              id: `fv_${Date.now()}`,
              version: 1,
              comment: 'Создан из шаблона',
              author: db.user.username,
              createdAt: nowIso(),
              status: 'draft',
              nodeCount: 2,
              edgeCount: 1,
              snapshot: {
                nodes: clone(nodes),
                edges: [{ id: `edge_${Date.now()}`, source: triggerId, target: actionId }],
              },
            },
          ],
        })
      }
      logEvent(bot.id, 'config', `Бот создан из шаблона «${template?.name ?? 'С нуля'}»`)
      addNotification({
        type: 'success',
        title: 'Бот создан',
        message: `«${bot.name}» готов к подключению. Запустите его из обзора.`,
        link: `/app/bots/${bot.id}`,
      })
      persistDb()
      return clone(bot)
    },
    async update(botId: string, patch: UpdateBotInput): Promise<Bot> {
      await randomDelay(200, 400)
      const bot = findBot(botId)
      Object.assign(bot, patch, { updatedAt: nowIso() })
      logEvent(botId, 'config', 'Профиль бота обновлён')
      persistDb()
      return clone(bot)
    },
    async remove(botId: string) {
      await randomDelay(250, 450)
      const db = getDb()
      findBot(botId)
      db.bots = db.bots.filter((bot) => bot.id !== botId)
      db.botEvents = db.botEvents.filter((event) => event.botId !== botId)
      db.moduleStates = db.moduleStates.filter((state) => state.botId !== botId)
      db.commands = db.commands.filter((command) => command.botId !== botId)
      db.flows = db.flows.filter((flow) => flow.botId !== botId)
      persistDb()
    },
    async start(botId: string): Promise<Bot> {
      await randomDelay(200, 400)
      const bot = findBot(botId)
      bot.status = 'starting'
      bot.desiredState = 'running'
      bot.updatedAt = nowIso()
      logEvent(botId, 'runtime', 'Запрошен запуск бота')
      persistDb()
      window.setTimeout(() => {
        const db = getDb()
        const current = db.bots.find((item) => item.id === botId)
        if (!current || current.status !== 'starting') return
        current.status = 'online'
        current.ping = 22 + Math.floor(Math.random() * 48)
        current.uptimeSeconds = 1
        current.lastError = undefined
        current.updatedAt = nowIso()
        logEvent(botId, 'runtime', `Gateway подключён · ping ${current.ping} мс`)
        persistDb()
      }, 1_800)
      return clone(bot)
    },
    async stop(botId: string): Promise<Bot> {
      await randomDelay(200, 400)
      const bot = findBot(botId)
      bot.status = 'stopped'
      bot.desiredState = 'stopped'
      bot.ping = 0
      bot.uptimeSeconds = 0
      bot.updatedAt = nowIso()
      logEvent(botId, 'runtime', 'Бот остановлен по запросу пользователя')
      persistDb()
      return clone(bot)
    },
    async restart(botId: string): Promise<Bot> {
      await randomDelay(200, 400)
      const bot = findBot(botId)
      bot.status = 'starting'
      bot.desiredState = 'running'
      bot.updatedAt = nowIso()
      logEvent(botId, 'runtime', 'Перезапуск бота')
      persistDb()
      window.setTimeout(() => {
        const db = getDb()
        const current = db.bots.find((item) => item.id === botId)
        if (!current || current.status !== 'starting') return
        current.status = 'online'
        current.ping = 24 + Math.floor(Math.random() * 42)
        current.lastError = undefined
        current.updatedAt = nowIso()
        logEvent(botId, 'runtime', `Бот онлайн · ping ${current.ping} мс`)
        persistDb()
      }, 1_800)
      return clone(bot)
    },
    async validateToken(token: string) {
      await randomDelay(500, 900)
      if (token.trim().length < 20) {
        throw new ApiError(400, 'invalid_token', 'Discord отклонил токен. Проверьте значение.')
      }
      return {
        valid: true,
        username: 'Хранитель',
        applicationId: `${Math.floor(1e17 + Math.random() * 8e17)}`,
        avatarColor: '#5865f2',
        guildsCount: 2,
      }
    },
    async replaceToken(botId: string, token: string): Promise<Bot> {
      await randomDelay(400, 700)
      if (token.trim().length < 20) {
        throw new ApiError(400, 'invalid_token', 'Discord отклонил токен. Проверьте значение.')
      }
      const bot = findBot(botId)
      bot.tokenMasked = `${token.slice(0, 10)}.***.***${token.slice(-4)}`
      bot.lastError = undefined
      bot.status = 'stopped'
      bot.desiredState = 'stopped'
      bot.updatedAt = nowIso()
      logEvent(botId, 'config', 'Токен заменён, бот остановлен')
      addNotification({
        type: 'success',
        title: 'Токен заменён',
        message: `Токен «${bot.name}» обновлён. Запустите бота, чтобы применить изменения.`,
        link: `/app/bots/${botId}`,
      })
      persistDb()
      return clone(bot)
    },
    async availableGuilds(): Promise<Guild[]> {
      await randomDelay(180, 380)
      return clone(getDb().guilds.filter((guild) => guild.canManage || guild.owner))
    },
    async guilds(botId: string): Promise<Guild[]> {
      await randomDelay(120, 260)
      return clone(findBot(botId).guilds)
    },
    async events(botId: string): Promise<BotActivityEvent[]> {
      await randomDelay(100, 200)
      return clone(
        getDb()
          .botEvents.filter((event) => event.botId === botId)
          .sort((a, b) => b.createdAt.localeCompare(a.createdAt)),
      )
    },
    async copySettings(
      botId: string,
      input: { fromGuildId: string; toGuildId: string },
    ) {
      await randomDelay(250, 500)
      const db = getDb()
      findBot(botId)
      const states = db.moduleStates.filter((state) => state.botId === botId)
      for (const state of states) {
        if (state.settings[input.fromGuildId]) {
          state.settings[input.toGuildId] = clone(state.settings[input.fromGuildId])
        }
      }
      logEvent(botId, 'module', 'Настройки гильдий скопированы')
      persistDb()
    },
    async saveAsTemplate(botId: string, input: { name: string; description: string }) {
      await randomDelay(300, 550)
      const db = getDb()
      const bot = findBot(botId)
      const enabledModules = db.moduleStates
        .filter((state) => state.botId === botId && state.enabled)
        .map((state) => state.moduleId)
      const template: Template = {
        id: `tpl_${Date.now()}`,
        name: input.name,
        description: input.description,
        category: 'community',
        tags: ['личный'],
        iconColor: bot.avatarColor,
        featured: false,
        system: false,
        version: '1.0.0',
        minPlan: 'pro',
        modules: enabledModules,
        commandsCount: db.commands.filter((command) => command.botId === botId).length,
        flowsCount: db.flows.filter((flow) => flow.botId === botId).length,
        botsCount: 0,
        author: db.user.username,
        ownerId: db.user.id,
        shareId: `${bot.id.slice(-4)}-${Math.random().toString(36).slice(2, 7)}`,
        createdAt: nowIso(),
      }
      db.templates.push(template)
      persistDb()
      return clone(template)
    },
  },

  modules: {
    async list(): Promise<ModuleManifest[]> {
      await randomDelay(100, 220)
      return clone(getDb().modules)
    },
    async forBot(botId: string): Promise<{ manifest: ModuleManifest; state: ModuleState }[]> {
      await randomDelay(120, 260)
      const db = getDb()
      findBot(botId)
      return db.modules.map((manifest) => {
        let state = db.moduleStates.find(
          (item) => item.botId === botId && item.moduleId === manifest.id,
        )
        if (!state) {
          state = moduleStateFor(findBot(botId), manifest, manifest.enabledByDefault)
          db.moduleStates.push(state)
        }
        return { manifest: clone(manifest), state: clone(state) }
      })
    },
    async get(botId: string, moduleId: string) {
      await randomDelay(100, 220)
      const db = getDb()
      const manifest = findModule(moduleId)
      const state = db.moduleStates.find(
        (item) => item.botId === botId && item.moduleId === moduleId,
      )
      if (!state) throw new ApiError(404, 'module_state_not_found', 'Настройки модуля не найдены.')
      return { manifest: clone(manifest), state: clone(state) }
    },
    async toggle(botId: string, moduleId: string, enabled: boolean): Promise<ModuleState> {
      await randomDelay(180, 320)
      const db = getDb()
      findBot(botId)
      let state = db.moduleStates.find(
        (item) => item.botId === botId && item.moduleId === moduleId,
      )
      if (!state) {
        const manifest = findModule(moduleId)
        state = moduleStateFor(findBot(botId), manifest, enabled)
        db.moduleStates.push(state)
      }
      state.enabled = enabled
      state.updatedAt = nowIso()
      logEvent(botId, 'module', `Модуль «${findModule(moduleId).title}» ${enabled ? 'включён' : 'выключен'}`)
      persistDb()
      return clone(state)
    },
    async updateSettings(
      botId: string,
      moduleId: string,
      guildId: string,
      settings: Record<string, unknown>,
    ): Promise<ModuleState> {
      await randomDelay(220, 420)
      const db = getDb()
      const state = db.moduleStates.find(
        (item) => item.botId === botId && item.moduleId === moduleId,
      )
      if (!state) throw new ApiError(404, 'module_state_not_found', 'Настройки модуля не найдены.')
      state.settings[guildId] = settings
      state.updatedAt = nowIso()
      state.warnings = []
      logEvent(botId, 'module', `Настройки модуля «${findModule(moduleId).title}» обновлены`)
      persistDb()
      return clone(state)
    },
  },

  commands: {
    async list(botId: string): Promise<Command[]> {
      await randomDelay(120, 250)
      findBot(botId)
      return clone(
        getDb()
          .commands.filter((command) => command.botId === botId)
          .sort((a, b) => a.name.localeCompare(b.name)),
      )
    },
    async library(): Promise<LibraryCommand[]> {
      await randomDelay(150, 320)
      return clone(getDb().library)
    },
    async install(botId: string, libraryId: string): Promise<Command> {
      await randomDelay(280, 520)
      const db = getDb()
      findBot(botId)
      const source = db.library.find((item) => item.id === libraryId)
      if (!source) throw new ApiError(404, 'library_command_not_found', 'Команда не найдена.')
      const conflict = db.commands.find(
        (command) =>
          command.botId === botId && command.name.toLowerCase() === source.name.toLowerCase(),
      )
      if (conflict) {
        throw new ApiError(409, 'command_conflict', `Команда /${source.name} уже существует.`)
      }
      const command: Command = {
        id: `cmd_${Date.now()}`,
        botId,
        name: source.name,
        description: source.description,
        type: source.type,
        enabled: true,
        source: 'library',
        category: source.category,
        libraryId: source.id,
        responseText: source.preview,
        updatedAt: nowIso(),
      }
      db.commands.push(command)
      logEvent(botId, 'command', `Установлена команда /${command.name}`)
      persistDb()
      return clone(command)
    },
    async create(botId: string, input: Partial<Command>): Promise<Command> {
      await randomDelay(280, 500)
      const db = getDb()
      findBot(botId)
      const name = (input.name ?? '').trim().toLowerCase().replace(/^\//, '')
      if (!name) throw new ApiError(400, 'invalid_name', 'Укажите имя команды.')
      const conflict = db.commands.find(
        (command) => command.botId === botId && command.name.toLowerCase() === name,
      )
      if (conflict) {
        throw new ApiError(409, 'command_conflict', `Команда /${name} уже существует.`)
      }
      const command: Command = {
        id: `cmd_${Date.now()}`,
        botId,
        name,
        description: input.description ?? '',
        type: input.type ?? 'slash',
        enabled: true,
        source: 'custom',
        category: input.category ?? 'utility',
        requiredRoleId: input.requiredRoleId,
        responseText: input.responseText ?? '',
        embed: input.embed,
        updatedAt: nowIso(),
      }
      db.commands.push(command)
      logEvent(botId, 'command', `Создана команда /${command.name}`)
      persistDb()
      return clone(command)
    },
    async update(botId: string, commandId: string, patch: Partial<Command>): Promise<Command> {
      await randomDelay(220, 420)
      const db = getDb()
      const command = db.commands.find(
        (item) => item.id === commandId && item.botId === botId,
      )
      if (!command) throw new ApiError(404, 'command_not_found', 'Команда не найдена.')
      if (patch.name && patch.name.toLowerCase() !== command.name.toLowerCase()) {
        const conflict = db.commands.find(
          (item) =>
            item.botId === botId &&
            item.id !== commandId &&
            item.name.toLowerCase() === patch.name?.toLowerCase(),
        )
        if (conflict) throw new ApiError(409, 'command_conflict', 'Команда с таким именем уже существует.')
      }
      Object.assign(command, patch, { updatedAt: nowIso() })
      persistDb()
      return clone(command)
    },
    async remove(botId: string, commandId: string) {
      await randomDelay(180, 320)
      const db = getDb()
      db.commands = db.commands.filter(
        (command) => !(command.botId === botId && command.id === commandId),
      )
      persistDb()
    },
    async sync(botId: string): Promise<{ count: number; syncedAt: string }> {
      await randomDelay(550, 900)
      const db = getDb()
      findBot(botId)
      const commands = db.commands.filter((command) => command.botId === botId)
      const syncedAt = nowIso()
      for (const command of commands) command.syncedAt = syncedAt
      logEvent(botId, 'command', `Синхронизировано ${commands.length} команд`)
      persistDb()
      return { count: commands.length, syncedAt }
    },
    async test(
      _botId: string,
      input: { name: string; requiredRoleId?: string; responseText: string; embed?: Command['embed'] },
    ): Promise<FlowTestResult> {
      await randomDelay(450, 800)
      const steps = [
        {
          id: 'step_trigger',
          title: `Slash-команда /${input.name || 'command'} получена`,
          status: 'ok' as const,
          detail: 'Пользователь: @tester · Канал: #general',
          variables: { 'user.id': '842013445120', 'user.roles': ['VIP'] },
        },
        {
          id: 'step_condition',
          title: input.requiredRoleId ? 'Проверка роли' : 'Дополнительных условий нет',
          status: 'ok' as const,
          detail: input.requiredRoleId
            ? 'У пользователя есть необходимая роль. Условие выполнено.'
            : 'Команда доступна всем участникам.',
        },
        {
          id: 'step_action',
          title: 'Формирование ответа',
          status: input.responseText ? ('ok' as const) : ('error' as const),
          detail: input.responseText
            ? input.embed
              ? 'Эмбед собран и проверен по лимитам Discord.'
              : 'Текстовый ответ подготовлен.'
            : 'Ответ пуст: добавьте текст или эмбед.',
        },
        {
          id: 'step_send',
          title: 'Отправка ответа',
          status: input.responseText ? ('ok' as const) : ('skipped' as const),
          detail: input.responseText
            ? 'Dry-run: сообщение не отправлено в Discord.'
            : 'Пропущено из-за ошибки.',
        },
      ]
      return {
        success: Boolean(input.responseText),
        durationMs: 47,
        steps,
        variables: { 'user.id': '842013445120', 'user.roles': ['VIP'], 'guild.id': 'guild_design' },
        output: input.responseText || 'Ответ не сформирован.',
      }
    },
  },

  flows: {
    async list(botId: string): Promise<Flow[]> {
      await randomDelay(120, 260)
      findBot(botId)
      return clone(
        getDb()
          .flows.filter((flow) => flow.botId === botId)
          .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)),
      )
    },
    async get(botId: string, flowId: string): Promise<Flow> {
      await randomDelay(100, 220)
      const flow = findFlow(flowId)
      if (flow.botId !== botId) throw new ApiError(404, 'flow_not_found', 'Сценарий не найден.')
      return clone(flow)
    },
    async create(botId: string, input?: { name?: string; description?: string }): Promise<Flow> {
      await randomDelay(300, 550)
      const db = getDb()
      const bot = findBot(botId)
      const triggerId = `n_${Date.now()}_t`
      const actionId = `n_${Date.now()}_a`
      const nodes = [
        {
          id: triggerId,
          type: 'block' as const,
          position: { x: 40, y: 40 },
          data: {
            blockId: 'trigger.slash',
            label: 'Slash-команда',
            config: { commandName: 'hello' },
          },
        },
        {
          id: actionId,
          type: 'block' as const,
          position: { x: 40, y: 220 },
          data: {
            blockId: 'action.send_message',
            label: 'Отправить ответ',
            config: {
              channelId: bot.guilds[0]?.channels[0]?.id ?? '',
              text: 'Привет! Это новый сценарий.',
            },
          },
        },
      ]
      const edges = [{ id: `e_${Date.now()}`, source: triggerId, target: actionId }]
      const flow: Flow = {
        id: `flow_${Date.now()}`,
        botId,
        name: input?.name ?? 'Новый сценарий',
        description: input?.description ?? 'Черновик сценария.',
        status: 'draft',
        version: 1,
        updatedAt: nowIso(),
        nodes,
        edges,
        versions: [
          {
            id: `fv_${Date.now()}`,
            version: 1,
            comment: 'Создан черновик',
            author: db.user.username,
            createdAt: nowIso(),
            status: 'draft',
            nodeCount: nodes.length,
            edgeCount: edges.length,
            snapshot: { nodes: clone(nodes), edges: clone(edges) },
          },
        ],
      }
      db.flows.push(flow)
      logEvent(botId, 'config', `Создан сценарий «${flow.name}»`)
      persistDb()
      return clone(flow)
    },
    async save(botId: string, flowId: string, input: FlowSaveInput): Promise<Flow> {
      await randomDelay(220, 420)
      const flow = findFlow(flowId)
      if (flow.botId !== botId) throw new ApiError(404, 'flow_not_found', 'Сценарий не найден.')
      flow.nodes = clone(input.nodes)
      flow.edges = clone(input.edges)
      if (input.name !== undefined) flow.name = input.name
      if (input.description !== undefined) flow.description = input.description
      flow.updatedAt = nowIso()
      persistDb()
      return clone(flow)
    },
    async remove(botId: string, flowId: string) {
      await randomDelay(200, 380)
      const db = getDb()
      db.flows = db.flows.filter((flow) => !(flow.id === flowId && flow.botId === botId))
      persistDb()
    },
    async validate(
      _botId: string,
      flowId: string,
      input?: FlowSaveInput,
    ): Promise<FlowIssue[]> {
      await randomDelay(250, 450)
      const flow = findFlow(flowId)
      return validateFlowGraph(input?.nodes ?? flow.nodes, input?.edges ?? flow.edges)
    },
    async test(botId: string, flowId: string, input?: FlowSaveInput): Promise<FlowTestResult> {
      await randomDelay(500, 900)
      const flow = findFlow(flowId)
      if (flow.botId !== botId) throw new ApiError(404, 'flow_not_found', 'Сценарий не найден.')
      return simulateFlow(input?.nodes ?? flow.nodes, input?.edges ?? flow.edges)
    },
    async publish(botId: string, flowId: string, comment: string): Promise<Flow> {
      await randomDelay(320, 600)
      const db = getDb()
      const flow = findFlow(flowId)
      if (flow.botId !== botId) throw new ApiError(404, 'flow_not_found', 'Сценарий не найден.')
      const issues = validateFlowGraph(flow.nodes, flow.edges)
      const blocking = issues.filter((issue) => issue.severity === 'error')
      if (blocking.length) {
        throw new ApiError(422, 'flow_invalid', 'Сценарий содержит ошибки и не может быть опубликован.', blocking)
      }
      flow.version += 1
      flow.status = 'published'
      flow.updatedAt = nowIso()
      flow.versions.unshift({
        id: `fv_${Date.now()}`,
        version: flow.version,
        comment: comment || 'Публикация',
        author: db.user.username,
        createdAt: nowIso(),
        status: 'published',
        nodeCount: flow.nodes.length,
        edgeCount: flow.edges.length,
        snapshot: { nodes: clone(flow.nodes), edges: clone(flow.edges) },
      })
      for (const version of flow.versions.slice(1)) {
        if (version.status === 'published') version.status = 'archived'
      }
      logEvent(botId, 'config', `Опубликован сценарий «${flow.name}» v${flow.version}`)
      addNotification({
        type: 'success',
        title: 'Сценарий опубликован',
        message: `«${flow.name}» v${flow.version} активен.`,
        link: `/app/bots/${botId}/flows/${flowId}/versions`,
      })
      persistDb()
      return clone(flow)
    },
    async rollback(botId: string, flowId: string, versionId: string): Promise<Flow> {
      await randomDelay(320, 600)
      const db = getDb()
      const flow = findFlow(flowId)
      if (flow.botId !== botId) throw new ApiError(404, 'flow_not_found', 'Сценарий не найден.')
      const version = flow.versions.find((item) => item.id === versionId)
      if (!version) throw new ApiError(404, 'version_not_found', 'Версия не найдена.')
      flow.nodes = clone(version.snapshot.nodes)
      flow.edges = clone(version.snapshot.edges)
      flow.version += 1
      flow.status = 'published'
      flow.updatedAt = nowIso()
      flow.versions.unshift({
        id: `fv_${Date.now()}`,
        version: flow.version,
        comment: `Откат к версии ${version.version}`,
        author: db.user.username,
        createdAt: nowIso(),
        status: 'published',
        nodeCount: flow.nodes.length,
        edgeCount: flow.edges.length,
        snapshot: { nodes: clone(flow.nodes), edges: clone(flow.edges) },
      })
      logEvent(botId, 'config', `Откат сценария «${flow.name}» к v${version.version}`)
      persistDb()
      return clone(flow)
    },
  },

  templates: {
    async list(): Promise<Template[]> {
      await randomDelay(150, 300)
      return clone(getDb().templates.filter((template) => template.system))
    },
    async mine(): Promise<Template[]> {
      await randomDelay(120, 260)
      const db = getDb()
      return clone(
        db.templates
          .filter((template) => template.ownerId === db.user.id)
          .sort((a, b) => b.createdAt.localeCompare(a.createdAt)),
      )
    },
    async get(templateId: string): Promise<Template> {
      await randomDelay(100, 220)
      return clone(findTemplate(templateId))
    },
    async createFromBot(botId: string, input: { name: string; description: string }) {
      return mockApi.bots.saveAsTemplate(botId, input)
    },
    async import(payload: TemplateExport): Promise<Template> {
      await randomDelay(280, 500)
      const db = getDb()
      const template: Template = {
        id: `tpl_${Date.now()}`,
        name: payload.name,
        description: payload.description,
        category: payload.category,
        tags: payload.tags,
        iconColor: '#5865f2',
        featured: false,
        system: false,
        version: payload.version,
        minPlan: 'pro',
        modules: payload.modules,
        commandsCount: payload.commands.length,
        flowsCount: payload.flows.length,
        botsCount: 0,
        author: db.user.username,
        ownerId: db.user.id,
        shareId: `imp-${Math.random().toString(36).slice(2, 8)}`,
        createdAt: nowIso(),
      }
      db.templates.push(template)
      persistDb()
      return clone(template)
    },
    async remove(templateId: string) {
      await randomDelay(200, 380)
      const db = getDb()
      db.templates = db.templates.filter((template) => template.id !== templateId)
      persistDb()
    },
    async export(templateId: string): Promise<TemplateExport> {
      await randomDelay(200, 380)
      const template = findTemplate(templateId)
      return {
        schemaVersion: 1,
        name: template.name,
        description: template.description,
        category: template.category,
        tags: template.tags,
        version: template.version,
        modules: template.modules,
        commands: [],
        flows: [],
        createdAt: nowIso(),
      }
    },
    async share(templateId: string): Promise<{ shareId: string; url: string }> {
      await randomDelay(180, 320)
      const template = findTemplate(templateId)
      if (!template.shareId) {
        template.shareId = `${template.id.slice(-4)}-${Math.random().toString(36).slice(2, 8)}`
        persistDb()
      }
      return {
        shareId: template.shareId,
        url: `${window.location.origin}/t/${template.shareId}`,
      }
    },
  },

  billing: {
    async overview(): Promise<BillingOverview> {
      await randomDelay(150, 300)
      return clone(getDb().billing)
    },
    async checkout(planId: string) {
      await randomDelay(350, 700)
      return { url: `https://checkout.stripe.test/session/${planId}` }
    },
    async portal() {
      await randomDelay(300, 600)
      return { url: 'https://billing.stripe.test/portal' }
    },
    async cancel() {
      await randomDelay(300, 550)
      const db = getDb()
      db.billing.subscription.cancelAtPeriodEnd = true
      persistDb()
      return clone(db.billing)
    },
    async downloadInvoice(invoiceId: string) {
      await randomDelay(150, 300)
      return { url: `#invoice-${invoiceId}` }
    },
  },

  account: {
    async get() {
      await randomDelay(120, 260)
      const db = getDb()
      return {
        user: clone(db.user),
        sessions: clone(db.sessions),
        notifications: clone(db.accountNotifications),
      }
    },
    async updateProfile(patch: Partial<User>): Promise<User> {
      await randomDelay(250, 450)
      const db = getDb()
      Object.assign(db.user, patch)
      persistDb()
      return clone(db.user)
    },
    async updateNotifications(
      patch: Partial<{
        botErrors: boolean
        payments: boolean
        productUpdates: boolean
        weeklyDigest: boolean
      }>,
    ) {
      await randomDelay(200, 380)
      const db = getDb()
      Object.assign(db.accountNotifications, patch)
      persistDb()
      return clone(db.accountNotifications)
    },
    async revokeSession(sessionId: string) {
      await randomDelay(200, 360)
      const db = getDb()
      db.sessions = db.sessions.filter((session) => session.id !== sessionId)
      persistDb()
    },
    async logoutEverywhere() {
      await randomDelay(250, 450)
      const db = getDb()
      db.sessions = db.sessions.filter((session) => session.current)
      persistDb()
    },
    async deleteAccount() {
      await randomDelay(500, 800)
      addNotification({
        type: 'warning',
        title: 'Аккаунт помечен на удаление',
        message: 'Данные будут удалены через 14 дней. Поддержка может восстановить аккаунт.',
      })
      persistDb()
    },
  },

  notifications: {
    async list(): Promise<Notification[]> {
      await randomDelay(100, 220)
      return clone(
        getDb().notifications.sort((a, b) => b.createdAt.localeCompare(a.createdAt)),
      )
    },
    async markRead(notificationId: string) {
      await randomDelay(80, 160)
      const db = getDb()
      const notification = db.notifications.find((item) => item.id === notificationId)
      if (notification) notification.read = true
      persistDb()
    },
    async markAllRead() {
      await randomDelay(150, 280)
      const db = getDb()
      for (const notification of db.notifications) notification.read = true
      persistDb()
    },
  },

  messages: {
    async list(): Promise<MessageDraft[]> {
      await randomDelay(120, 250)
      return clone(getDb().messages)
    },
    async save(draft: MessageDraft): Promise<MessageDraft> {
      await randomDelay(220, 400)
      const db = getDb()
      const index = db.messages.findIndex((item) => item.id === draft.id)
      const next = { ...clone(draft), updatedAt: nowIso() }
      if (index >= 0) db.messages[index] = next
      else db.messages.unshift(next)
      persistDb()
      return clone(next)
    },
    async sendTest(_draft: MessageDraft) {
      await randomDelay(500, 850)
      return { ok: true }
    },
  },
}

export type MockApi = typeof mockApi

export function resetMockData() {
  const db = getDb()
  db.notifications = db.notifications.map((item) => ({ ...item, read: true }))
  persistDb()
}

export type { Session }
