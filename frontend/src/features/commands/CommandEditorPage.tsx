import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Badge,
  Box,
  Button,
  Card,
  ColorInput,
  Divider,
  Group,
  Select,
  SimpleGrid,
  Stack,
  Switch,
  Text,
  TextInput,
  Textarea,
  ThemeIcon,
  Title,
} from '@mantine/core'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  IconArrowLeft,
  IconCheck,
  IconPlayerPlay,
  IconTrash,
  IconX,
} from '@tabler/icons-react'
import { api } from '../../shared/api'
import {
  qk,
  useBot,
  useCommands,
  useToastMutation,
} from '../../shared/api/hooks'
import type { Command, CommandType } from '../../shared/api/types'
import { PageHeader } from '../../shared/components/bits'
import { ConfirmModal } from '../../shared/components/ConfirmModal'
import { LoadingState } from '../../shared/components/states'
import { commandCategoryOptions, commandTypeLabel } from '../../shared/lib/status'

interface TraceStep {
  id: string
  title: string
  status: 'ok' | 'skipped' | 'error'
  detail: string
}

export default function CommandEditorPage() {
  const { t } = useTranslation()
  const { botId, commandId } = useParams()
  const navigate = useNavigate()
  const { data: bot } = useBot(botId)
  const commands = useCommands(botId)
  const existing = commands.data?.find((command) => command.id === commandId)
  const isEdit = Boolean(commandId)

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [type, setType] = useState<CommandType>('slash')
  const [category, setCategory] = useState('utility')
  const [requiredRoleId, setRequiredRoleId] = useState<string | null>(null)
  const [enabled, setEnabled] = useState(true)
  const [responseText, setResponseText] = useState('')
  const [embedEnabled, setEmbedEnabled] = useState(false)
  const [embedTitle, setEmbedTitle] = useState('')
  const [embedDescription, setEmbedDescription] = useState('')
  const [embedColor, setEmbedColor] = useState('#5865F2')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [deleteOpened, setDeleteOpened] = useState(false)
  const [userHasRole, setUserHasRole] = useState(true)
  const [trace, setTrace] = useState<TraceStep[] | null>(null)

  useEffect(() => {
    if (!existing) return
    setName(existing.name)
    setDescription(existing.description)
    setType(existing.type)
    setCategory(existing.category)
    setRequiredRoleId(existing.requiredRoleId ?? null)
    setEnabled(existing.enabled)
    setResponseText(existing.responseText)
    setEmbedEnabled(Boolean(existing.embed))
    setEmbedTitle(existing.embed?.title ?? '')
    setEmbedDescription(existing.embed?.description ?? '')
    setEmbedColor(existing.embed?.color ?? '#5865F2')
  }, [existing])

  const roleOptions = useMemo(() => {
    if (!bot) return []
    return bot.guilds.flatMap((guild) =>
      guild.roles.map((role) => ({
        value: role.id,
        label: `${guild.name} · ${role.name}`,
      })),
    )
  }, [bot])

  const payload = (): Partial<Command> => ({
    name: name.trim().toLowerCase(),
    description: description.trim(),
    type,
    category,
    requiredRoleId: requiredRoleId ?? undefined,
    enabled,
    responseText,
    embed:
      embedEnabled && (embedTitle || embedDescription)
        ? { title: embedTitle, description: embedDescription, color: embedColor }
        : undefined,
  })

  const saveMutation = useToastMutation({
    mutationFn: () =>
      isEdit
        ? api.commands.update(botId as string, commandId as string, payload())
        : api.commands.create(botId as string, payload()),
    successMessage: t('commands.published'),
    invalidateKeys: [qk.commands(botId ?? ''), qk.bot(botId ?? '')],
    onSuccess: () => navigate(`/app/bots/${botId}/commands`),
  })

  const deleteMutation = useToastMutation({
    mutationFn: () => api.commands.remove(botId as string, commandId as string),
    successMessage: t('common.delete'),
    invalidateKeys: [qk.commands(botId ?? '')],
    onSuccess: () => navigate(`/app/bots/${botId}/commands`),
  })

  const save = () => {
    const nextErrors: Record<string, string> = {}
    if (!/^[a-z0-9_-]{1,32}$/.test(name.trim().toLowerCase())) {
      nextErrors.name = 'Только строчные латинские буквы, цифры, _ и -, до 32 символов.'
    }
    if (!description.trim()) nextErrors.description = t('validation.required')
    if (!responseText.trim()) nextErrors.responseText = t('validation.required')
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return
    saveMutation.mutate()
  }

  const runTest = () => {
    const steps: TraceStep[] = [
      {
        id: 'trigger',
        title: `Триггер /${name || 'command'}`,
        status: 'ok',
        detail: commandTypeLabel[type],
      },
    ]
    if (requiredRoleId) {
      steps.push({
        id: 'role',
        title: t('commands.roleCondition'),
        status: userHasRole ? 'ok' : 'error',
        detail: roleOptions.find((role) => role.value === requiredRoleId)?.label ?? requiredRoleId,
      })
    } else {
      steps.push({
        id: 'role',
        title: t('commands.condition'),
        status: 'skipped',
        detail: 'Ограничений по роли нет',
      })
    }
    steps.push({
      id: 'response',
      title: t('commands.response'),
      status: requiredRoleId && !userHasRole ? 'skipped' : responseText ? 'ok' : 'error',
      detail: responseText || 'Ответ не задан',
    })
    setTrace(steps)
  }

  if (!bot) return <LoadingState minHeight={280} />
  if (isEdit && commands.isLoading) return <LoadingState minHeight={280} />

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
        title={isEdit ? t('commands.editTitle') : t('commands.newTitle')}
        description={
          isEdit
            ? `/${existing?.name ?? ''} · ${existing?.source === 'library' ? t('commands.library') : t('commands.create')}`
            : t('commands.subtitle')
        }
        actions={
          <>
            {isEdit && (
              <Button
                variant="light"
                color="red"
                leftSection={<IconTrash size={16} />}
                onClick={() => setDeleteOpened(true)}
              >
                {t('common.delete')}
              </Button>
            )}
            <Button leftSection={<IconCheck size={16} />} loading={saveMutation.isPending} onClick={save}>
              {isEdit ? t('common.save') : t('common.create')}
            </Button>
          </>
        }
      />

      <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="lg">
        <Card withBorder radius="lg" p="lg">
          <Stack gap="md">
            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
              <TextInput
                label={t('commands.name')}
                placeholder="welcome"
                leftSection={<Text size="sm" c="dimmed">/</Text>}
                leftSectionWidth={28}
                value={name}
                onChange={(event) => setName(event.currentTarget.value)}
                error={errors.name}
                disabled={existing?.source === 'library'}
              />
              <Select
                label="Тип"
                data={[
                  { value: 'slash', label: t('commands.typeSlash') },
                  { value: 'message', label: t('commands.typeMessage') },
                  { value: 'user', label: t('commands.typeUser') },
                ]}
                value={type}
                onChange={(value) => setType((value as CommandType) ?? 'slash')}
                allowDeselect={false}
              />
              <Select
                label={t('commands.category')}
                data={commandCategoryOptions}
                value={category}
                onChange={(value) => setCategory(value ?? 'utility')}
                allowDeselect={false}
              />
              <Select
                label={t('commands.roleCondition')}
                data={roleOptions}
                value={requiredRoleId}
                onChange={setRequiredRoleId}
                clearable
                searchable
                placeholder={t('common.none')}
              />
            </SimpleGrid>

            <Textarea
              label={t('commands.description')}
              value={description}
              onChange={(event) => setDescription(event.currentTarget.value)}
              error={errors.description}
              autosize
              minRows={2}
              maxRows={3}
            />

            <Switch
              label={t('common.enabled')}
              checked={enabled}
              onChange={(event) => setEnabled(event.currentTarget.checked)}
            />

            <Divider />

            <Textarea
              label={t('commands.responseText')}
              value={responseText}
              onChange={(event) => setResponseText(event.currentTarget.value)}
              error={errors.responseText}
              autosize
              minRows={4}
              maxRows={8}
              placeholder="Привет, {user.mention}!"
            />

            <Switch
              label={t('commands.embedTitle')}
              checked={embedEnabled}
              onChange={(event) => setEmbedEnabled(event.currentTarget.checked)}
            />

            {embedEnabled && (
              <Stack gap="sm">
                <TextInput
                  label={t('commands.embedTitle')}
                  value={embedTitle}
                  onChange={(event) => setEmbedTitle(event.currentTarget.value)}
                />
                <Textarea
                  label={t('commands.embedDescription')}
                  value={embedDescription}
                  onChange={(event) => setEmbedDescription(event.currentTarget.value)}
                  autosize
                  minRows={2}
                />
                <ColorInput
                  label={t('commands.embedColor')}
                  value={embedColor}
                  onChange={setEmbedColor}
                  format="hex"
                  swatches={['#5865F2', '#3BA55D', '#FAA81A', '#ED4245', '#00A8FC']}
                />
              </Stack>
            )}
          </Stack>
        </Card>

        <Stack gap="lg">
          <Card withBorder radius="lg" p="lg" bg="#313338" c="#dbdee1">
            <Group gap="sm" mb="md">
              <ThemeIcon size={36} radius="xl" color="brand">
                <Text size="sm" fw={700}>
                  B
                </Text>
              </ThemeIcon>
              <Stack gap={0}>
                <Group gap={6}>
                  <Text size="sm" fw={700} c="#f2f3f5">
                    {bot.name}
                  </Text>
                  <Badge size="xs" color="brand" variant="filled">
                    BOT
                  </Badge>
                </Group>
                <Text size="10px" c="#949ba4">
                  Сегодня в 12:00
                </Text>
              </Stack>
            </Group>
            <Stack gap="sm">
              <Box
                p="sm"
                style={{
                  borderLeft: `4px solid ${embedColor}`,
                  background: '#2b2d31',
                  borderRadius: 4,
                }}
              >
                {embedTitle && (
                  <Text size="sm" fw={700} c="#f2f3f5" mb={4}>
                    {embedTitle}
                  </Text>
                )}
                {embedDescription && (
                  <Text size="sm" c="#dbdee1" style={{ whiteSpace: 'pre-wrap' }}>
                    {embedDescription}
                  </Text>
                )}
              </Box>
              {responseText && (
                <Text size="sm" style={{ whiteSpace: 'pre-wrap' }}>
                  {responseText}
                </Text>
              )}
              {!responseText && !embedEnabled && (
                <Text size="sm" c="#949ba4">
                  {t('messages.noEmbed')}
                </Text>
              )}
            </Stack>
          </Card>

          <Card withBorder radius="lg" p="lg">
            <Group justify="space-between" mb="sm">
              <Title order={3} fz={17}>
                {t('commands.testTrace')}
              </Title>
              <Button
                size="compact-sm"
                leftSection={<IconPlayerPlay size={14} />}
                onClick={runTest}
              >
                {t('commands.runTest')}
              </Button>
            </Group>
            {requiredRoleId && (
              <Switch
                label="У пользователя есть нужная роль"
                checked={userHasRole}
                onChange={(event) => setUserHasRole(event.currentTarget.checked)}
                mb="sm"
              />
            )}
            {!trace && (
              <Text size="sm" c="dimmed">
                Запустите трассировку, чтобы проверить триггер, условие и ответ.
              </Text>
            )}
            {trace && (
              <Stack gap="xs">
                {trace.map((step) => (
                  <Group
                    key={step.id}
                    align="flex-start"
                    wrap="nowrap"
                    p="xs"
                    style={{
                      borderRadius: 10,
                      border: '1px solid var(--mantine-color-default-border)',
                    }}
                  >
                    <ThemeIcon
                      size={22}
                      radius="xl"
                      variant="light"
                      color={
                        step.status === 'ok'
                          ? 'teal'
                          : step.status === 'error'
                            ? 'red'
                            : 'gray'
                      }
                    >
                      {step.status === 'ok' ? (
                        <IconCheck size={12} />
                      ) : step.status === 'error' ? (
                        <IconX size={12} />
                      ) : (
                        <Text size="9px">—</Text>
                      )}
                    </ThemeIcon>
                    <Stack gap={0}>
                      <Text size="sm" fw={600}>
                        {step.title}
                      </Text>
                      <Text size="xs" c="dimmed">
                        {step.detail}
                      </Text>
                    </Stack>
                  </Group>
                ))}
                <Alert
                  color={trace.every((step) => step.status !== 'error') ? 'teal' : 'red'}
                  variant="light"
                >
                  {trace.every((step) => step.status !== 'error')
                    ? t('commands.testOk')
                    : t('commands.testFailed')}
                </Alert>
              </Stack>
            )}
          </Card>
        </Stack>
      </SimpleGrid>

      <ConfirmModal
        opened={deleteOpened}
        onClose={() => setDeleteOpened(false)}
        onConfirm={() => deleteMutation.mutate()}
        loading={deleteMutation.isPending}
        title={t('common.delete')}
        description={`Команда /${existing?.name ?? name} будет удалена.`}
        confirmLabel={t('common.delete')}
      />
    </Stack>
  )
}
