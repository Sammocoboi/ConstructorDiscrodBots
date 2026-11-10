import { useId, useRef, useState, type KeyboardEvent } from 'react'
import { Box, Group, Stack, Text, Textarea, UnstyledButton, type TextareaProps } from '@mantine/core'
import { useTranslation } from 'react-i18next'

// These are the fields exposed by the Discord runtime in its user context.
const userFields = ['id', 'name', 'display_name', 'mention'] as const
type UserField = (typeof userFields)[number]

type Completion = { start: number; end: number; prefix: string }

function getCompletion(value: string, caret: number): Completion | null {
  const before = value.slice(0, caret)
  if (before.endsWith('{user.}')) {
    return { start: caret - '{user.}'.length, end: caret, prefix: '' }
  }

  const match = /\{user\.([a-z0-9_-]*)$/i.exec(before)
  if (!match) return null

  const suffix = /^[a-z0-9_-]*\}?/i.exec(value.slice(caret))?.[0] ?? ''
  return { start: match.index, end: caret + suffix.length, prefix: match[1].toLowerCase() }
}

type Props = Pick<TextareaProps, 'label' | 'description' | 'placeholder'> & {
  value: string
  onChange: (value: string) => void
}

export function FlowTemplateTextarea({ value, onChange, ...props }: Props) {
  const { t } = useTranslation()
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const listId = useId()
  const [completion, setCompletion] = useState<Completion | null>(null)
  const [activeIndex, setActiveIndex] = useState(0)
  const options = completion ? userFields.filter((field) => field.startsWith(completion.prefix)) : []
  const activeField = options[activeIndex]

  function updateCompletion(input: HTMLTextAreaElement) {
    setCompletion(
      input.selectionStart === input.selectionEnd
        ? getCompletion(input.value, input.selectionStart)
        : null,
    )
    setActiveIndex(0)
  }

  function insertField(field: UserField) {
    if (!completion) return

    const expression = `{user.${field}}`
    const caret = completion.start + expression.length
    onChange(value.slice(0, completion.start) + expression + value.slice(completion.end))
    setCompletion(null)
    requestAnimationFrame(() => {
      inputRef.current?.focus()
      inputRef.current?.setSelectionRange(caret, caret)
    })
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (!options.length || event.nativeEvent.isComposing) return

    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      const step = event.key === 'ArrowDown' ? 1 : -1
      setActiveIndex((index) => (index + step + options.length) % options.length)
    } else if (event.key === 'Enter' && activeField && !event.shiftKey) {
      event.preventDefault()
      insertField(activeField)
    } else if (event.key === 'Escape') {
      event.preventDefault()
      setCompletion(null)
    }
  }

  return (
    <Stack gap={4}>
      <Textarea
        {...props}
        ref={inputRef}
        value={value}
        onChange={(event) => {
          onChange(event.currentTarget.value)
          updateCompletion(event.currentTarget)
        }}
        onFocus={(event) => updateCompletion(event.currentTarget)}
        onSelect={(event) => updateCompletion(event.currentTarget)}
        onBlur={() => setCompletion(null)}
        onKeyDown={handleKeyDown}
        aria-autocomplete="list"
        aria-controls={options.length ? listId : undefined}
        aria-activedescendant={activeField ? `${listId}-${activeField}` : undefined}
        autosize
        minRows={2}
        maxRows={6}
      />
      {options.length > 0 && (
        <Box
          id={listId}
          role="listbox"
          aria-label={t('flows.userFields.label')}
          p={4}
          style={{
            border: '1px solid var(--mantine-color-default-border)',
            borderRadius: 'var(--mantine-radius-sm)',
          }}
        >
          {options.map((field, index) => (
            <UnstyledButton
              key={field}
              id={`${listId}-${field}`}
              type="button"
              role="option"
              aria-selected={index === activeIndex}
              tabIndex={-1}
              w="100%"
              px="xs"
              py={4}
              bg={index === activeIndex ? 'var(--mantine-color-default-hover)' : undefined}
              onMouseDown={(event) => event.preventDefault()}
              onMouseEnter={() => setActiveIndex(index)}
              onClick={() => insertField(field)}
            >
              <Group gap={4} justify="space-between">
                <Text component="code" size="xs">{`user.${field}`}</Text>
                <Text size="xs" c="dimmed">{t(`flows.userFields.${field}`)}</Text>
              </Group>
            </UnstyledButton>
          ))}
        </Box>
      )}
    </Stack>
  )
}
