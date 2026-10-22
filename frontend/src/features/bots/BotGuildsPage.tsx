import { useMemo, useState } from 'react'
import {
  Badge,
  Button,
  Card,
  Group,
  Modal,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'
import {
  IconBrandDiscord,
  IconCopy,
  IconExternalLink,
  IconShield,
} from '@tabler/icons-react'
import { notifications } from '@mantine/notifications'
import { api } from '../../shared/api'
import {
  qk,
  useAvailableGuilds,
  useBot,
  useToastMutation,
} from '../../shared/api/hooks'
import { BotAvatar } from '../../shared/components/bits'
import { PageHeader } from '../../shared/components/bits'
import { EmptyState, LoadingState } from '../../shared/components/states'
import { formatNumber } from '../../shared/lib/format'

export default function BotGuildsPage() {
  const { t } = useTranslation()
  const { botId } = useParams()
  const { data: bot } = useBot(botId)
  const available = useAvailableGuilds()
  const [copyOpened, setCopyOpened] = useState(false)
  const [source, setSource] = useState<string | null>(null)
  const [target, setTarget] = useState<string | null>(null)

  const copyMutation = useToastMutation({
    mutationFn: () =>
      api.bots.copySettings(botId as string, {
        fromGuildId: source as string,
        toGuildId: target as string,
      }),
    successMessage: t('bot.settingsCopied'),
    invalidateKeys: [qk.botGuilds(botId ?? ''), qk.botModules(botId ?? ''), qk.bot(botId ?? '')],
    onSuccess: () => {
      setCopyOpened(false)
      setSource(null)
      setTarget(null)
    },
  })

  const missingGuilds = useMemo(() => {
    if (!bot || !available.data) return []
    const added = new Set(bot.guilds.map((guild) => guild.id))
    return available.data.filter((guild) => !added.has(guild.id))
  }, [available.data, bot])

  if (!bot) return <LoadingState minHeight={280} />

  const guildOptions =
    bot.guilds.map((guild) => ({ value: guild.id, label: guild.name })) ?? []

  const openInvite = (url: string) => {
    window.open(url, '_blank', 'noopener,noreferrer')
  }

  const copyInvite = async (url: string) => {
    try {
      await navigator.clipboard.writeText(url)
      notifications.show({ color: 'teal', message: t('bot.inviteCopied') })
    } catch {
      notifications.show({ color: 'red', message: t('common.error') })
    }
  }

  return (
    <Stack gap="lg">
      <PageHeader
        title={t('bot.guildsTitle')}
        description={t('bot.guildsSubtitle')}
        actions={
          <>
            <Button
              variant="default"
              leftSection={<IconCopy size={16} />}
              disabled={bot.guilds.length < 2}
              onClick={() => {
                setSource(null)
                setTarget(null)
                setCopyOpened(true)
              }}
            >
              {t('bot.copySettings')}
            </Button>
            <Button
              leftSection={<IconBrandDiscord size={17} />}
              onClick={() => openInvite(bot.inviteUrl)}
            >
              {t('bot.invite')}
            </Button>
          </>
        }
      />

      <SimpleGrid cols={{ base: 1, md: 2, xl: 3 }} spacing="md">
        {bot.guilds.map((guild) => (
          <Card key={guild.id} withBorder radius="lg" p="lg" className="bf-hover-lift">
            <Group justify="space-between" align="flex-start" wrap="nowrap" mb="sm">
              <Group gap="sm" wrap="nowrap">
                <BotAvatar name={guild.name} color={guild.iconColor} size={48} radius={14} />
                <Stack gap={2}>
                  <Title order={3} fz={16} lineClamp={1}>
                    {guild.name}
                  </Title>
                  <Text size="xs" c="dimmed">
                    {formatNumber(guild.memberCount)} участников
                  </Text>
                </Stack>
              </Group>
              <Badge color={guild.botAdded ? 'teal' : 'gray'} variant="light" size="sm">
                {guild.botAdded ? t('bot.guildAdded') : t('bot.guildMissing')}
              </Badge>
            </Group>

            <Group gap={6} mb="md">
              <Badge variant="light" color="gray" size="sm">
                {guild.channels.length} каналов
              </Badge>
              <Badge variant="light" color="gray" size="sm">
                {guild.roles.length} ролей
              </Badge>
              {guild.owner && (
                <Badge variant="light" color="brand" size="sm">
                  Владелец
                </Badge>
              )}
              {!guild.canManage && (
                <Badge
                  variant="light"
                  color="orange"
                  size="sm"
                  leftSection={<IconShield size={11} />}
                >
                  Нет прав
                </Badge>
              )}
            </Group>

            <Group justify="space-between">
              <Text size="xs" c="dimmed">
                {guild.roles[0]?.name ?? '—'}
              </Text>
              <Group gap="xs">
                <Button
                  variant="subtle"
                  size="compact-xs"
                  leftSection={<IconCopy size={13} />}
                  onClick={() => void copyInvite(bot.inviteUrl)}
                >
                  {t('common.copy')}
                </Button>
                <Button
                  variant="light"
                  size="compact-sm"
                  leftSection={<IconExternalLink size={14} />}
                  onClick={() => openInvite(bot.inviteUrl)}
                >
                  {t('common.open')}
                </Button>
              </Group>
            </Group>
          </Card>
        ))}
      </SimpleGrid>

      {missingGuilds.length > 0 && (
        <Stack gap="sm">
          <Title order={3} fz={18}>
            Доступные серверы
          </Title>
          <SimpleGrid cols={{ base: 1, md: 2, xl: 3 }} spacing="md">
            {missingGuilds.map((guild) => (
              <Card key={guild.id} withBorder radius="lg" p="lg">
                <Group justify="space-between" wrap="nowrap" mb="sm">
                  <Group gap="sm" wrap="nowrap">
                    <BotAvatar name={guild.name} color={guild.iconColor} size={44} radius={13} />
                    <Stack gap={2}>
                      <Text fw={600} size="sm">
                        {guild.name}
                      </Text>
                      <Text size="xs" c="dimmed">
                        {formatNumber(guild.memberCount)} участников
                      </Text>
                    </Stack>
                  </Group>
                  <Badge variant="light" color="gray" size="sm">
                    {t('bot.guildMissing')}
                  </Badge>
                </Group>
                <Button
                  fullWidth
                  variant="light"
                  leftSection={<IconBrandDiscord size={16} />}
                  onClick={() => openInvite(bot.inviteUrl)}
                >
                  {t('bot.inviteBot')}
                </Button>
              </Card>
            ))}
          </SimpleGrid>
        </Stack>
      )}

      {bot.guilds.length === 0 && (
        <EmptyState
          icon="server"
          title={t('bot.guildsTitle')}
          description={t('bot.guildsSubtitle')}
          action={
            <Button
              leftSection={<IconBrandDiscord size={16} />}
              onClick={() => openInvite(bot.inviteUrl)}
            >
              {t('bot.inviteBot')}
            </Button>
          }
        />
      )}

      <Modal
        opened={copyOpened}
        onClose={() => setCopyOpened(false)}
        title={t('bot.copySettings')}
      >
        <Stack>
          <Text size="sm" c="dimmed">
            {t('bot.copySettingsText')}
          </Text>
          <Select
            label="Откуда"
            data={guildOptions}
            value={source}
            onChange={setSource}
            placeholder={t('bot.selectGuild')}
          />
          <Select
            label="Куда"
            data={guildOptions.filter((option) => option.value !== source)}
            value={target}
            onChange={setTarget}
            placeholder={t('bot.selectGuild')}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setCopyOpened(false)}>
              {t('common.cancel')}
            </Button>
            <Button
              disabled={!source || !target || source === target}
              loading={copyMutation.isPending}
              onClick={() => copyMutation.mutate()}
            >
              {t('common.apply')}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  )
}
