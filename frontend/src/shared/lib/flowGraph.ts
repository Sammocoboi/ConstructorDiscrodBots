import { getBlockDefinition } from '../blocks'
import type {
  FlowEdge,
  FlowIssue,
  FlowNode,
  FlowTestResult,
  FlowTraceStep,
} from '../api/types'

export function validateFlowGraph(nodes: FlowNode[], edges: FlowEdge[]): FlowIssue[] {
  const issues: FlowIssue[] = []
  const nodeIds = new Set(nodes.map((node) => node.id))
  const triggers = nodes.filter((node) => node.data.blockId.startsWith('trigger.'))
  const actions = nodes.filter((node) => node.data.blockId.startsWith('action.'))

  if (!nodes.length) {
    return [
      {
        id: 'empty',
        code: 'empty_flow',
        severity: 'error',
        message: 'Сценарий пуст. Добавьте хотя бы триггер и действие.',
      },
    ]
  }

  if (!triggers.length) {
    issues.push({
      id: 'no_trigger',
      code: 'no_trigger',
      severity: 'error',
      message: 'Нет триггера. Сценарий не сможет запуститься.',
    })
  }

  if (!actions.length) {
    issues.push({
      id: 'no_action',
      code: 'no_action',
      severity: 'warning',
      message: 'Нет действий. Сценарий ничего не делает.',
    })
  }

  for (const edge of edges) {
    if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target)) {
      issues.push({
        id: `dangling_${edge.id}`,
        code: 'dangling_edge',
        severity: 'error',
        message: 'Связь ссылается на удалённый блок.',
      })
    }
  }

  const incoming = new Map<string, number>()
  const outgoing = new Map<string, number>()
  for (const node of nodes) {
    incoming.set(node.id, 0)
    outgoing.set(node.id, 0)
  }
  for (const edge of edges) {
    incoming.set(edge.target, (incoming.get(edge.target) ?? 0) + 1)
    outgoing.set(edge.source, (outgoing.get(edge.source) ?? 0) + 1)
  }

  for (const node of nodes) {
    const definition = getBlockDefinition(node.data.blockId)
    if (!definition) {
      issues.push({
        id: `unknown_${node.id}`,
        code: 'unknown_block',
        severity: 'error',
        nodeId: node.id,
        message: `Неизвестный тип блока: ${node.data.blockId}.`,
      })
      continue
    }

    const incomingCount = incoming.get(node.id) ?? 0
    const outgoingCount = outgoing.get(node.id) ?? 0

    if (definition.category === 'trigger' && incomingCount > 0) {
      issues.push({
        id: `trigger_in_${node.id}`,
        code: 'trigger_has_input',
        severity: 'error',
        nodeId: node.id,
        message: `Триггер «${node.data.label}» не может иметь входящую связь.`,
      })
    }

    if (
      !definition.terminal &&
      definition.category !== 'trigger' &&
      outgoingCount === 0 &&
      definition.category !== 'action'
    ) {
      issues.push({
        id: `dead_end_${node.id}`,
        code: 'dead_end',
        severity: 'warning',
        nodeId: node.id,
        message: `Блок «${node.data.label}» не соединён со следующим шагом.`,
      })
    }

    if (definition.category === 'condition' && outgoingCount === 0) {
      issues.push({
        id: `condition_no_out_${node.id}`,
        code: 'condition_dead_end',
        severity: 'error',
        nodeId: node.id,
        message: `Условие «${node.data.label}» никуда не ведёт.`,
      })
    }

    for (const field of definition.fields) {
      if (!field.required) continue
      const value = node.data.config[field.key]
      if (value === undefined || value === null || value === '') {
        issues.push({
          id: `missing_${node.id}_${field.key}`,
          code: 'missing_field',
          severity: 'error',
          nodeId: node.id,
          message: `В блоке «${node.data.label}» не заполнено поле «${field.label}».`,
        })
      }
    }

    if (definition.permissions?.length) {
      const hasPermissions = node.data.config.permissionsOk !== false
      if (!hasPermissions) {
        issues.push({
          id: `perm_${node.id}`,
          code: 'permissions',
          severity: 'warning',
          nodeId: node.id,
          message: `Действие «${node.data.label}» требует прав: ${definition.permissions.join(', ')}.`,
        })
      }
    }
  }

  if (triggers.length) {
    const reachable = new Set<string>()
    const queue = triggers.map((node) => node.id)
    while (queue.length) {
      const current = queue.shift()
      if (!current || reachable.has(current)) continue
      reachable.add(current)
      for (const edge of edges) {
        if (edge.source === current && !reachable.has(edge.target)) queue.push(edge.target)
      }
    }
    for (const node of nodes) {
      if (!reachable.has(node.id)) {
        issues.push({
          id: `unreachable_${node.id}`,
          code: 'unreachable',
          severity: 'warning',
          nodeId: node.id,
          message: `Блок «${node.data.label}» недостижим из триггера.`,
        })
      }
    }
  }

  const visiting = new Set<string>()
  const visited = new Set<string>()
  const adjacency = new Map<string, string[]>()
  for (const edge of edges) {
    const list = adjacency.get(edge.source) ?? []
    list.push(edge.target)
    adjacency.set(edge.source, list)
  }
  const dfs = (nodeId: string): boolean => {
    if (visiting.has(nodeId)) return true
    if (visited.has(nodeId)) return false
    visiting.add(nodeId)
    for (const next of adjacency.get(nodeId) ?? []) {
      if (dfs(next)) return true
    }
    visiting.delete(nodeId)
    visited.add(nodeId)
    return false
  }
  if (nodes.some((node) => dfs(node.id))) {
    issues.push({
      id: 'cycle',
      code: 'cycle',
      severity: 'error',
      message: 'В сценарии есть цикл. Уберите повторяющиеся связи.',
    })
  }

  return issues
}

export function simulateFlow(nodes: FlowNode[], edges: FlowEdge[]): FlowTestResult {
  const steps: FlowTraceStep[] = []
  const variables: Record<string, unknown> = {
    'user.id': '842013445120',
    'user.name': 'new_member',
    'user.mention': '@new_member',
    'guild.name': 'Дизайн-сообщество',
    'guild.id': 'guild_design',
    'message.content': 'привет всем!',
  }

  if (!nodes.length) {
    return {
      success: false,
      durationMs: 0,
      steps: [
        {
          id: 'step_empty',
          title: 'Сценарий пуст',
          status: 'error',
          detail: 'Добавьте блоки и связи перед запуском.',
        },
      ],
      variables,
      output: 'Сценарий не выполнен.',
    }
  }

  const trigger = nodes.find((node) => node.data.blockId.startsWith('trigger.'))
  if (!trigger) {
    return {
      success: false,
      durationMs: 0,
      steps: [
        {
          id: 'step_no_trigger',
          title: 'Триггер не найден',
          status: 'error',
          detail: 'Без триггера сценарий не запускается.',
        },
      ],
      variables,
      output: 'Сценарий не выполнен.',
    }
  }

  const byId = new Map(nodes.map((node) => [node.id, node]))
  let current: FlowNode | undefined = trigger
  let guard = 0
  let output = ''

  while (current && guard < 50) {
    guard += 1
    const config = current.data.config

    if (current.data.blockId.startsWith('condition.')) {
      steps.push({
        id: `step_${current.id}`,
        nodeId: current.id,
        title: `Условие: ${current.data.label}`,
        status: 'ok',
        detail: 'Условие выполнено для тестового контекста.',
        variables: { ...variables },
      })
    } else if (current.data.blockId.startsWith('data.')) {
      const name = String(config.name ?? 'value')
      variables[name] = config.value ?? 'test'
      steps.push({
        id: `step_${current.id}`,
        nodeId: current.id,
        title: `Данные: ${current.data.label}`,
        status: 'ok',
        detail: `Переменная ${name} = ${String(variables[name])}`,
        variables: { ...variables },
      })
    } else if (current.data.blockId.startsWith('logic.')) {
      steps.push({
        id: `step_${current.id}`,
        nodeId: current.id,
        title: `Логика: ${current.data.label}`,
        status: 'ok',
        detail: current.data.blockId === 'logic.stop' ? 'Сценарий остановлен.' : 'Шаг выполнен.',
        variables: { ...variables },
      })
      if (current.data.blockId === 'logic.stop') break
    } else if (current.data.blockId.startsWith('action.')) {
      output = String(config.text ?? config.description ?? current.data.label)
      steps.push({
        id: `step_${current.id}`,
        nodeId: current.id,
        title: `Действие: ${current.data.label}`,
        status: 'ok',
        detail:
          current.data.blockId === 'action.send_message'
            ? `Сообщение отправлено в канал ${String(config.channelId ?? '#general')}.`
            : 'Действие выполнено в dry-run режиме.',
        variables: { ...variables },
      })
    } else {
      steps.push({
        id: `step_${current.id}`,
        nodeId: current.id,
        title: `Триггер: ${current.data.label}`,
        status: 'ok',
        detail: 'Событие получено, начинаем выполнение.',
        variables: { ...variables },
      })
    }

    const nextEdge = edges.find((edge) => edge.source === current?.id)
    current = nextEdge ? byId.get(nextEdge.target) : undefined
  }

  if (!steps.some((step) => step.title.startsWith('Действие'))) {
    steps.push({
      id: 'step_no_action',
      title: 'Действие не выполнено',
      status: 'error',
      detail: 'Сценарий завершился без действий.',
    })
    return {
      success: false,
      durationMs: steps.length * 18,
      steps,
      variables,
      output: 'Действий не найдено.',
    }
  }

  return {
    success: true,
    durationMs: steps.length * 18 + 9,
    steps,
    variables,
    output: output || 'Сценарий выполнен без вывода.',
  }
}

export function countIssueSeverity(issues: FlowIssue[], severity: FlowIssue['severity']) {
  return issues.filter((issue) => issue.severity === severity).length
}
