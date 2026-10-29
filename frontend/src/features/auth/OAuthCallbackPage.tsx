import { useEffect, useRef, useState } from 'react'
import { Alert, Button, Center, Loader, Stack, Text, Title } from '@mantine/core'
import { IconAlertTriangle } from '@tabler/icons-react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { http } from '../../shared/api/http'
import { errorMessage } from '../../shared/api/errors'
import { useAuthStore } from '../../shared/stores/authStore'
import type { User } from '../../shared/api/types'

interface ExchangeResponse {
  access: string
  user: User
}

export function OAuthCallbackPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const setSession = useAuthStore((state) => state.setSession)
  const started = useRef(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (started.current) return
    started.current = true

    const urlError = searchParams.get('error')
    if (urlError) {
      setError(urlError === 'access_denied' ? t('auth.oauthDenied') : urlError)
      return
    }

    const code = searchParams.get('code')
    if (!code) {
      setError(t('auth.oauthMissingCode'))
      return
    }

    const run = async () => {
      try {
        const data = await http.post<ExchangeResponse>('/auth/discord/exchange', { code })
        setSession(data.user, data.access)
        navigate('/app', { replace: true })
      } catch (callbackError) {
        setError(errorMessage(callbackError))
      }
    }
    void run()
  }, [navigate, setSession, searchParams, t])

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
