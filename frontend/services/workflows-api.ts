import { apiFetch } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const WS_BASE = API_BASE.replace(/^http/, "ws");

export interface WorkflowSummary {
  id: string;
  name: string;
  workflow_type: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  assigned_agents: string[];
  created_at: string;
}

export interface WorkflowStep {
  id: string;
  step_name: string;
  step_order: number;
  agent_name: string | null;
  node_type: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  retry_count: number;
}

export interface WorkflowDetail extends WorkflowSummary {
  input_data: Record<string, unknown>;
  output_data: Record<string, unknown>;
  error_message: string | null;
  duration_ms: number | null;
  steps: WorkflowStep[];
  created_by: string;
  transparency: WorkflowTransparency | null;
}

export interface WorkflowTransparencyQuestions {
  what_happened: string;
  why_did_it_happen: string;
  which_agent_executed: string;
  which_documents_were_used: string;
  which_validations_were_performed: string;
  who_approved_it: string;
}

export interface WorkflowTransparency {
  workflow_id: string;
  workflow_name: string;
  workflow_type: string;
  status: string;
  what_happened: string;
  why_it_happened: string;
  summary: string;
  confidence_score: number;
  confidence_level: string;
  confidence_display: string;
  processing_time_ms: number | null;
  agents_executed: Array<{
    name: string;
    step_name: string;
    step_order: number;
    node_type?: string;
    status: string;
    purpose: string;
    reasoning: string;
    confidence?: number;
    duration_ms?: number;
    error?: string;
    retry_count?: number;
  }>;
  documents_used: Array<{
    document_id: string;
    title: string;
    document_type?: string;
    used_in_steps: string[];
    agents: string[];
    page_numbers: number[];
  }>;
  validations_performed: Array<{
    step_name: string;
    agent_name: string | null;
    status: string;
    is_valid: boolean;
    checks_passed: string[];
    issues: Array<Record<string, unknown>>;
    reasoning: string;
    confidence?: number;
  }>;
  approvals: Array<{
    approval_id?: string;
    title: string;
    status: string;
    action?: string;
    requested_by?: string;
    reviewed_by?: string;
    reviewed_at?: string;
    review_notes?: string;
  }>;
  reasoning_path: Array<{
    step_type: string;
    label: string;
    detail: string;
    status: string;
    agent_name?: string;
  }>;
  questions: WorkflowTransparencyQuestions;
}

export interface WorkflowGraphNode {
  id: string;
  type: string;
  label: string;
  status: string;
  agent_name: string | null;
  step_order?: number;
  started_at?: string | null;
  completed_at?: string | null;
  error_message?: string | null;
  retry_count?: number;
  replay?: {
    logs: Array<Record<string, unknown>>;
    decisions: string[];
  };
}

export interface WorkflowGraph {
  workflow_id: string;
  workflow_name: string;
  workflow_type: string;
  status: string;
  nodes: WorkflowGraphNode[];
  edges: Array<{ from: string; to: string; type: string }>;
  assigned_agents: string[];
}

export interface TimelineEntry {
  type: string;
  label: string;
  status: string;
  timestamp?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  duration_ms?: number | null;
  agent_name?: string | null;
  error?: string | null;
  retry_count?: number | null;
  reasoning_summary?: string | null;
  confidence?: number | null;
  step_id?: string | null;
}

export interface WorkflowLog {
  id: string;
  action: string;
  agent_name: string | null;
  step_id: string | null;
  input_data: Record<string, unknown>;
  output_data: Record<string, unknown>;
  reasoning_summary: string | null;
  confidence: number | null;
  duration_ms: number | null;
  error_message: string | null;
  created_at: string;
}

export interface LiveWorkflow {
  id: string;
  name: string;
  workflow_type: string;
  status: string;
  progress: number;
  current_step: string | null;
  current_agent: string | null;
  started_at: string | null;
  assigned_agents: string[] | null;
}

export interface WorkflowAnalytics {
  period_days: number;
  completed_workflows: number;
  failed_workflows: number;
  success_rate: number;
  average_duration_ms: number;
  agent_utilization: Record<string, number>;
  active_agents: number;
}

export interface WorkflowTemplate {
  name: string;
  workflow_type: string;
  description: string;
  step_count: number;
  agents: string[];
}

export interface AgentActivity {
  agent_name: string;
  status: string;
  healthy: boolean;
  queue_length: number;
  execution_count: number;
  average_runtime_ms: number;
  success_rate: number;
  last_error: string | null;
}

export interface ApprovalItem {
  id: string;
  title: string;
  action?: string;
  status?: string;
  entity_type?: string;
  priority?: string;
  created_at?: string;
  reviewed_at?: string;
  review_notes?: string;
}

export interface PaginatedWorkflows {
  items: WorkflowSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export const workflowsApi = {
  templates: () => apiFetch<WorkflowTemplate[]>("/workflows/templates"),

  list: (page = 1, status?: string) =>
    apiFetch<PaginatedWorkflows>(
      `/workflows?page=${page}${status ? `&status=${status}` : ""}`,
    ),

  get: (id: string) => apiFetch<WorkflowDetail>(`/workflows/${id}`),

  transparency: (id: string) => apiFetch<WorkflowTransparency>(`/workflows/${id}/transparency`),

  graph: (id: string, replay = false) =>
    apiFetch<WorkflowGraph>(`/workflows/${id}/graph?replay=${replay}`),

  timeline: (id: string) => apiFetch<TimelineEntry[]>(`/workflows/${id}/timeline`),

  logs: (id: string) => apiFetch<WorkflowLog[]>(`/workflows/${id}/logs`),

  live: () => apiFetch<LiveWorkflow[]>("/workflows/live"),

  analytics: (days = 30) => apiFetch<WorkflowAnalytics>(`/workflows/analytics?days=${days}`),

  agentActivity: () => apiFetch<AgentActivity[]>("/workflows/agents/activity"),

  pendingApprovals: () => apiFetch<ApprovalItem[]>("/workflows/approvals/pending"),

  approvalHistory: () => apiFetch<ApprovalItem[]>("/workflows/approvals/history"),

  create: (name: string, workflowType: string, inputData: Record<string, unknown> = {}) =>
    apiFetch<WorkflowSummary>("/workflows", {
      method: "POST",
      body: JSON.stringify({ name, workflow_type: workflowType, input_data: inputData }),
    }),

  execute: (id: string) =>
    apiFetch<{ workflow_id: string; status: string }>(`/workflows/${id}/execute`, {
      method: "POST",
    }),

  retry: (workflowId: string, fromStep?: string) =>
    apiFetch<{ workflow_id: string; status: string }>("/workflows/retry", {
      method: "POST",
      body: JSON.stringify({ workflow_id: workflowId, from_step: fromStep || null }),
    }),

  cancel: (workflowId: string) =>
    apiFetch<{ workflow_id: string; status: string }>("/workflows/cancel", {
      method: "POST",
      body: JSON.stringify({ workflow_id: workflowId }),
    }),

  createLiveStream: (token: string) =>
    new WebSocket(`${WS_BASE}/workflows/live/stream?token=${encodeURIComponent(token)}`),
};
