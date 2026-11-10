import { useEffect, useState } from 'react'
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
  useModuleGuilds,
  useToastMutation,
} from '../../shared/api/hooks'
import type { JsonSchemaProperty } from '../../shared/api/types'
import { AppIcon } from '../../shared/components/icons'
import { PageHeader } from '../../shared/components/bits'
import { GuildResourcePicker } from '../../shared/components/GuildResourcePicker'
import { ErrorState, LoadingState } from '../../shared/components/states'
import { propertyDefault, schemaDefaults } from '../../shared/lib/jsonSchema'
import { discordLabel, moduleCategoryLabel } from '../../shared/lib/status'

function SchemaField({
  fieldKey,
  property,
  required,
  value,
  error,
  botId,
  guildId,
  onChange,
}: {
  fieldKey: string
  property: JsonSchemaProperty
  required: boolean
  value: unknown
  error?: string
  botId: string
  guildId?: string
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
          label: t(`modules.optionLabels.${option.value}`, { defaultValue: option.label }),
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

  if (property.format === 'channel' || property.format === 'role') {
    return (
      <GuildResourcePicker
        botId={botId}
        guildId={guildId}
        kind={property.format}
        channelType={fieldKey === 'category_id' || fieldKey === 'categoryId' ? 'category' : 'text'}
        multiple={property.type === 'array'}
        label={label}
        description={description}
        required={required}
        value={value}
        onChange={onChange}
        error={error}
      />
    )
  }

  if (property.type === 'object') {
    const fields = value && typeof value === 'object' && !Array.isArray(value)
      ? value as Record<string, unknown>
      : {}
    return (
      <Stack gap="sm">
        {Object.entries(property.properties ?? {}).map(([key, child]) => (
          <SchemaField
            key={key}
            fieldKey={key}
            property={child}
            required={Boolean(property.required?.includes(key))}
            value={fields[key] ?? propertyDefault(child)}
            botId={botId}
            guildId={guildId}
            onChange={(next) => onChange({ ...fields, [key]: next })}
          />
        ))}
      </Stack>
    )
  }

  if (property.type === 'array') {
    const items = Array.isArray(value) ? value : []
    const item = property.items
    if (item?.type === 'object') {
      return (
        <Stack gap="sm">
          <Text size="sm" fw={500}>{label}</Text>
          {items.map((entry, index) => (
            <Card key={index} withBorder p="sm">
              <Stack gap="sm">
                <SchemaField
                  fieldKey={fieldKey}
                  property={item}
                  required={false}
                  value={entry}
                  botId={botId}
                  guildId={guildId}
                  onChange={(next) => onChange(items.map((old, i) => i === index ? next : old))}
                />
                <Button
                  type="button"
                  color="red"
                  variant="subtle"
                  size="compact-xs"
                  style={{ alignSelf: 'flex-start' }}
                  onClick={() => onChange(items.filter((_, i) => i !== index))}
                >
                  {t('common.delete')}
                </Button>
              </Stack>
            </Card>
          ))}
          <Button
            type="button"
            variant="light"
            size="compact-sm"
            style={{ alignSelf: 'flex-start' }}
            onClick={() => onChange([...items, propertyDefault(item)])}
          >
            {t('modules.addValue')}
          </Button>
        </Stack>
      )
    }
    return (
      <TagsInput
        label={label}
        description={description}
        required={required}
        value={items.map(String)}
        onChange={onChange}
        error={error}
        placeholder={t('modules.addValue')}
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
  const { guilds, isPending: guildsLoading, isError: guildsError, refetch: refetchGuilds } =
    useModuleGuilds(botId, bot?.guilds)
  const [selectedGuildId, setSelectedGuildId] = useState<string | null>(null)
  const preferredGuildId = selectedGuildId ?? searchParams.get('guild')
  const guild = guilds.find((item) => item.id === preferredGuildId) ?? guilds[0]
  const guildId = guild?.id
  const { data, isLoading, isError, error, refetch } = useBotModule(
    botId,
    moduleId,
    guildId,
  )
  const [values, setValues] = useState<Record<string, unknown>>({})
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

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

  if (isLoading || !bot || (guildsLoading && !guild)) return <LoadingState minHeight={280} />
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
            {discordLabel(permission, t)}
          </Badge>
        ))}
        {manifest.intents.map((intent) => (
          <Badge key={intent} variant="outline" color="gray">
            {discordLabel(intent, t)}
          </Badge>
        ))}
      </Group>

      {guildsError && !guild ? (
        <ErrorState message={t('bot.guildsLoadError')} onRetry={() => void refetchGuilds()} />
      ) : !guild ? (
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
              data={guilds.map((item) => ({ value: item.id, label: item.name }))}
              value={guild?.id ?? null}
              onChange={setSelectedGuildId}
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
                    botId={bot.id}
                    guildId={guild.id}
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
