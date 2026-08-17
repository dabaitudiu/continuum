import dagre from '@dagrejs/dagre'
import { MarkerType, type Edge, type Node } from '@xyflow/react'

import type { GraphNodeDto, GraphReadModel } from './types'

const NODE_WIDTH = 204
const NODE_HEIGHT = 88

export interface FlowElements {
  nodes: Node<GraphNodeDto>[]
  edges: Edge[]
}

export function toFlowElements(readModel: GraphReadModel): FlowElements {
  const layout = new dagre.graphlib.Graph()
  layout.setGraph({
    rankdir: 'LR',
    ranksep: 76,
    nodesep: 34,
    edgesep: 18,
    marginx: 28,
    marginy: 28,
  })
  layout.setDefaultEdgeLabel(() => ({}))

  for (const node of readModel.nodes) {
    layout.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT })
  }
  for (const edge of readModel.edges) {
    layout.setEdge(edge.from_node_id, edge.to_node_id)
  }

  const supersessionEdges = readModel.nodes.flatMap((node) => {
    if (node.kind !== 'artifact' || !node.supersedes_artifact_id) return []
    layout.setEdge(node.id, node.supersedes_artifact_id)
    return [
      {
        id: `supersedes:${node.id}:${node.supersedes_artifact_id}`,
        source: node.id,
        target: node.supersedes_artifact_id,
        label: 'SUPERSEDES',
        type: 'smoothstep',
        className: 'graph-edge graph-edge--change',
        markerEnd: { type: MarkerType.ArrowClosed },
      } satisfies Edge,
    ]
  })

  dagre.layout(layout)

  const nodes = readModel.nodes.map((node) => {
    const point = layout.node(node.id)
    return {
      id: node.id,
      type: node.kind,
      position: {
        x: point.x - NODE_WIDTH / 2,
        y: point.y - NODE_HEIGHT / 2,
      },
      data: node,
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
      draggable: false,
      selectable: true,
    } satisfies Node<GraphNodeDto>
  })

  const affectedIds = new Set(Object.keys(readModel.causes))
  const edges = readModel.edges.map((edge) => {
    const affected = affectedIds.has(edge.to_node_id)
    return {
      id: edge.edge_id,
      source: edge.from_node_id,
      target: edge.to_node_id,
      label: edge.relation_type,
      type: 'smoothstep',
      animated: readModel.phase === 'DRIFTED' && affected,
      className: affected ? 'graph-edge graph-edge--affected' : 'graph-edge',
      markerEnd: { type: MarkerType.ArrowClosed },
      data: { critical: edge.critical, relationType: edge.relation_type },
    } satisfies Edge
  })

  return { nodes, edges: [...edges, ...supersessionEdges] }
}
