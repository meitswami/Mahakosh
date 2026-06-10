"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { knowledgeApi } from "@/services/knowledge-api";

export function useKnowledgeOverview() {
  return useQuery({
    queryKey: ["knowledge-overview"],
    queryFn: () => knowledgeApi.overview(),
    refetchInterval: 30000,
  });
}

export function useKnowledgeCollections() {
  return useQuery({
    queryKey: ["knowledge-collections"],
    queryFn: () => knowledgeApi.collections(),
  });
}

export function useKnowledgeSearch(query: string, mode = "hybrid", enabled = false) {
  return useQuery({
    queryKey: ["knowledge-search", query, mode],
    queryFn: () => knowledgeApi.search(query, mode),
    enabled: enabled && query.length > 0,
  });
}

export function useKnowledgeDocument(documentId: string | null) {
  return useQuery({
    queryKey: ["knowledge-document", documentId],
    queryFn: () => knowledgeApi.getDocument(documentId!),
    enabled: !!documentId,
  });
}

export function useKnowledgeGraph(documentId: string | null) {
  return useQuery({
    queryKey: ["knowledge-graph", documentId],
    queryFn: () => knowledgeApi.getGraph(documentId!),
    enabled: !!documentId,
  });
}

export function useKnowledgeUpload() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ file, documentType, title }: { file: File; documentType?: string; title?: string }) =>
      knowledgeApi.upload(file, documentType, title),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["knowledge-overview"] });
      queryClient.invalidateQueries({ queryKey: ["knowledge-collections"] });
    },
  });
}

export function useKnowledgeIndexText() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ title, text, documentType }: { title: string; text: string; documentType?: string }) =>
      knowledgeApi.indexText(title, text, documentType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["knowledge-overview"] });
      queryClient.invalidateQueries({ queryKey: ["knowledge-collections"] });
    },
  });
}
