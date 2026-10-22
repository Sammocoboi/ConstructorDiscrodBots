import { useState } from 'react'
import {
  Alert,
  Anchor,
  Button,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { IconArrowLeft, IconCheck, IconMail } from '@tabler/icons-react'
import { api } from '../../shared/api'
import { errorMessage } from '../../shared/api/errors'
import { forgotPasswordSchema } from '../../shared/lib/validation'
import { z } from 'zod'

type Values = z.infer<typeof forgotPasswordSchema>

export function ForgotPasswordPage() {
  const { t } = useTranslation()
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: '' },
  })

  const mutation = useMutation({
    mutationFn: (values: Values) => api.auth.forgotPassword(values.email),
    onSuccess: () => setSent(true),
    onError: (mutationError) => setError(errorMessage(mutationError)),
  })

  return (
    <Stack gap="lg">
      <Stack gap={4}>
        <Title order={2}>{t('auth.forgotTitle')}</Title>
        <Text c="dimmed" size="sm">
          {t('auth.forgotSubtitle')}
        </Text>
      </Stack>

      {sent ? (
        <Alert color="teal" icon={<IconCheck size={16} />} title={t('auth.verifyTitle')}>
          <Text size="sm">
            {t('auth.verifySubtitle', { email: getValues('email') })}
          </Text>
        </Alert>
      ) : (
        <>
          {error && (
            <Alert color="red" withCloseButton onClose={() => setError(null)}>
              {error}
            </Alert>
          )}
          <form onSubmit={handleSubmit((values) => mutation.mutate(values))}>
            <Stack>
              <TextInput
                label={t('auth.email')}
                leftSection={<IconMail size={16} />}
                placeholder="you@example.com"
                error={errors.email?.message ? t(errors.email.message) : undefined}
                {...register('email')}
              />
              <Button type="submit" loading={mutation.isPending}>
                {t('auth.sendLink')}
              </Button>
            </Stack>
          </form>
        </>
      )}

      <Anchor component={Link} to="/login" size="sm" fw={600}>
        <IconArrowLeft size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />
        {t('auth.backToLogin')}
      </Anchor>
    </Stack>
  )
}
