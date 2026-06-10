"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { OCRJob } from "@/services/ocr-api";

const statusVariant: Record<string, "success" | "warning" | "destructive" | "secondary"> = {
  completed: "success",
  processing: "warning",
  uploaded: "secondary",
  pending: "secondary",
  failed: "destructive",
};

interface JobListProps {
  jobs: OCRJob[];
  selectedId: string | null;
  onSelect: (jobId: string) => void;
}

export function JobList({ jobs, selectedId, onSelect }: JobListProps) {
  if (jobs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <p className="text-sm text-muted-foreground">No OCR jobs yet</p>
        <p className="mt-1 text-xs text-muted-foreground">Upload a document to begin</p>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {jobs.map((job) => (
        <button
          key={job.job_id}
          type="button"
          onClick={() => onSelect(job.job_id)}
          className={cn(
            "w-full rounded-lg border px-3 py-2.5 text-left transition-colors",
            selectedId === job.job_id
              ? "border-primary bg-primary/5"
              : "border-transparent hover:bg-muted/50",
          )}
        >
          <div className="flex items-center justify-between gap-2">
            <span className="truncate text-sm font-medium">
              {job.document_class?.replace(/_/g, " ") || "Document"}
            </span>
            <Badge variant={statusVariant[job.status] || "secondary"} className="shrink-0 capitalize">
              {job.status}
            </Badge>
          </div>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {new Date(job.created_at).toLocaleString("en-IN")}
          </p>
        </button>
      ))}
    </div>
  );
}
