"use client";

import { FileText } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ChatCitation } from "@/services/chat-api";

interface SourcePanelProps {
  citations: ChatCitation[];
  confidence?: number;
  structuredData?: Record<string, unknown>;
}

export function SourcePanel({ citations, confidence, structuredData }: SourcePanelProps) {
  const hasContent = citations.length > 0 || (structuredData && Object.keys(structuredData).length > 0);
  if (!hasContent) return null;

  return (
    <Card>
      <CardHeader className="pb-2 pt-4">
        <CardTitle className="flex items-center gap-2 text-sm font-medium">
          <FileText className="h-4 w-4" />
          Sources
          {confidence != null && (
            <Badge variant="secondary" className="ml-auto">
              {confidence.toFixed(0)}% confidence
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 pb-4">
        {structuredData &&
          Object.entries(structuredData)
            .filter(([k]) => !["agent_outputs", "raw", "metadata"].includes(k))
            .map(([key, val]) => (
              <div key={key} className="flex justify-between text-sm">
                <span className="text-muted-foreground">{key.replace(/_/g, " ")}</span>
                <span className="font-medium">
                  {typeof val === "number" && (key.includes("amount") || key.includes("purchase"))
                    ? `₹${val.toLocaleString("en-IN")}`
                    : String(val)}
                </span>
              </div>
            ))}
        {citations.map((c, i) => (
          <div key={i} className="rounded-md border p-2 text-xs">
            <p className="font-medium">{c.source_document}</p>
            {c.page_number != null && <p className="text-muted-foreground">Page {c.page_number}</p>}
            <p className="mt-1 text-muted-foreground line-clamp-2">{c.excerpt}</p>
            <Badge variant="outline" className="mt-1">
              {c.confidence_display}
            </Badge>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
