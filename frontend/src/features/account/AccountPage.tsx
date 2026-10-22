import { useEffect, useState } from 'react'
import {
  Avatar,
  Badge,
  Button,
  Card,
  Divider,
  Group,
  Stack,
  Switch,
  Table,
  Text,
  TextInput,
  ThemeIcon,
  Title,
} from '@mantine/core'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import {
  IconDeviceDesktop,
  IconDeviceMobile,
  IconDownload,
  IconLogout,
  IconMapPin,
  IconShieldLock,
  IconTrash,
  IconUser,
} from '@tabler/icons-react'
import { api } from '../../shared/api'
import { qk, useAccount, useToastMutation } from '../../shared/api/hooks'
import { useAuthStore } from '../../shared/stores/authStore'
import { PageHeader } from '../../shared/components/bits'
import { ConfirmModal } from '../../shared/components/ConfirmModal'
import { ErrorState, LoadingState } from '../../shared/components/states'
import { formatRelative, initials } from '../../shared/lib/format'
import { errorMessage } from '../../shared/api/errors'

type NotificationKey = 'botErrors' | 'payments' | 'productUpdates' | 'weeklyDigest'

export default function AccountPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const account = useAccount()
  const updateUser = useAuthStore((state) => state.updateUser)
  const authUser = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [prefs, setPrefs] = useState<Record<NotificationKey, boolean>>({
    botErrors: true,
    payments: true,
    productUpdates: true,
    weeklyDigest: false,
  })
  const [revokeId, setRevokeId] = useState<string | null>(null)
  const [logoutAllOpened, setLogoutAllOpened] = useState(false)
  const [deleteOpened, setDeleteOpened] = useState(false)

  useEffect(() => {
    if (account.data) {
      setName(account.data.user.username)
      setEmail(account.data.user.email)
      setPrefs(account.data.notifications)
    }
  }, [account.data])

  const saveProfileMutation = useToastMutation({
    mutationFn: () => api.account.updateProfile({ username: name, email }),
    successMessage: t('account.profileSaved'),
    invalidateKeys: [qk.account],
    onSuccess: (user) => updateUser({ username: user.username, email: user.email }),
  })

  const prefsMutation = useToastMutation({
    mutationFn: (patch: Partial<Record<NotificationKey, boolean>>) =>
      api.account.updateNotifications(patch),
    invalidateKeys: [qk.account],
  })

  const revokeMutation = useToastMutation({
    mutationFn: () => api.account.revokeSession(revokeId as string),
    successMessage: t('account.sessionRevoked'),
    invalidateKeys: [qk.account],
    onSuccess: () => setRevokeId(null),
  })

  const logoutAllMutation = useToastMutation({
    mutationFn: () => api.account.logoutEverywhere(),
    successMessage: t('account.loggedOutAll'),
    invalidateKeys: [qk.account],
    onSuccess: () => {
      setLogoutAllOpened(false)
      logout()
      navigate('/login', { replace: true })
    },
  })

  const deleteMutation = useToastMutation({
    mutationFn: () => api.account.deleteAccount(),
    successMessage: t('account.deleted'),
    onSuccess: () => {
      setDeleteOpened(false)
      logout()
      navigate('/', { replace: true })
    },
  })

  const togglePref = (key: NotificationKey, value: boolean) => {
    setPrefs((current) => ({ ...current, [key]: value }))
    prefsMutation.mutate({ [key]: value })
  }

  const exportData = () => {
    if (!account.data) return
    const blob = new Blob([JSON.stringify(account.data, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'botforge-account.json'
    link.click()
    URL.revokeObjectURL(url)
  }

  if (account.isLoading) return <LoadingState minHeight={320} />
  if (account.isError || !account.data) {
    return (
      <ErrorState
        message={errorMessage(account.error)}
        onRetry={() => void account.refetch()}
      />
    )
  }

  const user = account.data.user
  const notificationRows: { key: NotificationKey; label: string; description: string }[] = [
    { key: 'botErrors', label: t('account.notifyBotErrors'), description: t('account.notifyBotErrorsHint') },
    { key: 'payments', label: t('account.notifyPayments'), description: t('account.notifyPaymentsHint') },
    { key: 'productUpdates', label: t('account.notifyUpdates'), description: t('account.notifyUpdatesHint') },
    { key: 'weeklyDigest', label: t('account.notifyDigest'), description: t('account.notifyDigestHint') },
  ]

  return (
    <Stack gap="lg" maw={1000} mx="auto" w="100%">
      <PageHeader title={t('account.title')} description={t('account.subtitle')} />

      <Card withBorder radius="lg" p="lg">
        <Group gap="sm" mb="lg">
          <ThemeIcon variant="light" size="md" radius="md">
            <IconUser size={16} />
          </ThemeIcon>
          <Title order={3} fz={18}>
            {t('account.profile')}
          </Title>
        </Group>
        <Group align="flex-start" gap="xl" wrap="wrap">
          <Stack align="center" gap="xs">
            <Avatar color="brand" size={84} radius="xl">
              {initials(user.username)}
            </Avatar>
            <Text size="xs" c="dimmed">
              {t('account.userId')}: {user.id}
            </Text>
            <Badge variant="light">{user.plan}</Badge>
          </Stack>
          <Stack gap="sm" style={{ flex: 1, minWidth: 260 }}>
            <TextInput
              label={t('account.name')}
              value={name}
              onChange={(event) => setName(event.currentTarget.value)}
            />
            <TextInput
              label={t('auth.email')}
              type="email"
              value={email}
              onChange={(event) => setEmail(event.currentTarget.value)}
            />
            <Group justify="flex-end" mt="xs">
              <Button
                loading={saveProfileMutation.isPending}
                disabled={
                  !name.trim() ||
                  !email.trim() ||
                  (name === user.username && email === user.email)
                }
                onClick={() => saveProfileMutation.mutate()}
              >
                {t('common.save')}
              </Button>
            </Group>
          </Stack>
        </Group>
        <Divider my="lg" />
        <Group justify="space-between" wrap="nowrap">
          <Group gap="sm">
            <ThemeIcon variant="light" color={user.twoFactorEnabled ? 'teal' : 'gray'} radius="md">
              <IconShieldLock size={16} />
            </ThemeIcon>
            <Stack gap={0}>
              <Text size="sm" fw={600}>
                {t('account.twoFactor')}
              </Text>
              <Text size="xs" c="dimmed">
                {user.twoFactorEnabled ? t('account.twoFactorOn') : t('account.twoFactorOff')}
              </Text>
            </Stack>
          </Group>
          <Badge color={user.twoFactorEnabled ? 'teal' : 'gray'} variant="light">
            {user.twoFactorEnabled ? t('common.enabled') : t('common.disabled')}
          </Badge>
        </Group>
      </Card>

      <Card withBorder radius="lg" p="lg">
        <Title order={3} fz={18} mb="md">
          {t('account.notifications')}
        </Title>
        <Stack gap="sm">
          {notificationRows.map((row) => (
            <Group key={row.key} justify="space-between" wrap="nowrap">
              <Stack gap={0}>
                <Text size="sm" fw={600}>
                  {row.label}
                </Text>
                <Text size="xs" c="dimmed">
                  {row.description}
                </Text>
              </Stack>
              <Switch
                checked={prefs[row.key]}
                onChange={(event) => togglePref(row.key, event.currentTarget.checked)}
              />
            </Group>
          ))}
        </Stack>
      </Card>

      <Card withBorder radius="lg" p={0}>
        <Group justify="space-between" p="lg" pb="sm">
          <Title order={3} fz={18}>
            {t('account.sessions')}
          </Title>
          <Button
            variant="light"
            color="red"
            size="compact-sm"
            leftSection={<IconLogout size={14} />}
            onClick={() => setLogoutAllOpened(true)}
          >
            {t('account.logoutAll')}
          </Button>
        </Group>
        <Table verticalSpacing="sm" highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>{t('account.device')}</Table.Th>
              <Table.Th>{t('account.location')}</Table.Th>
              <Table.Th>{t('account.lastActive')}</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {account.data.sessions.map((session) => (
              <Table.Tr key={session.id}>
                <Table.Td>
                  <Group gap="sm" wrap="nowrap">
                    <ThemeIcon variant="light" radius="md">
                      {session.device.toLowerCase().includes('iphone') ||
                      session.device.toLowerCase().includes('android') ? (
                        <IconDeviceMobile size={16} />
                      ) : (
                        <IconDeviceDesktop size={16} />
                      )}
                    </ThemeIcon>
                    <Stack gap={0}>
                      <Group gap={6}>
                        <Text size="sm" fw={600}>
                          {session.device}
                        </Text>
                        {session.current && (
                          <Badge size="xs" color="teal">
                            {t('account.thisDevice')}
                          </Badge>
                        )}
                      </Group>
                      <Text size="xs" c="dimmed">
                        {session.browser} · {session.ip}
                      </Text>
                    </Stack>
                  </Group>
                </Table.Td>
                <Table.Td>
                  <Group gap={4} wrap="nowrap">
                    <IconMapPin size={13} />
                    <Text size="xs">{session.location}</Text>
                  </Group>
                </Table.Td>
                <Table.Td>
                  <Text size="xs" c="dimmed">
                    {formatRelative(session.lastActiveAt)}
                  </Text>
                </Table.Td>
                <Table.Td>
                  {!session.current && (
                    <Button
                      variant="subtle"
                      size="compact-xs"
                      color="red"
                      onClick={() => setRevokeId(session.id)}
                    >
                      {t('common.delete')}
                    </Button>
                  )}
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>

      <Card withBorder radius="lg" p="lg" style={{ borderColor: 'var(--mantine-color-red-4)' }}>
        <Title order={3} fz={18} c="red">
          {t('account.dangerZone')}
        </Title>
        <Text size="sm" c="dimmed" mt={4}>
          {t('account.dangerText')}
        </Text>
        <Group mt="md">
          <Button variant="default" leftSection={<IconDownload size={15} />} onClick={exportData}>
            {t('account.exportData')}
          </Button>
          <Button
            variant="light"
            color="red"
            leftSection={<IconTrash size={15} />}
            onClick={() => setDeleteOpened(true)}
          >
            {t('account.deleteAccount')}
          </Button>
        </Group>
      </Card>

      <ConfirmModal
        opened={Boolean(revokeId)}
        onClose={() => setRevokeId(null)}
        onConfirm={() => revokeMutation.mutate()}
        loading={revokeMutation.isPending}
        title={t('account.revokeTitle')}
        description={t('account.revokeText')}
        confirmLabel={t('common.delete')}
      />
      <ConfirmModal
        opened={logoutAllOpened}
        onClose={() => setLogoutAllOpened(false)}
        onConfirm={() => logoutAllMutation.mutate()}
        loading={logoutAllMutation.isPending}
        title={t('account.logoutAllTitle')}
        description={t('account.logoutAllText')}
        confirmLabel={t('account.logoutAll')}
      />
      <ConfirmModal
        opened={deleteOpened}
        onClose={() => setDeleteOpened(false)}
        onConfirm={() => deleteMutation.mutate()}
        loading={deleteMutation.isPending}
        title={t('account.deleteTitle')}
        description={t('account.deleteAccountText')}
        confirmLabel={t('account.deleteAccount')}
        requireText={authUser?.email ?? user.email}
      />
    </Stack>
  )
}
