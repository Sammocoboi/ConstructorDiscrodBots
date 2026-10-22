import { describe, expect, it } from 'vitest'
import type { FlowEdge, FlowNode } from '../api/types'
import { countIssueSeverity, validateFlowGraph } from './flowGraph'

function node(id: string, blockId: string, label = id): FlowNode {
  return {
    id,
    type: 'block',
    position: { x: 0, y: 0 },
    data: { blockId, label, config: {} },
  }
}

function edge(source: string, target: string): FlowEdge {
  return { id: `${source}-${target}`, source, target }
}

describe('validateFlowGraph', () => {
  it('reports an empty flow', () => {
    const issues = validateFlowGraph([], [])
    expect(issues).toHaveLength(1)
    expect(issues[0].code).toBe('empty_flow')
    expect(issues[0].severity).toBe('error')
  })

  it('reports a missing trigger', () => {
    const issues = validateFlowGraph([node('a', 'action.send_message')], [])
    expect(issues.some((issue) => issue.code === 'no_trigger')).toBe(true)
  })

  it('reports a missing action', () => {
    const issues = validateFlowGraph([node('t', 'trigger.member_join')], [])
    expect(issues.some((issue) => issue.code === 'no_action')).toBe(true)
  })

  it('reports unknown block definitions', () => {
    const issues = validateFlowGraph(
      [node('t', 'trigger.member_join'), node('x', 'action.does_not_exist')],
      [edge('t', 'x')],
    )
    expect(issues.some((issue) => issue.code === 'unknown_block')).toBe(true)
  })

  it('reports dangling edges', () => {
    const issues = validateFlowGraph(
      [node('t', 'trigger.member_join'), node('a', 'action.send_message')],
      [edge('t', 'ghost')],
    )
    expect(issues.some((issue) => issue.code === 'dangling_edge')).toBe(true)
  })

  it('counts issues by severity', () => {
    const issues = validateFlowGraph([], [])
    expect(countIssueSeverity(issues, 'error')).toBe(1)
    expect(countIssueSeverity(issues, 'warning')).toBe(0)
  })
})
