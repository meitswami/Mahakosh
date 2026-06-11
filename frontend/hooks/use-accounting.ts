"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { accountingApi } from "@/services/accounting-api";

export function useAccountingOverview() {
  return useQuery({
    queryKey: ["accounting-overview"],
    queryFn: () => accountingApi.overview(),
    refetchInterval: 30000,
  });
}

export function useConnectorTypes() {
  return useQuery({
    queryKey: ["accounting-connector-types"],
    queryFn: () => accountingApi.connectorTypes(),
  });
}

export function useAccountingConnectors() {
  return useQuery({
    queryKey: ["accounting-connectors"],
    queryFn: () => accountingApi.connectors(),
  });
}

export function useTallyCompanies(connectorId?: string) {
  return useQuery({
    queryKey: ["accounting-companies", connectorId],
    queryFn: () => accountingApi.companies(connectorId),
  });
}

export function useAccountingLedgers(page = 1) {
  return useQuery({
    queryKey: ["accounting-ledgers", page],
    queryFn: () => accountingApi.ledgers(page),
  });
}

export function useAccountingItems(page = 1) {
  return useQuery({
    queryKey: ["accounting-items", page],
    queryFn: () => accountingApi.items(page),
  });
}

export function useAccountingVouchers(page = 1, status?: string) {
  return useQuery({
    queryKey: ["accounting-vouchers", page, status],
    queryFn: () => accountingApi.vouchers(page, 20, status),
  });
}

export function useLedgerMappings(connectorId?: string) {
  return useQuery({
    queryKey: ["accounting-ledger-mappings", connectorId],
    queryFn: () => accountingApi.ledgerMappings(connectorId),
  });
}

export function useItemMappings(connectorId?: string) {
  return useQuery({
    queryKey: ["accounting-item-mappings", connectorId],
    queryFn: () => accountingApi.itemMappings(connectorId),
  });
}

export function useSyncDashboard() {
  return useQuery({
    queryKey: ["accounting-sync-dashboard"],
    queryFn: () => accountingApi.syncDashboard(),
    refetchInterval: 15000,
  });
}

export function useSyncJobs(connectorId?: string) {
  return useQuery({
    queryKey: ["accounting-sync-jobs", connectorId],
    queryFn: () => accountingApi.syncJobs(connectorId),
  });
}

export function useConnectAccounting() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: accountingApi.connect,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounting-connectors"] });
      queryClient.invalidateQueries({ queryKey: ["accounting-overview"] });
    },
  });
}

export function useSyncAccounting() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: accountingApi.sync,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounting-sync-jobs"] });
      queryClient.invalidateQueries({ queryKey: ["accounting-sync-dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["accounting-overview"] });
    },
  });
}

export function useImportAccounting() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: accountingApi.import,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounting-ledgers"] });
      queryClient.invalidateQueries({ queryKey: ["accounting-items"] });
      queryClient.invalidateQueries({ queryKey: ["accounting-overview"] });
    },
  });
}

export function useApproveVoucher() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (voucherId: string) => accountingApi.approveVoucher(voucherId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounting-vouchers"] });
    },
  });
}

export function useTwinOverview() {
  return useQuery({
    queryKey: ["accounting-twin-overview"],
    queryFn: () => accountingApi.twinOverview(),
    refetchInterval: 30000,
  });
}

export function useTwinLedgers(page = 1, connectorId?: string) {
  return useQuery({
    queryKey: ["accounting-twin-ledgers", page, connectorId],
    queryFn: () => accountingApi.twinLedgers(page, 20, connectorId),
  });
}

export function useTwinItems(page = 1, connectorId?: string) {
  return useQuery({
    queryKey: ["accounting-twin-items", page, connectorId],
    queryFn: () => accountingApi.twinItems(page, 20, connectorId),
  });
}

export function useTwinParties(page = 1, connectorId?: string) {
  return useQuery({
    queryKey: ["accounting-twin-parties", page, connectorId],
    queryFn: () => accountingApi.twinParties(page, 20, connectorId),
  });
}

export function useTwinIssues() {
  return useQuery({
    queryKey: ["accounting-twin-issues"],
    queryFn: () => accountingApi.twinIssues(),
  });
}

export function useNormalizeTwin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: accountingApi.normalizeTwin,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounting-twin-overview"] });
      queryClient.invalidateQueries({ queryKey: ["accounting-twin-ledgers"] });
      queryClient.invalidateQueries({ queryKey: ["accounting-twin-items"] });
      queryClient.invalidateQueries({ queryKey: ["accounting-twin-parties"] });
      queryClient.invalidateQueries({ queryKey: ["accounting-twin-issues"] });
    },
  });
}

export function useResolveTwinIssue() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ issueId, resolution }: { issueId: string; resolution: string }) =>
      accountingApi.resolveTwinIssue(issueId, resolution),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounting-twin-issues"] });
      queryClient.invalidateQueries({ queryKey: ["accounting-twin-overview"] });
    },
  });
}
