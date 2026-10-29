import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  ColorInput,
  Divider,
  Group,
  NumberInput,
  PasswordInput,
  Select,
  Stack,
  Switch,
  TagsInput,
  Text,
  Textarea,
  TextInput,
  ThemeIcon,
  Title,
} from '@mantine/core'
import { useTranslation } from 'react-i18next'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { IconAlertTriangle, IconArrowLeft, IconCheck, IconShield } from '@tabler/icons-react'
import { api } from '../../shared/api'
import {
  qk,
  useBot,
  useBotModule,
  useToastMutation,
} from '../../shared/api/hooks'
import type { JsonSchemaProperty } from '../../shared/api/types'
import { AppIcon } from '../../shared/components/icons'
import { PageHeader } from '../../shared/components/bits'
import { ErrorState, LoadingState } from '../../shared/components/states'
import { propertyDefault, schemaDefaults } from '../../shared/lib/jsonSchema'
import { moduleCategoryLabel } from '../../shared/lib/status'

function SchemaField({
  fieldKey,
  property,
  required,
  value,
  error,
  channels,
  roles,
  onChange,
}: {
  fieldKey: string
  property: JsonSchemaProperty
  required: boolean
  value: unknown
  error?: string
  channels: { value: string; label: string }[]
  roles: { value: string; label: string }[]
  onChange: (value: unknown) => void
}) {
  const { t } = useTranslation()
  const label = `${property.title}${required ? ' *' : ''}`
  const description = property.description

  if (property.enum?.length) {
    return (
      <Select
        label={label}
        description={description}
        required={required}
        data={property.enum.map((option) => ({
          value: String(option.value),
          label: option.label,
        }))}
        value={value === undefined || value === null ? null : String(value)}
        onChange={(next) => {
          const match = property.enum?.find((option) => String(option.value) === next)
          onChange(match ? match.value : next)
        }}
        error={error}
      />
    )
  }

  if (property.type === 'boolean') {
    return (
      <Switch
        label={label}
        description={description}
        checked={Boolean(value)}
        onChange={(event) => onChange(event.currentTarget.checked)}
      />
    )
  }

  if (property.type === 'number' || property.type === 'integer') {
    return (
      <NumberInput
        label={label}
        description={description}
        required={required}
        value={typeof value === 'number' ? value : Number(value ?? 0)}
        min={property.minimum}
        max={property.maximum}
        suffix={property.format === 'duration' ? ` ${t('common.seconds')}` : undefined}
        onChange={(next) => onChange(typeof next === 'number' ? next : Number(next) || 0)}
        error={error}
      />
    )
  }

  if (property.type === 'array') {
    return (
      <TagsInput
        label={label}
        description={description}
        required={required}
        value={Array.isArray(value) ? value.map(String) : []}
        onChange={(next) => onChange(next)}
        error={error}
        placeholder={t('modules.addValue')}
      />
    )
  }

  if (property.format === 'channel') {
    if (channels.length === 0) {
      return (
        <TextInput
          label={label}
          description={description}
          required={required}
          value={typeof value === 'string' ? value : ''}
          onChange={(event) => onChange(event.currentTarget.value)}
          error={error}
          placeholder={t('modules.channelIdPlaceholder')}
          styles={{ input: { fontFamily: 'monospace' } }}
        />
      )
    }
    return (
      <Select
        label={label}
        description={description}
        required={required}
        data={channels}
        searchable
        clearable
        value={typeof value === 'string' && value ? value : null}
        onChange={(next) => onChange(next ?? '')}
        error={error}
        placeholder={t('modules.selectChannel')}
      />
    )
  }

  if (property.format === 'role') {
    if (roles.length === 0) {
      return (
        <TextInput
          label={label}
          description={description}
          required={required}
          value={typeof value === 'string' ? value : ''}
          onChange={(event) => onChange(event.currentTarget.value)}
          error={error}
          placeholder={t('modules.roleIdPlaceholder')}
          styles={{ input: { fontFamily: 'monospace' } }}
        />
      )
    }
    return (
      <Select
        label={label}
        description={description}
        required={required}
        data={roles}
        searchable
        clearable
        value={typeof value === 'string' && value ? value : null}
        onChange={(next) => onChange(next ?? '')}
        error={error}
        placeholder={t('modules.selectRole')}
      />
    )
  }

  if (property.format === 'color') {
    return (
      <ColorInput
        label={label}
        description={description}
        required={required}
        format="hex"
        value={typeof value === 'string' ? value : '#5865F2'}
        onChange={(next) => onChange(next)}
        error={error}
        swatches={['#5865F2', '#3BA55D', '#FAA81A', '#ED4245', '#00A8FC']}
      />
    )
  }

  if (property.format === 'textarea') {
    return (
      <Textarea
        label={label}
        description={description}
        required={required}
        autosize
        minRows={3}
        maxRows={8}
        value={typeof value === 'string' ? value : ''}
        onChange={(event) => onChange(event.currentTarget.value)}
        error={error}
      />
    )
  }

  if (property.format === 'secret') {
    return (
      <PasswordInput
        label={label}
        description={description}
        required={required}
        value={typeof value === 'string' ? value : ''}
        onChange={(event) => onChange(event.currentTarget.value)}
        error={error}
      />
    )
  }

  return (
    <TextInput
      label={label}
      description={description}
      required={required}
      value={typeof value === 'string' ? value : String(value ?? '')}
      onChange={(event) => onChange(event.currentTarget.value)}
      error={error}
      styles={{ input: { fontFamily: fieldKey.toLowerCase().includes('id') ? 'monospace' : undefined } }}
    />
  )
}

export default function ModuleDetailPage() {
  const { t } = useTranslation()
  const { botId, moduleId } = useParams()
  const [searchParams] = useSearchParams()
  const { data: bot } = useBot(botId)
  const [guildId, setGuildId] = useState<string | null>(
    searchParams.get('guild') ?? null,
  )
  const { data, isLoading, isError, error, refetch } = useBotModule(
    botId,
    moduleId,
    guildId ?? undefined,
  )
  const [values, setValues] = useState<Record<string, unknown>>({})
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const guild = useMemo(
    () => bot?.guilds.find((item) => item.id === guildId) ?? bot?.guilds[0],
    [bot, guildId],
  )

  useEffect(() => {
    if (guild && !guildId) setGuildId(guild.id)
  }, [guild, guildId])

  useEffect(() => {
    if (!data) return
    const defaults = schemaDefaults(data.manifest.settingsSchema)
    const stored = guildId ? data.state.settings[guildId] ?? {} : {}
    setValues({ ...defaults, ...stored })
    setFieldErrors({})
  }, [data, guildId])

  const saveMutation = useToastMutation({
    mutationFn: () =>
      api.modules.updateSettings(
        botId as string,
        moduleId as string,
        guild?.id as string,
        values,
      ),
    successMessage: t('modules.saved'),
    invalidateKeys: [
      qk.botModule(botId ?? '', moduleId ?? '', guildId ?? undefined),
      qk.botModules(botId ?? '', guildId ?? undefined),
    ],
  })

  const toggleMutation = useToastMutation({
    mutationFn: (enabled: boolean) =>
      api.modules.toggle(
        botId as string,
        moduleId as string,
        enabled,
        guild?.id,
      ),
    successMessage: (enabled) =>
      enabled ? t('modules.enabledToast') : t('modules.disabledToast'),
    invalidateKeys: [
      qk.botModule(botId ?? '', moduleId ?? '', guildId ?? undefined),
      qk.botModules(botId ?? '', guildId ?? undefined),
      qk.bot(botId ?? ''),
    ],
  })

  if (isLoading || !bot) return <LoadingState minHeight={280} />
  if (isError || !data) {
    return (
      <ErrorState
        message={error ? (error as Error).message : undefined}
        onRetry={() => void refetch()}
      />
    )
  }

  const { manifest, state } = data
  const schema = manifest.settingsSchema
  const requiredFields = schema.required ?? []

  const save = () => {
    if (!guild) return
    const errors: Record<string, string> = {}
    for (const key of requiredFields) {
      const value = values[key]
      if (value === undefined || value === null || value === '') {
        errors[key] = t('validation.required')
      }
    }
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return
    saveMutation.mutate()
  }

  return (
    <Stack gap="lg">
      <Group gap="xs">
        <Button
          component={Link}
          to={`/app/bots/${bot.id}/overview`}
          variant="subtle"
          color="gray"
          size="compact-sm"
          leftSection={<IconArrowLeft size={15} />}
        >
          {t('bot.overview')}
        </Button>
        <Button
          component={Link}
          to={`/app/bots/${bot.id}/modules`}
          variant="subtle"
          color="gray"
          size="compact-sm"
        >
          {t('nav.modules')}
        </Button>
      </Group>

      <PageHeader
        title={
          <Group gap="sm">
            <ThemeIcon size={40} radius="md" variant="light">
              <AppIcon name={manifest.icon} size={21} />
            </ThemeIcon>
            <span>{manifest.title}</span>
          </Group>
        }
        description={manifest.description}
        actions={
          <>
            <Switch
              checked={state.enabled}
              label={t('common.enabled')}
              disabled={toggleMutation.isPending || !guild}
              onChange={(event) => toggleMutation.mutate(event.currentTarget.checked)}
            />
            <Button
              leftSection={<IconCheck size={16} />}
              loading={saveMutation.isPending}
              disabled={!guild}
              onClick={save}
            >
              {t('common.save')}
            </Button>
          </>
        }
      />

      {state.warnings.length > 0 && (
        <Alert color="yellow" icon={<IconAlertTriangle size={16} />} title={t('modules.warning')}>
          <Stack gap={2}>
            {state.warnings.map((warning) => (
              <Text key={warning} size="sm">
                {warning}
              </Text>
            ))}
          </Stack>
        </Alert>
      )}

      <Group gap="sm">
        <Badge variant="light" color="gray">
          {moduleCategoryLabel[manifest.category]}
        </Badge>
        {manifest.permissions.map((permission) => (
          <Badge
            key={permission}
            variant="light"
            color="orange"
            leftSection={<IconShield size={11} />}
          >
            {permission}
          </Badge>
        ))}
        {manifest.intents.map((intent) => (
          <Badge key={intent} variant="outline" color="gray">
            {intent}
          </Badge>
        ))}
      </Group>

      {bot.guilds.length === 0 ? (
        <Alert color="orange" title={t('modules.noGuildTitle')}>
          {t('modules.noGuildText')}
        </Alert>
      ) : (
        <Card withBorder radius="lg" p="lg">
          <Group justify="space-between" mb="lg" wrap="wrap">
            <Title order={3} fz={18}>
              {t('modules.settingsTitle')}
            </Title>
            <Select
              label={t('modules.selectGuild')}
              data={bot.guilds.map((item) => ({ value: item.id, label: item.name }))}
              value={guild?.id ?? null}
              onChange={(next) => setGuildId(next)}
              allowDeselect={false}
              w={{ base: '100%', sm: 280 }}
            />
          </Group>

          {Object.keys(schema.properties).length === 0 ? (
            <Text size="sm" c="dimmed">
              {t('modules.settingsEmpty')}
            </Text>
          ) : (
            <Stack gap="md">
              {Object.entries(schema.properties).map(([key, property]) => (
                <div key={key}>
                  <SchemaField
                    fieldKey={key}
                    property={property}
                    required={requiredFields.includes(key)}
                    value={values[key] ?? propertyDefault(property)}
                    error={fieldErrors[key]}
                    channels={(guild?.channels ?? []).map((channel) => ({
                      value: channel.id,
                      label: `#${channel.name}`,
                    }))}
                    roles={(guild?.roles ?? []).map((role) => ({
                      value: role.id,
                      label: role.name,
                    }))}
                    onChange={(next) => {
                      setValues((current) => ({ ...current, [key]: next }))
                      setFieldErrors((current) => {
                        if (!current[key]) return current
                        const nextErrors = { ...current }
                        delete nextErrors[key]
                        return nextErrors
                      })
                    }}
                  />
                  {Object.keys(schema.properties).indexOf(key) <
                    Object.keys(schema.properties).length - 1 && <Divider mt="md" />}
                </div>
              ))}
            </Stack>
          )}
        </Card>
      )}
    </Stack>
  )
}
