import {
  Accordion,
  Anchor,
  Badge,
  Box,
  Burger,
  Button,
  Card,
  Container,
  Divider,
  Drawer,
  Group,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import {
  IconArrowRight,
  IconBrandDiscord,
  IconCheck,
  IconPlus,
  IconSparkles,
} from '@tabler/icons-react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Logo } from '../../shared/components/Logo'
import { ThemeToggle } from '../../shared/components/ThemeToggle'
import { AppIcon } from '../../shared/components/icons'
import { useTemplates } from '../../shared/api/hooks'
import { useAuthStore } from '../../shared/stores/authStore'
import { plans } from '../../shared/mocks/plans'
import { formatMoney } from '../../shared/lib/format'
import '../../theme/global.css'
import './landing.css'

const featureKeys = [
  { icon: 'bolt', title: 'featureModules', text: 'featureModulesText' },
  { icon: 'messages', title: 'featureFlows', text: 'featureFlowsText' },
  { icon: 'terminal', title: 'featureCommands', text: 'featureCommandsText' },
  { icon: 'settings', title: 'featureProfiles', text: 'featureProfilesText' },
  { icon: 'template', title: 'featureTemplates', text: 'featureTemplatesText' },
  { icon: 'shield', title: 'featureSafe', text: 'featureSafeText' },
]

const faqRu = [
  {
    q: 'Нужно ли уметь программировать?',
    a: 'Нет. Модули включаются переключателями, а логика собирается из блоков на холсте. Для сложных случаев есть готовые сценарии и библиотека команд.',
  },
  {
    q: 'Как подключить своего бота?',
    a: 'Создайте приложение в Discord Developer Portal, скопируйте токен и вставьте его в мастер подключения. Мы проверим токен через Discord API и покажем имя бота.',
  },
  {
    q: 'Безопасно ли хранить токен?',
    a: 'Токен шифруется на сервере (AES-256-GCM), в API возвращается только маска, а в логах его нет. При компрометации токен можно заменить в профиле бота.',
  },
  {
    q: 'Можно ли пользоваться бесплатно?',
    a: 'Да, тариф Free включает одного бота, 5 000 выполнений в месяц и три гильдии. Для роста есть Pro и Business.',
  },
  {
    q: 'Что будет, если бот упадёт?',
    a: 'Runtime автоматически перезапускает бота до пяти раз, а на дашборде появляется статус и последняя ошибка запуска.',
  },
]

const faqEn = [
  {
    q: 'Do I need to know how to code?',
    a: 'No. Modules are toggles and logic is built from blocks on a canvas. Ready-made flows and a command library cover advanced cases.',
  },
  {
    q: 'How do I connect my bot?',
    a: 'Create an app in the Discord Developer Portal, copy the token and paste it into the setup wizard. We validate it through the Discord API and show the bot name.',
  },
  {
    q: 'Is storing the token safe?',
    a: 'The token is encrypted server-side (AES-256-GCM), the API returns only a mask and logs never contain it. You can replace it from the bot profile.',
  },
  {
    q: 'Can I use it for free?',
    a: 'Yes, the Free plan includes one bot, 5,000 executions per month and three guilds. Pro and Business are available as you grow.',
  },
  {
    q: 'What happens if the bot crashes?',
    a: 'The runtime restarts it up to five times, and the dashboard shows the status and the latest launch error.',
  },
]

export function LandingPage() {
  const { t, i18n } = useTranslation()
  const [navOpened, nav] = useDisclosure(false)
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const templatesQuery = useTemplates(isAuthenticated)
  const featured = (templatesQuery.data ?? []).filter((template) => template.featured).slice(0, 3)
  const faq = i18n.language.startsWith('en') ? faqEn : faqRu

  const navLinks = [
    { href: '#features', label: i18n.language.startsWith('en') ? 'Features' : 'Возможности' },
    { href: '#templates', label: t('landing.templatesTitle') },
    { href: '#pricing', label: t('landing.pricingTitle') },
    { href: '#faq', label: t('landing.faqTitle') },
  ]

  return (
    <Box>
      <header className="bf-marketing-header">
        <Container size="xl" py="sm">
          <Group justify="space-between">
            <Logo />
            <Group gap="lg" visibleFrom="md">
              {navLinks.map((link) => (
                <Anchor key={link.href} href={link.href} c="dimmed" size="sm" fw={600}>
                  {link.label}
                </Anchor>
              ))}
            </Group>
            <Group gap="xs">
              <ThemeToggle />
              <Button variant="subtle" component={Link} to="/login" visibleFrom="sm">
                {t('auth.login')}
              </Button>
              <Button component={Link} to="/register" leftSection={<IconBrandDiscord size={17} />}>
                {t('landing.ctaPrimary')}
              </Button>
              <Burger opened={navOpened} onClick={nav.toggle} hiddenFrom="md" size="sm" />
            </Group>
          </Group>
        </Container>
      </header>

      <Drawer opened={navOpened} onClose={nav.close} title={<Logo />} position="right">
        <Stack>
          {navLinks.map((link) => (
            <Anchor key={link.href} href={link.href} onClick={nav.close} fw={600}>
              {link.label}
            </Anchor>
          ))}
          <Divider />
          <Button variant="default" component={Link} to="/login" onClick={nav.close}>
            {t('auth.login')}
          </Button>
          <Button component={Link} to="/register" onClick={nav.close}>
            {t('landing.ctaPrimary')}
          </Button>
        </Stack>
      </Drawer>

      <section className="landing-hero">
        <Container size="xl">
          <div className="landing-hero-grid">
            <Stack gap={0}>
              <div>
                <span className="bf-eyebrow">
                  <IconSparkles size={14} /> {t('landing.eyebrow')}
                </span>
              </div>
              <Title className="landing-hero-title">
                {t('landing.title')}{' '}
                <span className="bf-gradient-text">{t('landing.titleAccent')}</span>
              </Title>
              <Text className="landing-hero-subtitle">{t('landing.subtitle')}</Text>

              <Group mt="xl" gap="sm">
                <Button
                  size="lg"
                  component={Link}
                  to="/register"
                  rightSection={<IconArrowRight size={18} />}
                >
                  {t('landing.ctaPrimary')}
                </Button>
                <Button
                  size="lg"
                  variant="default"
                  component={Link}
                  to="/login"
                >
                  {t('landing.ctaSecondary')}
                </Button>
              </Group>

              <Group mt="xl" gap="xl" wrap="wrap">
                <Stack gap={0}>
                  <Text fw={800} size="lg">
                    2 400+
                  </Text>
                  <Text size="xs" c="dimmed">
                    ботов создано
                  </Text>
                </Stack>
                <Stack gap={0}>
                  <Text fw={800} size="lg">
                    70
                  </Text>
                  <Text size="xs" c="dimmed">
                    готовых команд
                  </Text>
                </Stack>
                <Stack gap={0}>
                  <Text fw={800} size="lg">
                    5 мин
                  </Text>
                  <Text size="xs" c="dimmed">
                    до первого запуска
                  </Text>
                </Stack>
              </Group>
            </Stack>

            <div className="landing-preview-wrap">
              <div className="landing-preview-glow" />
              <div className="landing-float-card" style={{ top: -8, right: 8 }}>
                <span
                  className="bf-status-dot"
                  style={{ background: 'var(--mantine-color-teal-6)' }}
                />
                Бот онлайн · ping 34 мс
              </div>
              <div className="landing-float-card" style={{ bottom: 18, left: -8 }}>
                <ThemeIcon size={26} radius="xl" color="brand" variant="light">
                  <IconPlus size={15} />
                </ThemeIcon>
                Новый участник → приветствие
              </div>
              <div className="bf-discord-preview">
                <Group gap={0} align="stretch" wrap="nowrap">
                  <Box className="bf-discord-sidebar" p="sm" w={142} visibleFrom="xs">
                    <Text size="10px" fw={800} c="#9da3ae" tt="uppercase" mb="xs">
                      Дизайн-сообщество
                    </Text>
                    {['general', 'welcome', 'rules', 'showcase'].map((channel, index) => (
                      <Group
                        key={channel}
                        gap={6}
                        px={6}
                        py={4}
                        style={{
                          borderRadius: 5,
                          background: index === 1 ? 'rgba(255,255,255,0.08)' : undefined,
                        }}
                      >
                        <Text size="xs" c="#8e9297">
                          #
                        </Text>
                        <Text size="xs" c={index === 1 ? '#f2f3f5' : '#9da3ae'} fw={index === 1 ? 600 : 400}>
                          {channel}
                        </Text>
                      </Group>
                    ))}
                  </Box>
                  <Box style={{ flex: 1, minWidth: 0 }} p="md">
                    <Group gap={6} mb="md">
                      <Text c="#f2f3f5" fw={700} size="sm">
                        # welcome
                      </Text>
                      <Badge size="xs" color="teal" variant="filled">
                        online
                      </Badge>
                    </Group>
                    <div className="landing-chat-row" style={{ marginBottom: 14 }}>
                      <div className="landing-chat-avatar" style={{ background: '#e67e22' }}>
                        A
                      </div>
                      <Box>
                        <Group gap={6}>
                          <Text size="xs" fw={700} c="#f2f3f5">
                            admin
                          </Text>
                          <Text size="9px" c="#949ba4">
                            сегодня в 18:42
                          </Text>
                        </Group>
                        <Text size="xs" c="#dbdee1" mt={2}>
                          Встречайте нового участника 👋
                        </Text>
                      </Box>
                    </div>
                    <div className="landing-chat-row">
                      <div className="landing-chat-avatar" style={{ background: '#5865f2' }}>
                        B
                      </div>
                      <Box style={{ minWidth: 0, flex: 1 }}>
                        <Group gap={6} mb={4}>
                          <Text size="xs" fw={700} c="#f2f3f5">
                            Хранитель
                          </Text>
                          <Badge size="xs" color="brand" variant="filled">
                            БОТ
                          </Badge>
                          <Text size="9px" c="#949ba4">
                            сегодня в 18:42
                          </Text>
                        </Group>
                        <div className="bf-discord-embed">
                          <Text size="sm" fw={700} c="#f2f3f5">
                            Добро пожаловать, @new_member!
                          </Text>
                          <Text size="xs" c="#dbdee1" mt={6} style={{ lineHeight: 1.5 }}>
                            Расскажите о себе в #general, прочитайте правила и выберите роли.
                          </Text>
                          <Divider my="sm" color="rgba(255,255,255,0.1)" />
                          <Group gap="xs">
                            <Badge size="sm" color="brand" variant="light">
                              📘 Правила
                            </Badge>
                            <Badge size="sm" color="gray" variant="light">
                              🎨 Роли
                            </Badge>
                          </Group>
                        </div>
                      </Box>
                    </div>
                  </Box>
                </Group>
              </div>
            </div>
          </div>
        </Container>
      </section>

      <section id="features" className="bf-landing-section">
        <Container size="xl">
          <Stack align="center" gap={8} mb={44}>
            <span className="bf-eyebrow">
              <IconSparkles size={13} /> BotForge
            </span>
            <Title order={2} ta="center" fz={{ base: 28, sm: 38 }}>
              {t('landing.featuresTitle')}
            </Title>
            <Text ta="center" c="dimmed" maw={640}>
              {t('landing.featuresSubtitle')}
            </Text>
          </Stack>
          <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="lg">
            {featureKeys.map((feature) => (
              <Card key={feature.title} withBorder radius="lg" p="xl" className="landing-feature-card">
                <ThemeIcon size={46} radius="md" variant="light" color="brand">
                  <AppIcon name={feature.icon} size={24} />
                </ThemeIcon>
                <Text fw={700} mt="md">
                  {t(`landing.${feature.title}`)}
                </Text>
                <Text size="sm" c="dimmed" mt={6} style={{ lineHeight: 1.6 }}>
                  {t(`landing.${feature.text}`)}
                </Text>
              </Card>
            ))}
          </SimpleGrid>
        </Container>
      </section>

      <section id="templates" className="bf-landing-section" style={{ paddingTop: 0 }}>
        <Container size="xl">
          <Group justify="space-between" align="flex-end" mb={28} wrap="wrap">
            <Stack gap={6}>
              <Title order={2} fz={{ base: 26, sm: 34 }}>
                {t('landing.templatesTitle')}
              </Title>
              <Text c="dimmed">{t('landing.templatesSubtitle')}</Text>
            </Stack>
            <Button variant="light" component={Link} to="/register" rightSection={<IconArrowRight size={16} />}>
              {t('nav.catalog')}
            </Button>
          </Group>
          <SimpleGrid cols={{ base: 1, md: 3 }} spacing="lg">
            {templatesQuery.isLoading
              ? [0, 1, 2].map((index) => <Skeleton key={index} height={230} radius="lg" />)
              : featured.length > 0
                ? featured.map((template) => (
                    <Card
                      key={template.id}
                      withBorder
                      radius="lg"
                      p="lg"
                      className="bf-hover-lift landing-template-card"
                    >
                      <Group justify="space-between" align="flex-start">
                        <ThemeIcon
                          size={44}
                          radius="md"
                          style={{ background: `${template.iconColor}22`, color: template.iconColor }}
                        >
                          <AppIcon name="template" size={23} />
                        </ThemeIcon>
                        <Badge variant="light" color="gray" size="sm">
                          {t('landing.modulesCount', { count: template.modules.length })}
                        </Badge>
                      </Group>
                      <Text fw={700} mt="md">
                        {template.name}
                      </Text>
                      <Text size="sm" c="dimmed" mt={6} lineClamp={3} style={{ lineHeight: 1.55 }}>
                        {template.description}
                      </Text>
                      <Group mt="md" gap={6}>
                        {template.tags.slice(0, 3).map((tag) => (
                          <Badge key={tag} size="xs" variant="light" color="brand">
                            {tag}
                          </Badge>
                        ))}
                      </Group>
                      <Button
                        component={Link}
                        to="/app/bots/new"
                        variant="light"
                        fullWidth
                        mt="lg"
                        rightSection={<IconArrowRight size={15} />}
                      >
                        {t('templates.use')}
                      </Button>
                    </Card>
                  ))
                : (
                    <Card withBorder radius="lg" p="xl" style={{ gridColumn: '1 / -1' }}>
                      <Stack align="center" gap="sm">
                        <ThemeIcon size={52} radius="xl" variant="light">
                          <AppIcon name="template" size={26} />
                        </ThemeIcon>
                        <Text fw={600}>{t('landing.templatesEmptyTitle')}</Text>
                        <Text size="sm" c="dimmed" ta="center" maw={460}>
                          {t('landing.templatesEmptyText')}
                        </Text>
                        <Button component={Link} to="/login" mt="xs">
                          {t('auth.login')}
                        </Button>
                      </Stack>
                    </Card>
                  )}
          </SimpleGrid>
        </Container>
      </section>

      <section id="pricing" className="bf-landing-section">
        <Container size="xl">
          <Stack align="center" gap={8} mb={40}>
            <Title order={2} ta="center" fz={{ base: 28, sm: 38 }}>
              {t('landing.pricingTitle')}
            </Title>
            <Text c="dimmed" ta="center">
              {t('landing.pricingSubtitle')}
            </Text>
          </Stack>
          <SimpleGrid cols={{ base: 1, md: 3 }} spacing="lg">
            {plans.map((plan) => (
              <Card
                key={plan.id}
                withBorder
                radius="lg"
                p="xl"
                className={`landing-price-card ${plan.highlighted ? 'landing-price-highlight' : ''}`}
              >
                {plan.highlighted && (
                  <Badge
                    color="brand"
                    variant="filled"
                    size="sm"
                    style={{ position: 'absolute', top: -11, right: 20 }}
                  >
                    Популярный
                  </Badge>
                )}
                <Text fw={800} size="lg">
                  {plan.name}
                </Text>
                <Text size="sm" c="dimmed" mt={4} mb="md" mih={42}>
                  {plan.description}
                </Text>
                <Group align="flex-end" gap={6}>
                  <Text fw={800} fz={36} lh={1}>
                    {plan.priceMonthly === 0 ? '0' : formatMoney(plan.priceMonthly)}
                  </Text>
                  <Text size="sm" c="dimmed" mb={3}>
                    {t('billing.perMonth')}
                  </Text>
                </Group>
                <Divider my="lg" />
                <Stack gap="sm" style={{ flex: 1 }}>
                  {plan.features.map((feature) => (
                    <Group key={feature} gap="xs" align="flex-start" wrap="nowrap">
                      <ThemeIcon size={18} radius="xl" color="teal" variant="light">
                        <IconCheck size={12} />
                      </ThemeIcon>
                      <Text size="sm">{feature}</Text>
                    </Group>
                  ))}
                </Stack>
                <Button
                  component={Link}
                  to="/register"
                  mt="xl"
                  variant={plan.highlighted ? 'filled' : 'light'}
                  fullWidth
                >
                  {plan.id === 'free' ? t('landing.ctaPrimary') : t('billing.upgrade', { plan: plan.name })}
                </Button>
              </Card>
            ))}
          </SimpleGrid>
        </Container>
      </section>

      <section id="faq" className="bf-landing-section" style={{ paddingTop: 0 }}>
        <Container size="md">
          <Stack align="center" gap={8} mb={32}>
            <Title order={2} ta="center" fz={{ base: 28, sm: 36 }}>
              {t('landing.faqTitle')}
            </Title>
            <Text c="dimmed" ta="center">
              {t('landing.faqSubtitle')}
            </Text>
          </Stack>
          <Accordion variant="separated" radius="lg">
            {faq.map((item, index) => (
              <Accordion.Item key={item.q} value={`faq-${index}`}>
                <Accordion.Control>
                  <Text fw={600}>{item.q}</Text>
                </Accordion.Control>
                <Accordion.Panel>
                  <Text size="sm" c="dimmed" style={{ lineHeight: 1.6 }}>
                    {item.a}
                  </Text>
                </Accordion.Panel>
              </Accordion.Item>
            ))}
          </Accordion>
        </Container>
      </section>

      <Container size="xl" pb={64}>
        <div className="landing-cta">
          <Stack align="center" gap="md" maw={640} mx="auto" ta="center">
            <Title order={2} fz={{ base: 28, sm: 40 }} c="white">
              {t('landing.ctaTitle')}
            </Title>
            <Text c="rgba(255,255,255,0.8)" size="lg">
              {t('landing.ctaSubtitle')}
            </Text>
            <Group mt="sm">
              <Button
                size="lg"
                color="white"
                c="brand.7"
                component={Link}
                to="/register"
                leftSection={<IconBrandDiscord size={18} />}
              >
                {t('landing.ctaPrimary')}
              </Button>
              <Button
                size="lg"
                variant="white"
                color="gray"
                component={Link}
                to="/login"
              >
                {t('auth.login')}
              </Button>
            </Group>
          </Stack>
        </div>
      </Container>

      <footer className="landing-footer">
        <Container size="xl">
          <Group justify="space-between" wrap="wrap" gap="md">
            <Group gap="md">
              <Logo />
              <Text size="xs" c="dimmed">
                {t('landing.footer')}
              </Text>
            </Group>
            <Group gap="lg">
              <Anchor component={Link} to="/help" size="xs" c="dimmed">
                {t('nav.help')}
              </Anchor>
              <Anchor href="https://discord.com" target="_blank" size="xs" c="dimmed">
                Discord
              </Anchor>
              <Anchor href="#pricing" size="xs" c="dimmed">
                {t('nav.billing')}
              </Anchor>
            </Group>
          </Group>
        </Container>
      </footer>
    </Box>
  )
}
