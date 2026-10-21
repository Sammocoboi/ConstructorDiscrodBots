import type { ReactNode } from 'react'
import {
  Badge,
  Box,
  Card,
  Group,
  Paper,
  Progress,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from '@mantine/core'
import { botStatusMeta } from '../lib/status'
import { formatNumber, initials } from '../lib/format'
import type { BotStatus } from '../api/types'
import { AppIcon } from './icons'

export function BotAvatar({
  name,
  color,
  size = 48,
  radius = 14,
}: {
  name: string
  color: string
  size?: number
  radius?: number
}) {
  return (
    <Box
      style={{
        width: size,
        height: size,
        borderRadius: radius,
        flex: '0 0 auto',
        display: 'grid',
        placeItems: 'center',
        color: 'white',
        fontWeight: 800,
        fontSize: Math.max(12, size * 0.32),
        letterSpacing: '0.02em',
        background: `linear-gradient(145deg, ${color}, ${color}99)`,
        boxShadow: `0 10px 24px ${color}44`,
        border: '1px solid rgba(255,255,255,0.16)',
      }}
    >
      {initials(name) || 'B'}
    </Box>
  )
}

export function StatusBadge({
  status,
  size = 'md',
}: {
  status: BotStatus
  size?: 'sm' | 'md'
}) {
  const meta = botStatusMeta[status]
  return (
    <Badge
      size={size}
      variant="light"
      color={meta.color}
      leftSection={
        <span
          className="bf-status-dot"
          style={{ background: meta.dot, width: 7, height: 7 }}
        />
      }
    >
      {meta.label}
    </Badge>
  )
}

export function StatCard({
  label,
  value,
  icon,
  hint,
  progress,
  accent = 'brand',
}: {
  label: string
  value: ReactNode
  icon: string
  hint?: string
  progress?: number
  accent?: string
}) {
  return (
    <Card withBorder radius="lg" p="lg" className="bf-hover-lift">
      <Group justify="space-between" align="flex-start">
        <Stack gap={2}>
          <Text size="xs" c="dimmed" fw={700} tt="uppercase" style={{ letterSpacing: '0.06em' }}>
            {label}
          </Text>
          <Text fw={800} size="xl" lh={1.2}>
            {value}
          </Text>
          {hint && (
            <Text size="xs" c="dimmed">
              {hint}
            </Text>
          )}
        </Stack>
        <ThemeIcon variant="light" color={accent} size={42} radius="md">
          <AppIcon name={icon} size={22} />
        </ThemeIcon>
      </Group>
      {progress !== undefined && (
        <Progress value={progress} size="sm" mt="md" radius="xl" color={accent} />
      )}
    </Card>
  )
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: ReactNode
  description?: ReactNode
  actions?: ReactNode
}) {
  return (
    <Group justify="space-between" align="flex-start" gap="md" wrap="wrap" mb="lg">
      <Stack gap={4}>
        <Title order={2} fz={{ base: 22, sm: 28 }}>
          {title}
        </Title>
        {description && (
          <Text c="dimmed" size="sm" maw={720}>
            {description}
          </Text>
        )}
      </Stack>
      {actions && <Group gap="sm">{actions}</Group>}
    </Group>
  )
}

export function SectionCard({
  title,
  description,
  action,
  children,
  padding = 'lg',
}: {
  title?: ReactNode
  description?: ReactNode
  action?: ReactNode
  children: ReactNode
  padding?: string | number
}) {
  return (
    <Card withBorder radius="lg" p={padding}>
      {(title || action) && (
        <Group justify="space-between" align="flex-start" mb="md" wrap="wrap">
          <Stack gap={2}>
            {title && <Text fw={700}>{title}</Text>}
            {description && (
              <Text size="xs" c="dimmed">
                {description}
              </Text>
            )}
          </Stack>
          {action}
        </Group>
      )}
      {children}
    </Card>
  )
}

export function PermissionChips({ permissions }: { permissions: string[] }) {
  return (
    <Group gap={6}>
      {permissions.map((permission) => (
        <Badge key={permission} variant="light" color="gray" size="sm" tt="none">
          {permission}
        </Badge>
      ))}
    </Group>
  )
}

export function Metric({ label, value }: { label: string; value: ReactNode }) {
  return (
    <Paper withBorder radius="md" p="sm">
      <Text size="xs" c="dimmed" fw={600}>
        {label}
      </Text>
      <Text fw={700} mt={2}>
        {value}
      </Text>
    </Paper>
  )
}

export function LimitBar({
  label,
  value,
  limit,
  format = 'number',
}: {
  label: string
  value: number
  limit: number
  format?: 'number'
}) {
  const percentage = limit > 0 ? Math.min(100, Math.round((value / limit) * 100)) : 0
  const color = percentage >= 100 ? 'red' : percentage >= 80 ? 'yellow' : 'brand'
  const formattedValue =
    format === 'number' ? formatNumber(value) : String(value)
  const formattedLimit = format === 'number' ? formatNumber(limit) : String(limit)
  return (
    <Stack gap={6}>
      <Group justify="space-between">
        <Text size="sm" fw={600}>
          {label}
        </Text>
        <Text size="xs" c="dimmed">
          {formattedValue} / {formattedLimit} · {percentage}%
        </Text>
      </Group>
      <Progress value={percentage} color={color} radius="xl" size="md" />
    </Stack>
  )
}
