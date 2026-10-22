import { Box, Group, Text, UnstyledButton } from '@mantine/core'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { IconRobot } from '@tabler/icons-react'
import { tokens } from '../../theme/tokens'

export function Logo({ compact = false }: { compact?: boolean }) {
  const { t } = useTranslation()
  return (
    <UnstyledButton component={Link} to="/" aria-label={t('common.appName')}>
      <Group gap="xs" wrap="nowrap">
        <Box
          style={{
            width: 36,
            height: 36,
            borderRadius: 12,
            display: 'grid',
            placeItems: 'center',
            background: `linear-gradient(145deg, ${tokens.brand}, #00a8fc)`,
            color: 'white',
            boxShadow: '0 8px 20px rgba(88, 101, 242, 0.3)',
            flex: '0 0 auto',
          }}
        >
          <IconRobot size={22} stroke={1.9} />
        </Box>
        {!compact && (
          <Box>
            <Text fw={800} size="md" lh={1.1} className="bf-gradient-text">
              {t('common.appName')}
            </Text>
            <Text size="10px" c="dimmed" lh={1.2} fw={600}>
              {t('common.tagline')}
            </Text>
          </Box>
        )}
      </Group>
    </UnstyledButton>
  )
}
