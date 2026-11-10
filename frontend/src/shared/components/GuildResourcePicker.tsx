import { useState } from 'react'
import { Button, Group, Modal, MultiSelect, Select, Stack, Text, TextInput, type SelectProps } from '@mantine/core'
import { IconPlus } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import { api } from '../api'
import { qk, useGuildResources, useToastMutation } from '../api/hooks'

type Props = Pick<SelectProps, 'label' | 'description' | 'required' | 'error'> & {
  botId: string
  guildId?: string
  kind: 'channel' | 'role'
  channelType?: 'text' | 'category'
  multiple?: boolean
  value: unknown
  onChange: (value: string | string[]) => void
}

export function GuildResourcePicker({
  botId,
  guildId,
  kind,
  channelType = 'text',
  multiple = false,
  value,
  onChange,
  ...props
}: Props) {
  const { t } = useTranslation()
  const resources = useGuildResources(botId, guildId)
  const [opened, setOpened] = useState(false)
  const [name, setName] = useState('')
  const isRole = kind === 'role'
  const isCategory = kind === 'channel' && channelType === 'category'
  const labels = isRole
    ? { choose: 'selectRole', create: 'createRole', created: 'roleCreated' } as const
    : isCategory
      ? { choose: 'selectCategory', create: 'createCategory', created: 'categoryCreated' } as const
      : { choose: 'selectChannel', create: 'createChannel', created: 'channelCreated' } as const
  const singleValue = typeof value === 'string' && value ? value : null
  const multipleValues = Array.isArray(value) ? value.map(String) : []
  const choices = isRole
    ? resources.data?.roles.map((role) => ({ value: role.id, label: role.name })) ?? []
    : resources.data?.channels
        .filter((channel) => channel.type === channelType)
        .map((channel) => ({
          value: channel.id,
          label: isCategory ? channel.name : `#${channel.name}`,
        })) ?? []

  for (const id of multiple ? multipleValues : singleValue ? [singleValue] : []) {
    if (!choices.some((choice) => choice.value === id)) {
      choices.push({ value: id, label: t('guildResources.savedValue', { id }) })
    }
  }

  const create = useToastMutation({
    mutationFn: () => api.bots.createGuildResource(botId, guildId as string, {
      kind,
      name: name.trim(),
      channelType,
    }),
    successMessage: t(`guildResources.${labels.created}`),
    invalidateKeys: [qk.guildResources(botId, guildId ?? '')],
    onSuccess: ({ id }) => {
      onChange(multiple ? [...new Set([...multipleValues, id])] : id)
      setOpened(false)
    },
  })

  const fieldProps = {
    ...props,
    data: choices,
    disabled: !guildId || resources.isLoading,
    searchable: true,
    clearable: true,
    placeholder: resources.isLoading
      ? t('common.loading')
      : t(guildId ? `guildResources.${labels.choose}` : 'guildResources.selectServer'),
    nothingFoundMessage: t('guildResources.empty'),
    error: props.error ?? (resources.isError ? t('guildResources.loadError') : undefined),
  }

  return (
    <Stack gap={4}>
      {multiple
        ? <MultiSelect {...fieldProps} value={multipleValues} onChange={onChange} />
        : <Select {...fieldProps} value={singleValue} onChange={(next) => onChange(next ?? '')} />}
      {guildId && (
        <Button
          type="button"
          variant="subtle"
          size="compact-xs"
          style={{ alignSelf: 'flex-start' }}
          leftSection={<IconPlus size={13} />}
          onClick={() => {
            setName('')
            setOpened(true)
          }}
        >
          {t(`guildResources.${labels.create}`)}
        </Button>
      )}
      <Modal
        opened={opened}
        onClose={() => { if (!create.isPending) setOpened(false) }}
        title={t(`guildResources.${labels.create}`)}
        closeOnClickOutside={!create.isPending}
        closeOnEscape={!create.isPending}
      >
        <form onSubmit={(event) => {
          event.preventDefault()
          event.stopPropagation()
          if (name.trim() && guildId && !create.isPending) create.mutate()
        }}>
          <Stack>
            <Text size="sm" c="dimmed">
              {t(isRole ? 'guildResources.rolePermission' : 'guildResources.channelPermission')}
            </Text>
            <TextInput
              label={t('guildResources.name')}
              value={name}
              maxLength={100}
              onChange={(event) => setName(event.currentTarget.value)}
              data-autofocus
            />
            <Group justify="flex-end">
              <Button type="submit" loading={create.isPending} disabled={!name.trim() || !guildId}>
                {t('common.create')}
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>
    </Stack>
  )
}
