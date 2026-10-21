import { useMemo, useState } from 'react'
import {
  Button,
  Card,
  Group,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import {
  IconArrowRight,
  IconBell,
  IconPlus,
  IconSearch,
  IconSparkles,
} from '@tabler/icons-react'
import { useBots, useDashboardStats, useNotifications } from '../../shared/api/hooks'
import { PageHeader, StatCard } from '../../shared/components/bits'
import { EmptyState, ErrorState, LoadingState } from '../../shared/components/states'
import { AppIcon } from '../../shared/components/icons'
import { BotCard } from '../bots/BotCard'
import { formatNumber, formatRelative } from '../../shared/lib/format'
import { errorMessage } from '../../shared/api/errors'

export default function DashboardPage() {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const stats = useDashboardStats()
  const bots = useBots()
  const notifications = useNotifications()

  const filteredBots = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    if (!normalized) return bots.data ?? []
    return (bots.data ?? []).filter(
      (bot) =>
        bot.name.toLowerCase().includes(normalized) ||
        bot.description.toLowerCase().includes(normalized),
    )
  }, [bots.data, query])

  return (
    <Stack gap="lg" className="bf-fade-in" maw={1280} mx="auto" w="100%">
      <PageHeader
        title={t('dashboard.title')}
        description={t('dashboard.subtitle')}
        actions={
          <>
            <Button
              component={Link}
              to="/app/templates"
              variant="default"
              leftSection={<IconSparkles size={16} />}
            >
              {t('nav.catalog')}
            </Button>
            <Button
              component={Link}
              to="/app/bots/new"
              leftSection={<IconPlus size={16} />}
            >
              {t('nav.newBot')}
            </Button>
          </>
        }
      />

      {stats.isError ? (
        <ErrorState
          message={errorMessage(stats.error)}
          onRetry={() => void stats.refetch()}
          minHeight={160}
        />
      ) : (
        <SimpleGrid cols={{ base: 2, lg: 4 }} spacing="md">
          <StatCard
            label={t('dashboard.statsBots')}
            value={stats.data ? formatNumber(stats.data.bots) : '—'}
            icon="robot"
            hint={t('dashboard.yourBots')}
          />
          <StatCard
            label={t('dashboard.statsOnline')}
            value={stats.data ? formatNumber(stats.data.online) : '—'}
            icon="activity"
            accent="teal"
            hint={t('common.online')}
          />
          <StatCard
            label={t('dashboard.statsGuilds')}
            value={stats.data ? formatNumber(stats.data.guilds) : '—'}
            icon="server"
            accent="cyan"
            hint={t('nav.guilds')}
          />
          <StatCard
            label={t('dashboard.statsNotifications')}
            value={stats.data ? formatNumber(stats.data.unreadNotifications) : '—'}
            icon="bell"
            accent="orange"
            hint={t('nav.notifications')}
          />
        </SimpleGrid>
      )}

      <SimpleGrid cols={{ base: 1, lg: 3 }} spacing="lg">
        <Stack gap="md" style={{ gridColumn: 'span 2' }}>
          <Card withBorder radius="lg" p="lg">
            <Group justify="space-between" mb="md" wrap="wrap" gap="sm">
              <Stack gap={0}>
                <Title order={3} fz={19}>
                  {t('dashboard.yourBots')}
                </Title>
                <Text size="xs" c="dimmed">
                  {bots.data?.length ?? 0} {t('nav.bots').toLowerCase()}
                </Text>
              </Stack>
              <TextInput
                placeholder={t('dashboard.searchPlaceholder')}
                leftSection={<IconSearch size={15} />}
                value={query}
                onChange={(event) => setQuery(event.currentTarget.value)}
                w={{ base: '100%', sm: 240 }}
              />
            </Group>

            {bots.isLoading && <LoadingState minHeight={180} />}
            {bots.isError && (
              <ErrorState
                message={errorMessage(bots.error)}
                onRetry={() => void bots.refetch()}
                minHeight={180}
              />
            )}
            {bots.data && bots.data.length === 0 && (
              <EmptyState
                icon="robot"
                title={t('dashboard.emptyTitle')}
                description={t('dashboard.emptyText')}
                action={
                  <>
                    <Button component={Link} to="/app/bots/new" leftSection={<IconPlus size={16} />}>
                      {t('dashboard.createFirst')}
                    </Button>
                    <Button component={Link} to="/app/templates" variant="light">
                      {t('nav.catalog')}
                    </Button>
                  </>
                }
              />
            )}
            {bots.data && bots.data.length > 0 && filteredBots.length === 0 && (
              <Text c="dimmed" size="sm" py="md" ta="center">
                {t('common.notFound')}
              </Text>
            )}
            <Stack gap="sm">
              {filteredBots.map((bot) => (
                <BotCard key={bot.id} bot={bot} />
              ))}
            </Stack>
          </Card>
        </Stack>

        <Stack gap="md">
          <Card withBorder radius="lg" p="lg">
            <Group justify="space-between" mb="sm">
              <Group gap="xs">
                <IconBell size={17} />
                <Text fw={700}>{t('nav.notifications')}</Text>
              </Group>
              <Button
                component={Link}
                to="/app/notifications"
                variant="subtle"
                size="compact-xs"
                rightSection={<IconArrowRight size={13} />}
              >
                {t('common.all')}
              </Button>
            </Group>
            <Stack gap="xs">
              {notifications.data?.slice(0, 4).map((notification) => (
                <Group key={notification.id} align="flex-start" gap="sm" wrap="nowrap">
                  <AppIcon
                    name={
                      notification.type === 'error'
                        ? 'alert'
                        : notification.type === 'billing'
                          ? 'card'
                          : notification.type === 'warning'
                            ? 'alert'
                            : notification.type === 'success'
                              ? 'check'
                              : 'info'
                    }
                    size={16}
                  />
                  <Stack gap={0} style={{ flex: 1, minWidth: 0 }}>
                    <Text size="sm" fw={notification.read ? 500 : 700} lineClamp={1}>
                      {notification.title}
                    </Text>
                    <Text size="xs" c="dimmed" lineClamp={2}>
                      {notification.message}
                    </Text>
                    <Text size="10px" c="dimmed" mt={2}>
                      {formatRelative(notification.createdAt)}
                    </Text>
                  </Stack>
                </Group>
              ))}
              {notifications.data?.length === 0 && (
                <Text size="sm" c="dimmed">
                  {t('dashboard.noNotifications')}
                </Text>
              )}
            </Stack>
          </Card>

          <Card
            radius="lg"
            p="lg"
            style={{
              border: 'none',
              background: 'linear-gradient(150deg, #343aac 0%, #5865f2 60%, #00a8fc 130%)',
              color: 'white',
            }}
          >
            <Stack gap="sm">
              <IconSparkles size={24} />
              <Title order={3} fz={19}>
                {t('help.quickStart')}
              </Title>
              <Text size="sm" opacity={0.85}>
                {t('help.quickStartText')}
              </Text>
              <Button
                component={Link}
                to="/app/help"
                variant="white"
                color="brand"
                size="xs"
                rightSection={<IconArrowRight size={14} />}
                w="fit-content"
              >
                {t('nav.help')}
              </Button>
            </Stack>
          </Card>
        </Stack>
      </SimpleGrid>
    </Stack>
  )
}
