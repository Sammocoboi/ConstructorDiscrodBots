import { useEffect, useState } from 'react'
import {
  Avatar,
  Badge,
  Button,
  Card,
  Group,
  Stack,
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

export default function AccountPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const account = useAccount()
  const updateUser = useAuthStore((state) => state.updateUser)
  const authUser = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)

  const [name, setName] = useState('')
  const [revokeId, setRevokeId] = useState<string | null>(null)
  const [logoutAllOpened, setLogoutAllOpened] = useState(false)
  const [deleteOpened, setDeleteOpened] = useState(false)

  useEffect(() => {
    if (account.data) setName(account.data.user.username)
  }, [account.data])

  const saveProfileMutation = useToastMutation({
    mutationFn: () => api.account.updateProfile({ username: name }),
    successMessage: t('account.profileSaved'),
    invalidateKeys: [qk.account],
    onSuccess: (user) => updateUser({ username: user.username, email: user.email }),
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
            <Avatar color="brand" size={84} radius="xl" src={user.avatarUrl}>
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
              value={user.email}
              readOnly
              description={
                user.isEmailVerified
                  ? t('account.emailVerified')
                  : t('account.emailNotVerified')
              }
            />
            <Group justify="flex-end" mt="xs">
              <Button
                loading={saveProfileMutation.isPending}
                disabled={!name.trim() || name === user.username}
                onClick={() => saveProfileMutation.mutate()}
              >
                {t('common.save')}
              </Button>
            </Group>
          </Stack>
        </Group>
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
