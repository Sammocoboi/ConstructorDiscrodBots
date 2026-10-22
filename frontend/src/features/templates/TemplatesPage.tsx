import { useMemo, useState } from 'react'
import {
  Badge,
  Button,
  Card,
  Group,
  Modal,
  ScrollArea,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  ThemeIcon,
  Title,
} from '@mantine/core'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { IconArrowRight, IconSearch, IconSparkles, IconStar } from '@tabler/icons-react'
import { useModules, useTemplates } from '../../shared/api/hooks'
import type { Template } from '../../shared/api/types'
import { PageHeader } from '../../shared/components/bits'
import { BotAvatar } from '../../shared/components/bits'
import { EmptyState, LoadingState } from '../../shared/components/states'
import {
  templateCategoryLabel,
  templateCategoryOptions,
} from '../../shared/lib/status'
import { formatDate, formatNumber } from '../../shared/lib/format'

export default function TemplatesPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const templates = useTemplates()
  const modules = useModules()
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState<string | null>(null)
  const [plan, setPlan] = useState<string | null>(null)
  const [selected, setSelected] = useState<Template | null>(null)

  const moduleTitle = useMemo(() => {
    const map = new Map((modules.data ?? []).map((module) => [module.id, module.title]))
    return (id: string) => map.get(id) ?? id
  }, [modules.data])

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    return (templates.data ?? []).filter((template) => {
      if (category && template.category !== category) return false
      if (plan && template.minPlan !== plan) return false
      if (!normalized) return true
      return (
        template.name.toLowerCase().includes(normalized) ||
        template.description.toLowerCase().includes(normalized) ||
        template.tags.some((tag) => tag.toLowerCase().includes(normalized))
      )
    })
  }, [category, plan, query, templates.data])

  const applyTemplate = (template?: Template) => {
    if (template) navigate(`/app/bots/new?templateId=${encodeURIComponent(template.id)}`)
    else navigate('/app/bots/new')
  }

  return (
    <Stack gap="lg" maw={1400} mx="auto" w="100%">
      <PageHeader
        title={t('templates.title')}
        description={t('templates.subtitle')}
        actions={
          <>
            <Button component={Link} to="/app/templates/mine" variant="default">
              {t('nav.myTemplates')}
            </Button>
            <Button variant="light" onClick={() => applyTemplate()}>
              {t('nav.newBot')}
            </Button>
          </>
        }
      />

      <Card
        radius="lg"
        p="lg"
        style={{
          border: 'none',
          background: 'linear-gradient(120deg, #343aac, #5865f2 55%, #00a8fc 130%)',
          color: 'white',
        }}
      >
        <Group justify="space-between" wrap="wrap" gap="md">
          <Stack gap={4} maw={620}>
            <Group gap="xs">
              <IconSparkles size={18} />
              <Text size="xs" fw={800} tt="uppercase" style={{ letterSpacing: '0.08em' }}>
                {t('templates.title')}
              </Text>
            </Group>
            <Title order={2} fz={{ base: 22, sm: 28 }}>
              {t('landing.templatesTitle')}
            </Title>
            <Text size="sm" opacity={0.85}>
              {t('landing.templatesSubtitle')}
            </Text>
          </Stack>
          <Button variant="white" color="brand" onClick={() => applyTemplate()}>
            {t('templates.use')}
          </Button>
        </Group>
      </Card>

      <Card withBorder radius="lg" p="md">
        <Group gap="sm" wrap="wrap">
          <TextInput
            placeholder={t('templates.searchPlaceholder')}
            leftSection={<IconSearch size={15} />}
            value={query}
            onChange={(event) => setQuery(event.currentTarget.value)}
            style={{ flex: 1, minWidth: 220 }}
          />
          <Select
            placeholder={t('templates.allCategories')}
            data={templateCategoryOptions}
            value={category}
            onChange={setCategory}
            clearable
            w={{ base: '100%', sm: 220 }}
          />
          <Select
            placeholder={t('billing.currentPlan')}
            data={[
              { value: 'free', label: t('billing.planFree') },
              { value: 'pro', label: t('billing.planPro') },
              { value: 'business', label: t('billing.planBusiness') },
            ]}
            value={plan}
            onChange={setPlan}
            clearable
            w={{ base: '100%', sm: 180 }}
          />
        </Group>
      </Card>

      {templates.isLoading && <LoadingState />}
      {templates.data && filtered.length === 0 && (
        <EmptyState
          icon="search"
          title={t('templates.emptyTitle')}
          description={t('templates.emptyText')}
        />
      )}

      <SimpleGrid cols={{ base: 1, sm: 2, xl: 3 }} spacing="lg">
        {filtered.map((template) => (
          <Card key={template.id} withBorder radius="lg" p="lg" className="bf-hover-lift">
            <Stack gap="sm" style={{ height: '100%' }}>
              <Group justify="space-between" align="flex-start" wrap="nowrap">
                <Group gap="sm" wrap="nowrap">
                  <BotAvatar
                    name={template.name}
                    color={template.iconColor}
                    size={46}
                    radius={14}
                  />
                  <Stack gap={2}>
                    <Group gap={6}>
                      <Title order={3} fz={16}>
                        {template.name}
                      </Title>
                      {template.featured && <IconStar size={14} color="#faa81a" fill="#faa81a" />}
                    </Group>
                    <Badge size="xs" variant="light" color="gray">
                      {templateCategoryLabel[template.category]}
                    </Badge>
                  </Stack>
                </Group>
                {template.minPlan !== 'free' && (
                  <Badge size="xs" color="brand" variant="light">
                    {template.minPlan === 'business'
                      ? t('billing.planBusiness')
                      : t('billing.planPro')}
                  </Badge>
                )}
              </Group>

              <Text size="sm" c="dimmed" lineClamp={3} style={{ flex: 1 }}>
                {template.description}
              </Text>

              <Group gap={5}>
                {template.tags.slice(0, 3).map((tag) => (
                  <Badge key={tag} size="xs" variant="dot" color="gray" tt="none">
                    {tag}
                  </Badge>
                ))}
              </Group>

              <Group gap="lg">
                <Text size="xs" c="dimmed">
                  <strong>{template.modules.length}</strong> {t('templates.modulesCount')}
                </Text>
                <Text size="xs" c="dimmed">
                  <strong>{template.commandsCount}</strong> {t('templates.commandsCount')}
                </Text>
                <Text size="xs" c="dimmed">
                  <strong>{template.flowsCount}</strong> {t('templates.flowsCount')}
                </Text>
              </Group>

              <Group justify="space-between" mt="auto">
                <Text size="xs" c="dimmed">
                  {formatNumber(template.botsCount)} {t('templates.botsCount')}
                </Text>
                <Group gap="xs">
                  <Button
                    variant="subtle"
                    size="compact-sm"
                    onClick={() => setSelected(template)}
                  >
                    {t('templates.details')}
                  </Button>
                  <Button
                    size="compact-sm"
                    rightSection={<IconArrowRight size={13} />}
                    onClick={() => applyTemplate(template)}
                  >
                    {t('templates.use')}
                  </Button>
                </Group>
              </Group>
            </Stack>
          </Card>
        ))}
      </SimpleGrid>

      <Modal
        opened={Boolean(selected)}
        onClose={() => setSelected(null)}
        title={selected?.name}
        size="lg"
      >
        {selected && (
          <Stack>
            <Group gap="sm">
              <BotAvatar name={selected.name} color={selected.iconColor} size={54} radius={16} />
              <Stack gap={2}>
                <Group gap={6}>
                  <Text fw={700}>{selected.name}</Text>
                  <Badge size="xs" variant="light">
                    v{selected.version}
                  </Badge>
                  <Badge size="xs" variant="light" color="gray">
                    {templateCategoryLabel[selected.category]}
                  </Badge>
                </Group>
                <Text size="xs" c="dimmed">
                  {selected.author} В· {formatDate(selected.createdAt)}
                </Text>
              </Stack>
            </Group>
            <Text size="sm">{selected.description}</Text>
            <Group gap={6}>
              {selected.tags.map((tag) => (
                <Badge key={tag} size="sm" variant="light" color="gray" tt="none">
                  {tag}
                </Badge>
              ))}
            </Group>

            <Stack gap="xs">
              <Text size="sm" fw={700}>
                {t('templates.modulesCount')}: {selected.modules.length}
              </Text>
              <ScrollArea h={140}>
                <Group gap={6}>
                  {selected.modules.map((moduleId) => (
                    <Badge key={moduleId} variant="light" color="gray" tt="none">
                      {moduleTitle(moduleId)}
                    </Badge>
                  ))}
                </Group>
              </ScrollArea>
            </Stack>

            <SimpleGrid cols={3}>
              <ThemeIcon variant="light" size="xl" radius="md" style={{ width: '100%' }}>
                <Stack gap={0} align="center">
                  <Text fw={800}>{selected.modules.length}</Text>
                  <Text size="9px">{t('templates.modulesCount')}</Text>
                </Stack>
              </ThemeIcon>
              <ThemeIcon variant="light" color="cyan" size="xl" radius="md" style={{ width: '100%' }}>
                <Stack gap={0} align="center">
                  <Text fw={800}>{selected.commandsCount}</Text>
                  <Text size="9px">{t('templates.commandsCount')}</Text>
                </Stack>
              </ThemeIcon>
              <ThemeIcon variant="light" color="teal" size="xl" radius="md" style={{ width: '100%' }}>
                <Stack gap={0} align="center">
                  <Text fw={800}>{selected.flowsCount}</Text>
                  <Text size="9px">{t('templates.flowsCount')}</Text>
                </Stack>
              </ThemeIcon>
            </SimpleGrid>

            <Group justify="flex-end">
              <Button variant="default" onClick={() => setSelected(null)}>
                {t('common.close')}
              </Button>
              <Button
                rightSection={<IconArrowRight size={14} />}
                onClick={() => applyTemplate(selected)}
              >
                {t('templates.use')}
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>
    </Stack>
  )
}

