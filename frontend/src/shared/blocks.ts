export type BlockCategory = 'trigger' | 'condition' | 'action' | 'data' | 'logic'

export type BlockFieldType =
  | 'text'
  | 'textarea'
  | 'number'
  | 'boolean'
  | 'select'
  | 'channel'
  | 'role'
  | 'duration'
  | 'color'

export interface BlockField {
  key: string
  label: string
  type: BlockFieldType
  placeholder?: string
  description?: string
  required?: boolean
  min?: number
  max?: number
  options?: { value: string; label: string }[]
}

export interface BlockDefinition {
  id: string
  category: BlockCategory
  title: string
  description: string
  icon: string
  fields: BlockField[]
  permissions?: string[]
  terminal?: boolean
}

export const blockCategoryMeta: Record<BlockCategory, { label: string; color: string }> = {
  trigger: { label: 'Триггеры', color: '#5865f2' },
  condition: { label: 'Условия', color: '#faa81a' },
  action: { label: 'Действия', color: '#3ba55d' },
  data: { label: 'Данные', color: '#00a8fc' },
  logic: { label: 'Логика', color: '#9b59b6' },
}

export const blockDefinitions: BlockDefinition[] = [
  {
    id: 'trigger.member_join',
    category: 'trigger',
    title: 'Новый участник',
    description: 'Срабатывает, когда пользователь присоединяется к серверу.',
    icon: 'userPlus',
    fields: [],
  },
  {
    id: 'trigger.member_leave',
    category: 'trigger',
    title: 'Участник вышел',
    description: 'Срабатывает, когда пользователь покидает сервер.',
    icon: 'userMinus',
    fields: [],
  },
  {
    id: 'trigger.message',
    category: 'trigger',
    title: 'Новое сообщение',
    description: 'Срабатывает на сообщения в выбранных каналах.',
    icon: 'message',
    fields: [
      { key: 'contains', label: 'Содержит текст', type: 'text', placeholder: 'Необязательно' },
      { key: 'ignoreBots', label: 'Игнорировать ботов', type: 'boolean' },
    ],
  },
  {
    id: 'trigger.slash',
    category: 'trigger',
    title: 'Slash-команда',
    description: 'Запускается пользователем через slash-команду.',
    icon: 'terminal',
    fields: [
      {
        key: 'commandName',
        label: 'Команда',
        type: 'text',
        placeholder: 'welcome',
        required: true,
      },
    ],
  },
  {
    id: 'trigger.reaction',
    category: 'trigger',
    title: 'Реакция на сообщение',
    description: 'Срабатывает при добавлении реакции.',
    icon: 'reaction',
    fields: [
      { key: 'emoji', label: 'Эмодзи', type: 'text', placeholder: '🎉', required: true },
      { key: 'messageId', label: 'ID сообщения', type: 'text', placeholder: 'Необязательно' },
    ],
  },
  {
    id: 'trigger.schedule',
    category: 'trigger',
    title: 'Расписание',
    description: 'Запускается по cron-расписанию.',
    icon: 'clock',
    fields: [
      {
        key: 'cron',
        label: 'Cron-выражение',
        type: 'text',
        placeholder: '0 19 * * *',
        description: 'Минута час день месяц день-недели',
        required: true,
      },
      {
        key: 'timezone',
        label: 'Часовой пояс',
        type: 'select',
        options: [
          { value: 'Europe/Moscow', label: 'Москва (UTC+3)' },
          { value: 'Europe/London', label: 'Лондон (UTC+0)' },
          { value: 'America/New_York', label: 'Нью-Йорк (UTC−5)' },
        ],
      },
    ],
  },
  {
    id: 'trigger.button',
    category: 'trigger',
    title: 'Нажатие кнопки',
    description: 'Срабатывает на нажатие кнопки в сообщении бота.',
    icon: 'click',
    fields: [
      { key: 'customId', label: 'ID кнопки', type: 'text', placeholder: 'ticket:close', required: true },
    ],
  },
  {
    id: 'condition.account_age',
    category: 'condition',
    title: 'Возраст аккаунта',
    description: 'Проверяет, сколько дней существует аккаунт пользователя.',
    icon: 'calendar',
    fields: [
      {
        key: 'operator',
        label: 'Оператор',
        type: 'select',
        options: [
          { value: 'gte', label: 'больше или равно' },
          { value: 'lte', label: 'меньше или равно' },
        ],
      },
      { key: 'value', label: 'Дней', type: 'number', min: 0, max: 3650, required: true },
    ],
  },
  {
    id: 'condition.role',
    category: 'condition',
    title: 'Есть роль',
    description: 'Проверяет наличие роли у пользователя.',
    icon: 'badge',
    fields: [{ key: 'roleId', label: 'Роль', type: 'role', required: true }],
  },
  {
    id: 'condition.channel',
    category: 'condition',
    title: 'Канал',
    description: 'Ограничивает выполнение выбранным каналом.',
    icon: 'hash',
    fields: [{ key: 'channelId', label: 'Канал', type: 'channel', required: true }],
  },
  {
    id: 'condition.compare',
    category: 'condition',
    title: 'Сравнение',
    description: 'Сравнивает два значения или переменные.',
    icon: 'equal',
    fields: [
      { key: 'left', label: 'Слева', type: 'text', placeholder: '{user.id}', required: true },
      {
        key: 'operator',
        label: 'Оператор',
        type: 'select',
        options: [
          { value: 'eq', label: 'равно' },
          { value: 'neq', label: 'не равно' },
          { value: 'contains', label: 'содержит' },
        ],
      },
      { key: 'right', label: 'Справа', type: 'text', placeholder: '{role.id}', required: true },
    ],
  },
  {
    id: 'condition.spam_score',
    category: 'condition',
    title: 'Оценка спама',
    description: 'Срабатывает, если сообщение похоже на спам.',
    icon: 'sparkles',
    fields: [
      { key: 'threshold', label: 'Порог (0–1)', type: 'number', min: 0, max: 1, required: true },
    ],
  },
  {
    id: 'condition.cooldown',
    category: 'condition',
    title: 'Cooldown',
    description: 'Ограничивает частоту запуска для пользователя.',
    icon: 'hourglass',
    fields: [
      { key: 'seconds', label: 'Секунды', type: 'number', min: 1, max: 86_400, required: true },
    ],
  },
  {
    id: 'action.send_message',
    category: 'action',
    title: 'Отправить сообщение',
    description: 'Отправляет текст в выбранный канал.',
    icon: 'send',
    fields: [
      { key: 'channelId', label: 'Канал', type: 'channel', required: true },
      {
        key: 'text',
        label: 'Текст',
        type: 'textarea',
        placeholder: 'Добро пожаловать, {user.mention}!',
        required: true,
      },
    ],
    permissions: ['Send Messages', 'Embed Links'],
  },
  {
    id: 'action.send_embed',
    category: 'action',
    title: 'Отправить эмбед',
    description: 'Отправляет оформленный эмбед.',
    icon: 'layout',
    fields: [
      { key: 'channelId', label: 'Канал', type: 'channel', required: true },
      { key: 'title', label: 'Заголовок', type: 'text', required: true },
      { key: 'description', label: 'Описание', type: 'textarea', required: true },
      { key: 'color', label: 'Цвет', type: 'color' },
    ],
    permissions: ['Send Messages', 'Embed Links'],
  },
  {
    id: 'action.reply',
    category: 'action',
    title: 'Ответить на сообщение',
    description: 'Отправляет ответ на исходное сообщение.',
    icon: 'cornerDownRight',
    fields: [
      { key: 'text', label: 'Текст ответа', type: 'textarea', required: true },
      { key: 'ephemeral', label: 'Видно только автору', type: 'boolean' },
    ],
    permissions: ['Send Messages'],
  },
  {
    id: 'action.add_role',
    category: 'action',
    title: 'Выдать роль',
    description: 'Добавляет роль участнику.',
    icon: 'shieldPlus',
    fields: [{ key: 'roleId', label: 'Роль', type: 'role', required: true }],
    permissions: ['Manage Roles'],
  },
  {
    id: 'action.remove_role',
    category: 'action',
    title: 'Забрать роль',
    description: 'Удаляет роль у участника.',
    icon: 'shieldMinus',
    fields: [{ key: 'roleId', label: 'Роль', type: 'role', required: true }],
    permissions: ['Manage Roles'],
  },
  {
    id: 'action.timeout',
    category: 'action',
    title: 'Тайм-аут',
    description: 'Временно ограничивает участника.',
    icon: 'clockPause',
    fields: [
      { key: 'minutes', label: 'Минут', type: 'number', min: 1, max: 1440, required: true },
      { key: 'reason', label: 'Причина', type: 'text' },
    ],
    permissions: ['Moderate Members'],
  },
  {
    id: 'action.kick',
    category: 'action',
    title: 'Кикнуть участника',
    description: 'Исключает участника с сервера.',
    icon: 'userX',
    fields: [{ key: 'reason', label: 'Причина', type: 'text', required: true }],
    permissions: ['Kick Members'],
  },
  {
    id: 'action.dm',
    category: 'action',
    title: 'Личное сообщение',
    description: 'Отправляет сообщение в личку участнику.',
    icon: 'mail',
    fields: [{ key: 'text', label: 'Текст', type: 'textarea', required: true }],
  },
  {
    id: 'action.delete_message',
    category: 'action',
    title: 'Удалить сообщение',
    description: 'Удаляет сообщение, запустившее сценарий.',
    icon: 'trash',
    fields: [],
    permissions: ['Manage Messages'],
    terminal: true,
  },
  {
    id: 'action.add_reaction',
    category: 'action',
    title: 'Добавить реакцию',
    description: 'Ставит реакцию на сообщение.',
    icon: 'moodSmile',
    fields: [{ key: 'emoji', label: 'Эмодзи', type: 'text', placeholder: '✅', required: true }],
    permissions: ['Add Reactions'],
  },
  {
    id: 'data.set_variable',
    category: 'data',
    title: 'Установить переменную',
    description: 'Сохраняет значение в переменную сценария.',
    icon: 'variable',
    fields: [
      { key: 'name', label: 'Имя переменной', type: 'text', placeholder: 'targetUser', required: true },
      { key: 'value', label: 'Значение', type: 'text', placeholder: '{user.id}', required: true },
    ],
  },
  {
    id: 'data.random',
    category: 'data',
    title: 'Случайное число',
    description: 'Генерирует случайное число в диапазоне.',
    icon: 'dice',
    fields: [
      { key: 'name', label: 'Имя переменной', type: 'text', required: true },
      { key: 'min', label: 'Минимум', type: 'number', min: 0, required: true },
      { key: 'max', label: 'Максимум', type: 'number', min: 0, required: true },
    ],
  },
  {
    id: 'data.get_user',
    category: 'data',
    title: 'Данные участника',
    description: 'Достаёт данные автора или указанного участника.',
    icon: 'userSearch',
    fields: [
      {
        key: 'source',
        label: 'Источник',
        type: 'select',
        options: [
          { value: 'author', label: 'Автор события' },
          { value: 'target', label: 'Указанный участник' },
        ],
      },
      { key: 'name', label: 'Переменная', type: 'text', required: true },
    ],
  },
  {
    id: 'logic.delay',
    category: 'logic',
    title: 'Задержка',
    description: 'Приостанавливает сценарий на заданное время.',
    icon: 'clock',
    fields: [
      { key: 'seconds', label: 'Секунды', type: 'number', min: 1, max: 60, required: true },
    ],
  },
  {
    id: 'logic.stop',
    category: 'logic',
    title: 'Остановить',
    description: 'Завершает выполнение сценария.',
    icon: 'square',
    fields: [{ key: 'reason', label: 'Причина', type: 'text' }],
    terminal: true,
  },
]

export const blockMap = new Map(blockDefinitions.map((block) => [block.id, block]))

export function getBlockDefinition(id: string) {
  return blockMap.get(id)
}
