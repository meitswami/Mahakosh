"use client";

import { cn } from "@/lib/utils";
import type { TimelineEntry } from "@/services/workflows-api";
import { Bot, CheckCircle2, Clock, XCircle, AlertTriangle } from "lucide-react";

function formatDuration(ms: number | null | undefined) {
  if (!ms) return "—";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function StatusIcon({ status }: { status: string }) {
  if (status === "completed") return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
  if (status === "failed") return <XCircle className="h-4 w-4 text-red-500" />;
  if (status === "running") return <Clock className="h-4 w-4 animate-pulse text-blue-500" />;
  return <AlertTriangle className="h-4 w-4 text-amber-500" />;
}

export function WorkflowTimelineView({ entries }: { entries: TimelineEntry[] | undefined }) {
  if (!entries?.length) {
    return <p className="py-8 text-center text-sm text-muted-foreground">No timeline data yet.</p>;
  }

  return (
    <div className="relative space-y-0 pl-6">
      <div className="absolute bottom-2 left-[11px] top-2 w-px bg-border" />
      {entries.map((entry, i) => (
        <div key={`${entry.type}-${entry.timestamp}-${i}`} className="relative pb-6">
          <div className="absolute -left-6 top-1 flex h-6 w-6 items-center justify-center rounded-full bg-background ring-2 ring-border">
            <StatusIcon status={entry.status} />
          </div>
          <div className="ml-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium">{entry.label}</span>
              <span
                className={cn(
                  "rounded px-1.5 py-0.5 text-[10px] font-medium uppercase",
                  entry.status === "completed" && "bg-emerald-500/10 text-emerald-700",
                  entry.status === "failed" && "bg-red-500/10 text-red-700",
                  entry.status === "running" && "bg-blue-500/10 text-blue-700",
                  !["completed", "failed", "running"].includes(entry.status) &&
                    "bg-muted text-muted-foreground",
                )}
              >
                {entry.status}
              </span>
              {entry.duration_ms != null && (
                <span className="text-xs text-muted-foreground">{formatDuration(entry.duration_ms)}</span>
              )}
            </div>
            <div className="mt-0.5 flex flex-wrap gap-3 text-xs text-muted-foreground">
              {entry.timestamp && <span>{new Date(entry.timestamp).toLocaleString()}</span>}
              {entry.agent_name && (
                <span className="flex items-center gap-1">
                  <Bot className="h-3 w-3" />
                  {entry.agent_name}
                </span>
              )}
              {entry.retry_count != null && entry.retry_count > 0 && (
                <span>Retries: {entry.retry_count}</span>
              )}
            </div>
            {entry.reasoning_summary && (
              <p className="mt-1 text-xs text-muted-foreground">{entry.reasoning_summary}</p>
            )}
            {entry.error && <p className="mt-1 text-xs text-red-500">{entry.error}</p>}
          </div>
        </div>
      ))}
    </div>
  );
}
