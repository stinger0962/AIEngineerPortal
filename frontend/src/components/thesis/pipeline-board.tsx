"use client";

import { useState } from "react";
import { Bot, ChevronDown, OctagonPause, Undo2 } from "lucide-react";

import { PIPELINE_META, PIPELINE_NODES, type PipelineNode } from "@/lib/thesis/pipeline";
import { cn } from "@/lib/utils";

function NodeCard({ node, expanded, onToggle }: { node: PipelineNode; expanded: boolean; onToggle: () => void }) {
  return (
    <div className="relative pl-14 lg:pl-16">
      {/* number badge */}
      <button
        onClick={onToggle}
        aria-expanded={expanded}
        className={cn(
          "absolute left-0 top-1 flex h-10 w-10 items-center justify-center rounded-full text-base font-bold text-white shadow-panel transition-transform hover:scale-105 lg:h-11 lg:w-11",
          node.isPre ? "bg-violet-500" : "bg-teal"
        )}
      >
        {node.id}
      </button>

      <div
        className={cn(
          "overflow-hidden rounded-[20px] border bg-white/85 backdrop-blur transition-shadow",
          expanded ? "border-teal/30 shadow-panel" : "border-ink/10 hover:border-teal/25"
        )}
      >
        <button onClick={onToggle} className="flex w-full items-center gap-3 px-5 py-4 text-left">
          <div className="min-w-0 flex-1">
            <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-teal">{node.phase}</p>
            <h3 className="font-display text-lg leading-snug text-ink">{node.title}</h3>
          </div>
          <span className="flex shrink-0 items-center gap-1.5 rounded-full bg-amber-500/10 px-2.5 py-1 text-[11px] font-medium text-amber-700">
            <OctagonPause size={13} />
            人工闸门
          </span>
          <ChevronDown
            size={18}
            className={cn("shrink-0 text-ink/40 transition-transform", expanded && "rotate-180")}
          />
        </button>

        {expanded && (
          <div className="space-y-3 border-t border-ink/10 px-5 py-4">
            <DetailRow label="输入" value={node.input} />
            <DetailRow label="机器" value={node.machine} icon />
            <DetailRow label="输出" value={node.output} />
            <div className="rounded-xl border-[1.5px] border-dashed border-amber-500/70 bg-amber-500/[0.07] px-4 py-3">
              <p className="flex items-center gap-1.5 text-[13px] font-semibold text-amber-800">
                <OctagonPause size={14} />
                暂停等确认：{node.gate}
              </p>
              {node.gateBranches && (
                <ul className="mt-2 space-y-1 pl-5 text-[13px] text-ink/75 list-disc">
                  {node.gateBranches.map((b) => (
                    <li key={b} className={cn(b.includes("打回") && "font-semibold text-red-600")}>
                      {b.includes("打回") && <Undo2 size={12} className="mr-1 inline" />}
                      {b}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function DetailRow({ label, value, icon }: { label: string; value: string; icon?: boolean }) {
  return (
    <div className="flex gap-3 text-[13px] leading-6">
      <span className="flex w-10 shrink-0 items-center gap-1 pt-0.5 text-xs font-bold text-ink/45">
        {icon && <Bot size={12} className="text-teal" />}
        {label}
      </span>
      <p className="text-ink/80">{value}</p>
    </div>
  );
}

export function PipelineBoard() {
  const [expandedId, setExpandedId] = useState<number | null>(0);

  return (
    <div>
      {/* legend */}
      <div className="mb-6 flex flex-wrap gap-x-5 gap-y-2 text-xs text-ink/55">
        <span className="flex items-center gap-1.5">
          <i className="h-2.5 w-2.5 rounded-full bg-teal" /> 机器自动跑
        </span>
        <span className="flex items-center gap-1.5">
          <i className="h-2.5 w-2.5 rounded-full bg-amber-500" /> 人工闸门（暂停等确认）
        </span>
        <span className="flex items-center gap-1.5">
          <i className="h-2.5 w-2.5 rounded-full bg-red-500" /> 打回重做
        </span>
      </div>

      {/* pipeline */}
      <div className="relative space-y-3">
        <div
          aria-hidden="true"
          className="absolute bottom-6 left-5 top-6 w-px bg-gradient-to-b from-violet-400 via-teal/50 to-teal/20 lg:left-[22px]"
        />
        {PIPELINE_NODES.map((node: PipelineNode) => (
          <NodeCard
            key={node.id}
            node={node}
            expanded={expandedId === node.id}
            onToggle={() => setExpandedId((cur) => (cur === node.id ? null : node.id))}
          />
        ))}
      </div>

      {/* mechanics */}
      <section className="mt-8 rounded-[20px] border border-ink/10 bg-ink/[0.04] p-5 lg:p-6">
        <h3 className="font-display text-lg text-ink">运行机制</h3>
        <ul className="mt-3 space-y-2.5">
          {PIPELINE_META.mechanics.map((m) => (
            <li key={m.k} className="flex gap-3 text-[13px] leading-6">
              <span className="w-12 shrink-0 font-bold text-ink/60">{m.k}</span>
              <p className="text-ink/75">{m.v}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
