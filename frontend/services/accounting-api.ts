import { apiFetch } from "@/lib/api";

export interface AccountingOverview {
  ledger_count: number;
  item_count: number;
  voucher_count: number;
  mapping_count: number;
  connectors: number;
  connected_companies: number;
  pending_exports: number;
  last_sync: string | null;
  connector_types: ConnectorTypeInfo[];
  failed_jobs: { id: string; name: string; status: string; sync_type: string }[];
  recent_logs: { level: string; message: string; created_at: string }[];
}

export interface ConnectorTypeInfo {
  connector_type: string;
  name: string;
  description: string;
  version: string;
  priority: number;
  supported_erp_systems: string[];
}

export interface AccountingConnector {
  id: string;
  name: string;
  connector_type: string;
  status: string;
  config: Record<string, unknown>;
  priority: number;
  last_connected_at: string | null;
  last_sync_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TallyCompany {
  id: string;
  connector_id: string;
  name: string;
  financial_year: string | null;
  books_begin_from: string | null;
  books_status: string | null;
  voucher_count: number;
  ledger_count: number;
  inventory_count: number;
  is_active: boolean;
}

export interface Ledger {
  id: string;
  name: string;
  parent_group: string | null;
  ledger_type: string;
  opening_balance: number;
  current_balance: number;
  gstin: string | null;
  tally_ledger_name: string | null;
  is_active: boolean;
}

export interface AccountingItem {
  id: string;
  name: string;
  sku: string | null;
  hsn_code: string | null;
  unit: string;
  gst_rate: number | null;
  category: string | null;
  tally_stock_item_name: string | null;
  is_active: boolean;
}

export interface Voucher {
  id: string;
  voucher_type: string;
  voucher_number: string | null;
  voucher_date: string;
  party_name: string | null;
  party_gstin: string | null;
  subtotal: number;
  cgst_amount: number;
  sgst_amount: number;
  igst_amount: number;
  total_amount: number;
  status: string;
  narration: string | null;
  created_at: string;
}

export interface Mapping {
  id: string;
  connector_id: string;
  external_name: string;
  match_type: string;
  confidence: number;
  reasoning: string | null;
  is_confirmed: boolean;
  ledger_id?: string | null;
  item_id?: string | null;
}

export interface MatchResult {
  external_name: string;
  internal_id: string | null;
  internal_name: string | null;
  match_type: string;
  confidence: number;
  reasoning: string;
  source: string;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface SyncJob {
  id: string;
  connector_id: string;
  name: string;
  sync_type: string;
  trigger_mode: string;
  status: string;
  last_run_at: string | null;
  created_at: string;
}

export interface TwinObject {
  id: string;
  object_type: string;
  source_system: string;
  source_id: string;
  display_name: string;
  normalized_fields: Record<string, unknown>;
  quality_score: number;
  issues: { code: string; message: string; severity: string; suggestion?: string }[];
  normalization_notes: string[];
  connector_id: string | null;
  created_at: string;
  updated_at: string;
}

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

export const accountingApi = {
  overview: () => apiFetch<AccountingOverview>("/accounting/overview"),

  connectorTypes: () => apiFetch<{ connectors: ConnectorTypeInfo[] }>("/accounting/connector-types"),

  connectors: () => apiFetch<AccountingConnector[]>("/accounting/connectors"),

  connect: (data: { name: string; connector_type: string; config: Record<string, unknown>; priority?: number }) =>
    apiFetch<{ connector_id: string; success: boolean; status: string; error?: string }>("/accounting/connect", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  sync: (data: { connector_id: string; sync_type?: string; mode?: string; options?: Record<string, unknown> }) =>
    apiFetch<Record<string, unknown>>("/accounting/sync", { method: "POST", body: JSON.stringify(data) }),

  import: (data: {
    connector_id: string;
    entity_type: string;
    company_name?: string;
    persist?: boolean;
    options?: Record<string, unknown>;
  }) => apiFetch<Record<string, unknown>>("/accounting/import", { method: "POST", body: JSON.stringify(data) }),

  export: (data: {
    connector_id: string;
    entity_type: string;
    company_name?: string;
    options?: Record<string, unknown>;
  }) => apiFetch<Record<string, unknown>>("/accounting/export", { method: "POST", body: JSON.stringify(data) }),

  companies: (connectorId?: string) => {
    const params = connectorId ? `?connector_id=${connectorId}` : "";
    return apiFetch<TallyCompany[]>(`/accounting/companies${params}`);
  },

  ledgers: (page = 1, pageSize = 20) =>
    apiFetch<Paginated<Ledger>>(`/accounting/ledgers?page=${page}&page_size=${pageSize}`),

  items: (page = 1, pageSize = 20) =>
    apiFetch<Paginated<AccountingItem>>(`/accounting/items?page=${page}&page_size=${pageSize}`),

  vouchers: (page = 1, pageSize = 20, status?: string) => {
    const statusParam = status ? `&status=${status}` : "";
    return apiFetch<Paginated<Voucher>>(`/accounting/vouchers?page=${page}&page_size=${pageSize}${statusParam}`);
  },

  createVoucherDraft: (data: Record<string, unknown>) =>
    apiFetch<Voucher>("/accounting/vouchers/draft", { method: "POST", body: JSON.stringify(data) }),

  validateVoucher: (voucherId: string) =>
    apiFetch<Record<string, unknown>>(`/accounting/vouchers/${voucherId}/validate`, { method: "POST" }),

  approveVoucher: (voucherId: string) =>
    apiFetch<{ voucher_id: string; status: string }>(`/accounting/vouchers/${voucherId}/approve`, { method: "POST" }),

  exportVoucher: (voucherId: string, connectorId: string, companyId?: string) =>
    apiFetch<Record<string, unknown>>(`/accounting/vouchers/${voucherId}/export`, {
      method: "POST",
      body: JSON.stringify({ connector_id: connectorId, company_id: companyId }),
    }),

  ledgerMappings: (connectorId?: string) => {
    const params = connectorId ? `?connector_id=${connectorId}` : "";
    return apiFetch<Mapping[]>(`/accounting/mappings/ledgers${params}`);
  },

  itemMappings: (connectorId?: string) => {
    const params = connectorId ? `?connector_id=${connectorId}` : "";
    return apiFetch<Mapping[]>(`/accounting/mappings/items${params}`);
  },

  matchLedgers: (externalNames: string[], connectorId?: string) =>
    apiFetch<MatchResult[]>("/accounting/mappings/ledgers/match", {
      method: "POST",
      body: JSON.stringify({ external_names: externalNames, connector_id: connectorId }),
    }),

  matchItems: (externalNames: string[], connectorId?: string) =>
    apiFetch<MatchResult[]>("/accounting/mappings/items/match", {
      method: "POST",
      body: JSON.stringify({ external_names: externalNames, connector_id: connectorId }),
    }),

  syncDashboard: () => apiFetch<AccountingOverview>("/accounting/sync/dashboard"),

  syncJobs: (connectorId?: string) => {
    const params = connectorId ? `?connector_id=${connectorId}` : "";
    return apiFetch<SyncJob[]>(`/accounting/sync/jobs${params}`);
  },

  vendors: () => apiFetch<{ vendors: { id: string; name: string; gstin: string | null }[]; total: number }>("/accounting/vendors"),

  customers: () => apiFetch<{ customers: { id: string; name: string; gstin: string | null }[]; total: number }>("/accounting/customers"),

  twinOverview: () => apiFetch<TwinOverview>("/accounting/twin/overview"),

  twinLedgers: (page = 1, pageSize = 20, connectorId?: string) => {
    const connector = connectorId ? `&connector_id=${connectorId}` : "";
    return apiFetch<Paginated<TwinObject>>(`/accounting/twin/ledgers?page=${page}&page_size=${pageSize}${connector}`);
  },

  twinItems: (page = 1, pageSize = 20, connectorId?: string) => {
    const connector = connectorId ? `&connector_id=${connectorId}` : "";
    return apiFetch<Paginated<TwinObject>>(`/accounting/twin/items?page=${page}&page_size=${pageSize}${connector}`);
  },

  twinParties: (page = 1, pageSize = 20, connectorId?: string) => {
    const connector = connectorId ? `&connector_id=${connectorId}` : "";
    return apiFetch<Paginated<TwinObject>>(`/accounting/twin/parties?page=${page}&page_size=${pageSize}${connector}`);
  },

  twinVouchers: (page = 1, pageSize = 20, connectorId?: string) => {
    const connector = connectorId ? `&connector_id=${connectorId}` : "";
    return apiFetch<Paginated<TwinObject>>(`/accounting/twin/vouchers?page=${page}&page_size=${pageSize}${connector}`);
  },

  twinIssues: (page = 1, status = "open", severity?: string) => {
    const sev = severity ? `&severity=${severity}` : "";
    return apiFetch<Paginated<TwinIssue>>(`/accounting/twin/issues?page=${page}&status=${status}${sev}`);
  },

  normalizeTwin: (data: { connector_id?: string; entity_types?: string[] }) =>
    apiFetch<Record<string, unknown>>("/accounting/twin/normalize", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  resolveTwinIssue: (issueId: string, resolution: string) =>
    apiFetch<{ success: boolean }>("/accounting/twin/resolve-issue", {
      method: "POST",
      body: JSON.stringify({ issue_id: issueId, resolution }),
    }),

  mergeTwinDuplicate: (sourceId: string, targetId: string) =>
    apiFetch<{ success: boolean }>("/accounting/twin/merge-duplicate", {
      method: "POST",
      body: JSON.stringify({ source_id: sourceId, target_id: targetId }),
    }),
};
