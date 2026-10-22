import { useMemo, useState } from 'react'
import {
  Badge,
  Box,
  Button,
  Card,
  Group,
  SegmentedControl,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from '@mantine/core'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import {
  IconAlertCircle,
  IconAlertTriangle,
  IconArrowRight,
  IconCircleCheck,
  IconCreditCard,
  IconInfoCircle,
} from '@tabler/icons-react'
import { api } from '../../shared/api'
import {
  qk,
  useNotifications,
  useToastMutation,
} from '../../shared/api/hooks'
import type { Notification } from '../../shared/api/types'
import { PageHeader } from '../../shared/components/bits'
import { EmptyState, ErrorState, LoadingState } from '../../shared/components/states'
import { formatRelative } from '../../shared/lib/format'
import { errorMessage } from '../../shared/api/errors'

const typeMeta = {
  info: { icon: IconInfoCircle, color: 'blue', label: 'notifications.typeInfo' },
  success: { icon: IconCircleCheck, color: 'teal', label: 'notifications.typeSuccess' },
  warning: { icon: IconAlertTriangle, color: 'yellow', label: 'notifications.typeWarning' },
  error: { icon: IconAlertCircle, color: 'red', label: 'notifications.typeError' },
  billing: { icon: IconCreditCard, color: 'grape', label: 'notifications.typeBilling' },
} as const

function NotificationRow({
  notification,
  onOpen,
}: {
  notification: Notification
  onOpen: (notification: Notification) => void
}) {
  const { t } = useTranslation()
  const meta = typeMeta[notification.type]
  return (
    <Group
      wrap="nowrap"
      align="flex-start"
      gap="md"
      p="md"
      onClick={() => onOpen(notification)}
      style={{
        cursor: 'pointer',
        borderRadius: 'var(--mantine-radius-md)',
        background: notification.read
          ? undefined
          : 'var(--mantine-color-brand-light)',
      }}
    >
      <ThemeIcon variant="light" color={meta.color} radius="md" size={40}>
        <meta.icon size={19} />
      </ThemeIcon>
      <Stack gap={3} style={{ flex: 1, minWidth: 0 }}>
        <Group gap="xs" wrap="nowrap">
          <Text size="sm" fw={notification.read ? 600 : 800} truncate>
            {notification.title}
          </Text>
          {!notification.read && <Box w={7} h={7} bg="brand" style={{ borderRadius: '50%', flexShrink: 0 }} />}
        </Group>
        <Text size="sm" c="dimmed">
          {notification.message}
        </Text>
        <Group gap="xs" mt={2}>
          <Badge size="xs" variant="light" color={meta.color}>
            {t(meta.label)}
          </Badge>
          <Text size="xs" c="dimmed">
            {formatRelative(notification.createdAt)}
          </Text>
        </Group>
      </Stack>
      {notification.link && (
        <IconArrowRight size={16} style={{ flexShrink: 0, marginTop: 10 }} />
      )}
    </Group>
  )
}

export default function NotificationsPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const notifications = useNotifications()
  const [filter, setFilter] = useState<'all' | 'unread'>('all')

  const markRead = useToastMutation({
    mutationFn: (id: string) => api.notifications.markRead(id),
    invalidateKeys: [qk.notifications],
  })

  const markAll = useToastMutation({
    mutationFn: () => api.notifications.markAllRead(),
    successMessage: t('notifications.markedAll'),
    invalidateKeys: [qk.notifications],
  })

  const unreadCount = useMemo(
    () => (notifications.data ?? []).filter((item) => !item.read).length,
    [notifications.data],
  )

  const visible = useMemo(() => {
    const list = notifications.data ?? []
    return filter === 'unread' ? list.filter((item) => !item.read) : list
  }, [filter, notifications.data])

  const open = (notification: Notification) => {
    if (!notification.read) markRead.mutate(notification.id)
    if (notification.link) navigate(notification.link)
  }

  return (
    <Stack gap="lg" maw={900} mx="auto" w="100%">
      <PageHeader
        title={t('notifications.title')}
        description={t('notifications.subtitle')}
        actions={
          <Button
            variant="default"
            disabled={unreadCount === 0}
            loading={markAll.isPending}
            onClick={() => markAll.mutate()}
          >
            {t('notifications.markAll')}
          </Button>
        }
      />

      <Group justify="space-between" wrap="wrap">
        <SegmentedControl
          value={filter}
          onChange={(value) => setFilter(value as 'all' | 'unread')}
          data={[
            { value: 'all', label: `${t('notifications.all')} (${notifications.data?.length ?? 0})` },
            { value: 'unread', label: `${t('notifications.unread')} (${unreadCount})` },
          ]}
        />
        {unreadCount > 0 && (
          <Badge color="brand" variant="light">
            {t('notifications.unread')}: {unreadCount}
          </Badge>
        )}
      </Group>

      {notifications.isLoading && <LoadingState />}
      {notifications.isError && (
        <ErrorState
          message={errorMessage(notifications.error)}
          onRetry={() => void notifications.refetch()}
        />
      )}

      {notifications.data && visible.length === 0 && (
        <EmptyState
          icon="bell"
          title={t('notifications.empty')}
          description={t('notifications.emptyText')}
        />
      )}

      {visible.length > 0 && (
        <Card withBorder radius="lg" p={6}>
          <Stack gap={2}>
            {visible.map((notification) => (
              <NotificationRow
                key={notification.id}
                notification={notification}
                onOpen={open}
              />
            ))}
          </Stack>
        </Card>
      )}

      <Title order={4} fz={13} c="dimmed" fw={500} ta="center">
        {t('notifications.subtitle')}
      </Title>
    </Stack>
  )
}
