'use client';

import React, { useEffect, useMemo } from 'react';
import { AlertTriangle, Network, RefreshCw, Quote } from 'lucide-react';
import { useKnowledgeStore } from '@/stores/useKnowledgeStore';
import {
  ENTITY_TYPES,
  KnowledgeGraphCanvas,
  colorForType,
} from '@/components/knowledge';

export default function KnowledgePanelPage() {
  const {
    graph,
    isLoading,
    error,
    showProvenance,
    selectedId,
    fetchGraph,
    toggleProvenance,
    select,
  } = useKnowledgeStore();

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  // Hiding provenance hides its edges, and any entity those edges were the only
  // reason to draw. Leaving orphaned document nodes behind would make the toggle
  // look broken.
  const { nodes, edges } = useMemo(() => {
    if (!graph) return { nodes: [], edges: [] };
    if (showProvenance) return { nodes: graph.nodes, edges: graph.edges };

    const kept = graph.edges.filter((e) => !e.is_provenance);
    const connected = new Set(kept.flatMap((e) => [e.source, e.target]));
    return { nodes: graph.nodes.filter((n) => connected.has(n.id)), edges: kept };
  }, [graph, showProvenance]);

  const hiddenCount = graph ? graph.edges.length - edges.length : 0;

  const selected = useMemo(
    () => graph?.nodes.find((n) => n.id === selectedId) ?? null,
    [graph, selectedId]
  );

  /** Every relation touching the selected entity, with its evidence. */
  const selectedEdges = useMemo(() => {
    if (!selectedId || !graph) return [];
    return edges
      .filter((e) => e.source === selectedId || e.target === selectedId)
      .map((e) => {
        const otherId = e.source === selectedId ? e.target : e.source;
        return {
          edge: e,
          outgoing: e.source === selectedId,
          other: graph.nodes.find((n) => n.id === otherId) ?? null,
        };
      });
  }, [selectedId, edges, graph]);

  return (
    <div className="space-y-6">
      <div className="stone-card p-6 bg-white flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-normal text-ink-black tracking-tight">
            Company <span className="cyan-highlight">Knowledge Panel</span>
          </h1>
          <p className="text-xs text-warm-gray">
            Every entity Sentinel has extracted from your meetings, and how they connect
          </p>
        </div>

        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 text-xs text-warm-gray cursor-pointer select-none">
            <input
              type="checkbox"
              checked={showProvenance}
              onChange={toggleProvenance}
              className="accent-cyan-signal"
            />
            Show who said it
          </label>
          <button
            onClick={() => fetchGraph()}
            disabled={isLoading}
            className="btn-cyan text-xs px-4 py-2 flex items-center gap-1.5 w-fit disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="stone-card p-4 bg-white border-red-300/60 text-sm text-red-600">
          {error}
        </div>
      )}

      {/* Unreachable memory is not an empty graph, and must never read as one. */}
      {graph && !graph.available && (
        <div className="stone-card p-6 bg-white flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h3 className="text-sm font-semibold text-ink-black">Graph unavailable</h3>
            <p className="text-xs text-warm-gray">{graph.note}</p>
          </div>
        </div>
      )}

      {graph?.truncated && (
        <div className="stone-card p-3 bg-white border-amber-300/60 flex items-center gap-2 text-xs text-warm-gray">
          <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />
          Showing a partial graph — the result limit was reached, so some relations are
          not drawn.
        </div>
      )}

      {graph?.available && graph.nodes.length === 0 && (
        <div className="stone-card p-10 bg-white text-center space-y-2">
          <Network className="w-8 h-8 text-warm-gray/50 mx-auto" />
          <h3 className="text-sm font-semibold text-ink-black">Nothing recorded yet</h3>
          <p className="text-xs text-warm-gray max-w-md mx-auto">
            {graph.fact_count && graph.fact_count > 0
              ? `${graph.fact_count} fact${graph.fact_count === 1 ? '' : 's'} recorded, but the graph is still being built. Indexing runs in the background and takes a few minutes.`
              : 'Upload a meeting transcript and Sentinel will extract the decisions, people, and topics it mentions, then map how they connect.'}
          </p>
        </div>
      )}

      {graph?.available && graph.nodes.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-3">
            <div className="h-[560px]">
              <KnowledgeGraphCanvas
                nodes={nodes}
                edges={edges}
                selectedId={selectedId}
                onSelect={select}
              />
            </div>

            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-1">
              {ENTITY_TYPES.map((type) => (
                <span key={type} className="flex items-center gap-1.5 text-[11px] text-warm-gray">
                  <span
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ backgroundColor: colorForType(type) }}
                  />
                  {type}
                </span>
              ))}
              <span className="text-[11px] text-warm-gray ml-auto">
                {nodes.length} entities · {edges.length} relations
                {hiddenCount > 0 && ` · ${hiddenCount} attribution hidden`}
              </span>
            </div>
          </div>

          <aside className="stone-card p-5 bg-white space-y-4 h-fit lg:sticky lg:top-20">
            {!selected ? (
              <div className="space-y-2">
                <h3 className="text-sm font-semibold text-ink-black">Inspect an entity</h3>
                <p className="text-xs text-warm-gray">
                  Click any node to see what it is connected to and the exact sentence
                  behind each relation. Drag to rearrange, scroll to zoom.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="space-y-1">
                  <span className="flex items-center gap-1.5 text-[11px] text-warm-gray uppercase tracking-wide">
                    <span
                      className="w-2.5 h-2.5 rounded-full"
                      style={{ backgroundColor: colorForType(selected.type) }}
                    />
                    {selected.type}
                  </span>
                  <h3 className="text-base font-semibold text-ink-black capitalize">
                    {selected.name}
                  </h3>
                  <p className="text-xs text-warm-gray">
                    {selectedEdges.length} relation{selectedEdges.length === 1 ? '' : 's'}
                  </p>
                </div>

                <div className="space-y-3 max-h-[420px] overflow-y-auto pr-1">
                  {selectedEdges.map(({ edge, outgoing, other }) => (
                    <div
                      key={edge.id}
                      className="border-l-2 border-stone-border pl-3 space-y-1.5"
                    >
                      <p className="text-xs text-ink-black">
                        {outgoing ? '' : `${other?.name ?? 'unknown'} `}
                        <span className="text-cyan-edge font-medium">{edge.predicate}</span>
                        {outgoing ? ` ${other?.name ?? 'unknown'}` : ''}
                      </p>
                      {/* Rule 6: a claim the founder can check, not one to take on trust. */}
                      {edge.evidence
                        .filter((ev) => ev.context)
                        .map((ev, i) => (
                          <p
                            key={i}
                            className="text-[11px] text-warm-gray italic flex gap-1.5"
                          >
                            <Quote className="w-3 h-3 shrink-0 mt-0.5 opacity-50" />
                            {ev.context}
                          </p>
                        ))}
                    </div>
                  ))}
                </div>

                <button
                  onClick={() => select(null)}
                  className="text-[11px] text-warm-gray hover:text-ink-black transition"
                >
                  Clear selection
                </button>
              </div>
            )}
          </aside>
        </div>
      )}

      {isLoading && !graph && (
        <div className="stone-card p-10 bg-white text-center text-xs text-warm-gray">
          Loading the knowledge graph…
        </div>
      )}
    </div>
  );
}
