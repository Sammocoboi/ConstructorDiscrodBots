import { useRef, useState } from 'react'
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
  Textarea,
  Title,
} from '@mantine/core'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import {
  IconArrowLeft,
  IconDownload,
  IconPlus,
  IconShare,
  IconTrash,
  IconUpload,
} from '@tabler/icons-react'
import { notifications } from '@mantine/notifications'
import { api } from '../../shared/api'
import {
  qk,
  useBots,
  useMyTemplates,
  useToastMutation,
} from '../../shared/api/hooks'
import type { Template, TemplateExport } from '../../shared/api/types'
import { PageHeader } from '../../shared/components/bits'
import { BotAvatar } from '../../shared/components/bits'
import { ConfirmModal } from '../../shared/components/ConfirmModal'
import { EmptyState, LoadingState } from '../../shared/components/states'
import { templateCategoryLabel } from '../../shared/lib/status'
import { formatDate } from '../../shared/lib/format'
import { templateExportSchema } from '../../shared/lib/validation'

function TemplateCard({ template }: { template: Template }) {
  const { t } = useTranslation()
  const [deleteOpened, setDeleteOpened] = useState(false)

  const shareMutation = useToastMutation({
    mutationFn: () => api.templates.share(template.id),
    onSuccess: async (result) => {
      try {
        await navigator.clipboard.writeText(result.url)
        notifications.show({ color: 'teal', message: t('templates.shareCopied') })
      } catch {
        notifications.show({ color: 'red', message: t('common.error') })
      }
    },
  })

  const exportMutation = useToastMutation({
    mutationFn: () => api.templates.export(template.id),
    successMessage: t('templates.exportDone'),
    onSuccess: (payload) => {
      const blob = new Blob([JSON.stringify(payload, null, 2)], {
        type: 'application/json',
      })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${template.name.replace(/[^\w-]+/g, '-').toLowerCase()}.json`
      link.click()
      URL.revokeObjectURL(url)
    },
  })

  const deleteMutation = useToastMutation({
    mutationFn: () => api.templates.remove(template.id),
    successMessage: t('templates.deleted'),
    invalidateKeys: [qk.myTemplates],
    onSuccess: () => setDeleteOpened(false),
  })

  return (
    <>
      <Card withBorder radius="lg" p="lg" className="bf-hover-lift">
        <Stack gap="sm" style={{ height: '100%' }}>
          <Group justify="space-between" align="flex-start" wrap="nowrap">
            <Group gap="sm" wrap="nowrap">
              <BotAvatar name={template.name} color={template.iconColor} size={44} radius={13} />
              <Stack gap={2}>
                <Title order={3} fz={16}>
                  {template.name}
                </Title>
                <Group gap={5}>
                  <Badge size="xs" variant="light" color="gray">
                    {templateCategoryLabel[template.category]}
                  </Badge>
                  <Badge size="xs" variant="light" color="gray">
                    v{template.version}
                  </Badge>
                  {template.shareId && (
                    <Badge size="xs" variant="light" color="cyan">
                      share
                    </Badge>
                  )}
                </Group>
              </Stack>
            </Group>
            <Button
              variant="subtle"
              color="red"
              size="compact-sm"
              px={5}
              onClick={() => setDeleteOpened(true)}
              aria-label={t('common.delete')}
            >
              <IconTrash size={15} />
            </Button>
          </Group>

          <Text size="sm" c="dimmed" lineClamp={2} style={{ flex: 1 }}>
            {template.description || '—'}
          </Text>

          <Group gap="lg">
            <Text size="xs" c="dimmed">
              {template.modules.length} {t('templates.modulesCount')}
            </Text>
            <Text size="xs" c="dimmed">
              {template.commandsCount} {t('templates.commandsCount')}
            </Text>
            <Text size="xs" c="dimmed">
              {template.flowsCount} {t('templates.flowsCount')}
            </Text>
          </Group>

          <Text size="xs" c="dimmed">
            {formatDate(template.createdAt)} · {template.author}
          </Text>

          <Group gap="xs" mt="auto">
            <Button
              variant="default"
              size="compact-sm"
              leftSection={<IconShare size={14} />}
              loading={shareMutation.isPending}
              onClick={() => shareMutation.mutate()}
            >
              {t('templates.share')}
            </Button>
            <Button
              variant="default"
              size="compact-sm"
              leftSection={<IconDownload size={14} />}
              loading={exportMutation.isPending}
              onClick={() => exportMutation.mutate()}
            >
              {t('templates.export')}
            </Button>
            <Button
              component={Link}
              to={`/app/bots/new?templateId=${template.id}`}
              variant="light"
              size="compact-sm"
              ml="auto"
            >
              {t('templates.use')}
            </Button>
          </Group>
        </Stack>
      </Card>

      <ConfirmModal
        opened={deleteOpened}
        onClose={() => setDeleteOpened(false)}
        onConfirm={() => deleteMutation.mutate()}
        loading={deleteMutation.isPending}
        title={t('templates.deleteTitle')}
        description={t('templates.deleteText')}
        confirmLabel={t('common.delete')}
      />
    </>
  )
}

export default function MyTemplatesPage() {
  const { t } = useTranslation()
  const templates = useMyTemplates()
  const bots = useBots()
  const fileInput = useRef<HTMLInputElement>(null)
  const [createOpened, setCreateOpened] = useState(false)
  const [botId, setBotId] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')

  const createMutation = useToastMutation({
    mutationFn: () =>
      api.templates.createFromBot(botId as string, { name, description }),
    successMessage: t('templates.created'),
    invalidateKeys: [qk.myTemplates],
    onSuccess: () => {
      setCreateOpened(false)
      setName('')
      setDescription('')
      setBotId(null)
    },
  })

  const importMutation = useToastMutation({
    mutationFn: (payload: TemplateExport) => api.templates.import(payload),
    successMessage: t('templates.imported'),
    invalidateKeys: [qk.myTemplates],
  })

  const handleFile = async (file: File | undefined) => {
    if (!file) return
    try {
      const text = await file.text()
      const parsed = templateExportSchema.safeParse(JSON.parse(text))
      if (!parsed.success) {
        notifications.show({ color: 'red', message: t('templates.importError') })
        return
      }
      importMutation.mutate(parsed.data as unknown as TemplateExport)
    } catch {
      notifications.show({ color: 'red', message: t('templates.importError') })
    } finally {
      if (fileInput.current) fileInput.current.value = ''
    }
  }

  return (
    <Stack gap="lg" maw={1300} mx="auto" w="100%">
      <Group gap="sm">
        <Button
          component={Link}
          to="/app/templates"
          variant="subtle"
          color="gray"
          size="compact-sm"
          leftSection={<IconArrowLeft size={15} />}
        >
          {t('nav.catalog')}
        </Button>
      </Group>

      <PageHeader
        title={t('templates.myTitle')}
        description={t('templates.mySubtitle')}
        actions={
          <>
            <input
              ref={fileInput}
              type="file"
              accept="application/json,.json"
              hidden
              onChange={(event) => void handleFile(event.currentTarget.files?.[0])}
            />
            <Button
              variant="default"
              leftSection={<IconUpload size={16} />}
              loading={importMutation.isPending}
              onClick={() => fileInput.current?.click()}
            >
              {t('templates.import')}
            </Button>
            <Button
              leftSection={<IconPlus size={16} />}
              onClick={() => setCreateOpened(true)}
            >
              {t('templates.createFromBot')}
            </Button>
          </>
        }
      />

      {templates.isLoading && <LoadingState />}
      {templates.data && templates.data.length === 0 && (
        <EmptyState
          icon="template"
          title={t('templates.myEmptyTitle')}
          description={t('templates.myEmptyText')}
          action={
            <>
              <Button leftSection={<IconPlus size={16} />} onClick={() => setCreateOpened(true)}>
                {t('templates.createFromBot')}
              </Button>
              <Button
                variant="light"
                leftSection={<IconUpload size={16} />}
                onClick={() => fileInput.current?.click()}
              >
                {t('templates.import')}
              </Button>
            </>
          }
        />
      )}

      <SimpleGrid cols={{ base: 1, md: 2, xl: 3 }} spacing="md">
        {templates.data?.map((template) => (
          <TemplateCard key={template.id} template={template} />
        ))}
      </SimpleGrid>

      <Modal
        opened={createOpened}
        onClose={() => setCreateOpened(false)}
        title={t('templates.createTitle')}
      >
        <Stack>
          <Select
            label={t('templates.sourceBot')}
            data={(bots.data ?? []).map((bot) => ({ value: bot.id, label: bot.name }))}
            value={botId}
            onChange={(value) => setBotId(value)}
            placeholder={t('templates.sourceBot')}
            searchable
          />
          <TextInput
            label={t('templates.name')}
            value={name}
            onChange={(event) => setName(event.currentTarget.value)}
          />
          <Textarea
            label={t('templates.description')}
            value={description}
            onChange={(event) => setDescription(event.currentTarget.value)}
            autosize
            minRows={3}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setCreateOpened(false)}>
              {t('common.cancel')}
            </Button>
            <Button
              loading={createMutation.isPending}
              disabled={!botId || name.trim().length < 2}
              onClick={() => createMutation.mutate()}
            >
              {t('common.create')}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  )
}
