import { apiFetch } from "@/lib/api";

export interface AgentInfo {
  name: string;
  version: string;
  description: string;
  capabilities: string[];
  status: string;
  execution_count: number;
  success_rate: number;
  average_runtime_ms: number;
}

export interface AgentHealth {
  agent_name: string;
  status: string;
  healthy: boolean;
  execution_count: number;
  success_rate: number;
  average_runtime_ms: number;
  queue_length: number;
  last_error: string | null;
}

export interface AgentStatus {
  total_agents: number;
  active_tasks: number;
  agents: AgentInfo[];
  health: AgentHealth[];
}

export interface AgentExecution {
  id: string;
  agent_name: string;
  status: string;
  confidence: number | null;
  processing_time_ms: number | null;
  error_message: string | null;
  created_at: string;
}

export interface AgentEvent {
  id: string;
  event_type: string;
  source_agent: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface AgentExecuteResponse {
  success: boolean;
  agent_name: string;
  execution_id: string | null;
  data: Record<string, unknown>;
  confidence: number;
  confidence_level: string;
  reasoning: string;
  sources: unknown[];
  error: string | null;
  processing_time_ms: number | null;
}

export const agentsApi = {
  list: () => apiFetch<AgentInfo[]>("/agents"),

  status: () => apiFetch<AgentStatus>("/agents/status"),

  health: () => apiFetch<AgentHealth[]>("/agents/health"),

  executions: (agentName?: string) =>
    apiFetch<AgentExecution[]>(
      `/agents/executions${agentName ? `?agent_name=${agentName}` : ""}`,
    ),

  events: () => apiFetch<AgentEvent[]>("/agents/events"),

  pendingApprovals: () =>
    apiFetch<{ items: Array<{ id: string; title: string; action: string; priority: string }>; total: number }>(
      "/agents/approvals/pending",
    ),

  execute: (agentName: string, inputData: Record<string, unknown>) =>
    apiFetch<AgentExecuteResponse>(`/agents/${agentName}/execute`, {
      method: "POST",
      body: JSON.stringify({ input_data: inputData }),
    }),

  orchestrate: (taskType: string, payload: Record<string, unknown>, executionMode = "sequential") =>
    apiFetch<{
      success: boolean;
      task_id: string | null;
      data: Record<string, unknown>;
      confidence: number;
      execution_id: string | null;
    }>("/agents/orchestrate", {
      method: "POST",
      body: JSON.stringify({
        task_type: taskType,
        payload,
        execution_mode: executionMode,
      }),
    }),
};
