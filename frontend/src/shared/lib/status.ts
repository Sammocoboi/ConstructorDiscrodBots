import type { BotStatus, CommandType, ModuleCategory, TemplateCategory } from '../api/types'

export const botStatusMeta: Record<
  BotStatus,
  { label: string; color: string; dot: string }
> = {
  online: { label: 'Онлайн', color: 'teal', dot: 'var(--mantine-color-teal-6)' },
  starting: { label: 'Запускается', color: 'yellow', dot: 'var(--mantine-color-yellow-6)' },
  stopped: { label: 'Остановлен', color: 'gray', dot: 'var(--mantine-color-gray-6)' },
  error: { label: 'Ошибка', color: 'red', dot: 'var(--mantine-color-red-6)' },
  suspended: { label: 'Приостановлен', color: 'orange', dot: 'var(--mantine-color-orange-6)' },
}

export const commandTypeLabel: Record<CommandType, string> = {
  slash: 'Slash',
  message: 'Контекст: сообщение',
  user: 'Контекст: пользователь',
}

export const moduleCategoryLabel: Record<ModuleCategory, string> = {
  community: 'Сообщество',
  moderation: 'Модерация',
  roles: 'Роли',
  utility: 'Утилиты',
  engagement: 'Вовлечение',
  logs: 'Логи',
}

export const templateCategoryLabel: Record<TemplateCategory, string> = {
  community: 'Сообщества',
  moderation: 'Модерация',
  gaming: 'Игры',
  education: 'Образование',
  commerce: 'Магазины',
  content: 'Контент',
  roleplay: 'Ролевые',
  minimal: 'Минимальные',
}

export const templateCategoryOptions = Object.entries(templateCategoryLabel).map(
  ([value, label]) => ({ value, label }),
)

export const moduleCategoryOptions = Object.entries(moduleCategoryLabel).map(
  ([value, label]) => ({ value, label }),
)

export const commandCategoryLabel: Record<string, string> = {
  moderation: 'Модерация',
  utility: 'Утилиты',
  community: 'Сообщество',
  fun: 'Развлечения',
  roles: 'Роли',
  economy: 'Экономика',
}

export const commandCategoryOptions = Object.entries(commandCategoryLabel).map(
  ([value, label]) => ({ value, label }),
)
