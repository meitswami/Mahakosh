"use client";

import { GitBranch, CheckCircle2, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ReasoningStep } from "@/services/chat-api";

interface ReasoningPanelProps {
  steps: ReasoningStep[];
  isLoading?: boolean;
}

export function ReasoningPanel({ steps, isLoading }: ReasoningPanelProps) {
  if (!steps.length && !isLoading) return null;

  return (
    <Card className="border-dashed">
      <CardHeader className="pb-2 pt-4">
        <CardTitle className="flex items-center gap-2 text-sm font-medium">
          <GitBranch className="h-4 w-4 text-primary" />
          Reasoning Workflow
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 pb-4">
        {isLoading && steps.length === 0 && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Processing...
          </div>
        )}
        {steps.map((step, i) => (
          <div key={i} className="flex gap-2 text-sm">
            <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-green-600" />
            <div>
              <p className="font-medium">{step.label}</p>
              <p className="text-xs text-muted-foreground">{step.detail}</p>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
