import {
  Alert,
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
import { IconBrandDiscord, IconExternalLink, IconRefresh } from '@tabler/icons-react'
import { useAvailableGuilds, useBot, useDiscordBotGuilds } from '../../shared/api/hooks'
import type { Guild } from '../../shared/api/types'
import { BotAvatar } from '../../shared/components/bits'
import { PageHeader } from '../../shared/components/bits'
import { EmptyState, LoadingState } from '../../shared/components/states'

export default function BotGuildsPage() {
  const { t } = useTranslation()
  const { botId } = useParams()
  const { data: bot } = useBot(botId)
  const available = useAvailableGuilds()
  const membership = useDiscordBotGuilds(botId)

  if (!bot) return <LoadingState minHeight={280} />

  const installed = membership.data ?? bot.guilds.filter((guild) => guild.botAdded)
  const servers = new Map<string, Pick<Guild, 'id' | 'name' | 'iconColor' | 'iconUrl' | 'canManage'> & {
    botAdded: boolean
  }>()

  for (const guild of available.data ?? []) {
    if (guild.owner || guild.canManage) {
      servers.set(guild.id, { ...guild, canManage: true, botAdded: false })
    }
  }
  for (const guild of installed) {
    const existing = servers.get(guild.id)
    servers.set(guild.id, {
      id: guild.id,
      name: guild.name,
      iconColor: existing?.iconColor ?? '#5865f2',
      iconUrl: guild.iconUrl === undefined ? existing?.iconUrl : guild.iconUrl,
      canManage: Boolean(existing),
      botAdded: true,
    })
  }

  const inviteTo = (guildId: string) => {
    if (!bot.inviteUrl) return ''
    const url = new URL(bot.inviteUrl)
    url.searchParams.set('guild_id', guildId)
    url.searchParams.set('disable_guild_select', 'true')
    return url.toString()
  }

  return (
    <Stack gap="lg">
      <PageHeader
        title={t('bot.guildsTitle')}
        description={t('bot.guildsSubtitle')}
        actions={
          <Group>
            <Button
              variant="default"
              leftSection={<IconRefresh size={16} />}
              loading={available.isFetching || membership.isFetching}
              onClick={() => {
                void available.refetch()
                void membership.refetch()
              }}
            >
              {t('common.refresh')}
            </Button>
            {bot.inviteUrl && (
              <Button
                component="a"
                href={bot.inviteUrl}
                target="_blank"
                rel="noopener noreferrer"
                leftSection={<IconBrandDiscord size={17} />}
              >
                {t('bot.invite')}
              </Button>
            )}
          </Group>
        }
      />

      {(available.isError || membership.isError) && (
        <Alert color="yellow">{t('bot.guildsLoadError')}</Alert>
      )}
      {available.isSuccess && available.data.length === 0 && servers.size > 0 && (
        <Alert color="blue">{t('bot.guildsEmptyHint')}</Alert>
      )}
      {available.isPending || membership.isPending ? (
        <LoadingState minHeight={180} />
      ) : servers.size === 0 ? (
        <EmptyState
          icon="server"
          title={t('bot.noManageableGuildsTitle')}
          description={t('bot.guildsEmptyHint')}
        />
      ) : (
        <SimpleGrid cols={{ base: 1, md: 2, xl: 3 }} spacing="md">
          {[...servers.values()].map((guild) => (
            <Card key={guild.id} withBorder radius="lg" p="lg" className="bf-hover-lift">
              <Group justify="space-between" align="flex-start" wrap="nowrap">
                <Group gap="sm" wrap="nowrap">
                  <BotAvatar
                    name={guild.name}
                    color={guild.iconColor}
                    src={guild.iconUrl ?? undefined}
                    size={48}
                    radius={14}
                  />
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
                  {guild.botAdded
                    ? t('bot.guildAdded')
                    : t(membership.isError ? 'bot.guildStatusUnknown' : 'bot.guildMissing')}
                </Badge>
              </Group>

              <Group justify="flex-end" mt="md">
                {guild.botAdded ? (
                  <Button
                    component="a"
                    href={`https://discord.com/channels/${guild.id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    variant="light"
                    size="compact-sm"
                    leftSection={<IconExternalLink size={14} />}
                  >
                    {t('common.open')}
                  </Button>
                ) : guild.canManage && bot.inviteUrl && (
                  <Button
                    component="a"
                    href={inviteTo(guild.id)}
                    target="_blank"
                    rel="noopener noreferrer"
                    variant="light"
                    size="compact-sm"
                    leftSection={<IconBrandDiscord size={14} />}
                  >
                    {t('bot.inviteBot')}
                  </Button>
                )}
              </Group>
            </Card>
          ))}
        </SimpleGrid>
      )}
    </Stack>
  )
}
