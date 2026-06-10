"use client";

import type { WorkflowLog } from "@/services/workflows-api";
import { Bot } from "lucide-react";

export function ExecutionLogsView({ logs }: { logs: WorkflowLog[] | undefined }) {
  if (!logs?.length) {
    return <p className="py-4 text-center text-sm text-muted-foreground">No execution logs yet.</p>;
  }

  return (
    <div className="space-y-3">
      {logs.map((log) => (
        <div key={log.id} className="rounded-lg border p-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium">{log.action}</span>
            {log.agent_name && (
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                <Bot className="h-3 w-3" />
                {log.agent_name}
              </span>
            )}
            {log.duration_ms != null && (
              <span className="text-xs text-muted-foreground">{log.duration_ms}ms</span>
            )}
            {log.confidence != null && (
              <span className="text-xs text-muted-foreground">
                {(log.confidence * 100).toFixed(0)}% conf
              </span>
            )}
            <span className="ml-auto text-[10px] text-muted-foreground">
              {new Date(log.created_at).toLocaleString()}
            </span>
          </div>
          {log.reasoning_summary && (
            <p className="mt-2 text-xs text-muted-foreground">{log.reasoning_summary}</p>
          )}
          {log.error_message && (
            <p className="mt-1 text-xs text-red-500">{log.error_message}</p>
          )}
        </div>
      ))}
    </div>
  );
}
