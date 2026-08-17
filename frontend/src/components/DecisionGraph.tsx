import {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  Position,
  ReactFlow,
  type Node,
  type NodeProps,
  type NodeTypes,
} from '@xyflow/react'
import {
  Check,
  CircleAlert,
  FileClock,
  FileText,
  GitBranch,
  Octagon,
  Play,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react'
import { useMemo } from 'react'

import { toFlowElements } from '../graph-model'
import type { GraphNodeDto, GraphReadModel, NodeStatus } from '../types'

const iconByKind = {
  artifact: FileText,
  evidence: ShieldCheck,
  decision: GitBranch,
  action: Play,
}

function StatusIcon({ status }: { status: NodeStatus }) {
  if (status === 'STALE') return <CircleAlert aria-hidden="true" />
  if (status === 'BLOCKED') return <Octagon aria-hidden="true" />
  if (status === 'REVALIDATING') return <RefreshCw aria-hidden="true" />
  if (status === 'SUPERSEDED') return <FileClock aria-hidden="true" />
  return <Check aria-hidden="true" />
}

function RuntimeNode({ data, selected }: NodeProps<Node<GraphNodeDto>>) {
  const KindIcon = iconByKind[data.kind]
  const detail = data.version ?? data.revision ?? data.outcome ?? data.action_type
  return (
    <article
      className={`runtime-node runtime-node--${data.kind} status-${data.status.toLowerCase()}${selected ? ' is-selected' : ''}`}
      data-testid={`node-${data.id}`}
    >
      <Handle type="target" position={Position.Left} />
      {data.kind === 'artifact' ? (
        <Handle id="supersedes-target" type="target" position={Position.Top} />
      ) : null}
      <div className="runtime-node__header">
        <KindIcon aria-hidden="true" />
        <span>{data.kind}</span>
        <span className="runtime-node__id">{data.id}</span>
      </div>
      <strong>{data.label}</strong>
      <div className="runtime-node__footer">
        <span className="status-label">
          <StatusIcon status={data.status} />
          {data.status}
        </span>
        {data.preserved === true ? <span className="preserved-label">PRESERVED</span> : null}
        {detail ? <span className="node-detail">{String(detail)}</span> : null}
      </div>
      <Handle type="source" position={Position.Right} />
      {data.kind === 'artifact' ? (
        <Handle id="supersedes-source" type="source" position={Position.Bottom} />
      ) : null}
    </article>
  )
}

const nodeTypes: NodeTypes = {
  artifact: RuntimeNode,
  evidence: RuntimeNode,
  decision: RuntimeNode,
  action: RuntimeNode,
}

export function DecisionGraph({
  graph,
  onSelect,
}: {
  graph: GraphReadModel
  onSelect(nodeId: string): void
}) {
  const elements = useMemo(() => {
    const result = toFlowElements(graph)
    return {
      ...result,
      nodes: result.nodes.map((node) => ({
        ...node,
        data: {
          ...node.data,
          preserved: graph.plan.retained_decision_ids.includes(node.id),
        },
      })),
    }
  }, [graph])

  return (
    <section className="graph-panel" aria-label="Decision dependency graph">
      <ReactFlow
        key={`${graph.mission_id}:${graph.phase}`}
        nodes={elements.nodes}
        edges={elements.edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.12, maxZoom: 1.1 }}
        minZoom={0.5}
        maxZoom={1.5}
        nodesConnectable={false}
        onNodeClick={(_, node: Node) => onSelect(node.id)}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#D9DED8" gap={24} size={1} variant={BackgroundVariant.Dots} />
        <Controls showInteractive={false} position="bottom-left" />
      </ReactFlow>
    </section>
  )
}
