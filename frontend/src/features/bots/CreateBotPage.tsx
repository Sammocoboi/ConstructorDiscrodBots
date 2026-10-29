import { useState } from 'react'
import {
  Alert,
  Button,
  Card,
  ColorInput,
  Group,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
} from '@mantine/core'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { IconAlertTriangle, IconArrowLeft, IconCheck } from '@tabler/icons-react'
import { api } from '../../shared/api'
import { qk, useToastMutation } from '../../shared/api/hooks'
import { createBotSchema, type CreateBotFormValues } from '../../shared/lib/validation'
import { BotAvatar } from '../../shared/components/bits'
import { PageHeader } from '../../shared/components/bits'

const presetColors = ['#5865f2', '#3ba55d', '#faa81a', '#ed4245', '#00a8fc', '#9b59b6']

export default function CreateBotPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [token, setToken] = useState('')
  const [error, setError] = useState<string | null>(null)

  const {
    register,
    control,
    handleSubmit,
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
  const avatarColor = watch('avatarColor')

  const createMutation = useToastMutation({
    mutationFn: (values: CreateBotFormValues) =>
      api.bots.create({
        name: values.name,
        description: values.description,
        token: token.trim(),
        guildIds: [],
        avatarColor: values.avatarColor,
      }),
    successMessage: t('dashboard.started'),
    invalidateKeys: [qk.bots, qk.dashboard],
    onSuccess: (bot) => navigate(`/app/bots/${bot.id}/overview`),
  })

  const submit = (values: CreateBotFormValues) => {
    setError(null)
    if (token.trim().length < 20) {
      setError(t('bot.tokenRequired'))
      return
    }
    createMutation.mutate(values)
  }

  return (
    <Stack gap="lg" maw={880} mx="auto" w="100%" className="bf-fade-in">
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
        description={t('bot.createSubtitle')}
      />

      <Card withBorder radius="lg" p={{ base: 'md', md: 'xl' }}>
        <form onSubmit={handleSubmit(submit)}>
          <Stack gap="lg">
            <Group align="flex-start" gap="lg" wrap="wrap">
              <BotAvatar name={name || 'Bot'} color={avatarColor} size={86} radius={24} />
              <Stack gap="sm" style={{ flex: 1, minWidth: 260 }}>
                <TextInput
                  label={t('templates.name')}
                  placeholder={t('bot.namePlaceholder')}
                  error={errors.name?.message ? t(errors.name.message) : undefined}
                  {...register('name')}
                />
                <Textarea
                  label={t('templates.description')}
                  placeholder={t('bot.descriptionPlaceholder')}
                  autosize
                  minRows={2}
                  maxRows={4}
                  error={
                    errors.description?.message ? t(errors.description.message) : undefined
                  }
                  {...register('description')}
                />
              </Stack>
            </Group>

            <Controller
              name="avatarColor"
              control={control}
              render={({ field }) => (
                <ColorInput
                  label={t('bot.avatarColor')}
                  value={field.value}
                  onChange={field.onChange}
                  format="hex"
                  swatches={presetColors}
                  maw={280}
                />
              )}
            />

            <Stack gap={4}>
              <Title order={3} fz={18}>
                {t('bot.token')}
              </Title>
              <Text size="sm" c="dimmed">
                {t('bot.tokenHelp')}
              </Text>
            </Stack>
            <TextInput
              label={t('bot.token')}
              placeholder="MTIzNDU2Nzg5…"
              className="bf-token-field"
              value={token}
              onChange={(event) => setToken(event.currentTarget.value)}
              type="password"
              error={error ?? undefined}
            />

            <Group justify="space-between">
              <Button variant="subtle" component={Link} to="/app">
                {t('common.cancel')}
              </Button>
              <Button
                type="submit"
                leftSection={<IconCheck size={16} />}
                loading={createMutation.isPending}
                disabled={!name.trim() || token.trim().length < 20}
              >
                {t('common.create')}
              </Button>
            </Group>
          </Stack>
        </form>
      </Card>

      <Alert color="blue" icon={<IconAlertTriangle size={16} />}>
        {t('bot.createHint')}
      </Alert>
    </Stack>
  )
}
