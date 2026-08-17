import { describe, expect, it } from 'vitest'

import { toFlowElements } from './graph-model'
import type { GraphReadModel } from './types'

const driftedReadModel: GraphReadModel = {
  mission_id: 'demo-001',
  phase: 'DRIFTED',
  summary: { stale: 2, preserved: 1, blocked: 1 },
  nodes: [
    {
      id: 'policy-v12',
      kind: 'artifact',
      label: 'security-policy',
      status: 'SUPERSEDED',
      artifact_id: 'policy-v12',
      version: 'v12',
    },
    {
      id: 'policy-v13',
      kind: 'artifact',
      label: 'security-policy',
      status: 'CURRENT',
      artifact_id: 'policy-v13',
      version: 'v13',
      supersedes_artifact_id: 'policy-v12',
    },
    { id: 'soc2-A31', kind: 'evidence', label: 'SOC2_CONTROL', status: 'VALID' },
    { id: 'financial-F7', kind: 'evidence', label: 'FINANCIAL_REPORT', status: 'VALID' },
    { id: 'D42', kind: 'decision', label: 'SECURITY_REVIEW', status: 'STALE' },
    { id: 'D43', kind: 'decision', label: 'FINANCIAL_REVIEW', status: 'VALID' },
    { id: 'D50', kind: 'decision', label: 'PROCUREMENT_REVIEW', status: 'STALE' },
    { id: 'activate-vendor', kind: 'action', label: 'ACTIVATE_VENDOR', status: 'BLOCKED' },
  ],
  edges: [
    { edge_id: 'policy-D42', from_node_id: 'policy-v12', to_node_id: 'D42', relation_type: 'GOVERNED_BY', critical: true },
    { edge_id: 'soc2-D42', from_node_id: 'soc2-A31', to_node_id: 'D42', relation_type: 'SUPPORTED_BY', critical: true },
    { edge_id: 'financial-D43', from_node_id: 'financial-F7', to_node_id: 'D43', relation_type: 'SUPPORTED_BY', critical: true },
    { edge_id: 'D42-D50', from_node_id: 'D42', to_node_id: 'D50', relation_type: 'REQUIRES', critical: true },
    { edge_id: 'D43-D50', from_node_id: 'D43', to_node_id: 'D50', relation_type: 'REQUIRES', critical: true },
    { edge_id: 'D50-activate', from_node_id: 'D50', to_node_id: 'activate-vendor', relation_type: 'AUTHORIZES', critical: true },
  ],
  plan: {
    stale_decision_ids: ['D42', 'D50'],
    runnable_decision_ids: ['D42'],
    waiting_decision_ids: ['D50'],
    blocked_action_ids: ['activate-vendor'],
    retained_decision_ids: ['D43'],
    cause_by_node_id: { D42: 'policy-v12', D50: 'D42', 'activate-vendor': 'D50' },
  },
  causes: { D42: 'policy-v12', D50: 'D42', 'activate-vendor': 'D50' },
  events: [],
  dispatches: [],
}

describe('toFlowElements', () => {
  it('maps drifted statuses and causal edges without ID-specific styling', () => {
    const result = toFlowElements(driftedReadModel)

    expect(result.nodes.map(({ id, type, data }) => ({ id, type, status: data.status }))).toEqual([
      { id: 'policy-v12', type: 'artifact', status: 'SUPERSEDED' },
      { id: 'policy-v13', type: 'artifact', status: 'CURRENT' },
      { id: 'soc2-A31', type: 'evidence', status: 'VALID' },
      { id: 'financial-F7', type: 'evidence', status: 'VALID' },
      { id: 'D42', type: 'decision', status: 'STALE' },
      { id: 'D43', type: 'decision', status: 'VALID' },
      { id: 'D50', type: 'decision', status: 'STALE' },
      { id: 'activate-vendor', type: 'action', status: 'BLOCKED' },
    ])
    expect(result.edges).toHaveLength(7)
    expect(result.edges.at(-1)).toMatchObject({
      source: 'policy-v13',
      target: 'policy-v12',
      label: 'SUPERSEDES',
    })
  })
})
