"use client";

import type { AgentActivity } from "@/services/workflows-api";
import { Badge } from "@/components/ui/badge";
import { Bot, Activity, Clock } from "lucide-react";

export function AgentActivityPanel({ agents }: { agents: AgentActivity[] | undefined }) {
  if (!agents?.length) {
    return <p className="py-4 text-center text-sm text-muted-foreground">No agent activity recorded.</p>;
  }

  return (
    <div className="space-y-2">
      {agents.map((agent) => (
        <div
          key={agent.agent_name}
          className="flex items-center justify-between rounded-lg border p-3"
        >
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary/10">
              <Bot className="h-4 w-4 text-primary" />
            </div>
            <div>
              <p className="text-sm font-medium">{agent.agent_name}</p>
              <p className="text-xs text-muted-foreground">
                {agent.execution_count} runs · {agent.average_runtime_ms.toFixed(0)}ms avg
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={agent.healthy ? "success" : "warning"}>
              {agent.status}
            </Badge>
            {agent.queue_length > 0 && (
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                <Activity className="h-3 w-3" />
                {agent.queue_length}
              </span>
            )}
            <span className="flex items-center gap-1 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              {agent.success_rate.toFixed(0)}%
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
