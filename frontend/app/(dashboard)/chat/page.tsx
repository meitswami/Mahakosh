"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Send, Sparkles, Bot, Loader2, Eye } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SessionSidebar } from "@/components/chat/session-sidebar";
import { TransparencyPanel } from "@/components/chat/transparency-panel";
import {
  useChatHistory,
  useChatSession,
  useChatQuery,
  useChatStream,
  type ChatMessage,
} from "@/hooks/use-chat";
import { chatApi, type ChatQueryResponse } from "@/services/chat-api";
import { cn } from "@/lib/utils";

const SUGGESTIONS = [
  "Show GST summary",
  "Top vendors this month",
  "Find invoices from ABC Traders",
  "Which workflows failed?",
  "Show pending approvals",
  "What is OCR Agent doing?",
];

export default function ChatPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [lastResponse, setLastResponse] = useState<ChatQueryResponse | null>(null);
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const { data: history, refetch: refetchHistory } = useChatHistory();
  const { data: sessionData } = useChatSession(sessionId);
  const queryMutation = useChatQuery();
  const { send: streamSend, isStreaming, streamedContent, transparency: streamTransparency } = useChatStream();

  useEffect(() => {
    if (sessionData?.messages) {
      setMessages(sessionData.messages);
      const lastAssistant = [...sessionData.messages].reverse().find((m) => m.role === "assistant");
      if (lastAssistant) setSelectedMessageId(lastAssistant.id);
    }
  }, [sessionData]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, streamedContent]);

  const appendAssistant = useCallback((result: ChatQueryResponse) => {
    const msgId = result.message_id || `resp-${Date.now()}`;
    setSessionId(result.session_id);
    setLastResponse(result);
    setSelectedMessageId(msgId);
    setMessages((prev) => [
      ...prev,
      {
        id: msgId,
        role: "assistant",
        content: result.answer,
        chat_type: result.chat_type,
        intent: result.intent,
        confidence: result.transparency?.confidence_score ?? result.confidence,
        citations: result.citations,
        structured_data: result.structured_data,
        agents_used: result.agents_used,
        reasoning_steps: result.reasoning_steps,
        transparency: result.transparency,
        created_at: new Date().toISOString(),
      },
    ]);
    refetchHistory();
  }, [refetchHistory]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || queryMutation.isPending || isStreaming) return;

    setMessages((prev) => [
      ...prev,
      { id: `temp-${Date.now()}`, role: "user", content: text, created_at: new Date().toISOString() },
    ]);
    setInput("");

    streamSend(text, sessionId || undefined, appendAssistant);
  }, [input, sessionId, queryMutation, isStreaming, streamSend, appendAssistant]);

  const handleNewSession = () => {
    setSessionId(null);
    setMessages([]);
    setLastResponse(null);
    setSelectedMessageId(null);
  };

  const handleDeleteSession = async (id: string) => {
    await chatApi.deleteSession(id);
    if (sessionId === id) handleNewSession();
    refetchHistory();
  };

  const selectedMessage = messages.find((m) => m.id === selectedMessageId && m.role === "assistant");
  const activeTransparency =
    selectedMessage?.transparency ||
    lastResponse?.transparency ||
    streamTransparency ||
    (selectedMessage?.structured_data?.transparency as ChatQueryResponse["transparency"]) ||
    null;

  return (
    <>
      <Header
        title="AI Chat"
        description="ज्ञान से निर्णय तक — every answer shows how it was generated"
      />
      <div className="flex flex-1 overflow-hidden">
        <div className="hidden w-56 shrink-0 md:block lg:w-64">
          <SessionSidebar
            sessions={history?.sessions || []}
            activeId={sessionId}
            onSelect={setSessionId}
            onNew={handleNewSession}
            onDelete={handleDeleteSession}
          />
        </div>

        <div className="flex flex-1 flex-col min-w-0">
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 md:p-6">
            <div className="mx-auto max-w-3xl space-y-4">
              {messages.length === 0 && !isStreaming && (
                <div className="flex flex-col items-center py-12 text-center">
                  <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
                    <Sparkles className="h-7 w-7 text-primary" />
                  </div>
                  <h3 className="mt-4 text-lg font-semibold">Mahakosh AI</h3>
                  <p className="mt-1 max-w-md text-sm text-muted-foreground">
                    Ask in natural language. Every answer exposes agents, documents, chunks, sources, and confidence — never blind trust.
                  </p>
                  <div className="mt-4 flex items-center gap-1.5 text-xs text-muted-foreground">
                    <Eye className="h-3.5 w-3.5" />
                    Full reasoning transparency on every response
                  </div>
                  <div className="mt-6 flex flex-wrap justify-center gap-2">
                    {SUGGESTIONS.map((s) => (
                      <Button key={s} variant="outline" size="sm" className="text-xs" onClick={() => setInput(s)}>
                        {s}
                      </Button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={cn("flex gap-3", msg.role === "user" ? "justify-end" : "justify-start")}
                >
                  {msg.role === "assistant" && (
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
                      <Bot className="h-4 w-4 text-primary" />
                    </div>
                  )}
                  <div
                    className={cn(
                      "max-w-[85%] rounded-2xl px-4 py-3 text-sm",
                      msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted",
                      msg.role === "assistant" && selectedMessageId === msg.id && "ring-2 ring-primary/30",
                    )}
                    onClick={() => msg.role === "assistant" && setSelectedMessageId(msg.id)}
                  >
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                    {msg.role === "assistant" && (
                      <>
                        <div className="mt-2 flex flex-wrap gap-1">
                          {(msg.transparency?.confidence_display || msg.confidence != null) && (
                            <Badge variant="secondary" className="text-[10px]">
                              {msg.transparency?.confidence_display || `${msg.confidence?.toFixed(0)}%`}
                            </Badge>
                          )}
                          {msg.intent && (
                            <Badge variant="outline" className="text-[10px]">{msg.intent}</Badge>
                          )}
                          {msg.transparency && (
                            <Badge variant="outline" className="text-[10px]">
                              {msg.transparency.documents_consulted.length} docs · {msg.transparency.chunks_retrieved.length} chunks
                            </Badge>
                          )}
                        </div>
                        <TransparencyPanel transparency={msg.transparency} compact />
                      </>
                    )}
                  </div>
                </div>
              ))}

              {isStreaming && (
                <div className="flex gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
                    <Bot className="h-4 w-4 text-primary" />
                  </div>
                  <div className="max-w-[85%] rounded-2xl bg-muted px-4 py-3 text-sm">
                    {streamedContent ? (
                      <p className="whitespace-pre-wrap">{streamedContent}</p>
                    ) : (
                      <p className="text-muted-foreground">Analyzing intent, retrieving knowledge…</p>
                    )}
                    <Loader2 className="mt-2 h-3 w-3 animate-spin text-muted-foreground" />
                    {streamTransparency && <TransparencyPanel transparency={streamTransparency} compact defaultOpen />}
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="border-t bg-background p-4">
            <div className="mx-auto flex max-w-3xl gap-2">
              <input
                className="flex h-10 flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                placeholder="Ask anything about your business..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
                disabled={queryMutation.isPending || isStreaming}
              />
              <Button size="icon" onClick={handleSend} disabled={!input.trim() || queryMutation.isPending || isStreaming}>
                {queryMutation.isPending || isStreaming ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>
        </div>

        <div className="hidden w-80 shrink-0 overflow-y-auto border-l p-4 md:block">
          <TransparencyPanel transparency={activeTransparency} defaultOpen />
        </div>
      </div>
    </>
  );
}
