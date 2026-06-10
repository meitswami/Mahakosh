import { apiFetch } from "@/lib/api";

export const documentsApi = {
  list: (page = 1, pageSize = 20) =>
    apiFetch(`/documents?page=${page}&page_size=${pageSize}`),
};

export const agentsApi = {
  list: () => apiFetch("/agents"),
  execute: (agentName: string, inputData: Record<string, unknown>) =>
    apiFetch(`/agents/${agentName}/execute`, {
      method: "POST",
      body: JSON.stringify({ input_data: inputData }),
    }),
};

export const workflowsApi = {
  list: (page = 1) => apiFetch(`/workflows?page=${page}`),
  create: (data: Record<string, unknown>) =>
    apiFetch("/workflows", { method: "POST", body: JSON.stringify(data) }),
};
