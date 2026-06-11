import { apiFetch } from "@/lib/api";

export const platformApi = {
  dashboard: () => apiFetch<Record<string, unknown>>("/platform/dashboard"),
  listTenants: (page = 1) => apiFetch<{ tenants: TenantRow[]; total: number }>(`/tenants?page=${page}`),
  createTenant: (data: Record<string, unknown>) =>
    apiFetch("/tenants/create", { method: "POST", body: JSON.stringify(data) }),
  currentSubscription: () => apiFetch<Record<string, unknown>>("/subscriptions/current"),
  usage: (days = 30) => apiFetch<Record<string, unknown>>(`/usage?days=${days}`),
  compliance: (tenantId: string) => apiFetch<Record<string, unknown>>(`/tenants/${tenantId}/compliance`),
  partnerDashboard: () => apiFetch<Record<string, unknown>>("/platform/partners/dashboard"),
  updateBranding: (tenantId: string, data: Record<string, unknown>) =>
    apiFetch(`/tenants/${tenantId}/branding`, { method: "PUT", body: JSON.stringify(data) }),
};

export interface TenantRow {
  id: string;
  name: string;
  slug: string;
  tenant_type: string;
  subscription_tier: string;
  is_active: boolean;
  user_count: number;
  trial_ends_at: string | null;
  created_at: string;
}
