import {
  Badge,
  Button,
  Card,
  Group,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'
import { IconBrandDiscord, IconExternalLink } from '@tabler/icons-react'
import { useBot } from '../../shared/api/hooks'
import { BotAvatar } from '../../shared/components/bits'
import { PageHeader } from '../../shared/components/bits'
import { EmptyState, LoadingState } from '../../shared/components/states'

export default function BotGuildsPage() {
  const { t } = useTranslation()
  const { botId } = useParams()
  const { data: bot } = useBot(botId)

  if (!bot) return <LoadingState minHeight={280} />

  const openInvite = (url: string) => {
    window.open(url, '_blank', 'noopener,noreferrer')
  }

  return (
    <Stack gap="lg">
      <PageHeader
        title={t('bot.guildsTitle')}
        description={t('bot.guildsSubtitle')}
        actions={
          <Button
            leftSection={<IconBrandDiscord size={17} />}
            disabled={!bot.inviteUrl}
            onClick={() => openInvite(bot.inviteUrl)}
          >
            {t('bot.invite')}
          </Button>
        }
      />

      {bot.guilds.length === 0 ? (
        <EmptyState
          icon="server"
          title={t('bot.guildsTitle')}
          description={t('bot.guildsSubtitle')}
          action={
            <Button
              leftSection={<IconBrandDiscord size={16} />}
              disabled={!bot.inviteUrl}
              onClick={() => openInvite(bot.inviteUrl)}
            >
              {t('bot.inviteBot')}
            </Button>
          }
        />
      ) : (
        <SimpleGrid cols={{ base: 1, md: 2, xl: 3 }} spacing="md">
          {bot.guilds.map((guild) => (
            <Card key={guild.id} withBorder radius="lg" p="lg" className="bf-hover-lift">
              <Group justify="space-between" align="flex-start" wrap="nowrap">
                <Group gap="sm" wrap="nowrap">
                  <BotAvatar name={guild.name} color={guild.iconColor} size={48} radius={14} />
                  <Stack gap={2}>
                    <Title order={3} fz={16} lineClamp={1}>
                      {guild.name}
                    </Title>
                    <Text size="xs" c="dimmed" ff="monospace">
                      {guild.id}
                    </Text>
                  </Stack>
                </Group>
                <Badge color={guild.botAdded ? 'teal' : 'gray'} variant="light" size="sm">
                  {guild.botAdded ? t('bot.guildAdded') : t('bot.guildMissing')}
                </Badge>
              </Group>

              <Group justify="flex-end" mt="md">
                <Button
                  variant="light"
                  size="compact-sm"
                  leftSection={<IconExternalLink size={14} />}
                  disabled={!bot.inviteUrl}
                  onClick={() => openInvite(bot.inviteUrl)}
                >
                  {t('common.open')}
                </Button>
              </Group>
            </Card>
          ))}
        </SimpleGrid>
      )}
    </Stack>
  )
}
