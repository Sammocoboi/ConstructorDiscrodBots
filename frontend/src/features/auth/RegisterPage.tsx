import { useState } from 'react'
import {
  Alert,
  Anchor,
  Button,
  Checkbox,
  Divider,
  Group,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { IconAlertTriangle, IconBrandDiscord, IconLock, IconMail, IconUser } from '@tabler/icons-react'
import { api } from '../../shared/api'
import { errorMessage } from '../../shared/api/errors'
import { registerSchema, type RegisterFormValues } from '../../shared/lib/validation'
import { useAuthStore } from '../../shared/stores/authStore'

export function RegisterPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const setSession = useAuthStore((state) => state.setSession)
  const [error, setError] = useState<string | null>(null)

  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { name: '', email: '', password: '', passwordConfirm: '', terms: undefined },
  })

  const registerMutation = useMutation({
    mutationFn: (values: RegisterFormValues) =>
      api.auth.register({
        name: values.name,
        email: values.email,
        password: values.password,
      }),
    onSuccess: (session) => {
      if (session.accessToken) {
        setSession(session.user, session.accessToken)
      }
      navigate(`/verify-email?email=${encodeURIComponent(session.user.email)}`, {
        replace: true,
      })
    },
    onError: (mutationError) => setError(errorMessage(mutationError)),
  })

  const discordMutation = useMutation({
    mutationFn: () => api.auth.loginWithDiscord(),
    onSuccess: (session) => {
      if (!session) return
      setSession(session.user, session.accessToken)
      navigate('/app', { replace: true })
    },
    onError: (mutationError) => setError(errorMessage(mutationError)),
  })

  return (
    <Stack gap="lg">
      <Stack gap={4}>
        <Title order={2}>{t('auth.registerTitle')}</Title>
        <Text c="dimmed" size="sm">
          {t('auth.registerSubtitle')}
        </Text>
      </Stack>

      <Button
        size="md"
        leftSection={<IconBrandDiscord size={19} />}
        loading={discordMutation.isPending}
        onClick={() => discordMutation.mutate()}
      >
        {t('auth.discordRegister')}
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

      <form onSubmit={handleSubmit((values) => registerMutation.mutate(values))}>
        <Stack>
          <TextInput
            label={t('auth.name')}
            placeholder="danila"
            leftSection={<IconUser size={16} />}
            autoComplete="nickname"
            error={errors.name?.message ? t(errors.name.message) : undefined}
            {...register('name')}
          />
          <TextInput
            label={t('auth.email')}
            placeholder="you@example.com"
            leftSection={<IconMail size={16} />}
            autoComplete="email"
            error={errors.email?.message ? t(errors.email.message) : undefined}
            {...register('email')}
          />
          <Group grow align="flex-start">
            <PasswordInput
              label={t('auth.password')}
              placeholder="••••••••"
              leftSection={<IconLock size={16} />}
              autoComplete="new-password"
              error={errors.password?.message ? t(errors.password.message) : undefined}
              {...register('password')}
            />
            <PasswordInput
              label={t('auth.passwordConfirm')}
              placeholder="••••••••"
              leftSection={<IconLock size={16} />}
              autoComplete="new-password"
              error={
                errors.passwordConfirm?.message
                  ? t(errors.passwordConfirm.message)
                  : undefined
              }
              {...register('passwordConfirm')}
            />
          </Group>
          <Controller
            name="terms"
            control={control}
            render={({ field }) => (
              <Checkbox
                size="sm"
                label={t('auth.terms')}
                checked={field.value === true}
                onChange={(event) => field.onChange(event.currentTarget.checked)}
                error={errors.terms?.message ? t(errors.terms.message) : undefined}
              />
            )}
          />
          <Button type="submit" size="md" loading={registerMutation.isPending}>
            {t('auth.register')}
          </Button>
        </Stack>
      </form>

      <Text size="sm" ta="center" c="dimmed">
        {t('auth.hasAccount')}{' '}
        <Anchor component={Link} to="/login" fw={700}>
          {t('auth.login')}
        </Anchor>
      </Text>
    </Stack>
  )
}
