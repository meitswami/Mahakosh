"use client";

import Link from "next/link";
import {
  FileText,
  GitBranch,
  IndianRupee,
  TrendingUp,
  Bot,
  BarChart3,
  ArrowRight,
  AlertTriangle,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { MetricCard } from "@/components/dashboard/metric-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/utils";
import { useExecutiveDashboard } from "@/hooks/use-intelligence";
import { useWorkflows } from "@/hooks/use-workflows";

export default function DashboardPage() {
  const { data: executive, isLoading } = useExecutiveDashboard();
  const { data: workflows } = useWorkflows(1);

  const health = executive?.business_health_score;
  const liveWorkflows = workflows?.items?.filter((w) => ["running", "queued", "waiting"].includes(w.status)).length ?? 0;

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
              label="Revenue"
              value={isLoading ? "—" : formatCurrency(executive?.revenue ?? 0)}
              change={executive?.growth?.revenue_pct ?? undefined}
              icon={IndianRupee}
            />
            <MetricCard
              label="Profit"
              value={isLoading ? "—" : formatCurrency(executive?.profit ?? 0)}
              icon={TrendingUp}
            />
            <MetricCard
              label="GST Liability"
              value={isLoading ? "—" : formatCurrency(executive?.gst_liability ?? 0)}
              icon={FileText}
            />
            <MetricCard
              label="Health Score"
              value={isLoading ? "—" : `${Math.round(health?.score ?? 0)}/100`}
              icon={BarChart3}
            />
          </div>

          {executive?.insights?.warnings && executive.insights.warnings.length > 0 && (
            <Card className="border-amber-500/30 bg-amber-500/5">
              <CardContent className="flex items-center justify-between p-4">
                <div className="flex items-center gap-3">
                  <AlertTriangle className="h-5 w-5 text-amber-600" />
                  <p className="text-sm">{executive.insights.warnings[0].text}</p>
                </div>
                <Link href="/intelligence">
                  <Button variant="outline" size="sm">View Intelligence</Button>
                </Link>
              </CardContent>
            </Card>
          )}

          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader className="flex flex-row items-center justify-between pb-3">
                <CardTitle className="text-base">Top Customers</CardTitle>
                <Link href="/intelligence" className="text-xs text-muted-foreground hover:text-foreground">
                  Full intelligence <ArrowRight className="inline h-3 w-3" />
                </Link>
              </CardHeader>
              <CardContent>
                {executive?.top_customers?.length ? (
                  <div className="space-y-2">
                    {executive.top_customers.map((c, i) => (
                      <div key={i} className="flex items-center justify-between rounded-lg border px-3 py-2">
                        <span className="text-sm font-medium">{c.name}</span>
                        <span className="text-sm tabular-nums">{formatCurrency(c.value)}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="py-6 text-center text-sm text-muted-foreground">
                    Sync accounting data to see customer intelligence
                  </p>
                )}
              </CardContent>
            </Card>

            <div className="space-y-6">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Bot className="h-4 w-4" />
                    Business Health
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-col items-center py-4">
                    <p className="text-4xl font-bold tabular-nums">{isLoading ? "—" : Math.round(health?.score ?? 0)}</p>
                    <Badge variant="secondary" className="mt-2 capitalize">
                      {health?.level?.replace("_", " ") ?? "—"}
                    </Badge>
                    {health?.components && (
                      <div className="mt-4 w-full space-y-1.5">
                        {Object.entries(health.components).map(([k, v]) => (
                          <div key={k} className="flex justify-between text-xs">
                            <span className="text-muted-foreground capitalize">{k.replace(/_/g, " ")}</span>
                            <span className="tabular-nums">{Math.round(v)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <GitBranch className="h-4 w-4" />
                    Operations
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Pending Approvals</span>
                    <span className="font-medium">{executive?.pending_approvals ?? 0}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Active Workflows</span>
                    <span className="font-medium">{liveWorkflows}</span>
                  </div>
                  <Link href="/workflows">
                    <Button variant="outline" size="sm" className="w-full">Workflow Center</Button>
                  </Link>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
