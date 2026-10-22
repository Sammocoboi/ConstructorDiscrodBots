import type {
  BillingOverview,
  Bot,
  BotActivityEvent,
  Command,
  Flow,
  Guild,
  LibraryCommand,
  MessageDraft,
  ModuleManifest,
  ModuleState,
  Notification,
  Session,
  Template,
  User,
} from '../api/types'

export interface AccountNotificationSettings {
  botErrors: boolean
  payments: boolean
  productUpdates: boolean
  weeklyDigest: boolean
}

export interface MockDatabase {
  user: User
  guilds: Guild[]
  bots: Bot[]
  botEvents: BotActivityEvent[]
  modules: ModuleManifest[]
  moduleStates: ModuleState[]
  commands: Command[]
  library: LibraryCommand[]
  flows: Flow[]
  templates: Template[]
  notifications: Notification[]
  billing: BillingOverview
  sessions: Session[]
  accountNotifications: AccountNotificationSettings
  messages: MessageDraft[]
}
