import { useMemo, useState } from 'react'
import {
  Badge,
  Button,
  Card,
  Group,
  Modal,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  ThemeIcon,
  Title,
} from '@mantine/core'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'
import {
  IconArrowLeft,
  IconCheck,
  IconDownload,
  IconSearch,
  IconTerminal,
} from '@tabler/icons-react'
import { api } from '../../shared/api'
import {
  qk,
  useBot,
  useCommandLibrary,
  useCommands,
  useToastMutation,
} from '../../shared/api/hooks'
import type { LibraryCommand } from '../../shared/api/types'
import { PageHeader } from '../../shared/components/bits'
import { EmptyState, LoadingState } from '../../shared/components/states'
import { commandCategoryLabel, commandCategoryOptions, commandTypeLabel } from '../../shared/lib/status'
import { formatNumber } from '../../shared/lib/format'

export default function CommandLibraryPage() {
  const { t } = useTranslation()
  const { botId } = useParams()
  const { data: bot } = useBot(botId)
  const library = useCommandLibrary()
  const commands = useCommands(botId)
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState<string | null>(null)
  const [selected, setSelected] = useState<LibraryCommand | null>(null)

  const installedIds = useMemo(
    () => new Set((commands.data ?? []).map((command) => command.libraryId).filter(Boolean)),
    [commands.data],
  )

  const installMutation = useToastMutation({
    mutationFn: (libraryId: string) => api.commands.install(botId as string, libraryId),
    successMessage: t('commands.installedToast'),
    invalidateKeys: [qk.commands(botId ?? '')],
  })

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    return (library.data ?? []).filter((command) => {
      if (category && command.category !== category) return false
      if (!normalized) return true
      return (
        command.name.toLowerCase().includes(normalized) ||
        command.description.toLowerCase().includes(normalized)
      )
    })
  }, [category, library.data, query])

  if (!bot) return <LoadingState minHeight={280} />

  return (
    <Stack gap="lg">
      <Group gap="sm">
        <Button
          component={Link}
          to={`/app/bots/${bot.id}/commands`}
          variant="subtle"
          color="gray"
          size="compact-sm"
          leftSection={<IconArrowLeft size={15} />}
        >
          {t('nav.commands')}
        </Button>
      </Group>

      <PageHeader
        title={t('commands.library')}
        description={t('commands.librarySubtitle')}
        actions={
          <TextFieldActions botId={bot.id} />
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
            placeholder={t('templates.allCategories')}
            data={commandCategoryOptions}
            value={category}
            onChange={setCategory}
            clearable
            w={{ base: '100%', sm: 220 }}
          />
        </Group>
      </Card>

      {library.isLoading && <LoadingState />}
      {library.data && filtered.length === 0 && (
        <EmptyState icon="search" title={t('common.notFound')} compact />
      )}

      <SimpleGrid cols={{ base: 1, md: 2, xl: 3 }} spacing="md">
        {filtered.map((command) => {
          const installed = installedIds.has(command.id)
          return (
            <Card key={command.id} withBorder radius="lg" p="lg" className="bf-hover-lift">
              <Stack gap="sm" style={{ height: '100%' }}>
                <Group justify="space-between" align="flex-start" wrap="nowrap">
                  <Group gap="sm" wrap="nowrap">
                    <ThemeIcon size={40} radius="md" variant="light" color="brand">
                      <IconTerminal size={19} />
                    </ThemeIcon>
                    <Stack gap={2}>
                      <Title order={3} fz={16} ff="monospace">
                        /{command.name}
                      </Title>
                      <Text size="xs" c="dimmed">
                        {commandTypeLabel[command.type]} ·{' '}
                        {commandCategoryLabel[command.category] ?? command.category}
                      </Text>
                    </Stack>
                  </Group>
                  {installed && (
                    <Badge color="teal" variant="light" size="sm" leftSection={<IconCheck size={11} />}>
                      {t('commands.installed')}
                    </Badge>
                  )}
                </Group>

                <Text size="sm" c="dimmed" lineClamp={3} style={{ flex: 1 }}>
                  {command.description}
                </Text>

                <Group gap={5}>
                  {command.permissions.slice(0, 2).map((permission) => (
                    <Badge key={permission} size="xs" variant="light" color="orange" tt="none">
                      {permission}
                    </Badge>
                  ))}
                  <Text size="10px" c="dimmed">
                    {formatNumber(command.installs)} установок
                  </Text>
                </Group>

                <Group gap="xs" grow>
                  <Button variant="default" size="compact-sm" onClick={() => setSelected(command)}>
                    {t('commands.flowSteps')}
                  </Button>
                  <Button
                    variant={installed ? 'light' : 'filled'}
                    size="compact-sm"
                    color={installed ? 'teal' : 'brand'}
                    leftSection={installed ? <IconCheck size={14} /> : <IconDownload size={14} />}
                    disabled={installed}
                    loading={installMutation.isPending && installMutation.variables === command.id}
                    onClick={() => installMutation.mutate(command.id)}
                  >
                    {installed ? t('commands.installed') : t('common.install')}
                  </Button>
                </Group>
              </Stack>
            </Card>
          )
        })}
      </SimpleGrid>

      <Modal
        opened={Boolean(selected)}
        onClose={() => setSelected(null)}
        title={selected ? `/${selected.name}` : ''}
        size="lg"
      >
        {selected && (
          <Stack>
            <Text size="sm">{selected.description}</Text>
            <Group gap={6}>
              <Badge variant="light" color="gray">
                {commandTypeLabel[selected.type]}
              </Badge>
              <Badge variant="light" color="gray">
                {commandCategoryLabel[selected.category] ?? selected.category}
              </Badge>
              <Badge variant="light" color="cyan">
                {selected.author}
              </Badge>
            </Group>

            {selected.parameters.length > 0 && (
              <Stack gap={4}>
                <Text fw={600} size="sm">
                  {t('commands.parameters')}
                </Text>
                {selected.parameters.map((parameter) => (
                  <Group key={parameter.name} gap="xs">
                    <Text size="xs" ff="monospace" c="brand">
                      {parameter.name}
                    </Text>
                    <Text size="xs" c="dimmed">
                      {parameter.type}
                      {parameter.required ? ' · обязательный' : ''} — {parameter.description}
                    </Text>
                  </Group>
                ))}
              </Stack>
            )}

            <Stack gap={4}>
              <Text fw={600} size="sm">
                {t('commands.flowSteps')}
              </Text>
              {selected.flowSummary.map((step, index) => (
                <Group key={step} gap="xs" wrap="nowrap">
                  <ThemeIcon size={18} radius="xl" variant="light">
                    <Text size="9px">{index + 1}</Text>
                  </ThemeIcon>
                  <Text size="sm">{step}</Text>
                </Group>
              ))}
            </Stack>

            <Card withBorder radius="md" p="sm" bg="var(--mantine-color-default)">
              <Text size="xs" c="dimmed" mb={2}>
                {t('commands.preview')}
              </Text>
              <Text size="sm" style={{ whiteSpace: 'pre-wrap' }}>
                {selected.preview}
              </Text>
            </Card>

            <Group justify="flex-end">
              <Button variant="default" onClick={() => setSelected(null)}>
                {t('common.close')}
              </Button>
              <Button
                leftSection={<IconDownload size={15} />}
                disabled={installedIds.has(selected.id)}
                loading={
                  installMutation.isPending && installMutation.variables === selected.id
                }
                onClick={() => installMutation.mutate(selected.id)}
              >
                {installedIds.has(selected.id) ? t('commands.installed') : t('common.install')}
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>
    </Stack>
  )
}

function TextFieldActions({ botId }: { botId: string }) {
  const { t } = useTranslation()
  return (
    <Button
      component={Link}
      to={`/app/bots/${botId}/commands`}
      variant="default"
      leftSection={<IconTerminal size={16} />}
    >
      {t('commands.title')}
    </Button>
  )
}
