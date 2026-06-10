"use client";

import Link from "next/link";
import type { LiveWorkflow } from "@/services/workflows-api";
import { Badge } from "@/components/ui/badge";
import { Activity, Loader2 } from "lucide-react";

const STATUS_VARIANT: Record<string, "default" | "success" | "warning" | "destructive" | "secondary"> = {
  running: "default",
  queued: "secondary",
  waiting: "warning",
  paused: "warning",
};

export function LiveMonitor({ workflows }: { workflows: LiveWorkflow[] | undefined }) {
  if (!workflows?.length) {
    return (
      <p className="py-4 text-center text-sm text-muted-foreground">
        No active workflows. Start one from a template below.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {workflows.map((wf) => (
        <Link
          key={wf.id}
          href={`/workflows/${wf.id}`}
          className="flex items-center gap-3 rounded-lg border p-3 transition-colors hover:bg-muted/50"
        >
          {(wf.status === "running" || wf.status === "queued") && (
            <Loader2 className="h-4 w-4 shrink-0 animate-spin text-blue-500" />
          )}
          {wf.status === "waiting" && <Activity className="h-4 w-4 shrink-0 text-amber-500" />}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <p className="truncate text-sm font-medium">{wf.name}</p>
              <Badge variant={STATUS_VARIANT[wf.status] || "secondary"}>{wf.status}</Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              {wf.current_step ? `${wf.current_step} · ${wf.current_agent}` : wf.workflow_type}
            </p>
            <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${wf.progress}%` }}
              />
            </div>
          </div>
          <span className="text-xs font-medium text-muted-foreground">{wf.progress}%</span>
        </Link>
      ))}
    </div>
  );
}
