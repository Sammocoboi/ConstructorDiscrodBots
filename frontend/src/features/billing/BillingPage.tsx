import {
  Alert,
  Badge,
  Button,
  Card,
  Divider,
  Grid,
  Group,
  SimpleGrid,
  Stack,
  Table,
  Text,
  ThemeIcon,
  Title,
} from '@mantine/core'
import { useTranslation } from 'react-i18next'
import {
  IconCheck,
  IconCreditCard,
  IconDownload,
  IconExternalLink,
  IconReceipt,
  IconShieldCheck,
} from '@tabler/icons-react'
import { api } from '../../shared/api'
import { useBilling, useToastMutation } from '../../shared/api/hooks'
import type { PlanId } from '../../shared/api/types'
import { PageHeader, LimitBar } from '../../shared/components/bits'
import { ErrorState, LoadingState } from '../../shared/components/states'
import { plans as fallbackPlans } from '../../shared/mocks/plans'
import { formatDate, formatMoney, formatNumber } from '../../shared/lib/format'
import { errorMessage } from '../../shared/api/errors'

const planName: Record<PlanId, string> = {
  free: 'Free',
  pro: 'Pro',
  business: 'Business',
}

export default function BillingPage() {
  const { t } = useTranslation()
  const billing = useBilling()

  const checkoutMutation = useToastMutation({
    mutationFn: (planId: string) => api.billing.checkout(planId),
    successMessage: t('billing.checkoutOpened'),
    onSuccess: (result) => window.open(result.url, '_blank', 'noopener,noreferrer'),
  })

  const portalMutation = useToastMutation({
    mutationFn: () => api.billing.portal(),
    successMessage: t('billing.portalOpened'),
    onSuccess: (result) => window.open(result.url, '_blank', 'noopener,noreferrer'),
  })

  if (billing.isLoading) return <LoadingState minHeight={320} />
  if (billing.isError || !billing.data) {
    return (
      <ErrorState
        message={errorMessage(billing.error)}
        onRetry={() => void billing.refetch()}
      />
    )
  }

  const { subscription, usage, invoices } = billing.data
  const availablePlans = billing.data.plans?.length ? billing.data.plans : fallbackPlans
  const currentPlan =
    availablePlans.find((plan) => plan.id === subscription.planId) ?? availablePlans[0]

  return (
    <Stack gap="lg" maw={1280} mx="auto" w="100%">
      <PageHeader
        title={t('billing.title')}
        description={t('billing.subtitle')}
        actions={
          <Button
            variant="default"
            leftSection={<IconCreditCard size={16} />}
            loading={portalMutation.isPending}
            onClick={() => portalMutation.mutate()}
          >
            {t('billing.manage')}
          </Button>
        }
      />

      <Grid gutter="lg">
        <Grid.Col span={{ base: 12, lg: 8 }}>
          <Card
            radius="lg"
            p="lg"
            h="100%"
            style={{
              border: 'none',
              background: 'linear-gradient(125deg, #262a78, #5865f2 60%, #00a8fc 140%)',
              color: 'white',
            }}
          >
            <Group justify="space-between" align="flex-start" wrap="wrap">
              <Stack gap={4}>
                <Text size="xs" fw={800} tt="uppercase" opacity={0.8}>
                  {t('billing.currentPlan')}
                </Text>
                <Title order={2} fz={34}>
                  {currentPlan?.name ?? planName[subscription.planId]}
                </Title>
                <Group gap="xs">
                  <Badge variant="white" color="brand" size="sm">
                    {subscription.status}
                  </Badge>
                  {subscription.cancelAtPeriodEnd && (
                    <Badge variant="light" color="yellow" size="sm">
                      {t('billing.cancelAtPeriodEnd')}
                    </Badge>
                  )}
                </Group>
                {currentPlan?.description && (
                  <Text size="sm" opacity={0.85} mt="xs" maw={480}>
                    {currentPlan.description}
                  </Text>
                )}
              </Stack>
              {currentPlan && (
                <Stack align="flex-end" gap={4}>
                  <Text fz={30} fw={800} lh={1}>
                    {formatMoney(currentPlan.priceMonthly)}
                  </Text>
                  <Text size="xs" opacity={0.8}>
                    {t('billing.perMonth')}
                  </Text>
                </Stack>
              )}
            </Group>
            <Group mt="lg" gap="sm">
              <Button
                variant="white"
                color="brand"
                leftSection={<IconExternalLink size={15} />}
                loading={portalMutation.isPending}
                onClick={() => portalMutation.mutate()}
              >
                {t('billing.portal')}
              </Button>
            </Group>
            {subscription.renewsAt && (
              <Text size="xs" opacity={0.75} mt="md">
                {t('billing.renews')}: {formatDate(subscription.renewsAt)}
              </Text>
            )}
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, lg: 4 }}>
          <Card withBorder radius="lg" p="lg" h="100%">
            <Group gap="xs" mb="md">
              <ThemeIcon variant="light" size="md" radius="md">
                <IconCreditCard size={16} />
              </ThemeIcon>
              <Text fw={700}>{t('billing.paymentMethod')}</Text>
            </Group>
            <Stack>
              <Text size="sm" c="dimmed">
                {t('billing.noPaymentMethod')}
              </Text>
              <Button onClick={() => portalMutation.mutate()} loading={portalMutation.isPending}>
                {t('billing.addPaymentMethod')}
              </Button>
            </Stack>
            <Divider my="md" />
            <Group gap="xs">
              <IconShieldCheck size={15} />
              <Text size="10px" c="dimmed">
                {t('billing.securePayments')}
              </Text>
            </Group>
          </Card>
        </Grid.Col>
      </Grid>

      <Card withBorder radius="lg" p="lg">
        <Title order={3} fz={18} mb="lg">
          {t('billing.usage')}
        </Title>
        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="lg">
          <LimitBar
            label={t('billing.bots')}
            value={usage.bots}
            limit={currentPlan?.limits.bots ?? 0}
          />
          <LimitBar
            label={t('billing.executions')}
            value={usage.executions}
            limit={currentPlan?.limits.executions ?? 0}
          />
        </SimpleGrid>
        <Text size="xs" c="dimmed" mt="md">
          {t('billing.period')}: {formatDate(usage.periodStart)} — {formatDate(usage.periodEnd)}
        </Text>
      </Card>

      <Stack gap="md">
        <Title order={3} fz={18}>
          {t('billing.title')}
        </Title>
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="md">
          {availablePlans.map((plan) => {
            const current = plan.id === subscription.planId
            return (
              <Card
                key={plan.id}
                withBorder
                radius="lg"
                p="lg"
                style={{
                  borderColor: plan.highlighted
                    ? 'var(--mantine-color-brand-5)'
                    : undefined,
                  borderWidth: plan.highlighted ? 2 : 1,
                }}
              >
                <Stack gap="sm" style={{ height: '100%' }}>
                  <Group justify="space-between">
                    <Title order={3} fz={20}>
                      {plan.name}
                    </Title>
                    {current && <Badge color="teal">{t('billing.currentPlan')}</Badge>}
                  </Group>
                  <Group align="flex-end" gap={4}>
                    <Text fz={30} fw={800} lh={1}>
                      {formatMoney(plan.priceMonthly)}
                    </Text>
                    <Text size="xs" c="dimmed" pb={4}>
                      {t('billing.perMonth')}
                    </Text>
                  </Group>
                  {plan.description && (
                    <Text size="sm" c="dimmed">
                      {plan.description}
                    </Text>
                  )}
                  {plan.features.length > 0 && (
                    <Stack gap={6} mt="xs" style={{ flex: 1 }}>
                      {plan.features.map((feature) => (
                        <Group key={feature} gap="xs" align="flex-start" wrap="nowrap">
                          <ThemeIcon size={17} radius="xl" variant="light" color="teal">
                            <IconCheck size={10} />
                          </ThemeIcon>
                          <Text size="sm">{feature}</Text>
                        </Group>
                      ))}
                    </Stack>
                  )}
                  <Button
                    fullWidth
                    variant={current ? 'light' : plan.highlighted ? 'filled' : 'default'}
                    disabled={current}
                    loading={checkoutMutation.isPending && checkoutMutation.variables === plan.id}
                    onClick={() => checkoutMutation.mutate(plan.id)}
                  >
                    {current ? t('common.installed') : t('billing.upgrade', { plan: plan.name })}
                  </Button>
                </Stack>
              </Card>
            )
          })}
        </SimpleGrid>
      </Stack>

      <Card withBorder radius="lg" p={0}>
        <Group justify="space-between" p="lg" pb="sm">
          <Group gap="xs">
            <ThemeIcon variant="light" size="md" radius="md">
              <IconReceipt size={16} />
            </ThemeIcon>
            <Title order={3} fz={18}>
              {t('billing.invoices')}
            </Title>
          </Group>
          <Text size="xs" c="dimmed">
            {formatNumber(invoices.length)}
          </Text>
        </Group>
        <Table highlightOnHover verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>{t('billing.invoiceNumber')}</Table.Th>
              <Table.Th>{t('billing.invoiceDate')}</Table.Th>
              <Table.Th>{t('billing.invoiceAmount')}</Table.Th>
              <Table.Th>{t('billing.invoiceStatus')}</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {invoices.map((invoice) => (
              <Table.Tr key={invoice.id}>
                <Table.Td>
                  <Text size="sm" fw={600}>
                    {invoice.number}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Text size="xs" c="dimmed">
                    {formatDate(invoice.createdAt)}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Text size="sm">{formatMoney(invoice.amount, invoice.currency)}</Text>
                </Table.Td>
                <Table.Td>
                  <Badge
                    size="sm"
                    variant="light"
                    color={
                      invoice.status === 'paid'
                        ? 'teal'
                        : invoice.status === 'open'
                          ? 'yellow'
                          : 'gray'
                    }
                  >
                    {invoice.status === 'paid'
                      ? t('billing.paid')
                      : invoice.status === 'open'
                        ? t('billing.open')
                        : t('billing.void')}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  {invoice.downloadUrl ? (
                    <Button
                      component="a"
                      href={invoice.downloadUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      variant="subtle"
                      size="compact-xs"
                      leftSection={<IconDownload size={13} />}
                    >
                      PDF
                    </Button>
                  ) : (
                    <Text size="xs" c="dimmed">
                      —
                    </Text>
                  )}
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
        {invoices.length === 0 && (
          <Alert color="gray" variant="light" m="md">
            {t('billing.invoices')} — {t('common.empty')}
          </Alert>
        )}
      </Card>
    </Stack>
  )
}
