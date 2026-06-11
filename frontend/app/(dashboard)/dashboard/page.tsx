"use client";

import Link from "next/link";
import {
  History,
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/utils";
import {
  useApproveCFORecommendation,
  useCEOBriefing,
  useCFORecommendations,
} from "@/hooks/use-cfo";
import type { BriefingItem } from "@/services/cfo-api";

const PRIORITY_VARIANT: Record<string, "destructive" | "warning" | "secondary" | "default"> = {
  critical: "destructive",
  high: "destructive",
  medium: "warning",
  low: "secondary",
};

const HEALTH_COLORS: Record<string, string> = {
  excellent: "text-emerald-600",
  good: "text-blue-600",
  fair: "text-amber-600",
  needs_attention: "text-red-600",
};

export default function DashboardPage() {
  const { data: briefing, isLoading } = useCEOBriefing();
  const { data: recs } = useCFORecommendations();
  const approve = useApproveCFORecommendation();

  const health = briefing?.health_score;
  const metrics = briefing?.key_metrics;

  return (
    <>
      <Header
        title="CEO Mode"
        description="ज्ञान से निर्णय तक — your business at a glance"
      />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-7xl space-y-6">
          {/* Headline + Health */}
          <div className="flex flex-col gap-4 rounded-xl border border-border/60 bg-gradient-to-br from-muted/40 to-background p-6 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Today&apos;s Briefing
              </p>
              <h2 className="text-lg font-semibold leading-snug sm:text-xl">
                {isLoading ? "Loading your briefing…" : briefing?.headline}
              </h2>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-center">
                <p className={`text-3xl font-bold tabular-nums ${HEALTH_COLORS[health?.level ?? "fair"]}`}>
                  {isLoading ? "—" : Math.round(health?.score ?? 0)}
                </p>
                <p className="text-xs text-muted-foreground capitalize">
                  {health?.level?.replace("_", " ") ?? "—"}
                </p>
              </div>
            </div>
          </div>

          {/* Key metrics strip */}
          <div className="grid gap-3 grid-cols-2 lg:grid-cols-5">
            <MetricPill label="Revenue" value={formatCurrency(metrics?.revenue ?? 0)} loading={isLoading} />
            <MetricPill label="Profit" value={formatCurrency(metrics?.profit ?? 0)} loading={isLoading} accent />
            <MetricPill label="Cash" value={formatCurrency(metrics?.cash_position ?? 0)} loading={isLoading} />
            <MetricPill label="GST Due" value={formatCurrency(metrics?.gst_liability ?? 0)} loading={isLoading} />
            <MetricPill
              label="Approvals"
              value={String(metrics?.pending_approvals ?? 0)}
              loading={isLoading}
              warn={(metrics?.pending_approvals ?? 0) > 0}
            />
          </div>

          {/* Four CEO questions */}
          <div className="grid gap-6 lg:grid-cols-2">
            <BriefingSection
              title="What happened?"
              icon={History}
              items={briefing?.what_happened ?? []}
              loading={isLoading}
              emptyText="Recent completed activity will appear here"
            />
            <BriefingSection
              title="What is happening?"
              icon={Activity}
              items={briefing?.what_is_happening ?? []}
              loading={isLoading}
              emptyText="Live operations will appear here"
              live
            />
            <BriefingSection
              title="What needs attention?"
              icon={AlertTriangle}
              items={briefing?.needs_attention ?? []}
              loading={isLoading}
              emptyText="All clear — nothing needs attention"
              accent
            />
            <BriefingSection
              title="What should be done next?"
              icon={ArrowRight}
              items={briefing?.next_actions ?? []}
              loading={isLoading}
              emptyText="Recommendations will appear after data sync"
              actions
              onApprove={(id) => approve.mutate({ id })}
              pendingRecs={recs?.recommendations ?? []}
            />
          </div>

          {/* CFO capabilities footer */}
          {briefing?.cfo_capabilities && briefing.cfo_capabilities.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  AI CFO Capabilities
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {briefing.cfo_capabilities.map((cap) => (
                    <Badge key={cap.type} variant="outline" className="text-xs">
                      {cap.name}
                    </Badge>
                  ))}
                </div>
                <p className="mt-3 text-xs text-muted-foreground">
                  All recommendations require human approval before execution.
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}

function MetricPill({
  label,
  value,
  loading,
  accent,
  warn,
}: {
  label: string;
  value: string;
  loading?: boolean;
  accent?: boolean;
  warn?: boolean;
}) {
  return (
    <div
      className={`rounded-lg border px-4 py-3 ${
        accent ? "border-primary/30 bg-primary/5" : warn ? "border-amber-500/30 bg-amber-500/5" : "border-border/60"
      }`}
    >
      <p className="text-[11px] text-muted-foreground">{label}</p>
      <p className="text-sm font-semibold tabular-nums">{loading ? "—" : value}</p>
    </div>
  );
}

function BriefingSection({
  title,
  icon: Icon,
  items,
  loading,
  emptyText,
  live,
  accent,
  actions,
  onApprove,
  pendingRecs,
}: {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  items: BriefingItem[];
  loading?: boolean;
  emptyText: string;
  live?: boolean;
  accent?: boolean;
  actions?: boolean;
  onApprove?: (id: string) => void;
  pendingRecs?: Array<{ id: string; title: string }>;
}) {
  return (
    <Card className={accent ? "border-amber-500/20" : undefined}>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Icon className={`h-4 w-4 ${accent ? "text-amber-500" : live ? "text-emerald-500" : ""}`} />
          {title}
          {live && items.length > 0 && (
            <span className="ml-auto flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {loading ? (
          <p className="py-4 text-center text-sm text-muted-foreground">Loading…</p>
        ) : items.length === 0 ? (
          <p className="py-4 text-center text-sm text-muted-foreground">{emptyText}</p>
        ) : (
          items.map((item) => (
            <div
              key={item.id}
              className="group flex items-start justify-between gap-3 rounded-lg border border-border/60 px-4 py-3 transition-colors hover:bg-muted/30"
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium leading-snug">{item.title}</p>
                <p className="mt-0.5 text-xs text-muted-foreground line-clamp-2">{item.summary}</p>
                {actions && Boolean(item.metadata?.requires_approval) && typeof item.metadata?.recommendation_id === "string" && (
                  <div className="mt-2 flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-7 text-xs"
                      onClick={() => onApprove?.(item.metadata!.recommendation_id as string)}
                    >
                      <CheckCircle2 className="mr-1 h-3 w-3" />
                      Approve
                    </Button>
                  </div>
                )}
              </div>
              <div className="flex shrink-0 flex-col items-end gap-1">
                <Badge variant={PRIORITY_VARIANT[item.priority] ?? "secondary"} className="text-[10px]">
                  {item.priority}
                </Badge>
                {item.action_url && (
                  <Link href={item.action_url} className="text-[10px] text-muted-foreground hover:text-foreground">
                    View →
                  </Link>
                )}
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
