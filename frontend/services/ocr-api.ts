import { apiFetch } from "@/lib/api";

export interface OCRJob {
  job_id: string;
  document_id: string;
  status: string;
  document_class: string | null;
  classification_confidence: number | null;
  page_count: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  processing_time_ms: number | null;
  created_at: string;
}

export interface OCRField {
  field_name: string;
  field_value: string | null;
  confidence: number;
  confidence_level: string;
  source_engine: string | null;
  paddle_value: string | null;
  surya_value: string | null;
}

export interface OCRTable {
  table_type: string;
  page_number: number;
  headers: string[];
  rows: string[][];
  confidence: number;
  confidence_level: string;
  extraction_method: string;
}

export interface OCRPipelineStage {
  stage_name: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  error_message: string | null;
}

export interface OCRResult {
  job_id: string;
  document_id: string;
  status: string;
  document_class: string | null;
  classification_confidence: number | null;
  paddle_output: Record<string, unknown>;
  surya_output: Record<string, unknown>;
  consensus_output: Record<string, unknown>;
  fields: OCRField[];
  tables: OCRTable[];
  pages: Array<{
    page_number: number;
    consensus_text: string | null;
    consensus_confidence: number | null;
  }>;
  confidence_scores: Array<{ score_type: string; score: number; level: string }>;
  pipeline_stages: OCRPipelineStage[];
  knowledge_document: Record<string, unknown>;
}

export interface OCRValidation {
  job_id: string;
  is_valid: boolean;
  issues: Array<{ code: string; severity: string; message: string; field?: string }>;
  checks_passed: string[];
  checks_failed: string[];
}

export const ocrApi = {
  listJobs: (page = 1, pageSize = 20) =>
    apiFetch<{ items: OCRJob[]; total: number }>(`/ocr/jobs?page=${page}&page_size=${pageSize}`),

  upload: async (file: File, title?: string) => {
    const formData = new FormData();
    formData.append("file", file);
    if (title) formData.append("title", title);

    const token = localStorage.getItem("access_token");
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/ocr/upload`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(err.detail || "Upload failed");
    }
    return response.json() as Promise<{ job_id: string; document_id: string; status: string }>;
  },

  process: (jobId: string, language = "en+hi", sync = false) =>
    apiFetch<OCRJob>("/ocr/process", {
      method: "POST",
      body: JSON.stringify({ job_id: jobId, language }),
    }),

  getStatus: (jobId: string) => apiFetch<OCRJob>(`/ocr/status/${jobId}`),

  getResult: (jobId: string) => apiFetch<OCRResult>(`/ocr/result/${jobId}`),

  getValidation: (jobId: string) => apiFetch<OCRValidation>(`/ocr/validation/${jobId}`),
};
