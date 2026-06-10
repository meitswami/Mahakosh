"use client";

import { useCallback, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  chatApi,
  type ChatMessage,
  type ChatQueryResponse,
  type StreamEvent,
  type TransparencyManifest,
} from "@/services/chat-api";

export function useChatHistory() {
  return useQuery({
    queryKey: ["chat-history"],
    queryFn: () => chatApi.history(),
  });
}

export function useChatSession(sessionId: string | null) {
  return useQuery({
    queryKey: ["chat-session", sessionId],
    queryFn: () => chatApi.getSession(sessionId!),
    enabled: !!sessionId,
  });
}

export function useChatQuery() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      message,
      sessionId,
      chatType,
    }: {
      message: string;
      sessionId?: string;
      chatType?: string;
    }) => chatApi.query(message, sessionId, chatType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat-history"] });
    },
  });
}

export function useChatStream() {
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamedContent, setStreamedContent] = useState("");
  const [reasoningSteps, setReasoningSteps] = useState<StreamEvent[]>([]);
  const [transparency, setTransparency] = useState<TransparencyManifest | null>(null);
  const [streamMeta, setStreamMeta] = useState<Partial<ChatQueryResponse>>({});
  const wsRef = useRef<WebSocket | null>(null);

  const send = useCallback(
    (
      message: string,
      sessionId?: string,
      onComplete?: (result: ChatQueryResponse) => void,
    ) => {
      const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
      if (!token) return;

      setIsStreaming(true);
      setStreamedContent("");
      setReasoningSteps([]);
      setTransparency(null);
      setStreamMeta({});

      if (wsRef.current) {
        wsRef.current.close();
      }

      const ws = chatApi.createStream(token);
      wsRef.current = ws;

      ws.onopen = () => {
        ws.send(JSON.stringify({ message, session_id: sessionId || null }));
      };

      ws.onmessage = (event) => {
        const data: StreamEvent = JSON.parse(event.data);
        if (data.type === "token") {
          setStreamedContent((prev) => prev + (data.content as string));
        } else if (data.type === "reasoning_step") {
          setReasoningSteps((prev) => [...prev, data]);
        } else if (data.type === "transparency") {
          setTransparency(data.content as TransparencyManifest);
        } else if (data.type === "citations") {
          setStreamMeta((prev) => ({ ...prev, citations: data.content as ChatQueryResponse["citations"] }));
        } else if (data.type === "agents") {
          setStreamMeta((prev) => ({ ...prev, agents_used: data.content as string[] }));
        } else if (data.type === "done") {
          setIsStreaming(false);
          const done = data.content as Record<string, unknown>;
          const fullTransparency = (done.transparency as TransparencyManifest) || transparency;
          onComplete?.({
            answer: done.answer as string,
            session_id: done.session_id as string,
            message_id: done.message_id as string | null,
            chat_type: (done.chat_type as string) || "general",
            intent: (done.intent as string) || "general",
            confidence: (done.confidence as number) || fullTransparency?.confidence_score || 0,
            citations: (done.citations as ChatQueryResponse["citations"]) || [],
            structured_data: (done.structured_data as Record<string, unknown>) || {},
            agents_used: (done.agents_used as string[]) || [],
            reasoning_steps: (done.reasoning_steps as ChatQueryResponse["reasoning_steps"]) || [],
            transparency: fullTransparency,
            query_id: null,
            processing_time_ms: done.processing_time_ms as number,
            model_used: (done.model_used as string) || fullTransparency?.model_used || null,
          });
        } else if (data.type === "error") {
          setIsStreaming(false);
        }
      };

      ws.onerror = () => setIsStreaming(false);
      ws.onclose = () => setIsStreaming(false);
    },
    [],
  );

  const stop = useCallback(() => {
    wsRef.current?.close();
    setIsStreaming(false);
  }, []);

  return { send, stop, isStreaming, streamedContent, reasoningSteps, transparency, streamMeta };
}

export type { ChatMessage, ChatQueryResponse };
