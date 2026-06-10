"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ocrApi } from "@/services/ocr-api";

export function useOCRJobs(page = 1) {
  return useQuery({
    queryKey: ["ocr-jobs", page],
    queryFn: () => ocrApi.listJobs(page),
    refetchInterval: 5000,
  });
}

export function useOCRJobStatus(jobId: string | null) {
  return useQuery({
    queryKey: ["ocr-status", jobId],
    queryFn: () => ocrApi.getStatus(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) =>
      query.state.data?.status === "processing" ? 2000 : false,
  });
}

export function useOCRResult(jobId: string | null) {
  return useQuery({
    queryKey: ["ocr-result", jobId],
    queryFn: () => ocrApi.getResult(jobId!),
    enabled: !!jobId,
  });
}

export function useOCRValidation(jobId: string | null) {
  return useQuery({
    queryKey: ["ocr-validation", jobId],
    queryFn: () => ocrApi.getValidation(jobId!),
    enabled: !!jobId,
  });
}

export function useOCRUpload() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ file, title }: { file: File; title?: string }) =>
      ocrApi.upload(file, title),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ocr-jobs"] }),
  });
}

export function useOCRProcess() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => ocrApi.process(jobId),
    onSuccess: (_, jobId) => {
      queryClient.invalidateQueries({ queryKey: ["ocr-jobs"] });
      queryClient.invalidateQueries({ queryKey: ["ocr-status", jobId] });
    },
  });
}
