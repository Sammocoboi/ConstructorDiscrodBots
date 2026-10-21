import { useEffect, useState, type ReactNode } from 'react'
import { Button, Group, Modal, Stack, Text, TextInput } from '@mantine/core'
import { useTranslation } from 'react-i18next'

export function ConfirmModal({
  opened,
  onClose,
  onConfirm,
  title,
  description,
  confirmLabel,
  cancelLabel,
  color = 'red',
  loading = false,
  requireText,
  children,
}: {
  opened: boolean
  onClose: () => void
  onConfirm: () => void
  title: string
  description?: ReactNode
  confirmLabel?: string
  cancelLabel?: string
  color?: string
  loading?: boolean
  requireText?: string
  children?: ReactNode
}) {
  const { t } = useTranslation()
  const [value, setValue] = useState('')

  useEffect(() => {
    if (!opened) setValue('')
  }, [opened])

  const blocked = Boolean(requireText) && value.trim() !== requireText

  return (
    <Modal opened={opened} onClose={onClose} title={title} centered>
      <Stack gap="md">
        {description && <Text size="sm">{description}</Text>}
        {children}
        {requireText && (
          <TextInput
            label={`Введите «${requireText}» для подтверждения`}
            value={value}
            onChange={(event) => setValue(event.currentTarget.value)}
            placeholder={requireText}
            autoFocus
          />
        )}
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose} disabled={loading}>
            {cancelLabel ?? t('common.cancel')}
          </Button>
          <Button
            color={color}
            onClick={onConfirm}
            loading={loading}
            disabled={blocked}
          >
            {confirmLabel ?? t('common.confirm')}
          </Button>
        </Group>
      </Stack>
    </Modal>
  )
}
