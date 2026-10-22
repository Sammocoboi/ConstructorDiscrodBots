import { Button, Center, Stack, Text, ThemeIcon, Title } from '@mantine/core'
import { IconArrowLeft, IconRobot } from '@tabler/icons-react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

export default function NotFoundPage() {
  const { t } = useTranslation()
  return (
    <Center mih="100vh" p="md">
      <Stack align="center" gap="md" maw={480} ta="center">
        <ThemeIcon size={84} radius="xl" variant="light" color="brand">
          <IconRobot size={42} />
        </ThemeIcon>
        <Title order={1} fz={64} lh={1} className="bf-gradient-text">
          404
        </Title>
        <Title order={3}>{t('common.notFound')}</Title>
        <Text c="dimmed">Такой страницы нет или она была перемещена.</Text>
        <Button component={Link} to="/app" leftSection={<IconArrowLeft size={16} />}>
          {t('bot.backToDashboard')}
        </Button>
      </Stack>
    </Center>
  )
}
