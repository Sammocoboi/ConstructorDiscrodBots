import { useMemo, useState } from 'react'
import {
  Alert,
  Badge,
  Card,
  Group,
  SegmentedControl,
  Select,
  SimpleGrid,
  Stack,
  Switch,
  Text,
  TextInput,
  ThemeIcon,
  Title,
  Tooltip,
} from '@mantine/core'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'
import { IconAlertTriangle, IconSearch } from '@tabler/icons-react'
import { api } from '../../shared/api'
import {
  qk,
  useBot,
  useBotModules,
  useToastMutation,
} from '../../shared/api/hooks'
import type { ModuleManifest, ModuleState } from '../../shared/api/types'
import { AppIcon } from '../../shared/components/icons'
import { PageHeader } from '../../shared/components/bits'
import { EmptyState, LoadingState } from '../../shared/components/states'
import { moduleCategoryLabel, moduleCategoryOptions } from '../../shared/lib/status'

function ModuleCard({
  botId,
  guildId,
  manifest,
  state,
}: {
  botId: string
  guildId?: string
  manifest: ModuleManifest
  state: ModuleState
}) {
  const { t } = useTranslation()
  const toggleMutation = useToastMutation({
    mutationFn: (enabled: boolean) =>
      api.modules.toggle(botId, manifest.id, enabled, guildId),
    successMessage: (enabled) =>
      enabled ? t('modules.enabledToast') : t('modules.disabledToast'),
    invalidateKeys: [qk.botModules(botId, guildId), qk.bot(botId)],
  })

  return (
    <Card
      withBorder
      radius="lg"
      p="lg"
      className="bf-hover-lift"
      style={{ display: 'flex', flexDirection: 'column' }}
    >
      <Stack gap="sm" style={{ flex: 1 }}>
        <Group justify="space-between" align="flex-start" wrap="nowrap">
          <Group gap="sm" wrap="nowrap">
            <ThemeIcon
              size={42}
              radius="md"
              variant={state.enabled ? 'light' : 'default'}
              color={state.enabled ? 'brand' : 'gray'}
            >
              <AppIcon name={manifest.icon} size={21} />
            </ThemeIcon>
            <Stack gap={2}>
              <Title order={3} fz={16}>
                <Link
                  to={
                    guildId
                      ? `/app/bots/${botId}/modules/${manifest.id}?guild=${guildId}`
                      : `/app/bots/${botId}/modules/${manifest.id}`
                  }
                >
                  {manifest.title}
                </Link>
              </Title>
              <Badge size="xs" variant="light" color="gray">
                {moduleCategoryLabel[manifest.category]}
              </Badge>
            </Stack>
          </Group>
          <Tooltip label={t('modules.noGuildTitle')} disabled={Boolean(guildId)}>
            <Switch
              checked={state.enabled}
              size="md"
              aria-label={manifest.title}
              disabled={toggleMutation.isPending || !guildId}
              onChange={(event) => toggleMutation.mutate(event.currentTarget.checked)}
            />
          </Tooltip>
        </Group>

        <Text size="sm" c="dimmed" lineClamp={3} style={{ flex: 1 }}>
          {manifest.description}
        </Text>

        {state.warnings.length > 0 && (
          <Alert
            color="yellow"
            variant="light"
            icon={<IconAlertTriangle size={15} />}
            p="xs"
          >
            <Text size="xs">{state.warnings[0]}</Text>
          </Alert>
        )}

        <Group gap={5}>
          {manifest.permissions.slice(0, 3).map((permission) => (
            <Badge key={permission} size="xs" variant="dot" color="gray" tt="none">
              {permission}
            </Badge>
          ))}
        </Group>
      </Stack>
    </Card>
  )
}

export default function ModulesPage() {
  const { t } = useTranslation()
  const { botId } = useParams()
  const { data: bot } = useBot(botId)
  const [selectedGuildId, setSelectedGuildId] = useState<string | null>(null)
  const guildId = selectedGuildId ?? bot?.guilds[0]?.id
  const modules = useBotModules(botId, guildId)
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState<string | null>(null)
  const [mode, setMode] = useState('all')

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    return (modules.data ?? []).filter(({ manifest, state }) => {
      if (mode === 'active' && !state.enabled) return false
      if (category && manifest.category !== category) return false
      if (!normalized) return true
      return (
        manifest.title.toLowerCase().includes(normalized) ||
        manifest.description.toLowerCase().includes(normalized)
      )
    })
  }, [category, mode, modules.data, query])

  if (!bot) return <LoadingState minHeight={280} />

  const activeCount = modules.data?.filter((item) => item.state.enabled).length ?? 0

  return (
    <Stack gap="lg">
      <PageHeader
        title={t('modules.title')}
        description={t('modules.subtitle')}
        actions={
          <Badge variant="light" size="lg">
            {activeCount} / {modules.data?.length ?? 0} {t('common.enabled').toLowerCase()}
          </Badge>
        }
      />

      <Card withBorder radius="lg" p="md">
        <Group gap="sm" wrap="wrap">
          <Select
            placeholder={t('modules.selectGuild')}
            data={(bot.guilds ?? []).map((guild) => ({ value: guild.id, label: guild.name }))}
            value={guildId ?? null}
            onChange={setSelectedGuildId}
            allowDeselect={false}
            disabled={(bot.guilds ?? []).length === 0}
            w={{ base: '100%', sm: 220 }}
          />
          <TextInput
            placeholder={t('common.search')}
            leftSection={<IconSearch size={15} />}
            value={query}
            onChange={(event) => setQuery(event.currentTarget.value)}
            style={{ flex: 1, minWidth: 220 }}
          />
          <Select
            placeholder={t('modules.catalog')}
            data={moduleCategoryOptions}
            value={category}
            onChange={setCategory}
            clearable
            w={{ base: '100%', sm: 200 }}
          />
          <SegmentedControl
            value={mode}
            onChange={setMode}
            data={[
              { value: 'all', label: t('common.all') },
              { value: 'active', label: t('modules.active') },
            ]}
          />
        </Group>
      </Card>

      {(bot.guilds ?? []).length === 0 && (
        <Alert color="yellow" icon={<IconAlertTriangle size={16} />}>
          <Text fw={600}>{t('modules.noGuildTitle')}</Text>
          <Text size="sm">{t('modules.noGuildText')}</Text>
        </Alert>
      )}

      {modules.isLoading && <LoadingState />}
      {filtered.length === 0 && modules.data && (
        <EmptyState
          icon="layout"
          title={query ? t('common.notFound') : t('modules.emptyTitle')}
          description={t('modules.emptyText')}
        />
      )}

      <SimpleGrid cols={{ base: 1, sm: 2, xl: 3 }} spacing="md">
        {filtered.map(({ manifest, state }) => (
          <ModuleCard
            key={manifest.id}
            botId={bot.id}
            guildId={guildId}
            manifest={manifest}
            state={state}
          />
        ))}
      </SimpleGrid>
    </Stack>
  )
}
