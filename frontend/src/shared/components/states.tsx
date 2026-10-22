import type { ReactNode } from 'react'
import { Button, Center, Group, Loader, Paper, Stack, Text, ThemeIcon, Title } from '@mantine/core'
import { IconAlertTriangle, IconRefresh, IconSearch } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import { AppIcon } from './icons'

export function LoadingState({
  label,
  minHeight = 220,
}: {
  label?: string
  minHeight?: number
}) {
  const { t } = useTranslation()
  return (
    <Center mih={minHeight}>
      <Stack align="center" gap="sm">
        <Loader size="md" />
        <Text size="sm" c="dimmed">
          {label ?? t('common.loading')}
        </Text>
      </Stack>
    </Center>
  )
}

export function ErrorState({
  title,
  message,
  onRetry,
  minHeight = 220,
}: {
  title?: string
  message?: string
  onRetry?: () => void
  minHeight?: number
}) {
  const { t } = useTranslation()
  return (
    <Center mih={minHeight}>
      <Stack align="center" gap="sm" maw={440} px="md">
        <ThemeIcon size={56} radius="xl" color="red" variant="light">
          <IconAlertTriangle size={28} />
        </ThemeIcon>
        <Title order={4}>{title ?? t('common.error')}</Title>
        <Text c="dimmed" ta="center" size="sm">
          {message ?? t('errors.unknown')}
        </Text>
        {onRetry && (
          <Button
            variant="light"
            leftSection={<IconRefresh size={16} />}
            onClick={onRetry}
            mt="xs"
          >
            {t('common.retry')}
          </Button>
        )}
      </Stack>
    </Center>
  )
}

export function EmptyState({
  icon = 'box',
  title,
  description,
  action,
  compact = false,
}: {
  icon?: string
  title: string
  description?: string
  action?: ReactNode
  compact?: boolean
}) {
  return (
    <Paper withBorder radius="lg" p={compact ? 'lg' : 'xl'} className="bf-fade-in">
      <Stack align="center" gap="sm" py={compact ? 10 : 28}>
        <div className="bf-empty-illustration">
          <AppIcon name={icon} size={36} stroke={1.4} color="var(--mantine-color-brand-5)" />
        </div>
        <Title order={4} ta="center">
          {title}
        </Title>
        {description && (
          <Text c="dimmed" size="sm" ta="center" maw={460}>
            {description}
          </Text>
        )}
        {action && <Group mt="sm">{action}</Group>}
      </Stack>
    </Paper>
  )
}

export function NoSearchResults({ query }: { query: string }) {
  return (
    <EmptyState
      icon="search"
      compact
      title="Ничего не найдено"
      description={`По запросу «${query}» нет результатов. Попробуйте изменить фильтры.`}
    />
  )
}

export const SearchIcon = IconSearch
