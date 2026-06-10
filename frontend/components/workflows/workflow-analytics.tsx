"use client";

import type { WorkflowAnalytics } from "@/services/workflows-api";
import { CheckCircle2, XCircle, Clock, Bot } from "lucide-react";

function Stat({ label, value, icon: Icon }: { label: string; value: string | number; icon: React.ElementType }) {
  return (
    <div className="rounded-lg border p-4">
      <div className="flex items-center gap-2 text-muted-foreground">
        <Icon className="h-4 w-4" />
        <span className="text-xs">{label}</span>
      </div>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </div>
  );
}

export function WorkflowAnalyticsPanel({ analytics }: { analytics: WorkflowAnalytics | undefined }) {
  if (!analytics) return null;

  const avgSec = (analytics.average_duration_ms / 1000).toFixed(1);

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Completed" value={analytics.completed_workflows} icon={CheckCircle2} />
        <Stat label="Failed" value={analytics.failed_workflows} icon={XCircle} />
        <Stat label="Success Rate" value={`${analytics.success_rate}%`} icon={CheckCircle2} />
        <Stat label="Avg Duration" value={`${avgSec}s`} icon={Clock} />
      </div>
      {Object.keys(analytics.agent_utilization).length > 0 && (
        <div>
          <h4 className="mb-2 flex items-center gap-2 text-sm font-semibold">
            <Bot className="h-4 w-4" />
            Agent Utilization
          </h4>
          <div className="flex flex-wrap gap-2">
            {Object.entries(analytics.agent_utilization).map(([name, count]) => (
              <span key={name} className="rounded-md border px-2 py-1 text-xs">
                {name}: {count}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
