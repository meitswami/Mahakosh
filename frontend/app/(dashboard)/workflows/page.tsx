"use client";

import { useState } from "react";
import Link from "next/link";
import {
  GitBranch,
  Activity,
  BarChart3,
  Shield,
  Bot,
  Play,
  ExternalLink,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LiveMonitor } from "@/components/workflows/live-monitor";
import { AgentActivityPanel } from "@/components/workflows/agent-activity-panel";
import { ApprovalCenter } from "@/components/workflows/approval-center";
import { WorkflowAnalyticsPanel } from "@/components/workflows/workflow-analytics";
import {
  useWorkflowTemplates,
  useWorkflows,
  useLiveWorkflows,
  useWorkflowAnalytics,
  useWorkflowAgentActivity,
  useWorkflowApprovals,
  useWorkflowApprovalHistory,
  useCreateWorkflow,
  useExecuteWorkflow,
} from "@/hooks/use-workflows";

const STATUS_COLORS: Record<string, "success" | "destructive" | "warning" | "secondary" | "default"> = {
  completed: "success",
  failed: "destructive",
  running: "default",
  waiting: "warning",
  queued: "secondary",
};

export default function WorkflowsPage() {
  const [page] = useState(1);
  const { data: templates } = useWorkflowTemplates();
  const { data: workflows } = useWorkflows(page);
  const { data: live } = useLiveWorkflows();
  const { data: analytics } = useWorkflowAnalytics();
  const { data: agents } = useWorkflowAgentActivity();
  const { data: pendingApprovals } = useWorkflowApprovals();
  const { data: approvalHistory } = useWorkflowApprovalHistory();
  const createWorkflow = useCreateWorkflow();
  const executeWorkflow = useExecuteWorkflow();

  const handleLaunch = async (name: string, workflowType: string) => {
    const wf = await createWorkflow.mutateAsync({ name, workflowType, inputData: {} });
    await executeWorkflow.mutateAsync(wf.id);
  };

  return (
    <>
      <Header
        title="Workflow Center"
        description="ज्ञान से निर्णय तक — visible pipelines from input to output"
      />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-7xl space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard icon={GitBranch} label="Templates" value={templates?.length ?? 0} />
            <StatCard icon={Activity} label="Live" value={live?.length ?? 0} accent />
            <StatCard icon={BarChart3} label="Completed (30d)" value={analytics?.completed_workflows ?? 0} />
            <StatCard icon={Shield} label="Pending Approvals" value={pendingApprovals?.length ?? 0} warning />
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Activity className="h-4 w-4" />
                  Live Monitoring
                </CardTitle>
              </CardHeader>
              <CardContent>
                <LiveMonitor workflows={live} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <BarChart3 className="h-4 w-4" />
                  Analytics
                </CardTitle>
              </CardHeader>
              <CardContent>
                <WorkflowAnalyticsPanel analytics={analytics} />
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Bot className="h-4 w-4" />
                Agent Activity
              </CardTitle>
            </CardHeader>
            <CardContent>
              <AgentActivityPanel agents={agents} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Shield className="h-4 w-4" />
                Approval Center
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ApprovalCenter pending={pendingApprovals} history={approvalHistory} />
            </CardContent>
          </Card>

          <div>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold">Workflow Templates</h2>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {(templates ?? []).map((wf) => (
                <Card key={wf.workflow_type} className="transition-shadow hover:shadow-md">
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                        <GitBranch className="h-5 w-5 text-primary" />
                      </div>
                      <Badge variant="success">available</Badge>
                    </div>
                    <h3 className="mt-4 font-semibold">{wf.name}</h3>
                    <p className="mt-1 text-sm text-muted-foreground line-clamp-2">{wf.description}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{wf.step_count} steps · {wf.agents.join(", ")}</p>
                    <Button
                      className="mt-4 w-full"
                      size="sm"
                      disabled={createWorkflow.isPending || executeWorkflow.isPending}
                      onClick={() => handleLaunch(`${wf.name} — ${new Date().toLocaleDateString()}`, wf.workflow_type)}
                    >
                      <Play className="mr-2 h-3 w-3" />
                      Launch Workflow
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Recent Workflows</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {workflows?.items?.length ? (
                  workflows.items.map((wf) => (
                    <Link
                      key={wf.id}
                      href={`/workflows/${wf.id}`}
                      className="flex items-center justify-between rounded-lg border p-3 transition-colors hover:bg-muted/50"
                    >
                      <div>
                        <p className="text-sm font-medium">{wf.name}</p>
                        <p className="text-xs text-muted-foreground">{wf.workflow_type}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={STATUS_COLORS[wf.status] || "secondary"}>{wf.status}</Badge>
                        <ExternalLink className="h-3 w-3 text-muted-foreground" />
                      </div>
                    </Link>
                  ))
                ) : (
                  <p className="py-4 text-center text-sm text-muted-foreground">
                    No workflows yet. Launch a template above.
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
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
  icon: React.ElementType;
  label: string;
  value: number;
  accent?: boolean;
  warning?: boolean;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-4">
        <div
          className={`flex h-10 w-10 items-center justify-center rounded-lg ${
            warning ? "bg-amber-500/10" : accent ? "bg-blue-500/10" : "bg-primary/10"
          }`}
        >
          <Icon className={`h-5 w-5 ${warning ? "text-amber-600" : accent ? "text-blue-600" : "text-primary"}`} />
        </div>
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-2xl font-semibold">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}
