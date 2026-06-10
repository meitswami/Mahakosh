import {
  FileText,
  GitBranch,
  IndianRupee,
  Receipt,
  Bot,
  CheckCircle2,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { MetricCard } from "@/components/dashboard/metric-card";
import { ActivityFeed } from "@/components/dashboard/activity-feed";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatCurrency } from "@/lib/utils";
import type { ActivityItem } from "@/types";

const activities: ActivityItem[] = [
  {
    id: "1",
    type: "document",
    title: "Invoice #INV-2024-1847 processed",
    description: "OCR extraction completed — 3 line items matched, GST validated",
    timestamp: "2 minutes ago",
    status: "completed",
  },
  {
    id: "2",
    type: "workflow",
    title: "Purchase voucher draft created",
    description: "Vendor: Sharma Traders Pvt Ltd — ₹1,24,500 incl. GST",
    timestamp: "15 minutes ago",
    status: "pending",
  },
  {
    id: "3",
    type: "agent",
    title: "GST Agent validated 12AABCJ1234F1Z5",
    description: "Active registration — Maharashtra, Regular taxpayer",
    timestamp: "1 hour ago",
    status: "completed",
  },
  {
    id: "4",
    type: "workflow",
    title: "Document batch upload in progress",
    description: "8 of 15 documents processed via OCR pipeline",
    timestamp: "2 hours ago",
    status: "running",
  },
];

const agents = [
  { name: "OCR Agent", status: "idle", tasks: 0 },
  { name: "GST Agent", status: "idle", tasks: 0 },
  { name: "Accounting Agent", status: "idle", tasks: 0 },
  { name: "Master Orchestrator", status: "ready", tasks: 0 },
];

export default function DashboardPage() {
  return (
    <>
      <Header
        title="Dashboard"
        description="Business intelligence overview — ज्ञान से निर्णय तक"
      />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-7xl space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              label="Documents Processed"
              value="1,247"
              change={12.5}
              icon={FileText}
            />
            <MetricCard
              label="Vouchers Drafted"
              value="384"
              change={8.2}
              icon={Receipt}
            />
            <MetricCard
              label="GST Validations"
              value="892"
              change={15.3}
              icon={CheckCircle2}
            />
            <MetricCard
              label="Total Processed Value"
              value={formatCurrency(28475000)}
              change={6.7}
              icon={IndianRupee}
            />
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <ActivityFeed activities={activities} />
            </div>

            <div className="space-y-6">
              <Card className="animate-fade-in">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Bot className="h-4 w-4" />
                    Agent Swarm Status
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {agents.map((agent) => (
                      <div
                        key={agent.name}
                        className="flex items-center justify-between rounded-lg border px-3 py-2"
                      >
                        <span className="text-sm font-medium">{agent.name}</span>
                        <Badge variant={agent.status === "ready" ? "success" : "secondary"}>
                          {agent.status}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card className="animate-fade-in">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <GitBranch className="h-4 w-4" />
                    Active Workflows
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-col items-center justify-center py-6 text-center">
                    <p className="text-2xl font-semibold">3</p>
                    <p className="text-sm text-muted-foreground">workflows running</p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
