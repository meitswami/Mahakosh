"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { workflowsApi } from "@/services/workflows-api";

export function useWorkflowTemplates() {
  return useQuery({
    queryKey: ["workflow-templates"],
    queryFn: () => workflowsApi.templates(),
  });
}

export function useWorkflows(page = 1, status?: string) {
  return useQuery({
    queryKey: ["workflows", page, status],
    queryFn: () => workflowsApi.list(page, status),
    refetchInterval: 10000,
  });
}

export function useWorkflow(id: string) {
  return useQuery({
    queryKey: ["workflow", id],
    queryFn: () => workflowsApi.get(id),
    enabled: !!id,
    refetchInterval: 5000,
  });
}

export function useWorkflowTransparency(id: string) {
  return useQuery({
    queryKey: ["workflow-transparency", id],
    queryFn: () => workflowsApi.transparency(id),
    enabled: !!id,
    refetchInterval: 5000,
  });
}

export function useWorkflowGraph(id: string, replay = false) {
  return useQuery({
    queryKey: ["workflow-graph", id, replay],
    queryFn: () => workflowsApi.graph(id, replay),
    enabled: !!id,
  });
}

export function useWorkflowTimeline(id: string) {
  return useQuery({
    queryKey: ["workflow-timeline", id],
    queryFn: () => workflowsApi.timeline(id),
    enabled: !!id,
  });
}

export function useWorkflowLogs(id: string) {
  return useQuery({
    queryKey: ["workflow-logs", id],
    queryFn: () => workflowsApi.logs(id),
    enabled: !!id,
  });
}

export function useLiveWorkflows() {
  return useQuery({
    queryKey: ["workflows-live"],
    queryFn: () => workflowsApi.live(),
    refetchInterval: 3000,
  });
}

export function useWorkflowAnalytics(days = 30) {
  return useQuery({
    queryKey: ["workflow-analytics", days],
    queryFn: () => workflowsApi.analytics(days),
    refetchInterval: 30000,
  });
}

export function useWorkflowAgentActivity() {
  return useQuery({
    queryKey: ["workflow-agent-activity"],
    queryFn: () => workflowsApi.agentActivity(),
    refetchInterval: 8000,
  });
}

export function useWorkflowApprovals() {
  return useQuery({
    queryKey: ["workflow-approvals-pending"],
    queryFn: () => workflowsApi.pendingApprovals(),
    refetchInterval: 15000,
  });
}

export function useWorkflowApprovalHistory() {
  return useQuery({
    queryKey: ["workflow-approvals-history"],
    queryFn: () => workflowsApi.approvalHistory(),
  });
}

export function useCreateWorkflow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      name,
      workflowType,
      inputData,
    }: {
      name: string;
      workflowType: string;
      inputData?: Record<string, unknown>;
    }) => workflowsApi.create(name, workflowType, inputData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workflows"] });
      queryClient.invalidateQueries({ queryKey: ["workflows-live"] });
    },
  });
}

export function useExecuteWorkflow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => workflowsApi.execute(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ["workflow", id] });
      queryClient.invalidateQueries({ queryKey: ["workflows"] });
      queryClient.invalidateQueries({ queryKey: ["workflows-live"] });
    },
  });
}

export function useRetryWorkflow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, fromStep }: { id: string; fromStep?: string }) =>
      workflowsApi.retry(id, fromStep),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ["workflow", id] });
      queryClient.invalidateQueries({ queryKey: ["workflows-live"] });
    },
  });
}

export function useCancelWorkflow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => workflowsApi.cancel(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workflows"] });
      queryClient.invalidateQueries({ queryKey: ["workflows-live"] });
    },
  });
}
