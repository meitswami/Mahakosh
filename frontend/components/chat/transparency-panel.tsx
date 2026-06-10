"use client";

import { useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  Bot,
  FileText,
  Layers,
  Shield,
  GitBranch,
  Eye,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { TransparencyManifest } from "@/services/chat-api";
import { cn } from "@/lib/utils";

interface TransparencyPanelProps {
  transparency: TransparencyManifest | null | undefined;
  compact?: boolean;
  defaultOpen?: boolean;
}

export function TransparencyPanel({
  transparency,
  compact = false,
  defaultOpen = false,
}: TransparencyPanelProps) {
  const [open, setOpen] = useState(defaultOpen);

  if (!transparency) {
    return (
      <Card className={cn("border-dashed", compact && "shadow-none")}>
        <CardContent className="py-4 text-center text-xs text-muted-foreground">
          <Eye className="mx-auto mb-2 h-4 w-4" />
          Transparency data will appear after the AI responds
        </CardContent>
      </Card>
    );
  }

  const levelColor =
    transparency.confidence_level === "high"
      ? "text-green-600"
      : transparency.confidence_level === "medium"
        ? "text-amber-600"
        : "text-orange-600";

  if (compact) {
    return (
      <div className="mt-2 rounded-lg border border-dashed bg-background/50 p-2">
        <button
          type="button"
          className="flex w-full items-center justify-between text-left text-xs"
          onClick={() => setOpen(!open)}
        >
          <span className="flex items-center gap-1.5 font-medium text-muted-foreground">
            <Eye className="h-3.5 w-3.5" />
            How this answer was generated
          </span>
          <span className="flex items-center gap-2">
            <Badge variant="secondary" className="text-[10px]">
              {transparency.confidence_display}
            </Badge>
            {open ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </span>
        </button>
        {open && (
          <div className="mt-2 space-y-2 border-t pt-2">
            <TransparencyBody transparency={transparency} compact />
          </div>
        )}
      </div>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2 pt-4">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-sm font-medium">
            <Eye className="h-4 w-4 text-primary" />
            Answer Transparency
          </CardTitle>
          <Badge variant="secondary" className={levelColor}>
            {transparency.confidence_display}
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground">{transparency.summary}</p>
      </CardHeader>
      <CardContent className="space-y-4 pb-4">
        <TransparencyBody transparency={transparency} />
      </CardContent>
    </Card>
  );
}

function TransparencyBody({
  transparency,
  compact = false,
}: {
  transparency: TransparencyManifest;
  compact?: boolean;
}) {
  return (
    <>
      <Section icon={Bot} title="Agents Participated" compact={compact}>
        {transparency.agents_participated.length === 0 ? (
          <p className="text-xs text-muted-foreground">No agents invoked</p>
        ) : (
          <ul className="space-y-1">
            {transparency.agents_participated.map((a) => (
              <li key={a.name} className="flex items-start justify-between gap-2 text-xs">
                <div>
                  <span className="font-medium">{a.name}</span>
                  <span className="text-muted-foreground"> · {a.role}</span>
                  {!compact && a.description && (
                    <p className="text-muted-foreground">{a.description}</p>
                  )}
                </div>
                {a.confidence != null && (
                  <Badge variant="outline" className="shrink-0 text-[10px]">
                    {a.confidence}%
                  </Badge>
                )}
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section icon={FileText} title="Documents Consulted" compact={compact}>
        {transparency.documents_consulted.length === 0 ? (
          <p className="text-xs text-muted-foreground">No documents retrieved</p>
        ) : (
          <ul className="space-y-1">
            {transparency.documents_consulted.map((d) => (
              <li key={d.document_id} className="text-xs">
                <span className="font-medium">{d.title}</span>
                <span className="text-muted-foreground">
                  {" "}
                  · {d.chunks_used} chunk{d.chunks_used !== 1 ? "s" : ""}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section icon={Layers} title="Knowledge Chunks Retrieved" compact={compact}>
        {transparency.chunks_retrieved.length === 0 ? (
          <p className="text-xs text-muted-foreground">No chunks retrieved</p>
        ) : (
          <ul className="space-y-2">
            {transparency.chunks_retrieved.slice(0, compact ? 3 : 8).map((c) => (
              <li key={c.chunk_id} className="rounded border p-2 text-xs">
                <div className="flex justify-between">
                  <span className="font-medium line-clamp-1">{c.document_title}</span>
                  <Badge variant="outline" className="ml-1 shrink-0 text-[10px]">
                    {c.confidence}%
                  </Badge>
                </div>
                <p className="text-muted-foreground">
                  Chunk {c.chunk_id.slice(0, 8)}…
                  {c.page_number != null && ` · Page ${c.page_number}`}
                </p>
                {!compact && c.excerpt && (
                  <p className="mt-1 line-clamp-2 text-muted-foreground">{c.excerpt}</p>
                )}
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section icon={Shield} title="Sources & Confidence" compact={compact}>
        <div className="mb-2 flex items-center gap-2 text-xs">
          <span className="text-muted-foreground">Overall confidence:</span>
          <span className="font-semibold">{transparency.confidence_display}</span>
          <Badge variant="outline" className="text-[10px]">
            {transparency.confidence_level.replace("_", " ")}
          </Badge>
        </div>
        {transparency.sources.length === 0 ? (
          <p className="text-xs text-muted-foreground">No source citations</p>
        ) : (
          <ul className="space-y-1">
            {transparency.sources.map((s, i) => (
              <li key={i} className="text-xs text-muted-foreground">
                {s.source_document}
                {s.page_number != null && ` · Page ${s.page_number}`}
                {" · "}
                {s.confidence_display}
              </li>
            ))}
          </ul>
        )}
      </Section>

      {!compact && transparency.reasoning_path.length > 0 && (
        <Section icon={GitBranch} title="Reasoning Path" compact={compact}>
          <ol className="space-y-1">
            {transparency.reasoning_path.map((step, i) => (
              <li key={i} className="flex gap-2 text-xs">
                <span className="font-mono text-muted-foreground">{i + 1}.</span>
                <div>
                  <span className="font-medium">{step.label}</span>
                  <p className="text-muted-foreground">{step.detail}</p>
                </div>
              </li>
            ))}
          </ol>
        </Section>
      )}
    </>
  );
}

function Section({
  icon: Icon,
  title,
  children,
  compact,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  children: React.ReactNode;
  compact?: boolean;
}) {
  return (
    <div>
      <p className={cn("mb-1.5 flex items-center gap-1.5 font-medium", compact ? "text-xs" : "text-sm")}>
        <Icon className="h-3.5 w-3.5 text-primary" />
        {title}
      </p>
      {children}
    </div>
  );
}
