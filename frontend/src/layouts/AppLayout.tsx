import { useEffect } from 'react'
import {
  ActionIcon,
  AppShell,
  Avatar,
  Badge,
  Box,
  Burger,
  Button,
  Divider,
  Group,
  Indicator,
  Menu,
  NavLink,
  ScrollArea,
  Stack,
  Text,
  Tooltip,
  UnstyledButton,
  Kbd,
} from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'
import {
  IconBell,
  IconChevronDown,
  IconCreditCard,
  IconHelpCircle,
  IconLanguage,
  IconLogout,
  IconSearch,
  IconSettings,
  IconUser,
} from '@tabler/icons-react'
import { Logo } from '../shared/components/Logo'
import { ThemeToggle } from '../shared/components/ThemeToggle'
import { AppIcon } from '../shared/components/icons'
import { BotAvatar } from '../shared/components/bits'
import { useBots, useNotifications } from '../shared/api/hooks'
import { api } from '../shared/api'
import { useAuthStore } from '../shared/stores/authStore'
import { setLanguage } from '../shared/i18n'
import { initials } from '../shared/lib/format'
import { botStatusMeta } from '../shared/lib/status'
import { CommandPalette } from './CommandPalette'

export function AppLayout() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const [navOpened, navHandlers] = useDisclosure(false)
  const [paletteOpened, paletteHandlers] = useDisclosure(false)
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)
  const queryClient = useQueryClient()
  const { data: bots } = useBots()
  const { data: notifications } = useNotifications()
  const unread = notifications?.filter((item) => !item.read).length ?? 0

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        paletteHandlers.toggle()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [paletteHandlers])

  const handleLogout = async () => {
    try {
      await api.auth.logout()
    } finally {
      logout()
      queryClient.clear()
      navigate('/login', { replace: true })
    }
  }

  const isActive = (path: string, exact = false) =>
    exact ? location.pathname === path : location.pathname.startsWith(path)

  const mainNav = [
    { to: '/app', label: t('nav.dashboard'), icon: 'dashboard', exact: true },
    { to: '/app/templates', label: t('nav.catalog'), icon: 'templates' },
    { to: '/app/templates/mine', label: t('nav.myTemplates'), icon: 'template' },
  ]

  const accountNav = [
    { to: '/app/billing', label: t('nav.billing'), icon: 'card' },
    { to: '/app/account', label: t('nav.account'), icon: 'settings' },
    { to: '/app/help', label: t('nav.help'), icon: 'help' },
  ]

  const planLabel = t(`billing.plan${(user?.plan ?? 'free').charAt(0).toUpperCase()}${(user?.plan ?? 'free').slice(1)}`)

  return (
    <AppShell
      header={{ height: 64 }}
      navbar={{
        width: 276,
        breakpoint: 'md',
        collapsed: { mobile: !navOpened },
      }}
      padding={0}
    >
      <AppShell.Header>
        <Group h="100%" px={{ base: 'sm', md: 'lg' }} justify="space-between" wrap="nowrap">
          <Group gap="sm" wrap="nowrap">
            <Burger opened={navOpened} onClick={navHandlers.toggle} hiddenFrom="md" size="sm" />
            <Box visibleFrom="md">
              <Logo />
            </Box>
            <Box hiddenFrom="md">
              <Logo compact />
            </Box>
          </Group>

          <Group gap={4} wrap="nowrap">
            <UnstyledButton
              onClick={paletteHandlers.open}
              visibleFrom="sm"
              px="sm"
              py={7}
              style={{
                borderRadius: 10,
                border: '1px solid var(--mantine-color-default-border)',
                background: 'var(--mantine-color-default)',
                minWidth: 220,
              }}
            >
              <Group gap="xs" justify="space-between">
                <Group gap="xs">
                  <IconSearch size={15} />
                  <Text size="sm" c="dimmed">
                    {t('common.search')}
                  </Text>
                </Group>
                <Kbd size="xs">⌘K</Kbd>
              </Group>
            </UnstyledButton>
            <ActionIcon variant="subtle" color="gray" size="lg" hiddenFrom="sm" onClick={paletteHandlers.open}>
              <IconSearch size={19} />
            </ActionIcon>

            <Tooltip label={t('nav.notifications')}>
              <Indicator
                disabled={unread === 0}
                label={unread > 9 ? '9+' : unread}
                size={16}
                color="red"
                offset={5}
              >
                <ActionIcon
                  variant="subtle"
                  color="gray"
                  size="lg"
                  onClick={() => navigate('/app/notifications')}
                  aria-label={t('nav.notifications')}
                >
                  <IconBell size={19} stroke={1.8} />
                </ActionIcon>
              </Indicator>
            </Tooltip>

            <ThemeToggle />

            <Menu position="bottom-end" width={180} shadow="md">
              <Menu.Target>
                <Tooltip label={t('account.language')}>
                  <ActionIcon variant="subtle" color="gray" size="lg" visibleFrom="sm">
                    <IconLanguage size={19} stroke={1.8} />
                  </ActionIcon>
                </Tooltip>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Item onClick={() => setLanguage('ru')} rightSection={i18n.language.startsWith('ru') ? '✓' : undefined}>
                  Русский
                </Menu.Item>
                <Menu.Item onClick={() => setLanguage('en')} rightSection={i18n.language.startsWith('en') ? '✓' : undefined}>
                  English
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>

            <Menu position="bottom-end" width={240} shadow="md">
              <Menu.Target>
                <UnstyledButton>
                  <Group gap="xs" wrap="nowrap">
                    <Avatar color="brand" radius="xl" size={34}>
                      {initials(user?.username ?? 'BF')}
                    </Avatar>
                    <Box visibleFrom="sm">
                      <Text size="sm" fw={600} lh={1.1}>
                        {user?.username ?? t('account.profile')}
                      </Text>
                      <Text size="xs" c="dimmed" lh={1.2}>
                        {user?.email}
                      </Text>
                    </Box>
                    <Box visibleFrom="sm">
                      <IconChevronDown size={14} />
                    </Box>
                  </Group>
                </UnstyledButton>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Label>{planLabel}</Menu.Label>
                <Menu.Item leftSection={<IconUser size={15} />} component={Link} to="/app/account">
                  {t('nav.profile')}
                </Menu.Item>
                <Menu.Item leftSection={<IconSettings size={15} />} component={Link} to="/app/account">
                  {t('common.settings')}
                </Menu.Item>
                <Menu.Item leftSection={<IconCreditCard size={15} />} component={Link} to="/app/billing">
                  {t('nav.billing')}
                </Menu.Item>
                <Menu.Item leftSection={<IconHelpCircle size={15} />} component={Link} to="/app/help">
                  {t('nav.help')}
                </Menu.Item>
                <Menu.Divider />
                <Menu.Item leftSection={<IconLogout size={15} />} color="red" onClick={handleLogout}>
                  {t('nav.logout')}
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="sm">
        <AppShell.Section>
          <Button
            component={Link}
            to="/app/bots/new"
            fullWidth
            leftSection={<AppIcon name="plus" size={16} />}
            onClick={navHandlers.close}
          >
            {t('nav.newBot')}
          </Button>
        </AppShell.Section>

        <AppShell.Section grow component={ScrollArea} mt="md" type="hover">
          <Stack gap={2}>
            <Text size="10px" fw={800} c="dimmed" tt="uppercase" px="sm" py={6} style={{ letterSpacing: '0.08em' }}>
              {t('nav.bots')}
            </Text>
            {bots?.map((bot) => {
              const meta = botStatusMeta[bot.status]
              return (
                <NavLink
                  key={bot.id}
                  component={Link}
                  to={`/app/bots/${bot.id}/overview`}
                  active={location.pathname.startsWith(`/app/bots/${bot.id}`)}
                  onClick={navHandlers.close}
                  leftSection={<BotAvatar name={bot.name} color={bot.avatarColor} size={24} radius={7} />}
                  label={bot.name}
                  rightSection={
                    <Box
                      w={8}
                      h={8}
                      style={{ borderRadius: '50%', background: meta.dot, flex: '0 0 auto' }}
                    />
                  }
                  styles={{ label: { fontWeight: 600 } }}
                />
              )
            })}
            {!bots?.length && (
              <Text size="xs" c="dimmed" px="sm" py="xs">
                {t('dashboard.emptyTitle')}
              </Text>
            )}

            <Divider my="sm" />
            <Text size="10px" fw={800} c="dimmed" tt="uppercase" px="sm" py={6} style={{ letterSpacing: '0.08em' }}>
              {t('nav.dashboard')}
            </Text>
            {mainNav.map((item) => (
              <NavLink
                key={item.to}
                component={Link}
                to={item.to}
                active={isActive(item.to, item.exact)}
                onClick={navHandlers.close}
                leftSection={<AppIcon name={item.icon} size={18} />}
                label={item.label}
              />
            ))}
            <Divider my="sm" />
            <Text size="10px" fw={800} c="dimmed" tt="uppercase" px="sm" py={6} style={{ letterSpacing: '0.08em' }}>
              {t('nav.account')}
            </Text>
            {accountNav.map((item) => (
              <NavLink
                key={item.to}
                component={Link}
                to={item.to}
                active={isActive(item.to)}
                onClick={navHandlers.close}
                leftSection={<AppIcon name={item.icon} size={18} />}
                label={item.label}
              />
            ))}
            <NavLink
              component={Link}
              to="/app/notifications"
              active={isActive('/app/notifications')}
              onClick={navHandlers.close}
              leftSection={<AppIcon name="bell" size={18} />}
              label={t('nav.notifications')}
              rightSection={
                unread > 0 ? (
                  <Badge size="sm" variant="filled" color="red" circle>
                    {unread}
                  </Badge>
                ) : undefined
              }
            />
          </Stack>
        </AppShell.Section>

        <AppShell.Section>
          <Box
            mt="sm"
            p="sm"
            style={{
              borderRadius: 14,
              border: '1px solid var(--mantine-color-default-border)',
              background: 'var(--mantine-color-default)',
            }}
          >
            <Group justify="space-between" mb={4}>
              <Text size="xs" fw={700}>
                {planLabel}
              </Text>
              <Badge size="xs" variant="light">
                {t('billing.currentPlan')}
              </Badge>
            </Group>
            <Text size="xs" c="dimmed" mb="xs">
              {t('billing.usage')}
            </Text>
            <Button
              component={Link}
              to="/app/billing"
              variant="light"
              size="xs"
              fullWidth
              onClick={navHandlers.close}
            >
              {t('billing.upgrade', { plan: 'Pro' })}
            </Button>
          </Box>
        </AppShell.Section>
      </AppShell.Navbar>

      <AppShell.Main>
        <Box p={{ base: 'md', md: 'xl' }} mih="calc(100vh - 64px)">
          <Outlet />
        </Box>
      </AppShell.Main>

      <CommandPalette opened={paletteOpened} onClose={paletteHandlers.close} />
    </AppShell>
  )
}
