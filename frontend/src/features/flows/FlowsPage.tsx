import { useState } from 'react'
import {
  Badge,
  Button,
  Card,
  Group,
  Menu,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from '@mantine/core'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  IconBolt,
  IconClock,
  IconDots,
  IconGitBranch,
  IconPlus,
  IconTrash,
} from '@tabler/icons-react'
import { api } from '../../shared/api'
import {
  qk,
  useBot,
  useFlows,
  useToastMutation,
} from '../../shared/api/hooks'
import type { Flow } from '../../shared/api/types'
import { PageHeader } from '../../shared/components/bits'
import { ConfirmModal } from '../../shared/components/ConfirmModal'
import { EmptyState, LoadingState } from '../../shared/components/states'
import { formatRelative } from '../../shared/lib/format'

function FlowCard({ botId, flow }: { botId: string; flow: Flow }) {
  const { t } = useTranslation()
  const [deleteOpened, setDeleteOpened] = useState(false)
  const deleteMutation = useToastMutation({
    mutationFn: () => api.flows.remove(botId, flow.id),
    successMessage: t('flows.deleted'),
    invalidateKeys: [qk.flows(botId), qk.bot(botId)],
    onSuccess: () => setDeleteOpened(false),
  })

  return (
    <>
      <Card withBorder radius="lg" p="lg" className="bf-hover-lift">
        <Stack gap="md" style={{ height: '100%' }}>
          <Group justify="space-between" align="flex-start" wrap="nowrap">
            <Group gap="sm" wrap="nowrap">
              <ThemeIcon size={42} radius="md" variant="light" color="brand">
                <IconBolt size={20} />
              </ThemeIcon>
              <Stack gap={2}>
                <Title order={3} fz={17}>
                  <Link to={`/app/bots/${botId}/flows/${flow.id}`}>{flow.name}</Link>
                </Title>
                <Text size="xs" c="dimmed" lineClamp={2}>
                  {flow.description || '—'}
                </Text>
              </Stack>
            </Group>
            <Menu position="bottom-end" width={200}>
              <Menu.Target>
                <Button variant="subtle" color="gray" size="compact-sm" px={5}>
                  <IconDots size={17} />
                </Button>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Item component={Link} to={`/app/bots/${botId}/flows/${flow.id}`}>
                  {t('common.edit')}
                </Menu.Item>
                <Menu.Item
                  component={Link}
                  to={`/app/bots/${botId}/flows/${flow.id}/versions`}
                >
                  {t('flows.versions')}
                </Menu.Item>
                <Menu.Divider />
                <Menu.Item
                  color="red"
                  leftSection={<IconTrash size={14} />}
                  onClick={() => setDeleteOpened(true)}
                >
                  {t('common.delete')}
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
          </Group>

          <Group gap={6}>
            <Badge
              variant="light"
              color={flow.status === 'published' ? 'teal' : 'yellow'}
              size="sm"
            >
              {flow.status === 'published' ? t('flows.publishedStatus') : t('flows.draft')}
            </Badge>
            <Badge variant="light" color="gray" size="sm">
              v{flow.version}
            </Badge>
            <Badge variant="light" color="gray" size="sm" leftSection={<IconGitBranch size={10} />}>
              {flow.nodes.length} {t('flows.nodeCount').toLowerCase()}
            </Badge>
            <Badge variant="light" color="gray" size="sm">
              {flow.edges.length} {t('flows.edgeCount').toLowerCase()}
            </Badge>
          </Group>

          <Group justify="space-between" mt="auto">
            <Group gap={4}>
              <IconClock size={12} />
              <Text size="xs" c="dimmed">
                {formatRelative(flow.updatedAt)}
              </Text>
            </Group>
            <Group gap="xs">
              <Button
                component={Link}
                to={`/app/bots/${botId}/flows/${flow.id}/versions`}
                size="compact-sm"
                variant="subtle"
              >
                {t('flows.versions')}
              </Button>
              <Button
                component={Link}
                to={`/app/bots/${botId}/flows/${flow.id}`}
                size="compact-sm"
                variant="default"
              >
                {t('common.open')}
              </Button>
            </Group>
          </Group>
        </Stack>
      </Card>

      <ConfirmModal
        opened={deleteOpened}
        onClose={() => setDeleteOpened(false)}
        onConfirm={() => deleteMutation.mutate()}
        loading={deleteMutation.isPending}
        title={t('flows.deleteFlowTitle')}
        description={t('flows.deleteFlowText')}
        confirmLabel={t('common.delete')}
      />
    </>
  )
}

export default function FlowsPage() {
  const { t } = useTranslation()
  const { botId } = useParams()
  const navigate = useNavigate()
  const { data: bot } = useBot(botId)
  const flows = useFlows(botId)

  const createMutation = useToastMutation({
    mutationFn: () =>
      api.flows.create(botId as string, { name: 'Новый сценарий', description: '' }),
    successMessage: t('flows.nodeAdded'),
    invalidateKeys: [qk.flows(botId ?? ''), qk.bot(botId ?? '')],
    onSuccess: (flow) => navigate(`/app/bots/${botId}/flows/${flow.id}`),
  })

  if (!bot) return <LoadingState minHeight={280} />

  return (
    <Stack gap="lg">
      <PageHeader
        title={t('flows.title')}
        description={t('flows.subtitle')}
        actions={
          <Button
            leftSection={<IconPlus size={16} />}
            loading={createMutation.isPending}
            onClick={() => createMutation.mutate()}
          >
            {t('flows.newFlow')}
          </Button>
        }
      />

      {flows.isLoading && <LoadingState />}
      {flows.data && flows.data.length === 0 && (
        <EmptyState
          icon="bolt"
          title={t('flows.emptyTitle')}
          description={t('flows.emptyText')}
          action={
            <Button
              leftSection={<IconPlus size={16} />}
              loading={createMutation.isPending}
              onClick={() => createMutation.mutate()}
            >
              {t('flows.newFlow')}
            </Button>
          }
        />
      )}

      <SimpleGrid cols={{ base: 1, md: 2, xl: 3 }} spacing="md">
        {flows.data?.map((flow) => (
          <FlowCard key={flow.id} botId={bot.id} flow={flow} />
        ))}
      </SimpleGrid>
    </Stack>
  )
}
