import { useEffect, useRef, useState } from 'react'
import { Alert, Button, Center, Loader, Stack, Text, Title } from '@mantine/core'
import { IconAlertTriangle } from '@tabler/icons-react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../../shared/api'
import { errorMessage } from '../../shared/api/errors'
import { getAccessToken, useAuthStore } from '../../shared/stores/authStore'

export function OAuthCallbackPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const setSession = useAuthStore((state) => state.setSession)
  const started = useRef(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (started.current) return
    started.current = true
    const run = async () => {
      try {
        const user = await api.auth.me()
        setSession(user, getAccessToken() ?? 'oauth-session')
        navigate('/app', { replace: true })
      } catch (callbackError) {
        setError(errorMessage(callbackError))
      }
    }
    void run()
  }, [navigate, setSession])

  return (
    <Center mih="60vh">
      {error ? (
        <Stack align="center" gap="md">
          <Alert color="red" icon={<IconAlertTriangle size={16} />}>
            {error}
          </Alert>
          <Button onClick={() => navigate('/login', { replace: true })}>
            {t('auth.backToLogin')}
          </Button>
        </Stack>
      ) : (
        <Stack align="center" gap="sm">
          <Loader />
          <Title order={3}>{t('auth.oauthTitle')}</Title>
          <Text c="dimmed" size="sm">
            {t('auth.oauthSubtitle')}
          </Text>
        </Stack>
      )}
    </Center>
  )
}
