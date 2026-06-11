import { apiFetch } from "@/lib/api";

export interface BriefingItem {
  id: string;
  title: string;
  summary: string;
  section: string;
  priority: string;
  category: string;
  confidence: number;
  entity_type?: string | null;
  entity_id?: string | null;
  action_url?: string | null;
  metadata?: Record<string, unknown>;
  timestamp?: string;
}

export interface CEOBriefing {
  generated_at: string;
  headline: string;
  health_score: {
    score: number;
    level: string;
    components: Record<string, number>;
  };
  key_metrics: {
    revenue: number;
    expenses: number;
    profit: number;
    profit_margin_pct: number;
    gst_liability: number;
    cash_position: number;
    receivables: number;
    payables: number;
    pending_approvals: number;
  };
  what_happened: BriefingItem[];
  what_is_happening: BriefingItem[];
  needs_attention: BriefingItem[];
  next_actions: BriefingItem[];
  cfo_capabilities: Array<{ type: string; name: string; status: string }>;
  growth: { revenue_pct: number | null; expense_pct: number | null };
}

export interface CFORecommendation {
  id: string;
  capability: string;
  title: string;
  description: string;
  rationale: string;
  priority: string;
  confidence: number;
  suggested_action: string | null;
  status: string;
  requires_approval: boolean;
  created_at: string;
  expires_at: string | null;
}

export const cfoApi = {
  briefing: (days = 30) =>
    apiFetch<CEOBriefing>(`/cfo/briefing?days=${days}`),

  capabilities: () =>
    apiFetch<{ capabilities: Array<{ type: string; name: string; status: string }> }>(
      "/cfo/capabilities",
    ),

  recommendations: () =>
    apiFetch<{ recommendations: CFORecommendation[] }>("/cfo/recommendations"),

  approve: (id: string, notes?: string) =>
    apiFetch<{ success: boolean }>(`/cfo/recommendations/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ notes }),
    }),

  reject: (id: string, notes?: string) =>
    apiFetch<{ success: boolean }>(`/cfo/recommendations/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ notes }),
    }),
};
