import { useEffect, useRef, useState } from 'react'
import { Alert, Anchor, Button, Group, Stack, Text, ThemeIcon, Title } from '@mantine/core'
import { IconArrowRight, IconCheck, IconMail } from '@tabler/icons-react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useMutation } from '@tanstack/react-query'
import { api } from '../../shared/api'
import { errorMessage } from '../../shared/api/errors'
import { useAuthStore } from '../../shared/stores/authStore'

export function VerifyEmailPage() {
  const { t } = useTranslation()
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const email = params.get('email') ?? ''
  const token = params.get('token') ?? ''
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const [error, setError] = useState<string | null>(null)
  const [verified, setVerified] = useState(false)
  const started = useRef(false)

  const verifyMutation = useMutation({
    mutationFn: () => api.auth.verifyEmail(token),
    onSuccess: () => setVerified(true),
    onError: (mutationError) => setError(errorMessage(mutationError)),
  })

  useEffect(() => {
    if (started.current || !token) return
    started.current = true
    verifyMutation.mutate()
  }, [token, verifyMutation])

  return (
    <Stack gap="lg" align="center" ta="center">
      <ThemeIcon size={70} radius="xl" variant="light" color="brand">
        <IconMail size={34} />
      </ThemeIcon>
      <Stack gap={4}>
        <Title order={2}>{verified ? t('notifications.typeSuccess') : t('auth.verifyTitle')}</Title>
        <Text c="dimmed" size="sm">
          {t('auth.verifySubtitle', { email: email || 'you@example.com' })}
        </Text>
      </Stack>

      {error && (
        <Alert color="red" w="100%" withCloseButton onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {!token && (
        <Alert color="yellow" w="100%">
          {t('auth.verifyMissingToken')}
        </Alert>
      )}
      {verified && (
        <Alert color="teal" icon={<IconCheck size={16} />} w="100%">
          {t('auth.verifySuccess')}
        </Alert>
      )}

      <Group>
        {token && !verified && (
          <Button
            variant="light"
            onClick={() => verifyMutation.mutate()}
            loading={verifyMutation.isPending}
          >
            {t('common.confirm')}
          </Button>
        )}
        {isAuthenticated && (
          <Button
            rightSection={<IconArrowRight size={16} />}
            onClick={() => navigate('/app')}
          >
            {t('nav.dashboard')}
          </Button>
        )}
      </Group>

      {!isAuthenticated && (
        <Anchor component={Link} to="/login" size="sm" fw={600}>
          {t('auth.backToLogin')}
        </Anchor>
      )}
    </Stack>
  )
}
