"use client";

import { useState } from "react";
import {
  BarChart3,
  TrendingUp,
  IndianRupee,
  AlertTriangle,
  Lightbulb,
  MessageSquare,
  Download,
  Shield,
  Users,
  Package,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatCurrency } from "@/lib/utils";
import {
  useExecutiveDashboard,
  useGenerateReport,
  useNLQuery,
  useReportTemplates,
} from "@/hooks/use-intelligence";

const HEALTH_COLORS: Record<string, string> = {
  excellent: "text-emerald-600",
  good: "text-blue-600",
  fair: "text-amber-600",
  needs_attention: "text-red-600",
};

export default function IntelligencePage() {
  const { data: executive, isLoading } = useExecutiveDashboard();
  const { data: templates } = useReportTemplates();
  const nlQuery = useNLQuery();
  const generateReport = useGenerateReport();
  const [question, setQuestion] = useState("Why did expenses increase?");
  const [activeTab, setActiveTab] = useState<"overview" | "insights" | "reports">("overview");

  const health = executive?.business_health_score;

  const handleAsk = async () => {
    if (!question.trim()) return;
    await nlQuery.mutateAsync({ question });
  };

  const handleDownload = async (reportType: string, name: string) => {
    const { blob, filename } = await generateReport.mutateAsync({
      name,
      reportType,
      format: "excel",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <Header
        title="Business Intelligence"
        description="ज्ञान से निर्णय तक — actionable intelligence from your accounting data"
      />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-7xl space-y-6">
          <div className="flex gap-2 border-b border-border pb-2">
            {(["overview", "insights", "reports"] as const).map((tab) => (
              <Button
                key={tab}
                variant={activeTab === tab ? "default" : "ghost"}
                size="sm"
                onClick={() => setActiveTab(tab)}
                className="capitalize"
              >
                {tab}
              </Button>
            ))}
          </div>

          {activeTab === "overview" && (
            <>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
                <MetricCard label="Revenue" value={formatCurrency(executive?.revenue ?? 0)} icon={IndianRupee} loading={isLoading} />
                <MetricCard label="Expenses" value={formatCurrency(executive?.expenses ?? 0)} icon={TrendingUp} loading={isLoading} />
                <MetricCard label="Profit" value={formatCurrency(executive?.profit ?? 0)} icon={BarChart3} loading={isLoading} accent />
                <MetricCard label="GST Liability" value={formatCurrency(executive?.gst_liability ?? 0)} icon={Shield} loading={isLoading} />
                <HealthCard health={health} loading={isLoading} />
              </div>

              <div className="grid gap-6 lg:grid-cols-2">
                <TrendChart title="Revenue Trend" data={executive?.charts.revenue_trend ?? []} />
                <TrendChart title="Expense Trend" data={executive?.charts.expense_trend ?? []} />
              </div>

              <div className="grid gap-6 lg:grid-cols-2">
                <RankingCard title="Top Customers" icon={Users} items={executive?.top_customers ?? []} />
                <RankingCard title="Top Vendors" icon={Package} items={executive?.top_vendors ?? []} />
              </div>

              {executive?.anomalies && executive.anomalies.length > 0 && (
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <AlertTriangle className="h-4 w-4 text-amber-500" />
                      Detected Anomalies
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {executive.anomalies.map((a, i) => (
                      <div key={i} className="flex items-start justify-between gap-3 rounded-lg border px-4 py-3">
                        <div>
                          <p className="text-sm font-medium">{a.title}</p>
                          <p className="text-xs text-muted-foreground">{a.description}</p>
                        </div>
                        <Badge variant={a.severity === "critical" || a.severity === "high" ? "destructive" : "warning"}>
                          {a.severity}
                        </Badge>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}
            </>
          )}

          {activeTab === "insights" && (
            <div className="grid gap-6 lg:grid-cols-3">
              <Card className="lg:col-span-1">
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <MessageSquare className="h-4 w-4" />
                    Ask Mahakosh
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Input
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="Why did expenses increase?"
                    onKeyDown={(e) => e.key === "Enter" && handleAsk()}
                  />
                  <Button className="w-full" onClick={handleAsk} disabled={nlQuery.isPending}>
                    {nlQuery.isPending ? "Analyzing…" : "Get Answer"}
                  </Button>
                  {nlQuery.data && (
                    <div className="rounded-lg bg-muted/50 p-4 text-sm">
                      <div className="mb-2 flex items-center justify-between">
                        <Badge variant="secondary">{nlQuery.data.type}</Badge>
                        <span className="text-xs text-muted-foreground">{nlQuery.data.confidence_display} confidence</span>
                      </div>
                      <p className="whitespace-pre-wrap">{nlQuery.data.answer}</p>
                    </div>
                  )}
                </CardContent>
              </Card>

              <div className="space-y-6 lg:col-span-2">
                <InsightSection title="Observations" icon={BarChart3} items={executive?.insights?.observations ?? []} />
                <InsightSection title="Recommendations" icon={Lightbulb} items={executive?.insights?.recommendations ?? []} variant="default" />
                <InsightSection title="Warnings" icon={AlertTriangle} items={executive?.insights?.warnings ?? []} variant="warning" />
              </div>
            </div>
          )}

          {activeTab === "reports" && (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {(templates?.templates ?? []).map((t) => (
                <Card key={t.type} className="transition-shadow hover:shadow-md">
                  <CardContent className="flex flex-col gap-4 p-6">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                        <BarChart3 className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <h3 className="font-medium">{t.name}</h3>
                        <p className="text-xs text-muted-foreground">{t.formats.join(", ")}</p>
                      </div>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      className="w-full"
                      onClick={() => handleDownload(t.type, t.name)}
                      disabled={generateReport.isPending}
                    >
                      <Download className="mr-2 h-4 w-4" />
                      Download Excel
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function MetricCard({
  label,
  value,
  icon: Icon,
  loading,
  accent,
}: {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
  loading?: boolean;
  accent?: boolean;
}) {
  return (
    <Card className={accent ? "border-primary/30 bg-primary/5" : undefined}>
      <CardContent className="flex items-center gap-4 p-5">
        <div className={`rounded-lg p-2.5 ${accent ? "bg-primary/10" : "bg-muted"}`}>
          <Icon className={`h-5 w-5 ${accent ? "text-primary" : "text-muted-foreground"}`} />
        </div>
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-xl font-semibold tabular-nums">{loading ? "—" : value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function HealthCard({ health, loading }: { health?: { score: number; level: string }; loading?: boolean }) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-5">
        <div className="relative flex h-14 w-14 items-center justify-center">
          <svg className="h-14 w-14 -rotate-90" viewBox="0 0 36 36">
            <circle cx="18" cy="18" r="15.5" fill="none" stroke="currentColor" strokeWidth="2" className="text-muted/30" />
            <circle
              cx="18" cy="18" r="15.5" fill="none" stroke="currentColor" strokeWidth="2.5"
              strokeDasharray={`${(health?.score ?? 0) * 0.97} 100`}
              className={HEALTH_COLORS[health?.level ?? "fair"] ?? "text-muted-foreground"}
            />
          </svg>
          <span className="absolute text-sm font-bold">{loading ? "—" : Math.round(health?.score ?? 0)}</span>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Business Health</p>
          <p className={`text-sm font-medium capitalize ${HEALTH_COLORS[health?.level ?? "fair"]}`}>
            {loading ? "—" : health?.level?.replace("_", " ")}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

function TrendChart({ title, data }: { title: string; data: Array<{ label: string; value: number }> }) {
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">Sync accounting data to see trends</p>
        ) : (
          <div className="flex h-32 items-end gap-1">
            {data.map((d) => (
              <div key={d.label} className="flex flex-1 flex-col items-center gap-1">
                <div
                  className="w-full rounded-t bg-primary/70 transition-all"
                  style={{ height: `${Math.max(4, (d.value / max) * 100)}%` }}
                  title={`${d.label}: ${formatCurrency(d.value)}`}
                />
                <span className="truncate text-[9px] text-muted-foreground">{d.label.split(" ")[0]}</span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function RankingCard({
  title,
  icon: Icon,
  items,
}: {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  items: Array<{ name: string; value: number; share_pct?: number }>;
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Icon className="h-4 w-4" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">No data available</p>
        ) : (
          <div className="space-y-2">
            {items.map((item, i) => (
              <div key={i} className="flex items-center justify-between rounded-lg border px-3 py-2">
                <span className="truncate text-sm font-medium">{item.name}</span>
                <div className="text-right">
                  <p className="text-sm tabular-nums">{formatCurrency(item.value)}</p>
                  {item.share_pct != null && (
                    <p className="text-xs text-muted-foreground">{item.share_pct}%</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function InsightSection({
  title,
  icon: Icon,
  items,
  variant,
}: {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  items: Array<{ type: string; text: string; confidence: number }>;
  variant?: "warning" | "default";
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Icon className={`h-4 w-4 ${variant === "warning" ? "text-amber-500" : ""}`} />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">No {title.toLowerCase()} yet</p>
        ) : (
          items.map((item, i) => (
            <div key={i} className="rounded-lg border px-4 py-3 text-sm">
              <p>{item.text}</p>
              <p className="mt-1 text-xs text-muted-foreground">{item.confidence}% confidence</p>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
