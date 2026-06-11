"use client";

import { Shield, FileCheck, Clock, AlertTriangle } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useCompliance } from "@/hooks/use-platform";
import { useAuthStore } from "@/store/auth-store";

export default function CompliancePage() {
  const { user } = useAuthStore();
  const { compliance, loading } = useCompliance(user?.tenant_id);

  const audit = (compliance?.audit_status as Record<string, unknown>) || {};
  const policies = (compliance?.governance_policies as unknown[]) || [];
  const retention = (compliance?.retention_policies as Record<string, unknown>) || {};
  const security = (compliance?.security_events as unknown[]) || [];
  const approvals = (compliance?.approval_history as Record<string, unknown>) || {};

  return (
    <>
      <Header
        title="Compliance Center"
        description="Audit status, retention policies, security events, and approval history"
      />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-7xl space-y-6">
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading compliance data...</p>
          ) : (
            <>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <StatusCard
                  icon={Shield}
                  label="Audit Status"
                  value={audit.enabled ? "enabled" : "disabled"}
                  detail={`${audit.events_last_30_days ?? 0} events (30d)`}
                />
                <StatusCard icon={FileCheck} label="Retention Days" value={String(retention.retention_days ?? "—")} />
                <StatusCard icon={AlertTriangle} label="Security Events" value={String(security.length)} />
                <StatusCard icon={Clock} label="Pending Approvals" value={String(approvals.pending ?? 0)} />
              </div>

              <div className="grid gap-4 lg:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Governance Policies</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {policies.length === 0 ? (
                      <p className="text-sm text-muted-foreground">No governance policies configured.</p>
                    ) : (
                      policies.map((p, i) => {
                        const policy = p as Record<string, unknown>;
                        return (
                          <div key={i} className="flex items-center justify-between rounded-lg border p-3">
                            <div>
                              <p className="font-medium">{String(policy.name)}</p>
                              <p className="text-xs text-muted-foreground">{String(policy.policy_type)}</p>
                            </div>
                            <Badge variant="default">active</Badge>
                          </div>
                        );
                      })
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Recent Security Events</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {security.length === 0 ? (
                      <p className="text-sm text-muted-foreground">No security events recorded.</p>
                    ) : (
                      security.slice(0, 8).map((e, i) => {
                        const event = e as Record<string, unknown>;
                        return (
                          <div key={i} className="rounded-lg border p-3">
                            <div className="flex items-center justify-between">
                              <span className="text-sm font-medium">{String(event.event_type)}</span>
                              <Badge variant="outline">{String(event.severity)}</Badge>
                            </div>
                            <p className="mt-1 text-xs text-muted-foreground">{String(event.description)}</p>
                          </div>
                        );
                      })
                    )}
                  </CardContent>
                </Card>
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}

function StatusCard({
  icon: Icon,
  label,
  value,
  detail,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  detail?: string;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 pt-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
          <Icon className="h-5 w-5 text-primary" />
        </div>
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="text-xl font-semibold capitalize">{value}</p>
          {detail && <p className="text-xs text-muted-foreground">{detail}</p>}
        </div>
      </CardContent>
    </Card>
  );
}
