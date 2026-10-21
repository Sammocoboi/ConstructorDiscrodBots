import {
  Badge,
  Button,
  Container,
  Group,
  Paper,
  Stack,
  Text,
  Title,
} from '@mantine/core'

export function App() {
  return (
    <Container size="sm" py="xl">
      <Paper withBorder radius="lg" p="xl">
        <Stack gap="md">
          <Group justify="space-between" align="flex-start">
            <div>
              <Title order={1}>BotForge</Title>
              <Text c="dimmed">Конструктор Discord-ботов</Text>
            </div>
            <Badge color="indigo" variant="light">
              frontend scaffold
            </Badge>
          </Group>

          <Text>
            Фронтенд подключён к репозиторию. Дальше здесь появятся кабинет,
            редактор сценариев и библиотека команд.
          </Text>

          <Group>
            <Button
              component="a"
              href="http://localhost:8000/admin/"
              target="_blank"
              rel="noreferrer"
            >
              Django admin
            </Button>
            <Button
              component="a"
              href="http://localhost:8000/api/docs/"
              target="_blank"
              rel="noreferrer"
              variant="light"
            >
              API docs
            </Button>
          </Group>
        </Stack>
      </Paper>
    </Container>
  )
}
