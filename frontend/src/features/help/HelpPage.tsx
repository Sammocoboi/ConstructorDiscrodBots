import { useState } from 'react'
import {
  Accordion,
  Anchor,
  Badge,
  Button,
  Card,
  Group,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  ThemeIcon,
  Title,
} from '@mantine/core'
import { useTranslation } from 'react-i18next'
import {
  IconArrowRight,
  IconBook,
  IconCompass,
  IconKeyboard,
  IconLifebuoy,
  IconMail,
  IconSearch,
} from '@tabler/icons-react'
import { PageHeader } from '../../shared/components/bits'
import { EmptyState } from '../../shared/components/states'

export default function HelpPage() {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')

  const articles = [
    {
      icon: IconBook,
      color: 'brand',
      title: t('help.docs'),
      text: t('help.docsText'),
    },
    {
      icon: IconCompass,
      color: 'cyan',
      title: t('help.guides'),
      text: t('help.guidesText'),
    },
    {
      icon: IconLifebuoy,
      color: 'teal',
      title: t('help.support'),
      text: t('help.supportText'),
    },
  ]

  const faqs = [
    { q: t('help.faqCreateQ'), a: t('help.faqCreateA') },
    { q: t('help.faqTokenQ'), a: t('help.faqTokenA') },
    { q: t('help.faqFlowsQ'), a: t('help.faqFlowsA') },
    { q: t('help.faqBillingQ'), a: t('help.faqBillingA') },
    { q: t('help.faqLimitsQ'), a: t('help.faqLimitsA') },
  ]

  const normalized = query.trim().toLowerCase()
  const filtered = normalized
    ? faqs.filter(
        (item) =>
          item.q.toLowerCase().includes(normalized) ||
          item.a.toLowerCase().includes(normalized),
      )
    : faqs

  const steps = [
    { title: t('help.step1Title'), text: t('help.step1Text') },
    { title: t('help.step2Title'), text: t('help.step2Text') },
    { title: t('help.step3Title'), text: t('help.step3Text') },
    { title: t('help.step4Title'), text: t('help.step4Text') },
  ]

  return (
    <Stack gap="lg" maw={1100} mx="auto" w="100%">
      <PageHeader
        title={t('help.title')}
        description={t('help.subtitle')}
        actions={
          <Button
            component="a"
            href="mailto:support@botforge.app"
            leftSection={<IconMail size={16} />}
          >
            {t('help.openSupport')}
          </Button>
        }
      />

      <Card
        radius="lg"
        p="xl"
        style={{
          border: 'none',
          background: 'linear-gradient(120deg, #262a78, #5865f2 60%, #00a8fc 140%)',
          color: 'white',
        }}
      >
        <Stack align="center" gap="sm" maw={640} mx="auto" py="md">
          <Title order={2} fz={{ base: 22, sm: 30 }} ta="center">
            {t('help.quickStart')}
          </Title>
          <Text size="sm" opacity={0.85} ta="center">
            {t('help.quickStartText')}
          </Text>
          <TextInput
            placeholder={t('help.searchPlaceholder')}
            leftSection={<IconSearch size={16} />}
            value={query}
            onChange={(event) => setQuery(event.currentTarget.value)}
            size="md"
            radius="xl"
            w="100%"
            mt="sm"
            styles={{ input: { color: '#1a1b1e' } }}
          />
        </Stack>
      </Card>

      <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
        {articles.map((article) => (
          <Card key={article.title} withBorder radius="lg" p="lg" className="bf-hover-lift">
            <ThemeIcon variant="light" color={article.color} size={42} radius="md" mb="sm">
              <article.icon size={21} />
            </ThemeIcon>
            <Title order={3} fz={16}>
              {article.title}
            </Title>
            <Text size="sm" c="dimmed" mt={4}>
              {article.text}
            </Text>
            <Button
              component="a"
              href="#faq"
              variant="subtle"
              size="compact-sm"
              mt="sm"
              rightSection={<IconArrowRight size={13} />}
            >
              {t('help.faq')}
            </Button>
          </Card>
        ))}
      </SimpleGrid>

      <Card withBorder radius="lg" p="lg">
        <Group gap="xs" mb="md">
          <ThemeIcon variant="light" size="md" radius="md">
            <IconCompass size={16} />
          </ThemeIcon>
          <Title order={3} fz={18}>
            {t('help.quickStart')}
          </Title>
        </Group>
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="md">
          {steps.map((step, index) => (
            <Stack key={step.title} gap={6}>
              <Badge size="lg" variant="light" circle>
                {index + 1}
              </Badge>
              <Text size="sm" fw={700}>
                {step.title}
              </Text>
              <Text size="xs" c="dimmed">
                {step.text}
              </Text>
            </Stack>
          ))}
        </SimpleGrid>
      </Card>

      <Card withBorder radius="lg" p="lg" id="faq">
        <Group justify="space-between" mb="md">
          <Title order={3} fz={18}>
            {t('help.faq')}
          </Title>
          <Badge variant="light">{filtered.length}</Badge>
        </Group>
        {filtered.length === 0 ? (
          <EmptyState icon="search" title={t('help.noResults')} />
        ) : (
          <Accordion variant="separated" radius="md">
            {filtered.map((item) => (
              <Accordion.Item key={item.q} value={item.q}>
                <Accordion.Control>{item.q}</Accordion.Control>
                <Accordion.Panel>
                  <Text size="sm" c="dimmed">
                    {item.a}
                  </Text>
                </Accordion.Panel>
              </Accordion.Item>
            ))}
          </Accordion>
        )}
      </Card>

      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
        <Card withBorder radius="lg" p="lg">
          <Group gap="xs" mb="xs">
            <ThemeIcon variant="light" size="md" radius="md">
              <IconKeyboard size={16} />
            </ThemeIcon>
            <Text fw={700}>{t('help.keyboard')}</Text>
          </Group>
          <Text size="sm" c="dimmed">
            {t('help.keyboardText')}
          </Text>
        </Card>
        <Card withBorder radius="lg" p="lg">
          <Group gap="xs" mb="xs">
            <ThemeIcon variant="light" color="teal" size="md" radius="md">
              <IconLifebuoy size={16} />
            </ThemeIcon>
            <Text fw={700}>{t('help.contact')}</Text>
          </Group>
          <Text size="sm" c="dimmed">
            {t('help.contactText')}
          </Text>
          <Anchor href="mailto:support@botforge.app" size="sm" fw={600} mt="xs" display="block">
            support@botforge.app
          </Anchor>
        </Card>
      </SimpleGrid>
    </Stack>
  )
}
