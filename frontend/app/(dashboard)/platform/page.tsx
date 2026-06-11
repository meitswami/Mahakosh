"use client";

import { Building2, Users, CreditCard, Activity, Shield } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { usePlatformDashboard, useTenants } from "@/hooks/use-platform";
import { useAuthStore } from "@/store/auth-store";
import Link from "next/link";

export default function PlatformPage() {
  const { user } = useAuthStore();
  const { data, loading, error } = usePlatformDashboard();
  const { tenants, total, loading: tenantsLoading } = useTenants();

  if (!user?.is_platform_admin) {
    return (
      <>
        <Header title="Platform" description="Super admin access required" />
        <div className="flex flex-1 items-center justify-center p-6">
          <Card className="max-w-md">
            <CardContent className="pt-6 text-center text-muted-foreground">
              <Shield className="mx-auto mb-3 h-10 w-10 opacity-50" />
              <p>Platform administration is restricted to Mahakosh platform administrators.</p>
            </CardContent>
          </Card>
        </div>
      </>
    );
  }

  const tenantStats = (data?.tenants as Record<string, unknown>) || {};
  const userStats = (data?.users as Record<string, unknown>) || {};
  const byPlan = ((data?.subscriptions as Record<string, unknown>)?.by_plan as Record<string, number>) || {};

  return (
    <>
      <Header
        title="Platform Control Center"
        description="Multi-tenant operations — tenants, usage, licenses, and health"
      />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-7xl space-y-6">
          {error && <p className="text-sm text-destructive">{error}</p>}

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard icon={Building2} label="Active Tenants" value={String(tenantStats.active ?? "—")} sub={`${tenantStats.total ?? 0} total`} />
            <MetricCard icon={Users} label="Total Users" value={String(userStats.total ?? "—")} />
            <MetricCard icon={CreditCard} label="Plans" value={String(Object.keys(byPlan).length)} sub="subscription tiers" />
            <MetricCard icon={Activity} label="Health" value={String(data?.health ?? "—")} />
          </div>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">Tenants ({total})</CardTitle>
              <Link href="/admin/compliance" className="text-sm text-primary hover:underline">
                Compliance Center
              </Link>
            </CardHeader>
            <CardContent>
              {tenantsLoading || loading ? (
                <p className="text-sm text-muted-foreground">Loading...</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-muted-foreground">
                        <th className="pb-2 pr-4 font-medium">Name</th>
                        <th className="pb-2 pr-4 font-medium">Type</th>
                        <th className="pb-2 pr-4 font-medium">Plan</th>
                        <th className="pb-2 pr-4 font-medium">Users</th>
                        <th className="pb-2 font-medium">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {tenants.map((t) => (
                        <tr key={t.id} className="border-b border-border/50">
                          <td className="py-3 pr-4">
                            <div className="font-medium">{t.name}</div>
                            <div className="text-xs text-muted-foreground">{t.slug}</div>
                          </td>
                          <td className="py-3 pr-4 capitalize">{t.tenant_type}</td>
                          <td className="py-3 pr-4">{t.subscription_tier}</td>
                          <td className="py-3 pr-4">{t.user_count}</td>
                          <td className="py-3">
                            <Badge variant={t.is_active ? "default" : "secondary"}>
                              {t.is_active ? "active" : "inactive"}
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}

function MetricCard({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 pt-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
          <Icon className="h-5 w-5 text-primary" />
        </div>
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="text-2xl font-semibold">{value}</p>
          {sub && <p className="text-xs text-muted-foreground">{sub}</p>}
        </div>
      </CardContent>
    </Card>
  );
}
