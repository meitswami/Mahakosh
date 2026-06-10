import { apiFetch } from "@/lib/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface KnowledgeCollection {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  collection_type: string;
  document_count: number;
  chunk_count: number;
}

export interface KnowledgeOverview {
  total_documents: number;
  total_chunks: number;
  total_queries: number;
  collections: KnowledgeCollection[];
  top_sources: Array<{ source: string; count: number }>;
  recent_queries: Array<{ query: string; mode: string; results: number; at: string }>;
}

export interface KnowledgeCitation {
  source_document: string;
  document_id: string;
  chunk_id: string;
  page_number: number | null;
  confidence: number;
  confidence_display: string;
  rank: number;
  excerpt: string;
  citation_text: string;
}

export interface KnowledgeSearchResult {
  chunk_id: string;
  document_id: string;
  content: string;
  score: number;
  document_title: string;
  document_type: string;
  source_name: string;
  page_number: number | null;
  metadata: Record<string, unknown>;
  citation: KnowledgeCitation | null;
}

export interface KnowledgeSearchResponse {
  query_id: string | null;
  query: string;
  mode: string;
  results: KnowledgeSearchResult[];
  citations: KnowledgeCitation[];
  processing_time_ms: number;
  total_found: number;
}

export interface KnowledgeDocument {
  id: string;
  title: string;
  document_type: string;
  source: string;
  index_status: string;
  chunk_count: number;
  confidence: number | null;
  vendor_name: string | null;
  customer_name: string | null;
  gstin: string | null;
  invoice_number: string | null;
  document_date: string | null;
  amount: number | null;
  tags: string[];
  indexed_at: string | null;
  created_at: string;
  structured_fields: Record<string, unknown>;
  tables: unknown[];
}

export interface KnowledgeGraph {
  document_id: string;
  nodes: Array<{ id: string; type: string; label: string; metadata?: Record<string, unknown> }>;
  edges: Array<{ source: string; target: string; type: string; confidence?: number }>;
}

export const knowledgeApi = {
  overview: () => apiFetch<KnowledgeOverview>("/knowledge/overview"),

  collections: () => apiFetch<KnowledgeCollection[]>("/knowledge/collections"),

  search: (query: string, mode = "hybrid", topK = 20, collectionSlug?: string) =>
    apiFetch<KnowledgeSearchResponse>("/knowledge/search", {
      method: "POST",
      body: JSON.stringify({
        query,
        mode,
        top_k: topK,
        rerank: true,
        collection_slug: collectionSlug || null,
      }),
    }),

  getDocument: (id: string) => apiFetch<KnowledgeDocument>(`/knowledge/document/${id}`),

  getGraph: (documentId: string) => apiFetch<KnowledgeGraph>(`/knowledge/graph/${documentId}`),

  indexText: (title: string, text: string, documentType = "general") =>
    apiFetch<KnowledgeDocument>("/knowledge/index", {
      method: "POST",
      body: JSON.stringify({ title, text, document_type: documentType }),
    }),

  upload: async (file: File, documentType = "general", title?: string) => {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    const formData = new FormData();
    formData.append("file", file);
    formData.append("document_type", documentType);
    if (title) formData.append("title", title);

    const headers: HeadersInit = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const response = await fetch(`${API_BASE_URL}/knowledge/index/upload`, {
      method: "POST",
      headers,
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(error.detail || "Upload failed");
    }
    return response.json() as Promise<KnowledgeDocument>;
  },
};
