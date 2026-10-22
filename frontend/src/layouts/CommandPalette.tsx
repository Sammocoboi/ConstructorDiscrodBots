import { useEffect, useMemo, useRef, useState } from 'react'
import { Box, Group, Kbd, Modal, ScrollArea, Stack, Text, TextInput, UnstyledButton } from '@mantine/core'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { IconCornerDownLeft, IconPlus, IconSearch } from '@tabler/icons-react'
import { useBots } from '../shared/api/hooks'
import { AppIcon } from '../shared/components/icons'
import { BotAvatar } from '../shared/components/bits'

interface PaletteItem {
  id: string
  label: string
  description?: string
  icon?: string
  to: string
  section: string
  color?: string
}

export function CommandPalette({
  opened,
  onClose,
}: {
  opened: boolean
  onClose: () => void
}) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { data: bots } = useBots()
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (opened) {
      setQuery('')
      setActive(0)
      window.setTimeout(() => inputRef.current?.focus(), 60)
    }
  }, [opened])

  const items = useMemo<PaletteItem[]>(() => {
    const navigation: PaletteItem[] = [
      { id: 'nav-dashboard', label: t('nav.dashboard'), icon: 'dashboard', to: '/app', section: t('nav.overview') },
      { id: 'nav-templates', label: t('nav.catalog'), icon: 'templates', to: '/app/templates', section: t('nav.templates') },
      { id: 'nav-my-templates', label: t('nav.myTemplates'), icon: 'template', to: '/app/templates/mine', section: t('nav.templates') },
      { id: 'nav-billing', label: t('nav.billing'), icon: 'card', to: '/app/billing', section: t('nav.account') },
      { id: 'nav-account', label: t('nav.account'), icon: 'settings', to: '/app/account', section: t('nav.account') },
      { id: 'nav-help', label: t('nav.help'), icon: 'help', to: '/app/help', section: t('nav.account') },
      { id: 'nav-notifications', label: t('nav.notifications'), icon: 'bell', to: '/app/notifications', section: t('nav.account') },
    ]
    const actions: PaletteItem[] = [
      { id: 'action-new-bot', label: t('nav.newBot'), icon: 'plus', to: '/app/bots/new', section: t('common.actions') },
    ]
    const botItems: PaletteItem[] = (bots ?? []).map((bot) => ({
      id: `bot-${bot.id}`,
      label: bot.name,
      description: bot.description,
      to: `/app/bots/${bot.id}/overview`,
      section: t('nav.bots'),
      color: bot.avatarColor,
    }))
    return [...actions, ...botItems, ...navigation]
  }, [bots, t])

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    if (!normalized) return items
    return items.filter(
      (item) =>
        item.label.toLowerCase().includes(normalized) ||
        item.description?.toLowerCase().includes(normalized) ||
        item.section.toLowerCase().includes(normalized),
    )
  }, [items, query])

  useEffect(() => {
    setActive(0)
  }, [query])

  const grouped = useMemo(() => {
    const map = new Map<string, PaletteItem[]>()
    filtered.forEach((item) => {
      const list = map.get(item.section) ?? []
      list.push(item)
      map.set(item.section, list)
    })
    return [...map.entries()]
  }, [filtered])

  const flat = grouped.flatMap(([, group]) => group)

  const run = (item: PaletteItem | undefined) => {
    if (!item) return
    navigate(item.to)
    onClose()
  }

  return (
    <Modal opened={opened} onClose={onClose} withCloseButton={false} size="lg" padding={0} radius="lg">
      <Box p="sm" style={{ borderBottom: '1px solid var(--mantine-color-default-border)' }}>
        <TextInput
          ref={inputRef}
          value={query}
          onChange={(event) => setQuery(event.currentTarget.value)}
          placeholder={t('common.search')}
          leftSection={<IconSearch size={17} />}
          variant="unstyled"
          size="md"
          onKeyDown={(event) => {
            if (event.key === 'ArrowDown') {
              event.preventDefault()
              setActive((current) => Math.min(current + 1, flat.length - 1))
            }
            if (event.key === 'ArrowUp') {
              event.preventDefault()
              setActive((current) => Math.max(current - 1, 0))
            }
            if (event.key === 'Enter') {
              event.preventDefault()
              run(flat[active])
            }
          }}
        />
      </Box>
      <ScrollArea.Autosize mah={420}>
        <Box p="xs">
          {grouped.length === 0 && (
            <Stack align="center" gap={4} py="lg">
              <Text c="dimmed" size="sm">
                {t('common.notFound')}
              </Text>
            </Stack>
          )}
          {grouped.map(([section, group]) => (
            <Box key={section} mb="xs">
              <Text size="10px" fw={800} tt="uppercase" c="dimmed" px="sm" py={6} style={{ letterSpacing: '0.08em' }}>
                {section}
              </Text>
              {group.map((item) => {
                const index = flat.indexOf(item)
                return (
                  <UnstyledButton
                    key={item.id}
                    w="100%"
                    px="sm"
                    py={8}
                    onClick={() => run(item)}
                    onMouseEnter={() => setActive(index)}
                    style={{
                      borderRadius: 8,
                      background:
                        index === active ? 'var(--mantine-color-default-hover)' : undefined,
                    }}
                  >
                    <Group gap="sm" wrap="nowrap">
                      {item.color ? (
                        <BotAvatar name={item.label} color={item.color} size={28} radius={8} />
                      ) : (
                        <Box w={28} style={{ display: 'grid', placeItems: 'center' }}>
                          {item.icon ? (
                            <AppIcon name={item.icon} size={18} />
                          ) : (
                            <IconPlus size={16} />
                          )}
                        </Box>
                      )}
                      <Box style={{ flex: 1, minWidth: 0 }}>
                        <Text size="sm" fw={600} truncate>
                          {item.label}
                        </Text>
                        {item.description && (
                          <Text size="xs" c="dimmed" truncate>
                            {item.description}
                          </Text>
                        )}
                      </Box>
                      {index === active && (
                        <Group gap={4} wrap="nowrap">
                          <Kbd size="xs">
                            <IconCornerDownLeft size={11} />
                          </Kbd>
                        </Group>
                      )}
                    </Group>
                  </UnstyledButton>
                )
              })}
            </Box>
          ))}
        </Box>
      </ScrollArea.Autosize>
    </Modal>
  )
}
