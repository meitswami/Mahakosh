import { apiFetch } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const WS_BASE = API_BASE.replace(/^http/, "ws");

export interface ChatCitation {
  source_document: string;
  document_id: string;
  chunk_id: string;
  page_number: number | null;
  confidence: number;
  confidence_display: string;
  excerpt: string;
  citation_text: string;
}

export interface ReasoningStep {
  step_type: string;
  label: string;
  detail: string;
  status: string;
  metadata?: Record<string, unknown>;
}

export interface TransparencyManifest {
  agents_participated: Array<{
    name: string;
    role: string;
    description?: string;
    confidence?: number;
    success?: boolean;
  }>;
  documents_consulted: Array<{
    document_id: string;
    title: string;
    document_type?: string;
    chunks_used: number;
  }>;
  chunks_retrieved: Array<{
    chunk_id: string;
    document_id: string;
    document_title: string;
    page_number: number | null;
    confidence: number;
    excerpt: string;
    rank: number;
  }>;
  confidence_score: number;
  confidence_level: string;
  confidence_display: string;
  sources: ChatCitation[];
  reasoning_path: ReasoningStep[];
  knowledge_query_id: string | null;
  model_used: string | null;
  processing_time_ms: number;
  summary: string;
}

export interface ChatQueryResponse {
  answer: string;
  session_id: string;
  message_id: string | null;
  chat_type: string;
  intent: string;
  confidence: number;
  citations: ChatCitation[];
  structured_data: Record<string, unknown>;
  agents_used: string[];
  reasoning_steps: ReasoningStep[];
  transparency: TransparencyManifest | null;
  query_id: string | null;
  processing_time_ms: number;
  model_used: string | null;
}

export interface ChatSessionSummary {
  id: string;
  title: string;
  chat_type: string;
  message_count: number;
  last_message_at: string | null;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  role: string;
  content: string;
  chat_type?: string | null;
  intent?: string | null;
  confidence?: number | null;
  citations?: ChatCitation[];
  structured_data?: Record<string, unknown>;
  agents_used?: string[];
  reasoning_steps?: ReasoningStep[];
  transparency?: TransparencyManifest | null;
  created_at: string;
}

export interface StreamEvent {
  type: string;
  content: unknown;
}

export const chatApi = {
  query: (message: string, sessionId?: string, chatType?: string) =>
    apiFetch<ChatQueryResponse>("/chat/query", {
      method: "POST",
      body: JSON.stringify({
        message,
        session_id: sessionId || null,
        chat_type: chatType || null,
      }),
    }),

  history: () => apiFetch<{ sessions: ChatSessionSummary[]; total: number }>("/chat/history"),

  getSession: (sessionId: string) =>
    apiFetch<{ id: string; title: string; chat_type: string; messages: ChatMessage[] }>(
      `/chat/session/${sessionId}`,
    ),

  deleteSession: (sessionId: string) =>
    apiFetch<{ deleted: boolean }>(`/chat/session/${sessionId}`, { method: "DELETE" }),

  createStream: (token: string) => {
    return new WebSocket(`${WS_BASE}/chat/stream?token=${encodeURIComponent(token)}`);
  },
};
