import { useEffect, useState } from 'react'
import {
  Alert,
  Badge,
  Box,
  Button,
  Card,
  ColorInput,
  Group,
  Modal,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
} from '@mantine/core'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'
import { IconAlertTriangle, IconCheck, IconKey, IconTemplate } from '@tabler/icons-react'
import { api } from '../../shared/api'
import {
  qk,
  useBot,
  useToastMutation,
} from '../../shared/api/hooks'
import { botProfileSchema, type BotProfileFormValues } from '../../shared/lib/validation'
import { BotAvatar } from '../../shared/components/bits'
import { PageHeader } from '../../shared/components/bits'
import { LoadingState } from '../../shared/components/states'
import { formatRelative } from '../../shared/lib/format'
import { errorMessage } from '../../shared/api/errors'

const activityLabels: Record<string, string> = {
  playing: 'Играет в',
  watching: 'Смотрит',
  listening: 'Слушает',
  competing: 'Соревнуется в',
}

export default function BotProfilePage() {
  const { t } = useTranslation()
  const { botId } = useParams()
  const { data: bot } = useBot(botId)
  const [tokenOpened, setTokenOpened] = useState(false)
  const [templateOpened, setTemplateOpened] = useState(false)
  const [newToken, setNewToken] = useState('')
  const [tokenError, setTokenError] = useState<string | null>(null)
  const [templateName, setTemplateName] = useState('')
  const [templateDescription, setTemplateDescription] = useState('')

  const {
    register,
    control,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isDirty },
  } = useForm<BotProfileFormValues>({
    resolver: zodResolver(botProfileSchema),
    defaultValues: {
      name: '',
      description: '',
      avatarColor: '#5865f2',
      bannerColor: '#1f2160',
      activityType: 'playing',
      activityText: '',
    },
  })

  useEffect(() => {
    if (!bot) return
    reset({
      name: bot.name,
      description: bot.description,
      avatarColor: bot.avatarColor,
      bannerColor: bot.bannerColor,
      activityType: bot.activity.type,
      activityText: bot.activity.text,
    })
  }, [bot, reset])

  const values = watch()

  const updateMutation = useToastMutation({
    mutationFn: (formValues: BotProfileFormValues) =>
      api.bots.update(botId as string, {
        name: formValues.name,
        description: formValues.description,
        avatarColor: formValues.avatarColor,
        bannerColor: formValues.bannerColor,
        activity: {
          type: formValues.activityType,
          text: formValues.activityText,
        },
      }),
    successMessage: t('bot.saved'),
    invalidateKeys: [qk.bot(botId ?? ''), qk.bots],
    onSuccess: (_data, formValues) => reset(formValues),
  })

  const validateTokenMutation = useToastMutation({
    mutationFn: () => api.bots.validateToken(newToken),
    successMessage: t('bot.tokenValid'),
  })

  const replaceTokenMutation = useToastMutation({
    mutationFn: () => api.bots.replaceToken(botId as string, newToken),
    successMessage: t('bot.tokenReplaced'),
    invalidateKeys: [qk.bot(botId ?? ''), qk.bots],
    onSuccess: () => {
      setTokenOpened(false)
      setNewToken('')
      setTokenError(null)
    },
  })

  const templateMutation = useToastMutation({
    mutationFn: () =>
      api.bots.saveAsTemplate(botId as string, {
        name: templateName,
        description: templateDescription,
      }),
    successMessage: t('bot.templateCreated'),
    invalidateKeys: [qk.myTemplates],
    onSuccess: () => setTemplateOpened(false),
  })

  if (!bot) return <LoadingState minHeight={280} />

  return (
    <Stack gap="lg">
      <PageHeader
        title={t('bot.profile')}
        description={t('bot.profileSubtitle')}
        actions={
          <>
            <Button
              variant="default"
              leftSection={<IconTemplate size={16} />}
              onClick={() => {
                setTemplateName(`${bot.name} — шаблон`)
                setTemplateDescription(bot.description)
                setTemplateOpened(true)
              }}
            >
              {t('bot.saveAsTemplate')}
            </Button>
            <Button
              leftSection={<IconCheck size={16} />}
              loading={updateMutation.isPending}
              disabled={!isDirty}
              onClick={handleSubmit((formValues) => updateMutation.mutate(formValues))}
            >
              {isDirty ? t('common.save') : t('common.saved')}
            </Button>
          </>
        }
      />

      <SimpleGrid cols={{ base: 1, lg: 3 }} spacing="lg">
        <Stack gap="lg" style={{ gridColumn: 'span 2' }}>
          <form onSubmit={handleSubmit((formValues) => updateMutation.mutate(formValues))}>
            <Card withBorder radius="lg" p="lg">
              <Title order={3} fz={18} mb="md">
                {t('bot.identity')}
              </Title>
              <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
                <TextInput
                  label={t('templates.name')}
                  error={errors.name?.message ? t(errors.name.message) : undefined}
                  {...register('name')}
                />
                <TextInput
                  label={t('bot.token')}
                  value={bot.tokenMasked}
                  readOnly
                  className="bf-token-field"
                  rightSectionWidth={110}
                  rightSection={
                    <Button
                      size="compact-xs"
                      variant="light"
                      leftSection={<IconKey size={13} />}
                      onClick={() => setTokenOpened(true)}
                    >
                      {t('bot.replaceToken')}
                    </Button>
                  }
                />
              </SimpleGrid>
              <Textarea
                label={t('templates.description')}
                mt="md"
                autosize
                minRows={2}
                maxRows={4}
                error={errors.description?.message ? t(errors.description.message) : undefined}
                {...register('description')}
              />
            </Card>

            <Card withBorder radius="lg" p="lg" mt="lg">
              <Title order={3} fz={18} mb="md">
                {t('bot.appearance')}
              </Title>
              <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
                <Controller
                  name="avatarColor"
                  control={control}
                  render={({ field }) => (
                    <ColorInput
                      label="Цвет аватара"
                      value={field.value}
                      onChange={field.onChange}
                      format="hex"
                      swatches={['#5865f2', '#3ba55d', '#faa81a', '#ed4245', '#00a8fc', '#9b59b6']}
                    />
                  )}
                />
                <Controller
                  name="bannerColor"
                  control={control}
                  render={({ field }) => (
                    <ColorInput
                      label="Цвет баннера"
                      value={field.value}
                      onChange={field.onChange}
                      format="hex"
                      swatches={['#1f2160', '#23272a', '#123f2e', '#4a1f1f', '#1f3a4a']}
                    />
                  )}
                />
              </SimpleGrid>
              <Stack gap={6} mt="lg">
                <Text size="sm" fw={600}>
                  {t('bot.activity')}
                </Text>
                <Group align="flex-start" gap="sm" wrap="wrap">
                  <Controller
                    name="activityType"
                    control={control}
                    render={({ field }) => (
                      <Select
                        data={Object.entries(activityLabels).map(([value, label]) => ({
                          value,
                          label,
                        }))}
                        value={field.value}
                        onChange={(value) => field.onChange(value ?? 'playing')}
                        w={{ base: '100%', sm: 180 }}
                        allowDeselect={false}
                      />
                    )}
                  />
                  <TextInput
                    placeholder="Собирает сообщество"
                    style={{ flex: 1, minWidth: 200 }}
                    error={
                      errors.activityText?.message
                        ? t(errors.activityText.message)
                        : undefined
                    }
                    {...register('activityText')}
                  />
                </Group>
              </Stack>
              <Group justify="flex-end" mt="lg">
                <Button
                  type="submit"
                  loading={updateMutation.isPending}
                  disabled={!isDirty}
                >
                  {t('common.save')}
                </Button>
              </Group>
            </Card>
          </form>
        </Stack>

        <Stack gap="md">
          <Card withBorder radius="lg" p={0} style={{ overflow: 'hidden' }}>
            <Box h={110} style={{ background: `linear-gradient(135deg, ${values.bannerColor}, ${values.avatarColor})` }} />
            <Box p="lg" mt={-34}>
              <BotAvatar
                name={values.name || bot.name}
                color={values.avatarColor}
                size={68}
                radius={20}
              />
              <Title order={3} fz={20} mt="sm">
                {values.name || bot.name}
              </Title>
              <Text size="sm" c="dimmed" lineClamp={2} mt={2}>
                {values.description || t('templates.description')}
              </Text>
              <Group gap={6} mt="sm">
                <Badge variant="light" size="sm">
                  {activityLabels[values.activityType] ?? values.activityType}{' '}
                  {values.activityText}
                </Badge>
              </Group>
            </Box>
          </Card>

          <Card withBorder radius="lg" p="lg">
            <Stack gap="xs">
              <Group justify="space-between">
                <Text size="xs" c="dimmed">
                  Application ID
                </Text>
                <Text size="xs" fw={600} className="bf-token-field">
                  {bot.applicationId}
                </Text>
              </Group>
              <Group justify="space-between">
                <Text size="xs" c="dimmed">
                  {t('bot.version')}
                </Text>
                <Text size="xs" fw={600}>
                  {bot.version}
                </Text>
              </Group>
              <Group justify="space-between">
                <Text size="xs" c="dimmed">
                  Создан
                </Text>
                <Text size="xs" fw={600}>
                  {formatRelative(bot.createdAt)}
                </Text>
              </Group>
              <Group justify="space-between">
                <Text size="xs" c="dimmed">
                  {t('bot.lastUpdated')}
                </Text>
                <Text size="xs" fw={600}>
                  {formatRelative(bot.updatedAt)}
                </Text>
              </Group>
            </Stack>
          </Card>
        </Stack>
      </SimpleGrid>

      <Modal
        opened={tokenOpened}
        onClose={() => setTokenOpened(false)}
        title={t('bot.replaceToken')}
      >
        <Stack>
          <Alert color="yellow" icon={<IconAlertTriangle size={16} />}>
            {t('bot.replaceTokenText')}
          </Alert>
          {tokenError && (
            <Alert color="red" withCloseButton onClose={() => setTokenError(null)}>
              {tokenError}
            </Alert>
          )}
          <TextInput
            label={t('bot.token')}
            value={newToken}
            onChange={(event) => setNewToken(event.currentTarget.value)}
            className="bf-token-field"
            type="password"
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setTokenOpened(false)}>
              {t('common.cancel')}
            </Button>
            <Button
              variant="light"
              loading={validateTokenMutation.isPending}
              disabled={newToken.trim().length < 20}
              onClick={() => {
                setTokenError(null)
                validateTokenMutation.mutate(undefined, {
                  onError: (error) => setTokenError(errorMessage(error)),
                })
              }}
            >
              {t('common.test')}
            </Button>
            <Button
              loading={replaceTokenMutation.isPending}
              disabled={newToken.trim().length < 20}
              onClick={() => replaceTokenMutation.mutate()}
            >
              {t('common.save')}
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Modal
        opened={templateOpened}
        onClose={() => setTemplateOpened(false)}
        title={t('bot.saveAsTemplate')}
      >
        <Stack>
          <TextInput
            label={t('templates.name')}
            value={templateName}
            onChange={(event) => setTemplateName(event.currentTarget.value)}
          />
          <Textarea
            label={t('templates.description')}
            value={templateDescription}
            onChange={(event) => setTemplateDescription(event.currentTarget.value)}
            autosize
            minRows={3}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setTemplateOpened(false)}>
              {t('common.cancel')}
            </Button>
            <Button
              loading={templateMutation.isPending}
              onClick={() => templateMutation.mutate()}
            >
              {t('common.create')}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  )
}
