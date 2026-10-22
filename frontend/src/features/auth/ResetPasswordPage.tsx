import { useState } from 'react'
import { Alert, Button, PasswordInput, Stack, Text, Title } from '@mantine/core'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { IconLock } from '@tabler/icons-react'
import { notifications } from '@mantine/notifications'
import { api } from '../../shared/api'
import { errorMessage } from '../../shared/api/errors'
import { resetPasswordSchema } from '../../shared/lib/validation'
import { z } from 'zod'

type Values = z.infer<typeof resetPasswordSchema>

export function ResetPasswordPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { password: '', passwordConfirm: '' },
  })

  const mutation = useMutation({
    mutationFn: (values: Values) => api.auth.resetPassword(values.password),
    onSuccess: () => {
      notifications.show({
        color: 'teal',
        title: t('notifications.typeSuccess'),
        message: t('account.saved'),
      })
      navigate('/login', { replace: true })
    },
    onError: (mutationError) => setError(errorMessage(mutationError)),
  })

  return (
    <Stack gap="lg">
      <Stack gap={4}>
        <Title order={2}>{t('auth.resetTitle')}</Title>
        <Text c="dimmed" size="sm">
          {t('auth.resetSubtitle')}
        </Text>
      </Stack>
      {error && (
        <Alert color="red" withCloseButton onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      <form onSubmit={handleSubmit((values) => mutation.mutate(values))}>
        <Stack>
          <PasswordInput
            label={t('auth.password')}
            leftSection={<IconLock size={16} />}
            error={errors.password?.message ? t(errors.password.message) : undefined}
            {...register('password')}
          />
          <PasswordInput
            label={t('auth.passwordConfirm')}
            leftSection={<IconLock size={16} />}
            error={
              errors.passwordConfirm?.message
                ? t(errors.passwordConfirm.message)
                : undefined
            }
            {...register('passwordConfirm')}
          />
          <Button type="submit" loading={mutation.isPending}>
            {t('common.save')}
          </Button>
        </Stack>
      </form>
    </Stack>
  )
}
