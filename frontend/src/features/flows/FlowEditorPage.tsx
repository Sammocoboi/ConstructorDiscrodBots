import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Alert,
  Badge,
  Box,
  Button,
  Card,
  ColorInput,
  Divider,
  Group,
  Modal,
  NumberInput,
  ScrollArea,
  Select,
  SegmentedControl,
  SimpleGrid,
  Stack,
  Switch,
  Text,
  TextInput,
  Textarea,
  ThemeIcon,
  Title,
  Tooltip,
} from '@mantine/core'
import { useMediaQuery } from '@mantine/hooks'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'
import {
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  addEdge,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type Node,
  type NodeProps,
  type OnNodesChange,
} from '@xyflow/react'
import {
  IconAlertTriangle,
  IconArrowLeft,
  IconCheck,
  IconDeviceFloppy,
  IconGitBranch,
  IconPlayerPlay,
  IconPlus,
  IconRocket,
  IconSearch,
  IconTrash,
  IconArrowBackUp,
  IconArrowForwardUp,
  IconX,
} from '@tabler/icons-react'
import { useMutation } from '@tanstack/react-query'
import { notifications } from '@mantine/notifications'
import { api } from '../../shared/api'
import {
  qk,
  useBot,
  useFlow,
  useToastMutation,
} from '../../shared/api/hooks'
import type {
  FlowEdge,
  FlowIssue,
  FlowNode,
  FlowNodeData,
  FlowSnapshot,
  FlowTestResult,
} from '../../shared/api/types'
import {
  blockCategoryMeta,
  blockDefinitions,
  getBlockDefinition,
  type BlockCategory,
  type BlockDefinition,
  type BlockField,
} from '../../shared/blocks'
import { AppIcon } from '../../shared/components/icons'
import { ErrorState, LoadingState } from '../../shared/components/states'
import { simulateFlow, validateFlowGraph } from '../../shared/lib/flowGraph'
import { formatRelative } from '../../shared/lib/format'

type FlowNodeType = Node<FlowNodeData>

function defaultConfig(definition: BlockDefinition) {
  const config: Record<string, unknown> = {}
  for (const field of definition.fields) {
    if (field.type === 'boolean') config[field.key] = false
    else if (field.type === 'number' || field.type === 'duration')
      config[field.key] = field.min ?? 0
    else if (field.type === 'select') config[field.key] = field.options?.[0]?.value ?? ''
    else if (field.type === 'color') config[field.key] = '#5865F2'
    else config[field.key] = ''
  }
  return config
}

function toFlowNodes(nodes: FlowNodeType[]): FlowNode[] {
  return nodes.map((node) => ({
    id: node.id,
    type: 'block',
    position: node.position,
    data: node.data,
  }))
}

function toFlowEdges(edges: Edge[]): FlowEdge[] {
  return edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    sourceHandle: edge.sourceHandle,
    targetHandle: edge.targetHandle,
  }))
}

function fromFlowNodes(nodes: FlowNode[]): FlowNodeType[] {
  return nodes.map((node) => ({
    id: node.id,
    type: 'block',
    position: node.position,
    data: node.data,
  }))
}

function fromFlowEdges(edges: FlowEdge[]): Edge[] {
  return edges.map((edge) => ({ ...edge, animated: true }))
}

const BlockNode = memo(function BlockNode({ data, selected }: NodeProps) {
  const nodeData = data as FlowNodeData
  const definition = getBlockDefinition(nodeData.blockId)
  const meta = definition ? blockCategoryMeta[definition.category] : blockCategoryMeta.action
  return (
    <Box
      style={{
        minWidth: 210,
        maxWidth: 260,
        borderRadius: 14,
        background: 'var(--mantine-color-body)',
        border: `2px solid ${selected ? 'var(--mantine-color-brand-5)' : meta.color}`,
        boxShadow: selected
          ? `0 0 0 4px color-mix(in srgb, ${meta.color} 22%, transparent)`
          : '0 8px 24px rgba(20, 24, 40, 0.12)',
        overflow: 'hidden',
      }}
    >
      {definition?.category !== 'trigger' && (
        <Handle
          type="target"
          position={Position.Left}
          style={{ width: 10, height: 10, background: meta.color }}
        />
      )}
      <Box px="sm" py={6} style={{ background: `${meta.color}1f` }}>
        <Group gap={6} wrap="nowrap">
          <AppIcon name={definition?.icon ?? 'box'} size={13} color={meta.color} />
          <Text size="10px" fw={800} tt="uppercase" c={meta.color} style={{ letterSpacing: '0.06em' }}>
            {meta.label}
          </Text>
        </Group>
      </Box>
      <Box p="sm">
        <Text size="sm" fw={700} lineClamp={2}>
          {nodeData.label}
        </Text>
        <Text size="xs" c="dimmed" lineClamp={2} mt={2}>
          {definition?.description}
        </Text>
        {nodeData.validationMessage && (
          <Text size="10px" c="red" mt={4}>
            {nodeData.validationMessage}
          </Text>
        )}
      </Box>
      {!definition?.terminal && (
        <Handle
          type="source"
          position={Position.Right}
          style={{ width: 10, height: 10, background: meta.color }}
        />
      )}
    </Box>
  )
})

const nodeTypes = { block: BlockNode }

function FieldEditor({
  field,
  value,
  channels,
  roles,
  onChange,
}: {
  field: BlockField
  value: unknown
  channels: { value: string; label: string }[]
  roles: { value: string; label: string }[]
  onChange: (value: unknown) => void
}) {
  const label = `${field.label}${field.required ? ' *' : ''}`
  if (field.type === 'boolean') {
    return (
      <Switch
        label={label}
        checked={Boolean(value)}
        onChange={(event) => onChange(event.currentTarget.checked)}
      />
    )
  }
  if (field.type === 'number' || field.type === 'duration') {
    return (
      <NumberInput
        label={label}
        description={field.description}
        value={typeof value === 'number' ? value : Number(value ?? 0)}
        min={field.min}
        max={field.max}
        suffix={field.type === 'duration' ? ' сек' : undefined}
        onChange={(next) => onChange(typeof next === 'number' ? next : Number(next) || 0)}
      />
    )
  }
  if (field.type === 'select') {
    return (
      <Select
        label={label}
        description={field.description}
        data={field.options ?? []}
        value={typeof value === 'string' ? value : null}
        onChange={(next) => onChange(next ?? '')}
        allowDeselect={false}
      />
    )
  }
  if (field.type === 'channel') {
    return (
      <Select
        label={label}
        description={field.description}
        data={channels}
        value={typeof value === 'string' && value ? value : null}
        onChange={(next) => onChange(next ?? '')}
        searchable
        clearable
        placeholder="Выберите канал"
      />
    )
  }
  if (field.type === 'role') {
    return (
      <Select
        label={label}
        description={field.description}
        data={roles}
        value={typeof value === 'string' && value ? value : null}
        onChange={(next) => onChange(next ?? '')}
        searchable
        clearable
        placeholder="Выберите роль"
      />
    )
  }
  if (field.type === 'color') {
    return (
      <ColorInput
        label={label}
        value={typeof value === 'string' ? value : '#5865F2'}
        onChange={(next) => onChange(next)}
        format="hex"
        swatches={['#5865F2', '#3BA55D', '#FAA81A', '#ED4245', '#00A8FC']}
      />
    )
  }
  if (field.type === 'textarea') {
    return (
      <Textarea
        label={label}
        description={field.description}
        placeholder={field.placeholder}
        value={typeof value === 'string' ? value : ''}
        onChange={(event) => onChange(event.currentTarget.value)}
        autosize
        minRows={2}
        maxRows={6}
      />
    )
  }
  return (
    <TextInput
      label={label}
      description={field.description}
      placeholder={field.placeholder}
      value={typeof value === 'string' ? value : String(value ?? '')}
      onChange={(event) => onChange(event.currentTarget.value)}
    />
  )
}

export default function FlowEditorPage() {
  const { t } = useTranslation()
  const { botId, flowId } = useParams()
  const isMobile = useMediaQuery('(max-width: 62em)')
  const { data: bot } = useBot(botId)
  const { data: flow, isLoading, isError, refetch } = useFlow(botId, flowId)
  const [nodes, setNodes, handleNodesChange] = useNodesState<FlowNodeType>([])
  const [edges, setEdges, handleEdgesChange] = useEdgesState<Edge>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [paletteQuery, setPaletteQuery] = useState('')
  const [mode, setMode] = useState('canvas')
  const [dirty, setDirty] = useState(false)
  const [lastSaved, setLastSaved] = useState<string | null>(null)
  const [hydratedId, setHydratedId] = useState<string | null>(null)
  const [issues, setIssues] = useState<FlowIssue[] | null>(null)
  const [issuesOpened, setIssuesOpened] = useState(false)
  const [testResult, setTestResult] = useState<FlowTestResult | null>(null)
  const [testOpened, setTestOpened] = useState(false)
  const [publishOpened, setPublishOpened] = useState(false)
  const [publishComment, setPublishComment] = useState('')
  const [simpleBlockId, setSimpleBlockId] = useState<string | null>(null)
  const [, setHistoryTick] = useState(0)

  const nodesRef = useRef<FlowNodeType[]>([])
  const edgesRef = useRef<Edge[]>([])
  const dirtyRef = useRef(false)
  const historyRef = useRef<FlowSnapshot[]>([])
  const historyIndexRef = useRef(-1)

  useEffect(() => {
    nodesRef.current = nodes
  }, [nodes])
  useEffect(() => {
    edgesRef.current = edges
  }, [edges])

  const markDirty = useCallback(() => {
    dirtyRef.current = true
    setDirty(true)
  }, [])

  const pushHistory = useCallback((nextNodes: FlowNodeType[], nextEdges: Edge[]) => {
    const snapshot: FlowSnapshot = {
      nodes: toFlowNodes(nextNodes),
      edges: toFlowEdges(nextEdges),
    }
    const trimmed = historyRef.current.slice(0, historyIndexRef.current + 1)
    trimmed.push(snapshot)
    if (trimmed.length > 50) trimmed.shift()
    historyRef.current = trimmed
    historyIndexRef.current = trimmed.length - 1
    setHistoryTick((tick) => tick + 1)
  }, [])

  useEffect(() => {
    if (!flow || hydratedId === flow.id) return
    const nextNodes = fromFlowNodes(flow.nodes)
    const nextEdges = fromFlowEdges(flow.edges)
    setNodes(nextNodes)
    setEdges(nextEdges)
    setHydratedId(flow.id)
    setDirty(false)
    dirtyRef.current = false
    historyRef.current = [{ nodes: flow.nodes, edges: flow.edges }]
    historyIndexRef.current = 0
  }, [flow, hydratedId, setEdges, setNodes])

  const saveMutation = useMutation({
    mutationFn: (snapshot: FlowSnapshot) =>
      api.flows.save(botId as string, flowId as string, snapshot),
    onSuccess: () => {
      dirtyRef.current = false
      setDirty(false)
      setLastSaved(new Date().toISOString())
    },
    onError: (error) => {
      dirtyRef.current = true
      setDirty(true)
      notifications.show({
        color: 'red',
        title: t('common.error'),
        message: error instanceof Error ? error.message : t('errors.unknown'),
      })
    },
  })

  const saveRef = useRef(saveMutation.mutate)
  saveRef.current = saveMutation.mutate

  useEffect(() => {
    const timer = window.setInterval(() => {
      if (!dirtyRef.current) return
      dirtyRef.current = false
      saveRef.current({
        nodes: toFlowNodes(nodesRef.current),
        edges: toFlowEdges(edgesRef.current),
      })
    }, 10_000)
    return () => window.clearInterval(timer)
  }, [])

  const snapshot = useCallback(
    (): FlowSnapshot => ({
      nodes: toFlowNodes(nodes),
      edges: toFlowEdges(edges),
    }),
    [edges, nodes],
  )

  const saveNow = () => {
    dirtyRef.current = false
    saveMutation.mutate(snapshot(), {
      onSuccess: () => {
        notifications.show({ color: 'teal', message: t('common.saved') })
      },
    })
  }

  const validateMutation = useMutation({
    mutationFn: () =>
      api.flows.validate(botId as string, flowId as string, snapshot()),
    onSuccess: (result) => {
      setIssues(result)
      setIssuesOpened(true)
    },
    onError: () => {
      setIssues(validateFlowGraph(toFlowNodes(nodes), toFlowEdges(edges)))
      setIssuesOpened(true)
    },
  })

  const testMutation = useMutation({
    mutationFn: () => api.flows.test(botId as string, flowId as string, snapshot()),
    onSuccess: (result) => {
      setTestResult(result)
      setTestOpened(true)
    },
    onError: () => {
      setTestResult(simulateFlow(toFlowNodes(nodes), toFlowEdges(edges)))
      setTestOpened(true)
    },
  })

  const publishMutation = useToastMutation({
    mutationFn: async () => {
      await api.flows.save(botId as string, flowId as string, snapshot())
      return api.flows.publish(botId as string, flowId as string, publishComment)
    },
    successMessage: t('flows.published'),
    invalidateKeys: [qk.flows(botId ?? '')],
    onSuccess: () => {
      setPublishOpened(false)
      dirtyRef.current = false
      setDirty(false)
      void refetch()
    },
  })

  const onNodesChange: OnNodesChange<FlowNodeType> = (changes) => {
    handleNodesChange(changes)
    if (
      changes.some(
        (change) =>
          change.type === 'position' ||
          change.type === 'remove' ||
          change.type === 'add' ||
          change.type === 'replace',
      )
    ) {
      markDirty()
    }
  }

  const onEdgesChange = (changes: Parameters<typeof handleEdgesChange>[0]) => {
    handleEdgesChange(changes)
    if (changes.some((change) => change.type === 'remove' || change.type === 'add')) {
      markDirty()
      pushHistory(nodesRef.current, edgesRef.current)
    }
  }

  const onConnect = (connection: Connection) => {
    if (isMobile) return
    const nextEdges = addEdge(
      {
        ...connection,
        id: `edge_${Date.now()}`,
        animated: true,
      },
      edges,
    )
    setEdges(nextEdges)
    pushHistory(nodes, nextEdges)
    markDirty()
  }

  const addBlock = (definition: BlockDefinition) => {
    if (isMobile) return
    const id = `n_${Date.now()}_${Math.random().toString(36).slice(2, 5)}`
    const newNode: FlowNodeType = {
      id,
      type: 'block',
      position: {
        x: 80 + Math.random() * 160,
        y: 80 + Math.random() * 220,
      },
      data: {
        blockId: definition.id,
        label: definition.title,
        config: defaultConfig(definition),
      },
    }
    const nextNodes = [...nodes, newNode]
    setNodes(nextNodes)
    setSelectedId(id)
    pushHistory(nextNodes, edges)
    markDirty()
  }

  const updateNode = (id: string, patch: Partial<FlowNodeData>) => {
    setNodes((current) =>
      current.map((node) =>
        node.id === id ? { ...node, data: { ...node.data, ...patch } } : node,
      ),
    )
    markDirty()
  }

  const updateConfig = (id: string, key: string, value: unknown) => {
    setNodes((current) =>
      current.map((node) =>
        node.id === id
          ? {
              ...node,
              data: {
                ...node.data,
                config: { ...node.data.config, [key]: value },
              },
            }
          : node,
      ),
    )
    markDirty()
  }

  const removeNode = (id: string) => {
    const nextNodes = nodes.filter((node) => node.id !== id)
    const nextEdges = edges.filter((edge) => edge.source !== id && edge.target !== id)
    setNodes(nextNodes)
    setEdges(nextEdges)
    if (selectedId === id) setSelectedId(null)
    pushHistory(nextNodes, nextEdges)
    markDirty()
  }

  const undo = () => {
    if (historyIndexRef.current <= 0) return
    historyIndexRef.current -= 1
    const target = historyRef.current[historyIndexRef.current]
    setNodes(fromFlowNodes(target.nodes))
    setEdges(fromFlowEdges(target.edges))
    setSelectedId(null)
    markDirty()
  }

  const redo = () => {
    if (historyIndexRef.current >= historyRef.current.length - 1) return
    historyIndexRef.current += 1
    const target = historyRef.current[historyIndexRef.current]
    setNodes(fromFlowNodes(target.nodes))
    setEdges(fromFlowEdges(target.edges))
    setSelectedId(null)
    markDirty()
  }

  const channels = useMemo(() => {
    if (!bot) return []
    return bot.guilds.flatMap((guild) =>
      guild.channels
        .filter((channel) => channel.type === 'text' || channel.type === 'forum')
        .map((channel) => ({
          value: channel.id,
          label: `${guild.name} · #${channel.name}`,
        })),
    )
  }, [bot])

  const roles = useMemo(() => {
    if (!bot) return []
    return bot.guilds.flatMap((guild) =>
      guild.roles.map((role) => ({
        value: role.id,
        label: `${guild.name} · ${role.name}`,
      })),
    )
  }, [bot])

  const selectedNode = nodes.find((node) => node.id === selectedId)
  const selectedDefinition = selectedNode
    ? getBlockDefinition(selectedNode.data.blockId)
    : undefined

  const groupedBlocks = useMemo(() => {
    const normalized = paletteQuery.trim().toLowerCase()
    const groups: Record<string, BlockDefinition[]> = {}
    for (const definition of blockDefinitions) {
      if (
        normalized &&
        !definition.title.toLowerCase().includes(normalized) &&
        !definition.description.toLowerCase().includes(normalized)
      ) {
        continue
      }
      groups[definition.category] = groups[definition.category] ?? []
      groups[definition.category].push(definition)
    }
    return groups
  }, [paletteQuery])

  const orderedNodes = useMemo(() => {
    if (!nodes.length) return []
    const trigger = nodes.find((node) => node.data.blockId.startsWith('trigger.'))
    const result: FlowNodeType[] = []
    const seen = new Set<string>()
    let current: FlowNodeType | undefined = trigger
    while (current && !seen.has(current.id)) {
      seen.add(current.id)
      result.push(current)
      const edge: Edge | undefined = edges.find((item) => item.source === current?.id)
      current = edge ? nodes.find((node) => node.id === edge.target) : undefined
    }
    for (const node of nodes) if (!seen.has(node.id)) result.push(node)
    return result
  }, [edges, nodes])

  const addSimpleStep = (blockId: string | null) => {
    const definition = blockId ? getBlockDefinition(blockId) : undefined
    if (!definition) return
    const id = `n_${Date.now()}_simple`
    const last = orderedNodes[orderedNodes.length - 1]
    const newNode: FlowNodeType = {
      id,
      type: 'block',
      position: { x: 80, y: (orderedNodes.length + 1) * 160 },
      data: {
        blockId: definition.id,
        label: definition.title,
        config: defaultConfig(definition),
      },
    }
    const nextNodes = [...nodes, newNode]
    const lastDefinition = last ? getBlockDefinition(last.data.blockId) : undefined
    const nextEdges: Edge[] =
      last && !lastDefinition?.terminal
        ? [
            ...edges,
            {
              id: `edge_${Date.now()}`,
              source: last.id,
              target: id,
              animated: true,
            },
          ]
        : edges
    setNodes(nextNodes)
    setEdges(nextEdges)
    setSimpleBlockId(null)
    pushHistory(nextNodes, nextEdges)
    markDirty()
  }

  if (isLoading) return <LoadingState minHeight={360} />
  if (isError || !flow) {
    return <ErrorState onRetry={() => void refetch()} message={t('flows.noFlows')} />
  }
  if (!bot) return <LoadingState minHeight={360} />

  const errorCount = issues?.filter((issue) => issue.severity === 'error').length ?? 0
  const warningCount = issues?.filter((issue) => issue.severity === 'warning').length ?? 0

  return (
    <Stack gap="md">
      <Group justify="space-between" align="flex-start" wrap="wrap" gap="sm">
        <Group gap="sm" align="flex-start">
          <Button
            component={Link}
            to={`/app/bots/${bot.id}/flows`}
            variant="subtle"
            color="gray"
            size="compact-sm"
            leftSection={<IconArrowLeft size={15} />}
            mt={3}
          >
            {t('nav.flows')}
          </Button>
          <Box>
            <Group gap="sm">
              <Title order={2} fz={22}>
                {flow.name}
              </Title>
              <Badge
                variant="light"
                color={flow.status === 'published' ? 'teal' : 'yellow'}
                size="sm"
              >
                {flow.status === 'published' ? t('flows.publishedStatus') : t('flows.draft')}
              </Badge>
              <Badge variant="light" color="gray" size="sm">
                v{flow.version}
              </Badge>
            </Group>
            <Text size="xs" c="dimmed" mt={2}>
              {t('flows.nodeCount')}: {nodes.length} · {t('flows.edgeCount')}: {edges.length}
              {' · '}
              {dirty ? t('flows.unsaved') : lastSaved ? `${t('flows.autosaved')} ${formatRelative(lastSaved)}` : t('common.saved')}
            </Text>
          </Box>
        </Group>
        <Group gap="xs" wrap="wrap">
          <Button
            variant="subtle"
            color="gray"
            size="compact-sm"
            px={6}
            onClick={undo}
            disabled={historyIndexRef.current <= 0}
            aria-label={t('flows.undo')}
          >
            <IconArrowBackUp size={16} />
          </Button>
          <Button
            variant="subtle"
            color="gray"
            size="compact-sm"
            px={6}
            onClick={redo}
            disabled={historyIndexRef.current >= historyRef.current.length - 1}
            aria-label={t('flows.redo')}
          >
            <IconArrowForwardUp size={16} />
          </Button>
          <Button
            variant="default"
            size="compact-sm"
            leftSection={<IconCheck size={15} />}
            loading={validateMutation.isPending}
            onClick={() => validateMutation.mutate()}
          >
            {t('flows.validate')}
          </Button>
          <Button
            variant="default"
            size="compact-sm"
            leftSection={<IconPlayerPlay size={15} />}
            loading={testMutation.isPending}
            onClick={() => testMutation.mutate()}
          >
            {t('flows.runTest')}
          </Button>
          <Button
            variant="default"
            size="compact-sm"
            leftSection={<IconDeviceFloppy size={15} />}
            loading={saveMutation.isPending}
            onClick={saveNow}
          >
            {t('common.save')}
          </Button>
          <Button
            size="compact-sm"
            leftSection={<IconRocket size={15} />}
            onClick={() => setPublishOpened(true)}
          >
            {t('common.publish')}
          </Button>
          <Button
            component={Link}
            to={`/app/bots/${bot.id}/flows/${flow.id}/versions`}
            variant="light"
            size="compact-sm"
            leftSection={<IconGitBranch size={15} />}
          >
            {t('flows.versions')}
          </Button>
        </Group>
      </Group>

      {isMobile && (
        <Alert color="yellow" icon={<IconAlertTriangle size={16} />}>
          {t('flows.mobileWarning')}
        </Alert>
      )}

      <Group justify="space-between">
        <SegmentedControl
          size="xs"
          value={mode}
          onChange={setMode}
          data={[
            { value: 'canvas', label: t('flows.advancedMode') },
            { value: 'simple', label: t('flows.simpleMode') },
          ]}
        />
        {issues && (
          <Group gap="xs">
            <Badge color={errorCount ? 'red' : 'teal'} variant="light">
              {t('flows.issues')}: {errorCount}
            </Badge>
            <Badge color={warningCount ? 'yellow' : 'gray'} variant="light">
              warnings: {warningCount}
            </Badge>
          </Group>
        )}
      </Group>

      {mode === 'canvas' ? (
        <Box
          style={{
            display: 'grid',
            gridTemplateColumns: isMobile ? '1fr' : '250px minmax(0, 1fr) 310px',
            gap: 12,
            alignItems: 'stretch',
          }}
        >
          {!isMobile && (
            <Card withBorder radius="lg" p={0}>
              <Box p="sm" style={{ borderBottom: '1px solid var(--mantine-color-default-border)' }}>
                <TextInput
                  size="xs"
                  placeholder={t('flows.searchBlocks')}
                  leftSection={<IconSearch size={14} />}
                  value={paletteQuery}
                  onChange={(event) => setPaletteQuery(event.currentTarget.value)}
                />
              </Box>
              <ScrollArea h={600}>
                <Stack gap={4} p="xs">
                  {(Object.keys(groupedBlocks) as BlockCategory[]).map((category) => (
                    <Box key={category}>
                      <Text
                        size="10px"
                        fw={800}
                        tt="uppercase"
                        c={blockCategoryMeta[category].color}
                        px="xs"
                        py={5}
                        style={{ letterSpacing: '0.07em' }}
                      >
                        {blockCategoryMeta[category].label}
                      </Text>
                      {groupedBlocks[category].map((definition) => (
                        <Button
                          key={definition.id}
                          variant="subtle"
                          color="gray"
                          fullWidth
                          justify="flex-start"
                          size="compact-sm"
                          leftSection={
                            <AppIcon
                              name={definition.icon}
                              size={15}
                              color={blockCategoryMeta[category].color}
                            />
                          }
                          onClick={() => addBlock(definition)}
                          styles={{ label: { whiteSpace: 'normal', textAlign: 'left' } }}
                        >
                          {definition.title}
                        </Button>
                      ))}
                    </Box>
                  ))}
                </Stack>
              </ScrollArea>
            </Card>
          )}

          <Card
            withBorder
            radius="lg"
            p={0}
            style={{ overflow: 'hidden', height: isMobile ? 520 : 640 }}
          >
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              onNodeClick={(_, node) => setSelectedId(node.id)}
              onPaneClick={() => setSelectedId(null)}
              onNodeDragStop={() => {
                pushHistory(nodesRef.current, edgesRef.current)
                markDirty()
              }}
              nodesDraggable={!isMobile}
              nodesConnectable={!isMobile}
              fitView
              proOptions={{ hideAttribution: true }}
              defaultEdgeOptions={{ animated: true, style: { stroke: '#5865f2', strokeWidth: 2 } }}
            >
              <Background gap={22} size={1} />
              <Controls showInteractive={!isMobile} />
              <MiniMap pannable zoomable />
            </ReactFlow>
          </Card>

          {!isMobile && (
            <Card withBorder radius="lg" p="md">
              <ScrollArea h={610}>
                {!selectedNode || !selectedDefinition ? (
                  <Stack align="center" gap="xs" py="xl">
                    <AppIcon name="settings" size={26} />
                    <Text size="sm" c="dimmed" ta="center">
                      {t('flows.noSelection')}
                    </Text>
                  </Stack>
                ) : (
                  <Stack gap="sm">
                    <Group justify="space-between" align="flex-start">
                      <Group gap="xs">
                        <ThemeIcon
                          size={30}
                          radius="md"
                          variant="light"
                          color={blockCategoryMeta[selectedDefinition.category].color}
                        >
                          <AppIcon name={selectedDefinition.icon} size={15} />
                        </ThemeIcon>
                        <Stack gap={0}>
                          <Text size="sm" fw={700}>
                            {selectedDefinition.title}
                          </Text>
                          <Text size="10px" c="dimmed">
                            {blockCategoryMeta[selectedDefinition.category].label}
                          </Text>
                        </Stack>
                      </Group>
                      <Button
                        variant="subtle"
                        color="red"
                        size="compact-xs"
                        px={5}
                        onClick={() => removeNode(selectedNode.id)}
                        aria-label={t('flows.deleteNode')}
                      >
                        <IconTrash size={14} />
                      </Button>
                    </Group>
                    <Divider />
                    <TextInput
                      label="Название блока"
                      value={selectedNode.data.label}
                      onChange={(event) =>
                        updateNode(selectedNode.id, { label: event.currentTarget.value })
                      }
                    />
                    {selectedDefinition.fields.map((field) => (
                      <FieldEditor
                        key={field.key}
                        field={field}
                        value={selectedNode.data.config[field.key]}
                        channels={channels}
                        roles={roles}
                        onChange={(value) => updateConfig(selectedNode.id, field.key, value)}
                      />
                    ))}
                    {selectedDefinition.permissions?.length ? (
                      <Alert color="orange" variant="light" p="xs" icon={<IconAlertTriangle size={14} />}>
                        <Text size="xs">
                          {t('modules.permissions')}: {selectedDefinition.permissions.join(', ')}
                        </Text>
                      </Alert>
                    ) : null}
                    {issues
                      ?.filter((issue) => issue.nodeId === selectedNode.id)
                      .map((issue) => (
                        <Text key={issue.id} size="xs" c={issue.severity === 'error' ? 'red' : 'yellow'}>
                          {issue.message}
                        </Text>
                      ))}
                  </Stack>
                )}
              </ScrollArea>
            </Card>
          )}
        </Box>
      ) : (
        <Card withBorder radius="lg" p="md">
          <Group justify="space-between" mb="md" wrap="wrap">
            <Title order={3} fz={17}>
              {t('flows.simpleMode')}
            </Title>
            <Group>
              <Select
                placeholder={t('flows.addStep')}
                data={blockDefinitions.map((definition) => ({
                  value: definition.id,
                  label: `${blockCategoryMeta[definition.category].label} · ${definition.title}`,
                }))}
                searchable
                value={simpleBlockId}
                onChange={setSimpleBlockId}
                w={260}
              />
              <Button
                size="compact-sm"
                leftSection={<IconPlus size={14} />}
                disabled={!simpleBlockId}
                onClick={() => addSimpleStep(simpleBlockId)}
              >
                {t('common.add')}
              </Button>
            </Group>
          </Group>
          <Stack gap="sm">
            {orderedNodes.length === 0 && (
              <Text c="dimmed" size="sm">
                {t('flows.emptyText')}
              </Text>
            )}
            {orderedNodes.map((node, index) => {
              const definition = getBlockDefinition(node.data.blockId)
              if (!definition) return null
              return (
                <Card key={node.id} withBorder radius="md" p="md">
                  <Group justify="space-between" mb="sm" wrap="nowrap">
                    <Group gap="sm">
                      <ThemeIcon
                        size={28}
                        radius="xl"
                        variant="light"
                        color={blockCategoryMeta[definition.category].color}
                      >
                        <Text size="11px" fw={700}>
                          {index + 1}
                        </Text>
                      </ThemeIcon>
                      <Stack gap={0}>
                        <Text size="sm" fw={700}>
                          {definition.title}
                        </Text>
                        <Text size="10px" c="dimmed">
                          {blockCategoryMeta[definition.category].label}
                        </Text>
                      </Stack>
                    </Group>
                    <Group gap="xs">
                      <TextInput
                        size="xs"
                        value={node.data.label}
                        onChange={(event) =>
                          updateNode(node.id, { label: event.currentTarget.value })
                        }
                      />
                      <Button
                        variant="subtle"
                        color="red"
                        size="compact-xs"
                        onClick={() => removeNode(node.id)}
                      >
                        <IconX size={14} />
                      </Button>
                    </Group>
                  </Group>
                  <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm">
                    {definition.fields.map((field) => (
                      <FieldEditor
                        key={field.key}
                        field={field}
                        value={node.data.config[field.key]}
                        channels={channels}
                        roles={roles}
                        onChange={(value) => updateConfig(node.id, field.key, value)}
                      />
                    ))}
                  </SimpleGrid>
                </Card>
              )
            })}
          </Stack>
        </Card>
      )}

      <Modal
        opened={issuesOpened}
        onClose={() => setIssuesOpened(false)}
        title={t('flows.validate')}
        size="lg"
      >
        <Stack gap="sm">
          {issues?.length === 0 ? (
            <Alert color="teal" icon={<IconCheck size={16} />}>
              {t('flows.valid')}
            </Alert>
          ) : (
            issues?.map((issue) => (
              <Group key={issue.id} align="flex-start" gap="sm" wrap="nowrap">
                <ThemeIcon
                  size={24}
                  radius="xl"
                  color={issue.severity === 'error' ? 'red' : 'yellow'}
                  variant="light"
                >
                  <IconAlertTriangle size={13} />
                </ThemeIcon>
                <Stack gap={0}>
                  <Text size="sm" fw={600}>
                    {issue.severity === 'error' ? t('common.error') : t('notifications.typeWarning')}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {issue.message}
                  </Text>
                </Stack>
              </Group>
            ))
          )}
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setIssuesOpened(false)}>
              {t('common.close')}
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Modal
        opened={testOpened}
        onClose={() => setTestOpened(false)}
        title={t('flows.testTitle')}
        size="lg"
      >
        {testResult && (
          <Stack>
            <Alert
              color={testResult.success ? 'teal' : 'red'}
              icon={testResult.success ? <IconCheck size={16} /> : <IconX size={16} />}
            >
              {testResult.success ? t('flows.testSuccess') : t('flows.testFailure')} ·{' '}
              {testResult.durationMs} ms
            </Alert>
            <Stack gap="xs">
              {testResult.steps.map((step) => (
                <Group
                  key={step.id}
                  align="flex-start"
                  wrap="nowrap"
                  p="xs"
                  style={{ borderRadius: 10, border: '1px solid var(--mantine-color-default-border)' }}
                >
                  <ThemeIcon
                    size={22}
                    radius="xl"
                    variant="light"
                    color={
                      step.status === 'ok' ? 'teal' : step.status === 'error' ? 'red' : 'gray'
                    }
                  >
                    {step.status === 'ok' ? (
                      <IconCheck size={12} />
                    ) : step.status === 'error' ? (
                      <IconX size={12} />
                    ) : (
                      <Text size="9px">—</Text>
                    )}
                  </ThemeIcon>
                  <Stack gap={0}>
                    <Text size="sm" fw={600}>
                      {step.title}
                    </Text>
                    <Text size="xs" c="dimmed">
                      {step.detail}
                    </Text>
                  </Stack>
                </Group>
              ))}
            </Stack>
            <Card withBorder radius="md" p="sm">
              <Text size="xs" c="dimmed">
                {t('flows.variables')}
              </Text>
              <Text size="xs" ff="monospace" style={{ whiteSpace: 'pre-wrap' }}>
                {JSON.stringify(testResult.variables, null, 2)}
              </Text>
            </Card>
            <Card withBorder radius="md" p="sm">
              <Text size="xs" c="dimmed">
                Output
              </Text>
              <Text size="sm">{testResult.output}</Text>
            </Card>
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setTestOpened(false)}>
                {t('common.close')}
              </Button>
              <Button onClick={() => testMutation.mutate()} loading={testMutation.isPending}>
                {t('flows.runAgain')}
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>

      <Modal
        opened={publishOpened}
        onClose={() => setPublishOpened(false)}
        title={t('flows.publishTitle')}
      >
        <Stack>
          <Text size="sm" c="dimmed">
            {t('flows.publishText')}
          </Text>
          <Textarea
            label={t('flows.publishComment')}
            value={publishComment}
            onChange={(event) => setPublishComment(event.currentTarget.value)}
            autosize
            minRows={2}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setPublishOpened(false)}>
              {t('common.cancel')}
            </Button>
            <Tooltip label={dirty ? t('flows.unsaved') : t('common.publish')}>
              <Button
                leftSection={<IconRocket size={15} />}
                loading={publishMutation.isPending}
                onClick={() => publishMutation.mutate()}
              >
                {t('common.publish')}
              </Button>
            </Tooltip>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  )
}
