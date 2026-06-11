"use client";

import { AlertTriangle, CheckCircle2, Info } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export interface TwinIssue {
  id: string;
  twin_object_id: string;
  issue_type: string;
  code: string;
  severity: string;
  message: string;
  suggestion: string | null;
  status: string;
  created_at: string;
}

export interface TwinOverview {
  object_counts: Record<string, number>;
  total_objects: number;
  avg_quality_score: number;
  open_issues: number;
  error_issues: number;
  suggestions: {
    type: string;
    priority: string;
    message: string;
    action: string;
    details?: Record<string, unknown>;
  }[];
  gst_liability: {
    net_liability?: number;
    output_tax?: { total?: number };
    input_tax?: { total?: number };
  };
}

function QualityBadge({ score }: { score: number }) {
  const variant = score >= 80 ? "default" : score >= 60 ? "secondary" : "destructive";
  return <Badge variant={variant}>{score.toFixed(0)}/100</Badge>;
}

function SeverityIcon({ severity }: { severity: string }) {
  if (severity === "error") return <AlertTriangle className="h-4 w-4 text-destructive" />;
  if (severity === "warning") return <AlertTriangle className="h-4 w-4 text-amber-500" />;
  return <Info className="h-4 w-4 text-muted-foreground" />;
}

export function DataQualityPanel({
  overview,
  issues,
  onResolve,
  onNormalize,
  resolving,
  normalizing,
}: {
  overview?: TwinOverview;
  issues?: TwinIssue[];
  onResolve: (issueId: string) => void;
  onNormalize: () => void;
  resolving: boolean;
  normalizing: boolean;
}) {
  if (!overview) {
    return <p className="py-4 text-center text-sm text-muted-foreground">Loading data quality...</p>;
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-4">
        <Stat label="Twin Objects" value={overview.total_objects} />
        <Stat label="Avg Quality" value={`${overview.avg_quality_score}/100`} />
        <Stat label="Open Issues" value={overview.open_issues} />
        <Stat label="Errors" value={overview.error_issues} />
      </div>

      {overview.gst_liability?.net_liability !== undefined && (
        <div className="rounded-lg border bg-muted/30 px-4 py-3">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">GST Liability (Twin)</p>
          <p className="text-lg font-semibold">
            ₹{overview.gst_liability.net_liability.toLocaleString("en-IN")}
          </p>
        </div>
      )}

      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">Cleanup Suggestions</p>
        <Button size="sm" variant="outline" disabled={normalizing} onClick={onNormalize}>
          Re-normalize
        </Button>
      </div>

      {overview.suggestions.length ? (
        <div className="space-y-2">
          {overview.suggestions.slice(0, 8).map((s, i) => (
            <div key={i} className="flex items-start gap-2 rounded-lg border px-3 py-2">
              <Badge variant={s.priority === "high" ? "destructive" : "secondary"}>{s.priority}</Badge>
              <div>
                <p className="text-sm">{s.message}</p>
                <p className="text-xs text-muted-foreground">Action: {s.action}</p>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">No cleanup suggestions — data looks good.</p>
      )}

      <p className="text-sm font-medium">Open Issues</p>
      {issues?.length ? (
        <div className="space-y-2">
          {issues.map((issue) => (
            <div key={issue.id} className="flex items-start justify-between gap-2 rounded-lg border px-3 py-2">
              <div className="flex items-start gap-2">
                <SeverityIcon severity={issue.severity} />
                <div>
                  <p className="text-sm font-medium">{issue.message}</p>
                  {issue.suggestion && (
                    <p className="text-xs text-muted-foreground">{issue.suggestion}</p>
                  )}
                  <p className="text-xs text-muted-foreground">{issue.code}</p>
                </div>
              </div>
              <Button
                size="sm"
                variant="ghost"
                disabled={resolving}
                onClick={() => onResolve(issue.id)}
              >
                <CheckCircle2 className="mr-1 h-3 w-3" />
                Resolve
              </Button>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">No open data quality issues.</p>
      )}
    </div>
  );
}

export { QualityBadge };

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-semibold">{value}</p>
    </div>
  );
}
