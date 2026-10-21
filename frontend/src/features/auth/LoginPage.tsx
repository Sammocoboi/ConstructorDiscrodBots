import { useState } from 'react'
import {
  Alert,
  Anchor,
  Button,
  Divider,
  Group,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { IconAlertTriangle, IconBrandDiscord, IconLock, IconMail } from '@tabler/icons-react'
import { api } from '../../shared/api'
import { errorMessage } from '../../shared/api/errors'
import { loginSchema, type LoginFormValues } from '../../shared/lib/validation'
import { useAuthStore } from '../../shared/stores/authStore'
import { notifications } from '@mantine/notifications'

export function LoginPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const setSession = useAuthStore((state) => state.setSession)
  const [error, setError] = useState<string | null>(null)
  const from =
    (location.state as { from?: string } | null)?.from ??
    new URLSearchParams(location.search).get('next') ??
    '/app'

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: 'danila@example.com', password: 'password123' },
  })

  const loginMutation = useMutation({
    mutationFn: (values: LoginFormValues) => api.auth.login(values),
    onSuccess: (session) => {
      setSession(session.user, session.accessToken)
      notifications.show({
        color: 'teal',
        title: t('notifications.typeSuccess'),
        message: t('auth.loginTitle'),
      })
      navigate(from, { replace: true })
    },
    onError: (mutationError) => setError(errorMessage(mutationError)),
  })

  const discordMutation = useMutation({
    mutationFn: () => api.auth.loginWithDiscord(),
    onSuccess: (session) => {
      if (!session) return
      setSession(session.user, session.accessToken)
      navigate(from, { replace: true })
    },
    onError: (mutationError) => setError(errorMessage(mutationError)),
  })

  return (
    <Stack gap="lg">
      <Stack gap={4}>
        <Title order={2}>{t('auth.loginTitle')}</Title>
        <Text c="dimmed" size="sm">
          {t('auth.loginSubtitle')}
        </Text>
      </Stack>

      <Button
        size="md"
        color="brand"
        leftSection={<IconBrandDiscord size={19} />}
        loading={discordMutation.isPending}
        onClick={() => discordMutation.mutate()}
      >
        {t('auth.discord')}
      </Button>

      <Divider label={t('auth.or')} labelPosition="center" />

      {error && (
        <Alert
          color="red"
          icon={<IconAlertTriangle size={16} />}
          withCloseButton
          onClose={() => setError(null)}
        >
          {error}
        </Alert>
      )}

      <form onSubmit={handleSubmit((values) => loginMutation.mutate(values))}>
        <Stack>
          <TextInput
            label={t('auth.email')}
            placeholder="you@example.com"
            leftSection={<IconMail size={16} />}
            autoComplete="email"
            error={errors.email?.message ? t(errors.email.message) : undefined}
            {...register('email')}
          />
          <PasswordInput
            label={t('auth.password')}
            placeholder="••••••••"
            leftSection={<IconLock size={16} />}
            autoComplete="current-password"
            error={errors.password?.message ? t(errors.password.message) : undefined}
            {...register('password')}
          />
          <Group justify="space-between">
            <Text size="xs" c="dimmed">
              {t('auth.demoHint')}
            </Text>
            <Anchor component={Link} to="/forgot-password" size="sm" fw={600}>
              {t('auth.forgot')}
            </Anchor>
          </Group>
          <Button type="submit" size="md" loading={loginMutation.isPending}>
            {t('auth.login')}
          </Button>
        </Stack>
      </form>

      <Text size="sm" ta="center" c="dimmed">
        {t('auth.noAccount')}{' '}
        <Anchor component={Link} to="/register" fw={700}>
          {t('auth.register')}
        </Anchor>
      </Text>
    </Stack>
  )
}
