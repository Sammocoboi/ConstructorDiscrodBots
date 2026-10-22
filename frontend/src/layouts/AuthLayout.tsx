import { Box, Button, Container, Group, Stack, Text, ThemeIcon, Title } from '@mantine/core'
import { IconArrowLeft, IconCheck, IconRobot } from '@tabler/icons-react'
import { Outlet, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Logo } from '../shared/components/Logo'
import { ThemeToggle } from '../shared/components/ThemeToggle'

const bulletsRu = [
  'Готовые модули и команды',
  'Визуальные сценарии без кода',
  'Безопасное хранение токена',
]
const bulletsEn = ['Ready modules and commands', 'Visual flows without code', 'Secure token storage']

export function AuthLayout() {
  const { t, i18n } = useTranslation()
  const bullets = i18n.language.startsWith('en') ? bulletsEn : bulletsRu
  return (
    <div className="bf-auth-shell">
      <aside className="bf-auth-art">
        <Group gap="sm">
          <ThemeIcon size={42} radius="md" variant="white" color="brand">
            <IconRobot size={25} />
          </ThemeIcon>
          <Box>
            <Text fw={800} size="lg" lh={1.1}>
              {t('common.appName')}
            </Text>
            <Text size="xs" opacity={0.7}>
              {t('common.tagline')}
            </Text>
          </Box>
        </Group>
        <Stack gap="md" maw={480}>
          <Title order={1} fz={{ base: 32, sm: 44 }} lh={1.08}>
            {i18n.language.startsWith('en')
              ? 'Your Discord bot, assembled in minutes.'
              : 'Ваш Discord-бот, собранный за несколько минут.'}
          </Title>
          <Text opacity={0.78} size="md" style={{ lineHeight: 1.6 }}>
            {i18n.language.startsWith('en')
              ? 'Connect a token, pick a template and launch modules, commands and visual flows from one dashboard.'
              : 'Подключите токен, выберите шаблон и запускайте модули, команды и визуальные сценарии из одного кабинета.'}
          </Text>
          <Stack gap="sm" mt="md">
            {bullets.map((bullet) => (
              <Group key={bullet} gap="sm">
                <ThemeIcon size={22} radius="xl" color="white" variant="white" c="brand.5">
                  <IconCheck size={13} />
                </ThemeIcon>
                <Text size="sm">{bullet}</Text>
              </Group>
            ))}
          </Stack>
        </Stack>
        <Group gap="sm" opacity={0.7}>
          <Text size="xs">Discord OAuth2 · JWT · AES-256-GCM</Text>
        </Group>
      </aside>

      <Box
        pos="relative"
        style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}
      >
        <Group justify="space-between" p="md">
          <Button
            component={Link}
            to="/"
            variant="subtle"
            color="gray"
            leftSection={<IconArrowLeft size={16} />}
          >
            {t('common.back')}
          </Button>
          <ThemeToggle />
        </Group>
        <Container size={460} w="100%" style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <Box pb="xl">
            <Group mb="xl" visibleFrom="md">
              <Logo />
            </Group>
            <Outlet />
          </Box>
        </Container>
      </Box>
    </div>
  )
}
