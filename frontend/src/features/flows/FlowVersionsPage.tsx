import { useState } from 'react'
import {
  Badge,
  Button,
  Card,
  Group,
  Modal,
  ScrollArea,
  Stack,
  Table,
  Text,
  ThemeIcon,
  Timeline,
} from '@mantine/core'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'
import {
  IconArrowLeft,
  IconGitBranch,
  IconRotateClockwise,
} from '@tabler/icons-react'
import { api } from '../../shared/api'
import {
  qk,
  useBot,
  useFlow,
  useToastMutation,
} from '../../shared/api/hooks'
import type { FlowVersion } from '../../shared/api/types'
import { PageHeader } from '../../shared/components/bits'
import { ConfirmModal } from '../../shared/components/ConfirmModal'
import { EmptyState, LoadingState } from '../../shared/components/states'
import { AppIcon } from '../../shared/components/icons'
import { formatDate } from '../../shared/lib/format'
import { getBlockDefinition } from '../../shared/blocks'

export default function FlowVersionsPage() {
  const { t } = useTranslation()
  const { botId, flowId } = useParams()
  const { data: bot } = useBot(botId)
  const { data: flow } = useFlow(botId, flowId)
  const [preview, setPreview] = useState<FlowVersion | null>(null)
  const [rollbackVersion, setRollbackVersion] = useState<FlowVersion | null>(null)

  const rollbackMutation = useToastMutation({
    mutationFn: () =>
      api.flows.rollback(botId as string, flowId as string, rollbackVersion?.id as string),
    successMessage: t('flows.rolledBack'),
    invalidateKeys: [
      qk.flow(botId ?? '', flowId ?? ''),
      qk.flows(botId ?? ''),
      qk.bot(botId ?? ''),
    ],
    onSuccess: () => setRollbackVersion(null),
  })

  if (!bot || !flow) return <LoadingState minHeight={300} />

  return (
    <Stack gap="lg">
      <Group gap="sm">
        <Button
          component={Link}
          to={`/app/bots/${bot.id}/flows/${flow.id}`}
          variant="subtle"
          color="gray"
          size="compact-sm"
          leftSection={<IconArrowLeft size={15} />}
        >
          {t('flows.editor')}
        </Button>
      </Group>

      <PageHeader
        title={t('flows.versions')}
        description={t('flows.versionsSubtitle')}
        actions={
          <Button
            component={Link}
            to={`/app/bots/${bot.id}/flows/${flow.id}`}
            variant="default"
            leftSection={<IconGitBranch size={16} />}
          >
            {t('flows.editor')}
          </Button>
        }
      />

      {flow.versions.length === 0 ? (
        <EmptyState
          icon="clock"
          title={t('flows.versions')}
          description={t('flows.versionsSubtitle')}
        />
      ) : (
        <Stack gap="md">
          <Card withBorder radius="lg" p="lg">
            <Timeline bulletSize={26} lineWidth={2}>
              {flow.versions.map((version) => (
                <Timeline.Item
                  key={version.id}
                  bullet={
                    <ThemeIcon
                      size={26}
                      radius="xl"
                      variant="light"
                      color={
                        version.status === 'published'
                          ? 'teal'
                          : version.status === 'draft'
                            ? 'yellow'
                            : 'gray'
                      }
                    >
                      <Text size="10px" fw={800}>
                        v{version.version}
                      </Text>
                    </ThemeIcon>
                  }
                  title={
                    <Group gap="sm" wrap="wrap">
                      <Text fw={700} size="sm">
                        v{version.version} ·{' '}
                        {version.comment || t('flows.publishComment')}
                      </Text>
                      <Badge
                        size="xs"
                        variant="light"
                        color={
                          version.status === 'published'
                            ? 'teal'
                            : version.status === 'draft'
                              ? 'yellow'
                              : 'gray'
                        }
                      >
                        {version.status}
                      </Badge>
                    </Group>
                  }
                >
                  <Group gap="lg" mt={4}>
                    <Text size="xs" c="dimmed">
                      {version.author}
                    </Text>
                    <Text size="xs" c="dimmed">
                      {formatDate(version.createdAt, true)}
                    </Text>
                    <Text size="xs" c="dimmed">
                      {version.nodeCount} {t('flows.nodeCount').toLowerCase()} ·{' '}
                      {version.edgeCount} {t('flows.edgeCount').toLowerCase()}
                    </Text>
                  </Group>
                  <Group gap="xs" mt="xs">
                    <Button
                      variant="subtle"
                      size="compact-xs"
                      onClick={() => setPreview(version)}
                    >
                      {t('common.preview')}
                    </Button>
                    {version.status !== 'published' && (
                      <Button
                        variant="light"
                        size="compact-xs"
                        leftSection={<IconRotateClockwise size={13} />}
                        onClick={() => setRollbackVersion(version)}
                      >
                        {t('flows.rollback')}
                      </Button>
                    )}
                  </Group>
                </Timeline.Item>
              ))}
            </Timeline>
          </Card>

          <Card withBorder radius="lg" p={0}>
            <Table highlightOnHover verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>{t('common.version')}</Table.Th>
                  <Table.Th>{t('common.status')}</Table.Th>
                  <Table.Th>{t('flows.publishComment')}</Table.Th>
                  <Table.Th>Author</Table.Th>
                  <Table.Th>{t('common.details')}</Table.Th>
                  <Table.Th />
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {flow.versions.map((version) => (
                  <Table.Tr key={version.id}>
                    <Table.Td>
                      <Text size="sm" fw={700}>
                        v{version.version}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Badge
                        size="sm"
                        variant="light"
                        color={
                          version.status === 'published'
                            ? 'teal'
                            : version.status === 'draft'
                              ? 'yellow'
                              : 'gray'
                        }
                      >
                        {version.status}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm" lineClamp={1}>
                        {version.comment || '—'}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="xs" c="dimmed">
                        {version.author}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="xs" c="dimmed">
                        {version.nodeCount} / {version.edgeCount} ·{' '}
                        {formatDate(version.createdAt, true)}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Button variant="subtle" size="compact-xs" onClick={() => setPreview(version)}>
                        {t('common.open')}
                      </Button>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
        </Stack>
      )}

      <Modal
        opened={Boolean(preview)}
        onClose={() => setPreview(null)}
        title={preview ? `v${preview.version}` : ''}
        size="lg"
      >
        {preview && (
          <Stack>
            <Group gap="sm">
              <Badge variant="light">{preview.status}</Badge>
              <Text size="sm" c="dimmed">
                {formatDate(preview.createdAt, true)}
              </Text>
              <Text size="sm" c="dimmed">
                {preview.author}
              </Text>
            </Group>
            <Text size="sm">{preview.comment}</Text>
            <ScrollArea h={360}>
              <Stack gap="xs">
                {preview.snapshot.nodes.map((node) => {
                  const definition = getBlockDefinition(node.data.blockId)
                  return (
                    <Group
                      key={node.id}
                      gap="sm"
                      wrap="nowrap"
                      p="xs"
                      style={{
                        borderRadius: 10,
                        border: '1px solid var(--mantine-color-default-border)',
                      }}
                    >
                      <ThemeIcon size={26} radius="md" variant="light">
                        <AppIcon name={definition?.icon ?? 'box'} size={14} />
                      </ThemeIcon>
                      <Stack gap={0}>
                        <Text size="sm" fw={600}>
                          {node.data.label}
                        </Text>
                        <Text size="xs" c="dimmed">
                          {definition?.title ?? node.data.blockId}
                        </Text>
                      </Stack>
                    </Group>
                  )
                })}
              </Stack>
            </ScrollArea>
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setPreview(null)}>
                {t('common.close')}
              </Button>
              {preview.status !== 'published' && (
                <Button
                  leftSection={<IconRotateClockwise size={15} />}
                  onClick={() => {
                    setRollbackVersion(preview)
                    setPreview(null)
                  }}
                >
                  {t('flows.rollback')}
                </Button>
              )}
            </Group>
          </Stack>
        )}
      </Modal>

      <ConfirmModal
        opened={Boolean(rollbackVersion)}
        onClose={() => setRollbackVersion(null)}
        onConfirm={() => rollbackMutation.mutate()}
        loading={rollbackMutation.isPending}
        title={t('flows.rollbackTitle')}
        description={t('flows.rollbackText')}
        confirmLabel={t('flows.rollback')}
        color="brand"
      />
    </Stack>
  )
}
