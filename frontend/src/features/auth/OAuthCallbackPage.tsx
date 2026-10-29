import { useEffect, useRef, useState } from 'react'
import { Alert, Button, Center, Loader, Stack, Text, Title } from '@mantine/core'
import { IconAlertTriangle } from '@tabler/icons-react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../../shared/api'
import { errorMessage } from '../../shared/api/errors'
import { useAuthStore } from '../../shared/stores/authStore'

export function OAuthCallbackPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const setSession = useAuthStore((state) => state.setSession)
  const started = useRef(false)
  const [error, setError] = useState<string | null>(null)

  const code = params.get('code')
  const oauthError = params.get('error')

  useEffect(() => {
    if (started.current) return
    started.current = true

    if (oauthError) {
      setError(t('auth.oauthDenied'))
      return
    }
    if (!code) {
      setError(t('auth.oauthMissingCode'))
      return
    }

    const run = async () => {
      try {
        const session = await api.auth.exchangeDiscordCode(code)
        if (!session.accessToken) {
          setError(t('auth.oauthFailed'))
          return
        }
        setSession(session.user, session.accessToken)
        navigate('/app', { replace: true })
      } catch (callbackError) {
        setError(errorMessage(callbackError, t('auth.oauthFailed')))
      }
    }
    void run()
  }, [code, oauthError, navigate, setSession, t])

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
