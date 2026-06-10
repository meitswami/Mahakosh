"use client";

import { useState } from "react";
import {
  Bot,
  Activity,
  GitBranch,
  Shield,
  Zap,
  CheckCircle2,
  AlertTriangle,
  Clock,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  useAgentStatus,
  useAgentExecutions,
  useAgentEvents,
  usePendingApprovals,
  useOrchestrate,
} from "@/hooks/use-agents";

const TASK_TYPES = [
  { value: "document_processing", label: "Document Processing" },
  { value: "batch_invoice_processing", label: "Batch Invoices" },
  { value: "gst_validation", label: "GST Validation" },
  { value: "report_generation", label: "Report Generation" },
  { value: "approval_flow", label: "Approval Flow" },
  { value: "tally_export", label: "Tally Export" },
];

export default function AgentsPage() {
  const [taskType, setTaskType] = useState("document_processing");
  const [query, setQuery] = useState("");

  const { data: status } = useAgentStatus();
  const { data: executions } = useAgentExecutions();
  const { data: events } = useAgentEvents();
  const { data: approvals } = usePendingApprovals();
  const orchestrate = useOrchestrate();

  const healthMap = new Map(status?.health.map((h) => [h.agent_name, h]) ?? []);

  return (
    <>
      <Header
        title="Agent Swarm"
        description="Digital workforce — task decomposition, parallel execution, consensus validation"
      />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-7xl space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard icon={Bot} label="Active Agents" value={status?.total_agents ?? 0} />
            <StatCard icon={Zap} label="Running Tasks" value={status?.active_tasks ?? 0} accent />
            <StatCard icon={Activity} label="Recent Executions" value={executions?.length ?? 0} />
            <StatCard icon={Shield} label="Pending Approvals" value={approvals?.total ?? 0} warning />
          </div>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <GitBranch className="h-4 w-4" />
                Orchestrator — Launch Task
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col gap-3 sm:flex-row">
                <div className="flex flex-wrap gap-2">
                  {TASK_TYPES.map((t) => (
                    <Button
                      key={t.value}
                      size="sm"
                      variant={taskType === t.value ? "default" : "outline"}
                      onClick={() => setTaskType(t.value)}
                    >
                      {t.label}
                    </Button>
                  ))}
                </div>
              </div>
              <div className="mt-3 flex gap-2">
                <Input
                  placeholder="Optional query or context..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="flex-1"
                />
                <Button
                  disabled={orchestrate.isPending}
                  onClick={() =>
                    orchestrate.mutate({
                      taskType,
                      payload: { query, allow_empty: true },
                      mode: taskType === "batch_invoice_processing" ? "parallel" : "sequential",
                    })
                  }
                >
                  {orchestrate.isPending ? "Running..." : "Execute"}
                </Button>
              </div>
              {orchestrate.data && (
                <div className="mt-3 rounded-md border p-3 text-sm">
                  <div className="flex items-center gap-2">
                    {orchestrate.data.success ? (
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                    ) : (
                      <AlertTriangle className="h-4 w-4 text-amber-600" />
                    )}
                    <span>
                      Task {orchestrate.data.task_id} — confidence {orchestrate.data.confidence}%
                    </span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <div className="grid gap-6 lg:grid-cols-12">
            <div className="lg:col-span-7 space-y-6">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Execution Graph</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="font-mono text-xs leading-relaxed text-muted-foreground">
                    <p className="text-foreground font-sans text-sm font-medium mb-3">User Task</p>
                    <p className="ml-4">↓</p>
                    <p className="ml-4 text-primary font-medium">Master Orchestrator</p>
                    <div className="ml-8 mt-2 space-y-1 border-l-2 border-primary/30 pl-4">
                      {(status?.agents ?? []).slice(0, 8).map((agent) => {
                        const h = healthMap.get(agent.name);
                        return (
                          <div key={agent.name} className="flex items-center gap-2">
                            <span>├── {agent.name}</span>
                            <HealthDot healthy={h?.healthy ?? true} />
                          </div>
                        );
                      })}
                    </div>
                    <p className="ml-4 mt-2">↓</p>
                    <p className="ml-4">Consensus Engine</p>
                    <p className="ml-4">↓</p>
                    <p className="ml-4 text-foreground font-sans font-medium">Final Result</p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Execution Timeline</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 max-h-80 overflow-y-auto">
                  {(executions ?? []).length === 0 ? (
                    <p className="text-sm text-muted-foreground">No executions yet.</p>
                  ) : (
                    executions?.map((ex) => (
                      <div key={ex.id} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
                        <div className="flex items-center gap-2">
                          <StatusIcon status={ex.status} />
                          <span className="font-medium">{ex.agent_name}</span>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          {ex.confidence != null && (
                            <Badge variant="secondary">{ex.confidence.toFixed(0)}%</Badge>
                          )}
                          {ex.processing_time_ms != null && (
                            <span className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {ex.processing_time_ms}ms
                            </span>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>
            </div>

            <div className="lg:col-span-5 space-y-6">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Agent Health</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 max-h-64 overflow-y-auto">
                  {(status?.health ?? []).map((h) => (
                    <div key={h.agent_name} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
                      <div className="flex items-center gap-2">
                        <HealthDot healthy={h.healthy} />
                        <span>{h.agent_name}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={h.healthy ? "secondary" : "outline"}>
                          {h.success_rate.toFixed(0)}%
                        </Badge>
                        <span className="text-xs text-muted-foreground">{h.execution_count} runs</span>
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Recent Events</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 max-h-48 overflow-y-auto">
                  {(events ?? []).slice(0, 10).map((ev) => (
                    <div key={ev.id} className="rounded-md border px-3 py-2 text-xs">
                      <div className="flex justify-between">
                        <Badge variant="outline">{ev.event_type}</Badge>
                        <span className="text-muted-foreground">{ev.source_agent}</span>
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Pending Approvals</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {(approvals?.items ?? []).length === 0 ? (
                    <p className="text-sm text-muted-foreground">No pending approvals.</p>
                  ) : (
                    approvals?.items.map((a) => (
                      <div key={a.id} className="rounded-md border px-3 py-2 text-sm">
                        <p className="font-medium">{a.title}</p>
                        <p className="text-xs text-muted-foreground">{a.action} · {a.priority}</p>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  accent,
  warning,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number;
  accent?: boolean;
  warning?: boolean;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 pt-6">
        <div
          className={`flex h-10 w-10 items-center justify-center rounded-lg ${
            warning ? "bg-amber-500/10" : accent ? "bg-primary/10" : "bg-muted"
          }`}
        >
          <Icon className={`h-5 w-5 ${warning ? "text-amber-600" : "text-primary"}`} />
        </div>
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-2xl font-semibold">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function HealthDot({ healthy }: { healthy: boolean }) {
  return (
    <span
      className={`inline-block h-2 w-2 rounded-full ${healthy ? "bg-green-500" : "bg-amber-500"}`}
    />
  );
}

function StatusIcon({ status }: { status: string }) {
  if (status === "completed") return <CheckCircle2 className="h-4 w-4 text-green-600" />;
  if (status === "failed") return <AlertTriangle className="h-4 w-4 text-red-500" />;
  return <Clock className="h-4 w-4 text-muted-foreground" />;
}
