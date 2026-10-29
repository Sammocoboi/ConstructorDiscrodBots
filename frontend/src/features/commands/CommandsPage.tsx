import { useMemo, useState } from 'react'
import {
  Badge,
  Button,
  Card,
  Group,
  Select,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'
import { IconBooks, IconSearch } from '@tabler/icons-react'
import { useBot, useCommands } from '../../shared/api/hooks'
import type { Command } from '../../shared/api/types'
import { PageHeader } from '../../shared/components/bits'
import { EmptyState, LoadingState } from '../../shared/components/states'
import { commandCategoryLabel, commandTypeLabel } from '../../shared/lib/status'
import { formatRelative } from '../../shared/lib/format'

function CommandRow({ command }: { command: Command }) {
  const { t } = useTranslation()

  return (
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
    </Group>
  )
}

export default function CommandsPage() {
  const { t } = useTranslation()
  const { botId } = useParams()
  const { data: bot } = useBot(botId)
  const commands = useCommands(botId)
  const [query, setQuery] = useState('')
  const [type, setType] = useState<string | null>(null)

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    return (commands.data ?? []).filter((command) => {
      if (type && command.type !== type) return false
      if (!normalized) return true
      return (
        command.name.toLowerCase().includes(normalized) ||
        command.description.toLowerCase().includes(normalized)
      )
    })
  }, [commands.data, query, type])

  if (!bot) return <LoadingState minHeight={280} />

  return (
    <Stack gap="lg">
      <PageHeader
        title={t('commands.title')}
        description={t('commands.subtitle')}
        actions={
          <Button
            component={Link}
            to={`/app/bots/${bot.id}/commands/library`}
            leftSection={<IconBooks size={16} />}
          >
            {t('commands.library')}
          </Button>
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
        </Group>
      </Card>

      {commands.isLoading && <LoadingState />}
      {commands.data && commands.data.length === 0 && (
        <EmptyState
          icon="terminal"
          title={t('commands.emptyTitle')}
          description={t('commands.emptyText')}
          action={
            <Button
              component={Link}
              to={`/app/bots/${bot.id}/commands/library`}
              leftSection={<IconBooks size={16} />}
            >
              {t('commands.openLibrary')}
            </Button>
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
            <CommandRow key={command.id} command={command} />
          ))}
        </Stack>
      </Card>
    </Stack>
  )
}
