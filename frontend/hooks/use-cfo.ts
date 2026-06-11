"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cfoApi } from "@/services/cfo-api";

export function useCEOBriefing(days = 30) {
  return useQuery({
    queryKey: ["ceo-briefing", days],
    queryFn: () => cfoApi.briefing(days),
    refetchInterval: 60000,
    staleTime: 30000,
  });
}

export function useCFORecommendations() {
  return useQuery({
    queryKey: ["cfo-recommendations"],
    queryFn: () => cfoApi.recommendations(),
    refetchInterval: 30000,
  });
}

export function useCFOCapabilities() {
  return useQuery({
    queryKey: ["cfo-capabilities"],
    queryFn: () => cfoApi.capabilities(),
  });
}

export function useApproveCFORecommendation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, notes }: { id: string; notes?: string }) => cfoApi.approve(id, notes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cfo-recommendations"] });
      qc.invalidateQueries({ queryKey: ["ceo-briefing"] });
    },
  });
}

export function useRejectCFORecommendation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, notes }: { id: string; notes?: string }) => cfoApi.reject(id, notes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cfo-recommendations"] });
      qc.invalidateQueries({ queryKey: ["ceo-briefing"] });
    },
  });
}
