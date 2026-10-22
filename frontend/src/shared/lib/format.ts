import i18n from '../i18n'

export function formatNumber(value: number, options?: Intl.NumberFormatOptions) {
  const locale = i18n.language.startsWith('en') ? 'en-US' : 'ru-RU'
  return new Intl.NumberFormat(locale, options).format(value)
}

export function formatMoney(value: number, currency = 'RUB') {
  const locale = i18n.language.startsWith('en') ? 'en-US' : 'ru-RU'
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(value)
}

export function formatDate(value: string | Date, withTime = false) {
  const date = typeof value === 'string' ? new Date(value) : value
  const locale = i18n.language.startsWith('en') ? 'en-US' : 'ru-RU'
  return new Intl.DateTimeFormat(locale, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    ...(withTime ? { hour: '2-digit', minute: '2-digit' } : {}),
  }).format(date)
}

export function formatRelative(value: string | Date) {
  const date = typeof value === 'string' ? new Date(value) : value
  const diff = date.getTime() - Date.now()
  const locale = i18n.language.startsWith('en') ? 'en-US' : 'ru-RU'
  const formatter = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' })
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ['year', 31_536_000_000],
    ['month', 2_592_000_000],
    ['day', 86_400_000],
    ['hour', 3_600_000],
    ['minute', 60_000],
    ['second', 1_000],
  ]
  for (const [unit, ms] of units) {
    if (Math.abs(diff) >= ms || unit === 'second') {
      return formatter.format(Math.round(diff / ms), unit)
    }
  }
  return formatter.format(0, 'second')
}

export function formatDuration(totalSeconds: number) {
  if (!Number.isFinite(totalSeconds) || totalSeconds <= 0) return '—'
  const seconds = Math.floor(totalSeconds % 60)
  const minutes = Math.floor((totalSeconds / 60) % 60)
  const hours = Math.floor((totalSeconds / 3600) % 24)
  const days = Math.floor(totalSeconds / 86_400)
  const parts: string[] = []
  if (days) parts.push(`${days}д`)
  if (hours) parts.push(`${hours}ч`)
  if (minutes && !days) parts.push(`${minutes}м`)
  if (seconds && !days && !hours) parts.push(`${seconds}с`)
  return parts.join(' ') || '0с'
}

export function formatUptimeSince(iso: string) {
  return formatDuration((Date.now() - new Date(iso).getTime()) / 1000)
}

export function initials(name: string) {
  return name
    .split(/[\s_-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('')
}

export function truncate(value: string, length = 80) {
  return value.length > length ? `${value.slice(0, length - 1)}…` : value
}

export function percent(value: number, limit: number) {
  if (limit <= 0) return 0
  return Math.min(100, Math.round((value / limit) * 100))
}

export function randomId(prefix = 'id') {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`
}

export function pluralizeRu(count: number, one: string, few: string, many: string) {
  const mod10 = count % 10
  const mod100 = count % 100
  if (mod10 === 1 && mod100 !== 11) return one
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return few
  return many
}
