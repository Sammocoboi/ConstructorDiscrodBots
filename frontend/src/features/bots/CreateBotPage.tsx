import { useState } from 'react'
import {
  Alert,
  Badge,
  Box,
  Button,
  Card,
  Checkbox,
  ColorInput,
  Divider,
  Group,
  Paper,
  SimpleGrid,
  Stack,
  Stepper,
  Text,
  TextInput,
  Textarea,
  ThemeIcon,
  Title,
  UnstyledButton,
} from '@mantine/core'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import {
  IconAlertTriangle,
  IconArrowLeft,
  IconCheck,
  IconKey,
  IconSparkles,
  IconTemplate,
} from '@tabler/icons-react'
import { api, isMockMode } from '../../shared/api'
import { errorMessage } from '../../shared/api/errors'
import {
  qk,
  useAvailableGuilds,
  useTemplates,
  useToastMutation,
} from '../../shared/api/hooks'
import { createBotSchema, type CreateBotFormValues } from '../../shared/lib/validation'
import { BotAvatar } from '../../shared/components/bits'
import { ErrorState, LoadingState } from '../../shared/components/states'
import { PageHeader } from '../../shared/components/bits'
import { formatNumber } from '../../shared/lib/format'
import { templateCategoryLabel } from '../../shared/lib/status'

const presetColors = ['#5865f2', '#3ba55d', '#faa81a', '#ed4245', '#00a8fc', '#9b59b6']

export default function CreateBotPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [active, setActive] = useState(0)
  const [token, setToken] = useState('')
  const [tokenValidated, setTokenValidated] = useState<{
    username: string
    applicationId: string
    guildsCount: number
  } | null>(null)
  const [guildIds, setGuildIds] = useState<string[]>([])
  const [templateId, setTemplateId] = useState<string | undefined>(
    searchParams.get('templateId') ?? undefined,
  )
  const [tokenError, setTokenError] = useState<string | null>(null)
  const [stepError, setStepError] = useState<string | null>(null)

  const guilds = useAvailableGuilds()
  const templates = useTemplates()
  const manageableGuilds = useMemo(
    () => guilds.data?.filter((guild) => guild.canManage || guild.owner) ?? [],
    [guilds.data],
  )

  const {
    register,
    control,
    trigger,
    watch,
    formState: { errors },
  } = useForm<CreateBotFormValues>({
    resolver: zodResolver(createBotSchema),
    defaultValues: {
      name: '',
      description: '',
      avatarColor: '#5865f2',
    },
  })

  const name = watch('name')
  const description = watch('description')
  const avatarColor = watch('avatarColor')

  const validateMutation = useMutation({
    mutationFn: () => api.bots.validateToken(token),
    onSuccess: (result) => {
      setTokenValidated(result)
      setTokenError(null)
    },
    onError: (error) => {
      setTokenValidated(null)
      setTokenError(errorMessage(error))
    },
  })

  const createMutation = useToastMutation({
    mutationFn: () =>
      api.bots.create({
        name,
        description,
        token,
        guildIds,
        avatarColor,
        templateId,
      }),
    successMessage: t('dashboard.started'),
    invalidateKeys: [qk.bots, qk.dashboard],
    onSuccess: (bot) => navigate(`/app/bots/${bot.id}/overview`),
  })

  const next = async () => {
    setStepError(null)
    if (active === 0) {
      if (!tokenValidated) {
        setStepError('Сначала проверьте токен.')
        return
      }
      setActive(1)
      return
    }
    if (active === 1) {
      const valid = await trigger(['name', 'description', 'avatarColor'])
      if (!valid) return
      setActive(2)
      return
    }
    if (active === 2) {
      if (guildIds.length === 0) {
        setStepError('Выберите хотя бы один сервер.')
        return
      }
      setActive(3)
      return
    }
    createMutation.mutate()
  }

  const selectedTemplate = templates.data?.find((template) => template.id === templateId)

  return (
    <Stack gap="lg" maw={1040} mx="auto" w="100%" className="bf-fade-in">
      <Group gap="sm">
        <Button
          component={Link}
          to="/app"
          variant="subtle"
          color="gray"
          size="compact-sm"
          leftSection={<IconArrowLeft size={15} />}
        >
          {t('nav.dashboard')}
        </Button>
      </Group>
      <PageHeader
        title={t('nav.newBot')}
        description="Подключите токен, заполните профиль, выберите серверы и стартовый шаблон."
      />

      <Stepper
        active={active}
        onStepClick={(step) => step < active && setActive(step)}
        allowNextStepsSelect={false}
      >
        <Stepper.Step
          label="Токен"
          description="Discord Developer Portal"
          icon={<IconKey size={16} />}
          completedIcon={<IconCheck size={16} />}
        />
        <Stepper.Step label="Профиль" description="Имя и оформление" />
        <Stepper.Step label="Серверы" description="Куда добавить бота" />
        <Stepper.Step
          label="Шаблон"
          description="Стартовая конфигурация"
          icon={<IconTemplate size={16} />}
          completedIcon={<IconCheck size={16} />}
        />
      </Stepper>

      <Card withBorder radius="lg" p={{ base: 'md', md: 'xl' }}>
        {active === 0 && (
          <Stack gap="md" maw={620}>
            <Stack gap={4}>
              <Title order={3} fz={20}>
                Подключите токен бота
              </Title>
              <Text size="sm" c="dimmed">
                Создайте приложение в Discord Developer Portal → Bot → Reset Token и вставьте
                токен. Он будет зашифрован и больше никогда не покажется полностью.
              </Text>
            </Stack>
            {tokenError && (
              <Alert
                color="red"
                icon={<IconAlertTriangle size={16} />}
                withCloseButton
                onClose={() => setTokenError(null)}
              >
                {tokenError}
              </Alert>
            )}
            <TextInput
              label={t('bot.token')}
              placeholder="MTIzNDU2Nzg5…"
              className="bf-token-field"
              value={token}
              onChange={(event) => {
                setToken(event.currentTarget.value)
                setTokenValidated(null)
              }}
              type="password"
            />
            <Group>
              <Button
                variant="light"
                loading={validateMutation.isPending}
                disabled={token.trim().length < 20}
                onClick={() => validateMutation.mutate()}
              >
                {t('common.test')}
              </Button>
              {isMockMode && (
                <Button
                  variant="subtle"
                  size="compact-sm"
                  onClick={() => {
                    const demo = 'MOCK_DISCORD_BOT_TOKEN_FOR_DEMO_1234567890'
                    setToken(demo)
                    setTokenValidated(null)
                  }}
                >
                  Вставить демо-токен
                </Button>
              )}
            </Group>
            {tokenValidated && (
              <Alert color="teal" icon={<IconCheck size={16} />} title={t('bot.tokenValid')}>
                <Text size="sm">
                  {tokenValidated.username} · app {tokenValidated.applicationId} ·{' '}
                  {tokenValidated.guildsCount} серверов доступно
                </Text>
              </Alert>
            )}
            <Text size="xs" c="dimmed">
              {t('bot.tokenHint')}
            </Text>
          </Stack>
        )}

        {active === 1 && (
          <Stack gap="lg">
            <Title order={3} fz={20}>
              Профиль бота
            </Title>
            <Group align="flex-start" gap="lg" wrap="wrap">
              <BotAvatar name={name || 'Bot'} color={avatarColor} size={86} radius={24} />
              <Stack gap="sm" style={{ flex: 1, minWidth: 260 }}>
                <TextInput
                  label={t('templates.name')}
                  placeholder="Например, Guardian"
                  error={errors.name?.message ? t(errors.name.message) : undefined}
                  {...register('name')}
                />
                <Textarea
                  label={t('templates.description')}
                  placeholder="Коротко о том, что делает бот"
                  autosize
                  minRows={2}
                  maxRows={4}
                  error={
                    errors.description?.message ? t(errors.description.message) : undefined
                  }
                  {...register('description')}
                />
                <Controller
                  name="avatarColor"
                  control={control}
                  render={({ field }) => (
                    <Stack gap="xs">
                      <ColorInput
                        label="Цвет аватара"
                        value={field.value}
                        onChange={field.onChange}
                        format="hex"
                        swatches={presetColors}
                      />
                      <Group gap={8}>
                        {presetColors.map((color) => (
                          <UnstyledButton
                            key={color}
                            onClick={() => field.onChange(color)}
                            aria-label={color}
                            style={{
                              width: 28,
                              height: 28,
                              borderRadius: 9,
                              background: color,
                              border:
                                field.value === color
                                  ? '3px solid var(--mantine-color-text)'
                                  : '2px solid transparent',
                            }}
                          />
                        ))}
                      </Group>
                    </Stack>
                  )}
                />
              </Stack>
            </Group>
          </Stack>
        )}

        {active === 2 && (
          <Stack gap="md">
            <Stack gap={2}>
              <Title order={3} fz={20}>
                {t('bot.guildsTitle')}
              </Title>
              <Text size="sm" c="dimmed">
                Бот будет добавлен на выбранные серверы после запуска. Настроить можно позже.
              </Text>
            </Stack>
            {guilds.isLoading && <LoadingState minHeight={160} />}
            {guilds.isError && (
              <ErrorState
                message={errorMessage(guilds.error)}
                onRetry={() => void guilds.refetch()}
                minHeight={160}
              />
            )}
            {!guilds.isLoading && !guilds.isError && manageableGuilds.length === 0 && (
              <EmptyState
                icon="server"
                title={t('bot.noManageableGuildsTitle', 'Нет доступных серверов')}
                description={t(
                  'bot.noManageableGuildsDescription',
                  'Показываются только серверы, где у вас есть права администратора или «Управление сервером».',
                )}
                minHeight={160}
              />
            )}
            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm">
              {manageableGuilds.map((guild) => {
                const checked = guildIds.includes(guild.id)
                const canManage = guild.canManage || guild.owner
                return (
                  <Paper
                    key={guild.id}
                    withBorder
                    radius="md"
                    p="sm"
                    onClick={() => {
                      if (!canManage) return
                      setGuildIds((current) =>
                        checked
                          ? current.filter((id) => id !== guild.id)
                          : [...current, guild.id],
                      )
                    }}
                    style={{
                      cursor: canManage ? 'pointer' : 'not-allowed',
                      opacity: canManage ? 1 : 0.6,
                    }}
                  >
                    <Group wrap="nowrap" justify="space-between">
                      <Group wrap="nowrap" gap="sm">
                        <BotAvatar name={guild.name} color={guild.iconColor} size={38} radius={11} />
                        <Stack gap={0}>
                          <Text size="sm" fw={600}>
                            {guild.name}
                          </Text>
                          <Text size="xs" c="dimmed">
                            {formatNumber(guild.memberCount)} участников
                            {guild.botAdded ? ' · бот уже добавлен' : ''}
                          </Text>
                        </Stack>
                      </Group>
                      <Checkbox checked={checked} readOnly tabIndex={-1} disabled={!canManage} />
                    </Group>
                  </Paper>
                )
              })}
            </SimpleGrid>
          </Stack>
        )}

        {active === 3 && (
          <Stack gap="md">
            <Stack gap={2}>
              <Title order={3} fz={20}>
                {t('nav.catalog')}
              </Title>
              <Text size="sm" c="dimmed">
                Шаблон сразу включит нужные модули и создаст первый сценарий. Можно выбрать
                позже.
              </Text>
            </Stack>
            {templates.isLoading && <LoadingState minHeight={160} />}
            <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="sm">
              <Paper
                withBorder
                radius="md"
                p="md"
                onClick={() => setTemplateId(undefined)}
                style={{
                  cursor: 'pointer',
                  borderColor: !templateId ? 'var(--mantine-color-brand-5)' : undefined,
                  borderWidth: !templateId ? 2 : 1,
                }}
              >
                <Group gap="sm" wrap="nowrap">
                  <ThemeIcon size={38} radius="md" variant="light" color="gray">
                    <IconSparkles size={18} />
                  </ThemeIcon>
                  <Box>
                    <Text size="sm" fw={700}>
                      Без шаблона
                    </Text>
                    <Text size="xs" c="dimmed">
                      Пустой бот
                    </Text>
                  </Box>
                </Group>
              </Paper>
              {templates.data?.map((template) => {
                const selected = templateId === template.id
                return (
                  <Paper
                    key={template.id}
                    withBorder
                    radius="md"
                    p="md"
                    onClick={() => setTemplateId(template.id)}
                    style={{
                      cursor: 'pointer',
                      borderColor: selected ? 'var(--mantine-color-brand-5)' : undefined,
                      borderWidth: selected ? 2 : 1,
                    }}
                  >
                    <Group gap="sm" wrap="nowrap" align="flex-start">
                      <BotAvatar name={template.name} color={template.iconColor} size={38} radius={11} />
                      <Stack gap={2}>
                        <Text size="sm" fw={700} lineClamp={1}>
                          {template.name}
                        </Text>
                        <Text size="xs" c="dimmed" lineClamp={2}>
                          {template.description}
                        </Text>
                        <Group gap={6} mt={2}>
                          <Badge size="xs" variant="light" color="gray">
                            {templateCategoryLabel[template.category]}
                          </Badge>
                          <Badge size="xs" variant="light" color="gray">
                            {template.modules.length} {t('templates.modulesCount')}
                          </Badge>
                        </Group>
                      </Stack>
                    </Group>
                  </Paper>
                )
              })}
            </SimpleGrid>

            <Divider my="sm" />
            <Paper withBorder radius="md" p="md">
              <Group justify="space-between" wrap="wrap" gap="sm">
                <Group gap="sm">
                  <BotAvatar name={name || 'Bot'} color={avatarColor} size={44} radius={12} />
                  <Stack gap={0}>
                    <Text fw={700}>{name || 'Без названия'}</Text>
                    <Text size="xs" c="dimmed">
                      {guildIds.length} серверов ·{' '}
                      {selectedTemplate ? selectedTemplate.name : 'без шаблона'}
                    </Text>
                  </Stack>
                </Group>
                <Badge variant="light">{tokenValidated?.username ?? 'token'}</Badge>
              </Group>
            </Paper>
          </Stack>
        )}

        {stepError && (
          <Alert color="red" mt="md" withCloseButton onClose={() => setStepError(null)}>
            {stepError}
          </Alert>
        )}

        <Group justify="space-between" mt="xl">
          <Button
            variant="default"
            disabled={active === 0}
            onClick={() => setActive((current) => Math.max(0, current - 1))}
          >
            {t('common.back')}
          </Button>
          <Group>
            <Button variant="subtle" component={Link} to="/app">
              {t('common.cancel')}
            </Button>
            <Button
              onClick={() => void next()}
              loading={createMutation.isPending}
              rightSection={active === 3 ? <IconCheck size={16} /> : undefined}
            >
              {active === 3 ? t('common.create') : t('common.next')}
            </Button>
          </Group>
        </Group>
      </Card>
    </Stack>
  )
}
