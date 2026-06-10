"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { agentsApi } from "@/services/agents-api";

export function useAgentStatus() {
  return useQuery({
    queryKey: ["agent-status"],
    queryFn: () => agentsApi.status(),
    refetchInterval: 5000,
  });
}

export function useAgentHealth() {
  return useQuery({
    queryKey: ["agent-health"],
    queryFn: () => agentsApi.health(),
    refetchInterval: 10000,
  });
}

export function useAgentExecutions(agentName?: string) {
  return useQuery({
    queryKey: ["agent-executions", agentName],
    queryFn: () => agentsApi.executions(agentName),
    refetchInterval: 8000,
  });
}

export function useAgentEvents() {
  return useQuery({
    queryKey: ["agent-events"],
    queryFn: () => agentsApi.events(),
    refetchInterval: 8000,
  });
}

export function usePendingApprovals() {
  return useQuery({
    queryKey: ["agent-approvals"],
    queryFn: () => agentsApi.pendingApprovals(),
    refetchInterval: 15000,
  });
}

export function useAgentExecute() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ agentName, input }: { agentName: string; input: Record<string, unknown> }) =>
      agentsApi.execute(agentName, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agent-status"] });
      queryClient.invalidateQueries({ queryKey: ["agent-executions"] });
      queryClient.invalidateQueries({ queryKey: ["agent-events"] });
    },
  });
}

export function useOrchestrate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      taskType,
      payload,
      mode,
    }: {
      taskType: string;
      payload: Record<string, unknown>;
      mode?: string;
    }) => agentsApi.orchestrate(taskType, payload, mode),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agent-status"] });
      queryClient.invalidateQueries({ queryKey: ["agent-executions"] });
    },
  });
}
