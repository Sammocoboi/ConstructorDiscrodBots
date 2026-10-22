import { useMemo, useState } from 'react'
import {
  ActionIcon,
  Alert,
  Badge,
  Box,
  Button,
  Card,
  ColorInput,
  Divider,
  Group,
  Modal,
  SegmentedControl,
  Select,
  SimpleGrid,
  Stack,
  Switch,
  Text,
  Textarea,
  TextInput,
  ThemeIcon,
  Title,
} from '@mantine/core'
import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'
import {
  IconAlertTriangle,
  IconBook,
  IconMessage,
  IconPlus,
  IconSend,
  IconTrash,
} from '@tabler/icons-react'
import { notifications } from '@mantine/notifications'
import { api } from '../../shared/api'
import {
  qk,
  useBot,
  useMessageLibrary,
  useToastMutation,
} from '../../shared/api/hooks'
import type {
  ButtonStyle,
  Embed,
  MessageButton,
  MessageDraft,
  MessageField,
  SelectOption,
} from '../../shared/api/types'
import { PageHeader } from '../../shared/components/bits'
import { LoadingState } from '../../shared/components/states'
import { randomId } from '../../shared/lib/format'

function emptyDraft(): MessageDraft {
  return {
    id: randomId('msg'),
    name: 'Новое сообщение',
    content: '',
    embeds: [],
    buttons: [],
    select: { enabled: false, placeholder: 'Выберите значение', options: [] },
    updatedAt: new Date().toISOString(),
  }
}

function emptyEmbed(): Embed {
  return {
    id: randomId('embed'),
    title: '',
    description: '',
    url: '',
    color: '#5865F2',
    authorName: '',
    authorIconUrl: '',
    footerText: '',
    footerIconUrl: '',
    thumbnailUrl: '',
    imageUrl: '',
    fields: [],
  }
}

const buttonStyles: { value: ButtonStyle; label: string }[] = [
  { value: 'primary', label: 'Primary' },
  { value: 'secondary', label: 'Secondary' },
  { value: 'success', label: 'Success' },
  { value: 'danger', label: 'Danger' },
  { value: 'link', label: 'Link' },
]

const buttonColors: Record<ButtonStyle, string> = {
  primary: '#5865f2',
  secondary: '#4e5058',
  success: '#248046',
  danger: '#da373c',
  link: '#4e5058',
}

export default function MessagesPage() {
  const { t } = useTranslation()
  const { botId } = useParams()
  const { data: bot } = useBot(botId)
  const library = useMessageLibrary()
  const [draft, setDraft] = useState<MessageDraft>(() => emptyDraft())
  const [previewTheme, setPreviewTheme] = useState('dark')
  const [libraryOpened, setLibraryOpened] = useState(false)

  const saveMutation = useToastMutation({
    mutationFn: () => api.messages.save(draft),
    successMessage: t('messages.saved'),
    invalidateKeys: [qk.messages],
  })

  const testMutation = useToastMutation({
    mutationFn: () => api.messages.sendTest(draft),
    successMessage: t('messages.testSent'),
  })

  const helpers = useMemo(
    () => ({
      update: (patch: Partial<MessageDraft>) => setDraft((current) => ({ ...current, ...patch })),
      updateEmbed: (id: string, patch: Partial<Embed>) =>
        setDraft((current) => ({
          ...current,
          embeds: current.embeds.map((embed) =>
            embed.id === id ? { ...embed, ...patch } : embed,
          ),
        })),
      updateField: (embedId: string, fieldId: string, patch: Partial<MessageField>) =>
        setDraft((current) => ({
          ...current,
          embeds: current.embeds.map((embed) =>
            embed.id === embedId
              ? {
                  ...embed,
                  fields: embed.fields.map((field) =>
                    field.id === fieldId ? { ...field, ...patch } : field,
                  ),
                }
              : embed,
          ),
        })),
      updateButton: (id: string, patch: Partial<MessageButton>) =>
        setDraft((current) => ({
          ...current,
          buttons: current.buttons.map((button) =>
            button.id === id ? { ...button, ...patch } : button,
          ),
        })),
      updateOption: (id: string, patch: Partial<SelectOption>) =>
        setDraft((current) => ({
          ...current,
          select: {
            ...current.select,
            options: current.select.options.map((option) =>
              option.id === id ? { ...option, ...patch } : option,
            ),
          },
        })),
    }),
    [],
  )

  if (!bot) return <LoadingState minHeight={280} />

  const totalEmbedLength = draft.embeds.reduce(
    (sum, embed) =>
      sum +
      embed.title.length +
      embed.description.length +
      embed.fields.reduce((fieldSum, field) => fieldSum + field.name.length + field.value.length, 0),
    0,
  )
  const hasPayload = draft.content.trim().length > 0 || draft.embeds.length > 0
  const tooLong = totalEmbedLength > 6000

  const addEmbed = () => {
    if (draft.embeds.length >= 10) {
      notifications.show({ color: 'yellow', message: t('messages.limitEmbeds') })
      return
    }
    helpers.update({ embeds: [...draft.embeds, emptyEmbed()] })
  }

  const addField = (embed: Embed) => {
    if (embed.fields.length >= 25) return
    helpers.updateEmbed(embed.id, {
      fields: [
        ...embed.fields,
        { id: randomId('field'), name: '', value: '', inline: true },
      ],
    })
  }

  const addButton = () => {
    if (draft.buttons.length >= 5) {
      notifications.show({ color: 'yellow', message: t('messages.limitButtons') })
      return
    }
    helpers.update({
      buttons: [
        ...draft.buttons,
        {
          id: randomId('button'),
          label: 'Кнопка',
          style: 'primary',
          emoji: '',
          url: '',
          disabled: false,
        },
      ],
    })
  }

  const addOption = () => {
    if (draft.select.options.length >= 25) return
    helpers.update({
      select: {
        ...draft.select,
        options: [
          ...draft.select.options,
          {
            id: randomId('option'),
            label: 'Опция',
            value: `option_${draft.select.options.length + 1}`,
            description: '',
            emoji: '',
          },
        ],
      },
    })
  }

  const save = () => {
    if (!hasPayload) {
      notifications.show({ color: 'yellow', message: 'Добавьте текст или эмбед.' })
      return
    }
    if (tooLong) {
      notifications.show({ color: 'red', message: 'Суммарная длина эмбедов больше 6000 символов.' })
      return
    }
    saveMutation.mutate()
  }

  const surface = previewTheme === 'dark' ? '#313338' : '#ffffff'
  const surfaceMuted = previewTheme === 'dark' ? '#2b2d31' : '#f2f3f5'
  const textColor = previewTheme === 'dark' ? '#dbdee1' : '#313338'
  const headingColor = previewTheme === 'dark' ? '#f2f3f5' : '#060607'
  const dimColor = previewTheme === 'dark' ? '#949ba4' : '#5c5e66'

  return (
    <Stack gap="lg">
      <PageHeader
        title={t('messages.title')}
        description={t('messages.subtitle')}
        actions={
          <>
            <Button
              variant="default"
              leftSection={<IconBook size={16} />}
              onClick={() => setLibraryOpened(true)}
            >
              {t('messages.library')}
            </Button>
            <Button
              variant="default"
              leftSection={<IconSend size={16} />}
              loading={testMutation.isPending}
              onClick={() => testMutation.mutate()}
            >
              {t('common.test')}
            </Button>
            <Button leftSection={<IconMessage size={16} />} loading={saveMutation.isPending} onClick={save}>
              {t('messages.saveToLibrary')}
            </Button>
          </>
        }
      />

      <SimpleGrid cols={{ base: 1, xl: 2 }} spacing="lg">
        <Stack gap="md">
          <Card withBorder radius="lg" p="lg">
            <Stack gap="sm">
              <TextInput
                label={t('messages.messageName')}
                value={draft.name}
                onChange={(event) => helpers.update({ name: event.currentTarget.value })}
              />
              <Textarea
                label={t('messages.content')}
                value={draft.content}
                onChange={(event) => helpers.update({ content: event.currentTarget.value })}
                autosize
                minRows={3}
                maxRows={8}
                maxLength={2000}
                description={`${draft.content.length} / 2000`}
                placeholder="Текст сообщения…"
              />
              <Group gap="xs">
                <Badge variant="light" color="gray">
                  embeds {draft.embeds.length} / 10
                </Badge>
                <Badge variant="light" color={totalEmbedLength > 6000 ? 'red' : 'gray'}>
                  {totalEmbedLength} / 6000
                </Badge>
                <Badge variant="light" color="gray">
                  buttons {draft.buttons.length} / 5
                </Badge>
              </Group>
            </Stack>
          </Card>

          <Card withBorder radius="lg" p="lg">
            <Group justify="space-between" mb="sm">
              <Title order={3} fz={17}>
                {t('messages.embeds')}
              </Title>
              <Button
                variant="light"
                size="compact-sm"
                leftSection={<IconPlus size={14} />}
                onClick={addEmbed}
              >
                {t('messages.addEmbed')}
              </Button>
            </Group>
            <Stack gap="md">
              {draft.embeds.length === 0 && (
                <Text size="sm" c="dimmed">
                  {t('messages.noEmbed')}
                </Text>
              )}
              {draft.embeds.map((embed, index) => (
                <Card key={embed.id} withBorder radius="md" p="md" bg="var(--mantine-color-default)">
                  <Group justify="space-between" mb="sm">
                    <Group gap="xs">
                      <Box w={10} h={10} style={{ borderRadius: 3, background: embed.color }} />
                      <Text size="sm" fw={700}>
                        Embed {index + 1}
                      </Text>
                    </Group>
                    <ActionIcon
                      variant="subtle"
                      color="red"
                      size="sm"
                      onClick={() =>
                        helpers.update({
                          embeds: draft.embeds.filter((item) => item.id !== embed.id),
                        })
                      }
                    >
                      <IconTrash size={14} />
                    </ActionIcon>
                  </Group>
                  <Stack gap="sm">
                    <SimpleGrid cols={{ base: 1, sm: 2 }}>
                      <TextInput
                        label={t('messages.titleField')}
                        value={embed.title}
                        maxLength={256}
                        onChange={(event) => helpers.updateEmbed(embed.id, { title: event.currentTarget.value })}
                      />
                      <TextInput
                        label={t('messages.author')}
                        value={embed.authorName}
                        onChange={(event) => helpers.updateEmbed(embed.id, { authorName: event.currentTarget.value })}
                      />
                    </SimpleGrid>
                    <Textarea
                      label={t('messages.description')}
                      value={embed.description}
                      maxLength={4096}
                      autosize
                      minRows={2}
                      maxRows={6}
                      onChange={(event) => helpers.updateEmbed(embed.id, { description: event.currentTarget.value })}
                    />
                    <SimpleGrid cols={{ base: 1, sm: 2 }}>
                      <ColorInput
                        label={t('messages.color')}
                        value={embed.color}
                        onChange={(value) => helpers.updateEmbed(embed.id, { color: value })}
                        format="hex"
                        swatches={['#5865F2', '#3BA55D', '#FAA81A', '#ED4245', '#00A8FC']}
                      />
                      <TextInput
                        label={t('messages.url')}
                        value={embed.url}
                        onChange={(event) => helpers.updateEmbed(embed.id, { url: event.currentTarget.value })}
                      />
                      <TextInput
                        label={t('messages.image')}
                        value={embed.imageUrl}
                        onChange={(event) => helpers.updateEmbed(embed.id, { imageUrl: event.currentTarget.value })}
                      />
                      <TextInput
                        label={t('messages.thumbnail')}
                        value={embed.thumbnailUrl}
                        onChange={(event) => helpers.updateEmbed(embed.id, { thumbnailUrl: event.currentTarget.value })}
                      />
                      <TextInput
                        label={t('messages.footer')}
                        value={embed.footerText}
                        onChange={(event) => helpers.updateEmbed(embed.id, { footerText: event.currentTarget.value })}
                      />
                    </SimpleGrid>

                    <Divider
                      label={`${t('messages.embeds')} · fields`}
                      labelPosition="left"
                    />
                    <Stack gap="xs">
                      {embed.fields.map((field) => (
                        <Card key={field.id} withBorder radius="sm" p="xs" bg="var(--mantine-color-body)">
                          <SimpleGrid cols={{ base: 1, sm: 2 }}>
                            <TextInput
                              size="xs"
                              label={t('messages.fieldName')}
                              value={field.name}
                              maxLength={256}
                              onChange={(event) =>
                                helpers.updateField(embed.id, field.id, {
                                  name: event.currentTarget.value,
                                })
                              }
                            />
                            <TextInput
                              size="xs"
                              label={t('messages.fieldValue')}
                              value={field.value}
                              maxLength={1024}
                              onChange={(event) =>
                                helpers.updateField(embed.id, field.id, {
                                  value: event.currentTarget.value,
                                })
                              }
                            />
                          </SimpleGrid>
                          <Group justify="space-between" mt="xs">
                            <Switch
                              size="xs"
                              label={t('messages.inline')}
                              checked={field.inline}
                              onChange={(event) =>
                                helpers.updateField(embed.id, field.id, {
                                  inline: event.currentTarget.checked,
                                })
                              }
                            />
                            <ActionIcon
                              variant="subtle"
                              color="red"
                              size="sm"
                              onClick={() =>
                                helpers.updateEmbed(embed.id, {
                                  fields: embed.fields.filter((item) => item.id !== field.id),
                                })
                              }
                            >
                              <IconTrash size={13} />
                            </ActionIcon>
                          </Group>
                        </Card>
                      ))}
                      <Button
                        variant="subtle"
                        size="compact-xs"
                        leftSection={<IconPlus size={12} />}
                        onClick={() => addField(embed)}
                        w="fit-content"
                      >
                        {t('messages.addField')}
                      </Button>
                    </Stack>
                  </Stack>
                </Card>
              ))}
            </Stack>
          </Card>

          <Card withBorder radius="lg" p="lg">
            <Group justify="space-between" mb="sm">
              <Title order={3} fz={17}>
                {t('messages.buttons')}
              </Title>
              <Button
                variant="light"
                size="compact-sm"
                leftSection={<IconPlus size={14} />}
                onClick={addButton}
              >
                {t('messages.addButton')}
              </Button>
            </Group>
            <Stack gap="xs">
              {draft.buttons.length === 0 && (
                <Text size="sm" c="dimmed">
                  {t('messages.limitButtons')}
                </Text>
              )}
              {draft.buttons.map((button) => (
                <Card key={button.id} withBorder radius="md" p="sm" bg="var(--mantine-color-default)">
                  <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="xs">
                    <TextInput
                      label={t('messages.buttonLabel')}
                      value={button.label}
                      onChange={(event) =>
                        helpers.updateButton(button.id, { label: event.currentTarget.value })
                      }
                    />
                    <Select
                      label={t('messages.buttonStyle')}
                      data={buttonStyles}
                      value={button.style}
                      onChange={(value) =>
                        helpers.updateButton(button.id, {
                          style: (value as ButtonStyle) ?? 'primary',
                        })
                      }
                      allowDeselect={false}
                    />
                  </SimpleGrid>
                  <Group justify="space-between" mt="xs" align="flex-end">
                    <TextInput
                      label={t('messages.emoji')}
                      value={button.emoji}
                      onChange={(event) =>
                        helpers.updateButton(button.id, { emoji: event.currentTarget.value })
                      }
                      w={110}
                    />
                    <Group gap="sm">
                      <Switch
                        label={t('messages.disabled')}
                        size="xs"
                        checked={button.disabled}
                        onChange={(event) =>
                          helpers.updateButton(button.id, {
                            disabled: event.currentTarget.checked,
                          })
                        }
                      />
                      <ActionIcon
                        variant="subtle"
                        color="red"
                        size="sm"
                        onClick={() =>
                          helpers.update({
                            buttons: draft.buttons.filter((item) => item.id !== button.id),
                          })
                        }
                      >
                        <IconTrash size={14} />
                      </ActionIcon>
                    </Group>
                  </Group>
                </Card>
              ))}
            </Stack>

            <Divider my="md" />
            <Group justify="space-between" mb="sm">
              <Switch
                label={t('messages.select')}
                checked={draft.select.enabled}
                onChange={(event) =>
                  helpers.update({
                    select: { ...draft.select, enabled: event.currentTarget.checked },
                  })
                }
              />
              <Button
                variant="light"
                size="compact-sm"
                leftSection={<IconPlus size={14} />}
                disabled={!draft.select.enabled}
                onClick={addOption}
              >
                {t('messages.addOption')}
              </Button>
            </Group>
            {draft.select.enabled && (
              <Stack gap="sm">
                <TextInput
                  label={t('messages.placeholder')}
                  value={draft.select.placeholder}
                  onChange={(event) =>
                    helpers.update({
                      select: {
                        ...draft.select,
                        placeholder: event.currentTarget.value,
                      },
                    })
                  }
                />
                {draft.select.options.map((option) => (
                  <SimpleGrid key={option.id} cols={{ base: 1, sm: 3 }} spacing="xs">
                    <TextInput
                      label={t('messages.optionLabel')}
                      value={option.label}
                      onChange={(event) =>
                        helpers.updateOption(option.id, { label: event.currentTarget.value })
                      }
                    />
                    <TextInput
                      label={t('messages.optionValue')}
                      value={option.value}
                      onChange={(event) =>
                        helpers.updateOption(option.id, { value: event.currentTarget.value })
                      }
                    />
                    <Group align="end" gap="xs">
                      <TextInput
                        label={t('messages.optionDescription')}
                        value={option.description}
                        onChange={(event) =>
                          helpers.updateOption(option.id, {
                            description: event.currentTarget.value,
                          })
                        }
                        style={{ flex: 1 }}
                      />
                      <ActionIcon
                        variant="subtle"
                        color="red"
                        size="lg"
                        onClick={() =>
                          helpers.update({
                            select: {
                              ...draft.select,
                              options: draft.select.options.filter(
                                (item) => item.id !== option.id,
                              ),
                            },
                          })
                        }
                      >
                        <IconTrash size={14} />
                      </ActionIcon>
                    </Group>
                  </SimpleGrid>
                ))}
              </Stack>
            )}
          </Card>
        </Stack>

        <Box>
          <Card withBorder radius="lg" p={0} style={{ position: 'sticky', top: 84 }}>
            <Group justify="space-between" p="md">
              <Title order={3} fz={17}>
                {t('messages.preview')}
              </Title>
              <SegmentedControl
                size="xs"
                value={previewTheme}
                onChange={setPreviewTheme}
                data={[
                  { value: 'light', label: t('messages.previewLight') },
                  { value: 'dark', label: t('messages.previewDark') },
                ]}
              />
            </Group>
            <Box p="lg" style={{ background: surface, minHeight: 420 }}>
              <Group align="flex-start" gap="sm" wrap="nowrap">
                <ThemeIcon size={40} radius="xl" color="brand">
                  <Text size="sm" fw={800}>
                    {bot.name.slice(0, 1).toUpperCase()}
                  </Text>
                </ThemeIcon>
                <Stack gap="xs" style={{ flex: 1, minWidth: 0 }}>
                  <Group gap={6}>
                    <Text size="sm" fw={700} c={headingColor}>
                      {bot.name}
                    </Text>
                    <Badge size="xs" color="brand" variant="filled">
                      BOT
                    </Badge>
                    <Text size="10px" c={dimColor}>
                      Сегодня в 12:00
                    </Text>
                  </Group>

                  {draft.content && (
                    <Text size="sm" style={{ whiteSpace: 'pre-wrap' }} c={textColor}>
                      {draft.content}
                    </Text>
                  )}

                  {draft.embeds.map((embed) => (
                    <Box
                      key={embed.id}
                      style={{
                        borderLeft: `4px solid ${embed.color}`,
                        background: surfaceMuted,
                        borderRadius: 4,
                        padding: '10px 14px',
                      }}
                    >
                      {embed.authorName && (
                        <Text size="xs" fw={700} c={headingColor} mb={4}>
                          {embed.authorName}
                        </Text>
                      )}
                      {embed.title && (
                        <Text size="sm" fw={700} c={headingColor} mb={4}>
                          {embed.title}
                        </Text>
                      )}
                      {embed.description && (
                        <Text size="sm" c={textColor} style={{ whiteSpace: 'pre-wrap' }}>
                          {embed.description}
                        </Text>
                      )}
                      {embed.fields.length > 0 && (
                        <SimpleGrid cols={2} spacing="xs" mt="xs">
                          {embed.fields.map((field) => (
                            <Box
                              key={field.id}
                              style={{ gridColumn: field.inline ? 'span 1' : 'span 2' }}
                            >
                              <Text size="xs" fw={700} c={headingColor}>
                                {field.name}
                              </Text>
                              <Text size="xs" c={textColor} style={{ whiteSpace: 'pre-wrap' }}>
                                {field.value}
                              </Text>
                            </Box>
                          ))}
                        </SimpleGrid>
                      )}
                      {embed.imageUrl && (
                        <Box
                          mt="xs"
                          h={120}
                          style={{
                            borderRadius: 4,
                            background: `linear-gradient(135deg, ${embed.color}55, ${embed.color}22)`,
                            border: `1px dashed ${embed.color}`,
                          }}
                        />
                      )}
                      {(embed.footerText || embed.thumbnailUrl) && (
                        <Group justify="space-between" mt="xs">
                          <Text size="10px" c={dimColor}>
                            {embed.footerText}
                          </Text>
                          {embed.thumbnailUrl && (
                            <Box
                              w={42}
                              h={42}
                              style={{ borderRadius: 6, background: `${embed.color}33` }}
                            />
                          )}
                        </Group>
                      )}
                    </Box>
                  ))}

                  {draft.buttons.length > 0 && (
                    <Group gap={6} mt="xs">
                      {draft.buttons.map((button) => (
                        <Button
                          key={button.id}
                          size="compact-xs"
                          disabled={button.disabled}
                          style={{
                            background: buttonColors[button.style],
                            color: 'white',
                            pointerEvents: 'none',
                          }}
                        >
                          {button.emoji ? `${button.emoji} ` : ''}
                          {button.label}
                        </Button>
                      ))}
                    </Group>
                  )}

                  {draft.select.enabled && (
                    <Box
                      p="xs"
                      style={{
                        borderRadius: 6,
                        background: '#1e1f22',
                        border: '1px solid #4e5058',
                      }}
                    >
                      <Text size="xs" c="#949ba4">
                        {draft.select.placeholder || 'Выберите значение'}
                      </Text>
                    </Box>
                  )}

                  {!hasPayload && (
                    <Text size="sm" c={dimColor}>
                      {t('messages.noEmbed')}
                    </Text>
                  )}
                </Stack>
              </Group>
            </Box>
            {tooLong && (
              <Alert color="red" variant="light" icon={<IconAlertTriangle size={15} />}>
                Суммарная длина эмбедов превышает лимит 6000 символов.
              </Alert>
            )}
          </Card>
        </Box>
      </SimpleGrid>

      <Modal
        opened={libraryOpened}
        onClose={() => setLibraryOpened(false)}
        title={t('messages.library')}
        size="lg"
      >
        <Stack gap="sm">
          {library.data?.length === 0 && (
            <Text size="sm" c="dimmed">
              {t('messages.libraryEmpty')}
            </Text>
          )}
          {library.data?.map((item) => (
            <Card key={item.id} withBorder radius="md" p="sm">
              <Group justify="space-between" wrap="nowrap">
                <Stack gap={2} style={{ minWidth: 0 }}>
                  <Text size="sm" fw={700} lineClamp={1}>
                    {item.name}
                  </Text>
                  <Text size="xs" c="dimmed" lineClamp={1}>
                    {item.content || `${item.embeds.length} embeds`}
                  </Text>
                </Stack>
                <Button
                  size="compact-sm"
                  variant="light"
                  onClick={() => {
                    setDraft({ ...item, updatedAt: new Date().toISOString() })
                    setLibraryOpened(false)
                  }}
                >
                  {t('messages.load')}
                </Button>
              </Group>
            </Card>
          ))}
        </Stack>
      </Modal>
    </Stack>
  )
}
