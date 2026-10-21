import { useMemo, useState } from 'react'
import {
  Badge,
  Button,
  Card,
  Group,
  Menu,
  Select,
  Stack,
  Switch,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'
import {
  IconBooks,
  IconDots,
  IconPlus,
  IconRefresh,
  IconSearch,
  IconTrash,
} from '@tabler/icons-react'
import { api } from '../../shared/api'
import {
  qk,
  useBot,
  useCommands,
  useToastMutation,
} from '../../shared/api/hooks'
import type { Command } from '../../shared/api/types'
import { PageHeader } from '../../shared/components/bits'
import { ConfirmModal } from '../../shared/components/ConfirmModal'
import { EmptyState, LoadingState } from '../../shared/components/states'
import { commandCategoryLabel, commandTypeLabel } from '../../shared/lib/status'
import { formatRelative } from '../../shared/lib/format'

function CommandRow({ botId, command }: { botId: string; command: Command }) {
  const { t } = useTranslation()
  const [deleteOpened, setDeleteOpened] = useState(false)

  const toggleMutation = useToastMutation({
    mutationFn: (enabled: boolean) =>
      api.commands.update(botId, command.id, { enabled }),
    successMessage: (enabled) =>
      enabled ? t('commands.enabledToast') : t('commands.disabledToast'),
    invalidateKeys: [qk.commands(botId)],
  })

  const deleteMutation = useToastMutation({
    mutationFn: () => api.commands.remove(botId, command.id),
    successMessage: t('common.delete'),
    invalidateKeys: [qk.commands(botId)],
    onSuccess: () => setDeleteOpened(false),
  })

  return (
    <>
      <Group
        justify="space-between"
        wrap="nowrap"
        p="sm"
        style={{
          borderRadius: 12,
          border: '1px solid var(--mantine-color-default-border)',
        }}
      >
        <Group gap="sm" wrap="nowrap" style={{ minWidth: 0 }}>
          <Text fw={700} ff="monospace" size="sm" c="brand">
            /{command.name}
          </Text>
          <Stack gap={1} style={{ minWidth: 0 }}>
            <Text size="sm" lineClamp={1}>
              {command.description}
            </Text>
            <Group gap={5}>
              <Badge size="xs" variant="light" color="gray">
                {commandTypeLabel[command.type]}
              </Badge>
              <Badge size="xs" variant="light" color="gray">
                {commandCategoryLabel[command.category] ?? command.category}
              </Badge>
              <Badge
                size="xs"
                variant="light"
                color={command.source === 'library' ? 'cyan' : 'brand'}
              >
                {command.source === 'library' ? t('commands.library') : t('commands.create')}
              </Badge>
              <Text size="10px" c="dimmed">
                {formatRelative(command.updatedAt)}
              </Text>
            </Group>
          </Stack>
        </Group>
        <Group gap="xs" wrap="nowrap">
          <Switch
            size="sm"
            checked={command.enabled}
            disabled={toggleMutation.isPending}
            onChange={(event) => toggleMutation.mutate(event.currentTarget.checked)}
            aria-label={command.name}
          />
          <Menu position="bottom-end" width={190}>
            <Menu.Target>
              <Button variant="subtle" color="gray" size="compact-sm" px={6}>
                <IconDots size={17} />
              </Button>
            </Menu.Target>
            <Menu.Dropdown>
              <Menu.Item component={Link} to={`/app/bots/${botId}/commands/${command.id}`}>
                {t('common.edit')}
              </Menu.Item>
              <Menu.Divider />
              <Menu.Item
                color="red"
                leftSection={<IconTrash size={14} />}
                onClick={() => setDeleteOpened(true)}
              >
                {t('common.delete')}
              </Menu.Item>
            </Menu.Dropdown>
          </Menu>
        </Group>
      </Group>

      <ConfirmModal
        opened={deleteOpened}
        onClose={() => setDeleteOpened(false)}
        onConfirm={() => deleteMutation.mutate()}
        loading={deleteMutation.isPending}
        title={t('common.delete')}
        description={`Команда /${command.name} будет удалена.`}
        confirmLabel={t('common.delete')}
      />
    </>
  )
}

export default function CommandsPage() {
  const { t } = useTranslation()
  const { botId } = useParams()
  const { data: bot } = useBot(botId)
  const commands = useCommands(botId)
  const [query, setQuery] = useState('')
  const [type, setType] = useState<string | null>(null)
  const [status, setStatus] = useState<string | null>(null)

  const syncMutation = useToastMutation({
    mutationFn: () => api.commands.sync(botId as string),
    successMessage: t('commands.synced'),
    invalidateKeys: [qk.commands(botId ?? '')],
  })

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    return (commands.data ?? []).filter((command) => {
      if (type && command.type !== type) return false
      if (status === 'enabled' && !command.enabled) return false
      if (status === 'disabled' && command.enabled) return false
      if (!normalized) return true
      return (
        command.name.toLowerCase().includes(normalized) ||
        command.description.toLowerCase().includes(normalized)
      )
    })
  }, [commands.data, query, status, type])

  if (!bot) return <LoadingState minHeight={280} />

  return (
    <Stack gap="lg">
      <PageHeader
        title={t('commands.title')}
        description={t('commands.subtitle')}
        actions={
          <>
            <Button
              component={Link}
              to={`/app/bots/${bot.id}/commands/library`}
              variant="default"
              leftSection={<IconBooks size={16} />}
            >
              {t('commands.library')}
            </Button>
            <Button
              variant="default"
              leftSection={<IconRefresh size={16} />}
              loading={syncMutation.isPending}
              onClick={() => syncMutation.mutate()}
            >
              {t('commands.sync')}
            </Button>
            <Button
              component={Link}
              to={`/app/bots/${bot.id}/commands/new`}
              leftSection={<IconPlus size={16} />}
            >
              {t('commands.create')}
            </Button>
          </>
        }
      />

      <Card withBorder radius="lg" p="md">
        <Group gap="sm" wrap="wrap">
          <TextInput
            placeholder={t('commands.searchPlaceholder')}
            leftSection={<IconSearch size={15} />}
            value={query}
            onChange={(event) => setQuery(event.currentTarget.value)}
            style={{ flex: 1, minWidth: 220 }}
          />
          <Select
            placeholder={t('commands.category')}
            data={[
              { value: 'slash', label: t('commands.typeSlash') },
              { value: 'message', label: t('commands.typeMessage') },
              { value: 'user', label: t('commands.typeUser') },
            ]}
            value={type}
            onChange={setType}
            clearable
            w={{ base: '100%', sm: 200 }}
          />
          <Select
            placeholder={t('common.status')}
            data={[
              { value: 'enabled', label: t('common.enabled') },
              { value: 'disabled', label: t('common.disabled') },
            ]}
            value={status}
            onChange={setStatus}
            clearable
            w={{ base: '100%', sm: 180 }}
          />
        </Group>
      </Card>

      {commands.isLoading && <LoadingState />}
      {commands.data && commands.data.length === 0 && (
        <EmptyState
          icon="terminal"
          title={t('commands.emptyTitle')}
          description={t('commands.emptyText')}
          action={
            <>
              <Button
                component={Link}
                to={`/app/bots/${bot.id}/commands/library`}
                leftSection={<IconBooks size={16} />}
              >
                {t('commands.openLibrary')}
              </Button>
              <Button
                component={Link}
                to={`/app/bots/${bot.id}/commands/new`}
                variant="light"
                leftSection={<IconPlus size={16} />}
              >
                {t('commands.create')}
              </Button>
            </>
          }
        />
      )}
      {commands.data && commands.data.length > 0 && filtered.length === 0 && (
        <EmptyState icon="search" title={t('common.notFound')} compact />
      )}

      <Card withBorder radius="lg" p="md">
        <Group justify="space-between" mb="sm">
          <Title order={3} fz={17}>
            {t('commands.title')} · {filtered.length}
          </Title>
        </Group>
        <Stack gap="xs">
          {filtered.map((command) => (
            <CommandRow key={command.id} botId={bot.id} command={command} />
          ))}
        </Stack>
      </Card>
    </Stack>
  )
}
