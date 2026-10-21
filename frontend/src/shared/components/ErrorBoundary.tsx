import { Component, type ErrorInfo, type ReactNode } from 'react'
import { Button, Center, Code, Paper, Stack, Text, Title } from '@mantine/core'
import { IconRefresh } from '@tabler/icons-react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error?: Error
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Unhandled UI error', error, info)
  }

  render() {
    if (!this.state.hasError) return this.props.children
    return (
      <Center mih="100vh" p="md">
        <Paper withBorder radius="lg" p="xl" maw={560}>
          <Stack>
            <Title order={3}>Что-то пошло не так</Title>
            <Text c="dimmed" size="sm">
              Интерфейс столкнулся с непредвиденной ошибкой. Можно перезагрузить страницу —
              данные сохранятся.
            </Text>
            {this.state.error && (
              <Code block style={{ maxHeight: 160, overflow: 'auto' }}>
                {this.state.error.message}
              </Code>
            )}
            <Button
              leftSection={<IconRefresh size={16} />}
              onClick={() => window.location.reload()}
            >
              Перезагрузить
            </Button>
          </Stack>
        </Paper>
      </Center>
    )
  }
}
