"use client";

import { cn } from "@/lib/utils";
import type { WorkflowGraph, WorkflowGraphNode } from "@/services/workflows-api";
import {
  Bot,
  CheckCircle2,
  Circle,
  GitBranch,
  Loader2,
  Shield,
  XCircle,
  AlertCircle,
} from "lucide-react";

const NODE_ICONS: Record<string, React.ElementType> = {
  start: Circle,
  end: CheckCircle2,
  agent: Bot,
  validation: Shield,
  approval: Shield,
  task: GitBranch,
  decision: GitBranch,
};

const STATUS_STYLES: Record<string, string> = {
  pending: "border-muted bg-muted/30 text-muted-foreground",
  running: "border-blue-500/50 bg-blue-500/10 text-blue-700 dark:text-blue-400 ring-2 ring-blue-500/20",
  completed: "border-emerald-500/50 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  failed: "border-red-500/50 bg-red-500/10 text-red-700 dark:text-red-400",
  waiting: "border-amber-500/50 bg-amber-500/10 text-amber-700 dark:text-amber-400",
};

function NodeCard({ node, replayMode }: { node: WorkflowGraphNode; replayMode?: boolean }) {
  const Icon = NODE_ICONS[node.type] || GitBranch;
  const statusStyle = STATUS_STYLES[node.status] || STATUS_STYLES.pending;

  return (
    <div className="flex flex-col items-center">
      <div
        className={cn(
          "relative flex w-36 flex-col items-center rounded-lg border px-3 py-3 transition-all",
          statusStyle,
        )}
      >
        {node.status === "running" && (
          <Loader2 className="absolute -right-1 -top-1 h-4 w-4 animate-spin text-blue-500" />
        )}
        {node.status === "failed" && (
          <XCircle className="absolute -right-1 -top-1 h-4 w-4 text-red-500" />
        )}
        <Icon className="mb-1 h-4 w-4" />
        <span className="text-center text-xs font-medium leading-tight">{node.label}</span>
        {node.agent_name && (
          <span className="mt-1 text-[10px] opacity-70">{node.agent_name}</span>
        )}
        {node.retry_count != null && node.retry_count > 0 && (
          <span className="mt-0.5 text-[10px] text-amber-600">retry {node.retry_count}</span>
        )}
      </div>
      {replayMode && node.replay?.decisions && node.replay.decisions.length > 0 && (
        <div className="mt-2 max-w-40 rounded border bg-card p-2 text-[10px] text-muted-foreground">
          {node.replay.decisions[0]}
        </div>
      )}
      {node.error_message && (
        <div className="mt-1 flex items-center gap-1 text-[10px] text-red-500">
          <AlertCircle className="h-3 w-3" />
          {node.error_message.slice(0, 40)}
        </div>
      )}
    </div>
  );
}

export function WorkflowGraphView({
  graph,
  replayMode = false,
}: {
  graph: WorkflowGraph | undefined;
  replayMode?: boolean;
}) {
  if (!graph) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
        Loading workflow graph...
      </div>
    );
  }

  const stepNodes = graph.nodes.filter((n) => n.type !== "start" && n.type !== "end");

  return (
    <div className="overflow-x-auto pb-4">
      <div className="flex min-w-max items-center gap-2 px-4 py-6">
        {graph.nodes.map((node, idx) => (
          <div key={node.id} className="flex items-center">
            <NodeCard node={node} replayMode={replayMode} />
            {idx < graph.nodes.length - 1 && (
              <div className="mx-1 flex items-center">
                <div className="h-px w-8 bg-border" />
                <div className="h-0 w-0 border-y-4 border-l-8 border-y-transparent border-l-border" />
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="flex flex-wrap gap-2 px-4 text-xs text-muted-foreground">
        <span>{stepNodes.filter((n) => n.status === "completed").length}/{stepNodes.length} steps complete</span>
        <span>·</span>
        <span>{graph.assigned_agents.length} agents</span>
      </div>
    </div>
  );
}
