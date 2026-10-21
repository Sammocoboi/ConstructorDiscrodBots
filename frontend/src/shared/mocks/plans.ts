import type { Plan } from '../api/types'

export const plans: Plan[] = [
  {
    id: 'free',
    name: 'Free',
    priceMonthly: 0,
    description: 'Для знакомства с конструктором и небольших серверов.',
    features: [
      '1 бот',
      'До 5 000 выполнений в месяц',
      '3 гильдии',
      'Базовые модули',
      'Библиотека команд',
    ],
    limits: { bots: 1, executions: 5_000, guilds: 3, members: 1_000 },
  },
  {
    id: 'pro',
    name: 'Pro',
    priceMonthly: 990,
    description: 'Для активных сообществ и авторов ботов.',
    features: [
      '5 ботов',
      'До 50 000 выполнений в месяц',
      '20 гильдий',
      'Все модули и сценарии',
      'Тестовые запуски с трассировкой',
      'Личные шаблоны и share-link',
    ],
    limits: { bots: 5, executions: 50_000, guilds: 20, members: 25_000 },
    highlighted: true,
  },
  {
    id: 'business',
    name: 'Business',
    priceMonthly: 2_990,
    description: 'Для сетей серверов и коммерческих проектов.',
    features: [
      '25 ботов',
      'До 500 000 выполнений в месяц',
      '100 гильдий',
      'Приоритетная поддержка',
      'Расширенная диагностика',
      'Экспорт и импорт конфигураций',
    ],
    limits: { bots: 25, executions: 500_000, guilds: 100, members: 250_000 },
  },
]
