"use client";

import { use, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  RotateCcw,
  XCircle,
  Play,
  History,
  GitBranch,
  Clock,
  Bot,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { WorkflowGraphView } from "@/components/workflows/workflow-graph";
import { WorkflowTimelineView } from "@/components/workflows/workflow-timeline";
import { ExecutionLogsView } from "@/components/workflows/execution-logs";
import { WorkflowTransparencyPanel } from "@/components/workflows/workflow-transparency-panel";
import {
  useWorkflow,
  useWorkflowGraph,
  useWorkflowTimeline,
  useWorkflowLogs,
  useExecuteWorkflow,
  useRetryWorkflow,
  useCancelWorkflow,
} from "@/hooks/use-workflows";

export default function WorkflowDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [replayMode, setReplayMode] = useState(false);

  const { data: workflow } = useWorkflow(id);
  const { data: graph } = useWorkflowGraph(id, replayMode);
  const { data: timeline } = useWorkflowTimeline(id);
  const { data: logs } = useWorkflowLogs(id);
  const execute = useExecuteWorkflow();
  const retry = useRetryWorkflow();
  const cancel = useCancelWorkflow();

  const canExecute = workflow?.status === "pending";
  const canRetry = workflow?.status === "failed" || workflow?.status === "waiting";
  const canCancel = ["running", "queued", "waiting", "paused"].includes(workflow?.status ?? "");
  const canReplay = workflow?.status === "completed" || workflow?.status === "failed";

  return (
    <>
      <Header
        title={workflow?.name ?? "Workflow"}
        description={workflow?.workflow_type ?? "Loading..."}
      />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-7xl space-y-6">
          <div className="flex flex-wrap items-center gap-3">
            <Button variant="outline" size="sm" asChild>
              <Link href="/workflows">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back
              </Link>
            </Button>
            {workflow && (
              <Badge
                variant={
                  workflow.status === "completed"
                    ? "success"
                    : workflow.status === "failed"
                      ? "destructive"
                      : "secondary"
                }
              >
                {workflow.status}
              </Badge>
            )}
            <div className="ml-auto flex flex-wrap gap-2">
              {canExecute && (
                <Button size="sm" disabled={execute.isPending} onClick={() => execute.mutate(id)}>
                  <Play className="mr-2 h-3 w-3" />
                  Execute
                </Button>
              )}
              {canRetry && (
                <Button
                  size="sm"
                  variant="outline"
                  disabled={retry.isPending}
                  onClick={() => retry.mutate({ id })}
                >
                  <RotateCcw className="mr-2 h-3 w-3" />
                  Retry
                </Button>
              )}
              {canCancel && (
                <Button
                  size="sm"
                  variant="destructive"
                  disabled={cancel.isPending}
                  onClick={() => cancel.mutate(id)}
                >
                  <XCircle className="mr-2 h-3 w-3" />
                  Cancel
                </Button>
              )}
              {canReplay && (
                <Button
                  size="sm"
                  variant={replayMode ? "default" : "outline"}
                  onClick={() => setReplayMode(!replayMode)}
                >
                  <History className="mr-2 h-3 w-3" />
                  {replayMode ? "Exit Replay" : "Replay Workflow"}
                </Button>
              )}
            </div>
          </div>

          {workflow && (
            <div className="grid gap-3 sm:grid-cols-3">
              <InfoCard icon={Clock} label="Duration" value={
                workflow.duration_ms ? `${(workflow.duration_ms / 1000).toFixed(1)}s` : "—"
              } />
              <InfoCard icon={Bot} label="Agents" value={workflow.assigned_agents.length.toString()} />
              <InfoCard icon={GitBranch} label="Steps" value={`${workflow.steps.filter((s) => s.status === "completed").length}/${workflow.steps.length}`} />
            </div>
          )}

          <WorkflowTransparencyPanel transparency={workflow?.transparency} />

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">
                {replayMode ? "Workflow Replay — Agent Decisions" : "Workflow Graph"}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <WorkflowGraphView graph={graph} replayMode={replayMode} />
            </CardContent>
          </Card>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Execution Timeline</CardTitle>
              </CardHeader>
              <CardContent>
                <WorkflowTimelineView entries={timeline} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Execution Logs</CardTitle>
              </CardHeader>
              <CardContent>
                <ExecutionLogsView logs={logs} />
              </CardContent>
            </Card>
          </div>

          {workflow?.error_message && (
            <Card className="border-red-500/30">
              <CardContent className="p-4">
                <p className="text-sm font-medium text-red-600">Error</p>
                <p className="mt-1 text-sm text-muted-foreground">{workflow.error_message}</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}

function InfoCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 p-4">
        <Icon className="h-4 w-4 text-muted-foreground" />
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="font-semibold">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}
