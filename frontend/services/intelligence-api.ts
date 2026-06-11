import { apiFetch } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface TrendPoint {
  period: string;
  label: string;
  value: number;
}

export interface BusinessHealthScore {
  score: number;
  level: string;
  components: Record<string, number>;
}

export interface ExecutiveDashboard {
  revenue: number;
  expenses: number;
  profit: number;
  profit_margin_pct: number;
  gst_liability: number;
  pending_approvals: number;
  business_health_score: BusinessHealthScore;
  top_customers: Array<{ name: string; value: number; share_pct: number }>;
  top_vendors: Array<{ name: string; value: number; share_pct: number }>;
  charts: {
    revenue_trend: TrendPoint[];
    expense_trend: TrendPoint[];
    gst_trend: TrendPoint[];
    vendor_distribution: Array<{ name: string; value: number; share_pct: number }>;
    customer_distribution: Array<{ name: string; value: number; share_pct: number }>;
    workflow_statistics: Array<{ date: string; completed: number; failed: number }>;
  };
  insights?: {
    observations: Array<{ type: string; text: string; confidence: number }>;
    recommendations: Array<{ type: string; text: string; confidence: number; action?: string }>;
    warnings: Array<{ type: string; text: string; confidence: number; severity?: string }>;
    opportunities: Array<{ type: string; text: string; confidence: number }>;
  };
  anomalies: Array<{ type: string; severity: string; title: string; description: string }>;
  growth: { revenue_pct: number | null; expense_pct: number | null };
}

export interface InsightItem {
  type: string;
  text: string;
  confidence: number;
  severity?: string;
  action?: string;
}

export const intelligenceApi = {
  executive: (days = 30) =>
    apiFetch<ExecutiveDashboard>(`/intelligence/executive?days=${days}`),

  financial: () => apiFetch<Record<string, unknown>>("/intelligence/financial"),

  gst: () => apiFetch<Record<string, unknown>>("/intelligence/gst"),

  vendors: () => apiFetch<Record<string, unknown>>("/intelligence/vendors"),

  customers: () => apiFetch<Record<string, unknown>>("/intelligence/customers"),

  inventory: () => apiFetch<Record<string, unknown>>("/intelligence/inventory"),

  workflows: (days = 30) =>
    apiFetch<Record<string, unknown>>(`/intelligence/workflows?days=${days}`),

  insights: (days = 30) =>
    apiFetch<{
      observations: InsightItem[];
      recommendations: InsightItem[];
      warnings: InsightItem[];
      opportunities: InsightItem[];
    }>(`/intelligence/insights?days=${days}`),

  query: (question: string, days = 30) =>
    apiFetch<{
      question: string;
      answer: string;
      type: string;
      confidence: number;
      confidence_display: string;
    }>("/intelligence/query", {
      method: "POST",
      body: JSON.stringify({ question, days }),
    }),

  forecasts: () => apiFetch<Record<string, unknown>>("/intelligence/forecasts"),

  anomalies: () =>
    apiFetch<Array<{ type: string; severity: string; title: string; description: string }>>(
      "/intelligence/anomalies",
    ),

  dashboard: (type: string, days = 30) =>
    apiFetch<Record<string, unknown>>(`/intelligence/dashboard/${type}?days=${days}`),

  reportTemplates: () =>
    apiFetch<{ templates: Array<{ type: string; name: string; formats: string[] }>; schedules: string[] }>(
      "/intelligence/reports/templates",
    ),

  generateReport: async (
    name: string,
    reportType: string,
    format: string,
    parameters: Record<string, unknown> = {},
  ) => {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    const response = await fetch(`${API_BASE}/intelligence/reports/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ name, report_type: reportType, format, parameters }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: "Report generation failed" }));
      throw new Error(err.detail || "Report generation failed");
    }
    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition");
    const filename = disposition?.match(/filename="(.+)"/)?.[1] || `${reportType}.${format}`;
    return { blob, filename };
  },
};
