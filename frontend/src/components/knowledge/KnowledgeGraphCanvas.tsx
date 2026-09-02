'use client';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  forceX,
  forceY,
  Simulation,
  SimulationNodeDatum,
} from 'd3-force';
import { GraphEdge, GraphNode } from '@/types';

/**
 * Colour carries entity type and nothing else.
 *
 * Deliberately NOT encoding `confidence`: every edge on live data scored exactly
 * 0.80, so weighting strokes by it would draw a signal that does not exist.
 */
const TYPE_COLORS: Record<string, string> = {
  person: '#3ba6f1',
  organization: '#8b5cf6',
  concept: '#f59e0b',
  document: '#64748b',
  knowledge: '#10b981',
};
const DEFAULT_COLOR = '#94a3b8';

/** Server lower-cases types, but a stray casing must not fall to grey silently. */
export function colorForType(type: string): string {
  return TYPE_COLORS[type?.toLowerCase()] ?? DEFAULT_COLOR;
}

export const ENTITY_TYPES = Object.keys(TYPE_COLORS);

interface SimNode extends SimulationNodeDatum {
  id: string;
  name: string;
  type: string;
  degree: number;
}

interface SimLink {
  source: SimNode;
  target: SimNode;
  id: string;
  predicate: string;
  isProvenance: boolean;
}

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}

const RADIUS_BASE = 9;
const MIN_ZOOM = 0.25;
const MAX_ZOOM = 3;

export const KnowledgeGraphCanvas: React.FC<Props> = ({
  nodes,
  edges,
  selectedId,
  onSelect,
}) => {
  const wrapRef = useRef<HTMLDivElement>(null);
  const simRef = useRef<Simulation<SimNode, undefined> | null>(null);
  const nodesRef = useRef<SimNode[]>([]);
  const linksRef = useRef<SimLink[]>([]);

  const [size, setSize] = useState({ width: 800, height: 560 });
  const [, setTick] = useState(0);
  const [transform, setTransform] = useState({ x: 0, y: 0, k: 1 });
  const [hoverId, setHoverId] = useState<string | null>(null);

  // Pointer bookkeeping. Refs, not state: these change every pointermove and would
  // otherwise re-render the whole graph on each event.
  const dragRef = useRef<{ id: string | null; pointerId: number } | null>(null);
  const panRef = useRef<{ x: number; y: number; tx: number; ty: number } | null>(null);
  const movedRef = useRef(false);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      if (width > 0 && height > 0) setSize({ width, height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // A stable identity for the data, so the simulation restarts when the graph
  // genuinely changes and not merely when the parent re-renders.
  const dataKey = useMemo(
    () => `${nodes.map((n) => n.id).join(',')}|${edges.map((e) => e.id).join(',')}`,
    [nodes, edges]
  );

  useEffect(() => {
    if (nodes.length === 0) {
      simRef.current?.stop();
      simRef.current = null;
      nodesRef.current = [];
      linksRef.current = [];
      setTick((t) => t + 1);
      return;
    }

    const degree = new Map<string, number>();
    edges.forEach((e) => {
      degree.set(e.source, (degree.get(e.source) ?? 0) + 1);
      degree.set(e.target, (degree.get(e.target) ?? 0) + 1);
    });

    // Clone. d3-force mutates x/y/vx/vy onto whatever it is handed, and these
    // objects belong to the Zustand store.
    const simNodes: SimNode[] = nodes.map((n) => ({
      id: n.id,
      name: n.name,
      type: n.type,
      degree: degree.get(n.id) ?? 0,
    }));
    const byId = new Map(simNodes.map((n) => [n.id, n]));

    const simLinks: SimLink[] = edges.flatMap((e) => {
      const source = byId.get(e.source);
      const target = byId.get(e.target);
      // An edge to a node the payload never described cannot be laid out.
      if (!source || !target) return [];
      return [{
        source,
        target,
        id: e.id,
        predicate: e.predicate,
        isProvenance: e.is_provenance,
      }];
    });

    nodesRef.current = simNodes;
    linksRef.current = simLinks;

    const sim = forceSimulation<SimNode>(simNodes)
      .force(
        'link',
        forceLink<SimNode, SimLink>(simLinks)
          .id((d) => d.id)
          .distance(110)
          .strength(0.35)
      )
      .force('charge', forceManyBody().strength(-420))
      .force('center', forceCenter(size.width / 2, size.height / 2))
      // Keeps labels from overlapping; the radius mirrors the drawn node plus text.
      .force('collide', forceCollide<SimNode>((d) => RADIUS_BASE + d.degree + 22))
      // Gentle inward pull so disconnected entities do not drift off-canvas.
      .force('x', forceX(size.width / 2).strength(0.04))
      .force('y', forceY(size.height / 2).strength(0.04))
      .on('tick', () => setTick((t) => t + 1));

    simRef.current = sim;
    return () => {
      sim.stop();
    };
    // `size` intentionally omitted: a resize should not restart the layout and
    // scatter a graph the founder has already arranged.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataKey]);

  /** Screen pixels → simulation coordinates. */
  const toSim = useCallback(
    (clientX: number, clientY: number) => {
      const rect = wrapRef.current?.getBoundingClientRect();
      if (!rect) return { x: 0, y: 0 };
      return {
        x: (clientX - rect.left - transform.x) / transform.k,
        y: (clientY - rect.top - transform.y) / transform.k,
      };
    },
    [transform]
  );

  const onNodePointerDown = (e: React.PointerEvent, id: string) => {
    e.stopPropagation();
    (e.target as Element).setPointerCapture?.(e.pointerId);
    dragRef.current = { id, pointerId: e.pointerId };
    movedRef.current = false;
    simRef.current?.alphaTarget(0.25).restart();
  };

  const onBackgroundPointerDown = (e: React.PointerEvent) => {
    panRef.current = {
      x: e.clientX,
      y: e.clientY,
      tx: transform.x,
      ty: transform.y,
    };
    movedRef.current = false;
  };

  const onPointerMove = (e: React.PointerEvent) => {
    const drag = dragRef.current;
    if (drag?.id) {
      movedRef.current = true;
      const node = nodesRef.current.find((n) => n.id === drag.id);
      if (node) {
        const p = toSim(e.clientX, e.clientY);
        // Pin while dragging so the simulation cannot fight the pointer.
        node.fx = p.x;
        node.fy = p.y;
      }
      return;
    }

    const pan = panRef.current;
    if (pan) {
      const dx = e.clientX - pan.x;
      const dy = e.clientY - pan.y;
      if (Math.abs(dx) > 2 || Math.abs(dy) > 2) movedRef.current = true;
      setTransform((t) => ({ ...t, x: pan.tx + dx, y: pan.ty + dy }));
    }
  };

  const endGesture = () => {
    const drag = dragRef.current;
    if (drag?.id) {
      const node = nodesRef.current.find((n) => n.id === drag.id);
      // Release the pin — a dragged node settles back into the layout rather than
      // staying frozen where it was dropped.
      if (node) {
        node.fx = null;
        node.fy = null;
      }
      simRef.current?.alphaTarget(0);
    }
    dragRef.current = null;
    panRef.current = null;
  };

  const onWheel = (e: React.WheelEvent) => {
    const rect = wrapRef.current?.getBoundingClientRect();
    if (!rect) return;
    const px = e.clientX - rect.left;
    const py = e.clientY - rect.top;

    setTransform((t) => {
      const k = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, t.k * (e.deltaY < 0 ? 1.12 : 1 / 1.12)));
      // Anchor the zoom at the cursor: the point under the pointer stays put.
      return {
        k,
        x: px - ((px - t.x) / t.k) * k,
        y: py - ((py - t.y) / t.k) * k,
      };
    });
  };

  const resetView = () => setTransform({ x: 0, y: 0, k: 1 });

  // Which nodes and edges are emphasised. Selection wins over hover.
  const focusId = selectedId ?? hoverId;
  const neighbours = useMemo(() => {
    if (!focusId) return null;
    const set = new Set<string>([focusId]);
    linksRef.current.forEach((l) => {
      if (l.source.id === focusId) set.add(l.target.id);
      if (l.target.id === focusId) set.add(l.source.id);
    });
    return set;
    // linksRef is mutable; focusId changing is the trigger that matters.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusId, dataKey]);

  const simNodes = nodesRef.current;
  const simLinks = linksRef.current;

  return (
    <div className="relative h-full w-full">
      <div
        ref={wrapRef}
        className="h-full w-full overflow-hidden rounded-cards border border-stone-border bg-stone-canvas touch-none"
      >
        <svg
          width={size.width}
          height={size.height}
          className="block cursor-grab active:cursor-grabbing select-none"
          onPointerDown={onBackgroundPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={endGesture}
          onPointerLeave={endGesture}
          onPointerCancel={endGesture}
          onWheel={onWheel}
          onClick={() => {
            // A pan that happened to end on the background is not a deselect.
            if (!movedRef.current) onSelect(null);
          }}
          role="img"
          aria-label={`Knowledge graph with ${nodes.length} entities and ${edges.length} relations`}
        >
          <defs>
            <marker
              id="kg-arrow"
              viewBox="0 0 10 10"
              refX={9}
              refY={5}
              markerWidth={5}
              markerHeight={5}
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" className="fill-warm-gray" />
            </marker>
          </defs>

          <g transform={`translate(${transform.x},${transform.y}) scale(${transform.k})`}>
            {simLinks.map((l) => {
              const dimmed = neighbours
                ? !(neighbours.has(l.source.id) && neighbours.has(l.target.id))
                : false;
              const x1 = l.source.x ?? 0;
              const y1 = l.source.y ?? 0;
              const x2 = l.target.x ?? 0;
              const y2 = l.target.y ?? 0;

              // Shorten the line so the arrowhead lands on the circle's edge
              // rather than under the node.
              const dx = x2 - x1;
              const dy = y2 - y1;
              const len = Math.hypot(dx, dy) || 1;
              const pad = RADIUS_BASE + l.target.degree + 6;
              const ex = x2 - (dx / len) * pad;
              const ey = y2 - (dy / len) * pad;

              const showLabel =
                !!focusId && (l.source.id === focusId || l.target.id === focusId);

              return (
                <g key={l.id} opacity={dimmed ? 0.12 : 1} className="transition-opacity duration-200">
                  <line
                    x1={x1}
                    y1={y1}
                    x2={ex}
                    y2={ey}
                    className="stroke-warm-gray"
                    strokeWidth={1.2}
                    strokeOpacity={l.isProvenance ? 0.4 : 0.7}
                    strokeDasharray={l.isProvenance ? '4 3' : undefined}
                    markerEnd="url(#kg-arrow)"
                  />
                  {showLabel && (
                    <text
                      x={(x1 + ex) / 2}
                      y={(y1 + ey) / 2 - 4}
                      textAnchor="middle"
                      className="fill-warm-gray text-[9px]"
                      style={{ paintOrder: 'stroke' }}
                    >
                      {l.predicate}
                    </text>
                  )}
                </g>
              );
            })}

            {simNodes.map((n) => {
              const dimmed = neighbours ? !neighbours.has(n.id) : false;
              const isSelected = n.id === selectedId;
              const r = RADIUS_BASE + Math.min(n.degree * 1.6, 10);
              const color = colorForType(n.type);

              return (
                <g
                  key={n.id}
                  transform={`translate(${n.x ?? 0},${n.y ?? 0})`}
                  opacity={dimmed ? 0.2 : 1}
                  className="cursor-pointer transition-opacity duration-200"
                  onPointerDown={(e) => onNodePointerDown(e, n.id)}
                  onPointerEnter={() => setHoverId(n.id)}
                  onPointerLeave={() => setHoverId(null)}
                  onClick={(e) => {
                    e.stopPropagation();
                    if (!movedRef.current) onSelect(isSelected ? null : n.id);
                  }}
                >
                  {isSelected && (
                    <circle r={r + 5} fill="none" stroke={color} strokeWidth={1.5} opacity={0.5} />
                  )}
                  <circle
                    r={r}
                    fill={color}
                    className="stroke-stone-canvas"
                    strokeWidth={2}
                  />
                  <text
                    y={r + 12}
                    textAnchor="middle"
                    className="fill-ink-black text-[10px] font-medium pointer-events-none"
                  >
                    {n.name.length > 26 ? `${n.name.slice(0, 25)}…` : n.name}
                  </text>
                </g>
              );
            })}
          </g>
        </svg>
      </div>

      <div className="absolute bottom-3 right-3 flex items-center gap-1.5">
        <span className="rounded-full bg-surface/90 px-2 py-1 text-[11px] text-warm-gray border border-stone-border">
          {Math.round(transform.k * 100)}%
        </span>
        <button
          onClick={resetView}
          className="rounded-full border border-stone-border bg-surface/90 px-2.5 py-1 text-[11px] text-warm-gray transition hover:text-ink-black hover:bg-stone-border/40"
        >
          Reset view
        </button>
      </div>
    </div>
  );
};
