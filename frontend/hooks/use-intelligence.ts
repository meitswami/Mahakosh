"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { intelligenceApi } from "@/services/intelligence-api";

export function useExecutiveDashboard(days = 30) {
  return useQuery({
    queryKey: ["intelligence-executive", days],
    queryFn: () => intelligenceApi.executive(days),
    refetchInterval: 60000,
  });
}

export function useIntelligenceInsights(days = 30) {
  return useQuery({
    queryKey: ["intelligence-insights", days],
    queryFn: () => intelligenceApi.insights(days),
  });
}

export function useIntelligenceGST() {
  return useQuery({
    queryKey: ["intelligence-gst"],
    queryFn: () => intelligenceApi.gst(),
  });
}

export function useIntelligenceVendors() {
  return useQuery({
    queryKey: ["intelligence-vendors"],
    queryFn: () => intelligenceApi.vendors(),
  });
}

export function useIntelligenceCustomers() {
  return useQuery({
    queryKey: ["intelligence-customers"],
    queryFn: () => intelligenceApi.customers(),
  });
}

export function useIntelligenceWorkflows(days = 30) {
  return useQuery({
    queryKey: ["intelligence-workflows", days],
    queryFn: () => intelligenceApi.workflows(days),
  });
}

export function useIntelligenceAnomalies() {
  return useQuery({
    queryKey: ["intelligence-anomalies"],
    queryFn: () => intelligenceApi.anomalies(),
  });
}

export function useNLQuery() {
  return useMutation({
    mutationFn: ({ question, days }: { question: string; days?: number }) =>
      intelligenceApi.query(question, days),
  });
}

export function useGenerateReport() {
  return useMutation({
    mutationFn: ({
      name,
      reportType,
      format,
      parameters,
    }: {
      name: string;
      reportType: string;
      format: string;
      parameters?: Record<string, unknown>;
    }) => intelligenceApi.generateReport(name, reportType, format, parameters),
  });
}

export function useReportTemplates() {
  return useQuery({
    queryKey: ["report-templates"],
    queryFn: () => intelligenceApi.reportTemplates(),
  });
}
