"use client";

import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { OCRPipelineStage } from "@/services/ocr-api";

const STAGE_LABELS: Record<string, string> = {
  upload: "Upload",
  classification: "Classification",
  preprocessing: "Preprocessing",
  ocr_paddle: "PaddleOCR",
  ocr_surya: "Surya OCR",
  ocr_consensus: "Consensus",
  layout_analysis: "Layout Analysis",
  table_extraction: "Table Extraction",
  field_extraction: "Field Extraction",
  validation: "Validation",
  confidence_scoring: "Confidence",
  knowledge_building: "Knowledge Build",
  storage: "Storage",
};

interface PipelineProgressProps {
  stages: OCRPipelineStage[];
}

export function PipelineProgress({ stages }: PipelineProgressProps) {
  if (stages.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">Pipeline stages will appear when processing starts.</p>
    );
  }

  return (
    <div className="space-y-2">
      {stages.map((stage) => {
        const Icon =
          stage.status === "completed"
            ? CheckCircle2
            : stage.status === "failed"
              ? XCircle
              : stage.status === "running"
                ? Loader2
                : Circle;

        return (
          <div key={stage.stage_name} className="flex items-center gap-3">
            <Icon
              className={cn(
                "h-4 w-4 shrink-0",
                stage.status === "completed" && "text-emerald-600",
                stage.status === "failed" && "text-red-600",
                stage.status === "running" && "animate-spin text-primary",
                stage.status !== "completed" && stage.status !== "failed" && stage.status !== "running" && "text-muted-foreground",
              )}
            />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium">
                {STAGE_LABELS[stage.stage_name] || stage.stage_name}
              </p>
              {stage.duration_ms != null && (
                <p className="text-xs text-muted-foreground">{stage.duration_ms}ms</p>
              )}
              {stage.error_message && (
                <p className="text-xs text-destructive truncate">{stage.error_message}</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
