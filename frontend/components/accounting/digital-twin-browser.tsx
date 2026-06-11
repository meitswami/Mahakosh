"use client";

import { Badge } from "@/components/ui/badge";
import { QualityBadge } from "@/components/accounting/data-quality-panel";

export interface TwinObject {
  id: string;
  object_type: string;
  source_system: string;
  display_name: string;
  normalized_fields: Record<string, unknown>;
  quality_score: number;
  issues: { code: string; message: string; severity: string }[];
  normalization_notes: string[];
}

export function DigitalTwinBrowser({
  title,
  objects,
  emptyMessage,
  renderMeta,
}: {
  title: string;
  objects?: TwinObject[];
  emptyMessage: string;
  renderMeta?: (obj: TwinObject) => string | null;
}) {
  return (
    <div>
      <p className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</p>
      {objects?.length ? (
        <div className="space-y-2">
          {objects.map((obj) => (
            <div key={obj.id} className="rounded-lg border px-3 py-2">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">{obj.display_name}</p>
                  <p className="text-xs text-muted-foreground">
                    {obj.source_system} · {obj.object_type}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {renderMeta?.(obj) && (
                    <span className="text-xs text-muted-foreground">{renderMeta(obj)}</span>
                  )}
                  <QualityBadge score={obj.quality_score} />
                </div>
              </div>
              {obj.issues.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {obj.issues.slice(0, 3).map((issue, i) => (
                    <Badge key={i} variant="outline" className="text-xs">
                      {issue.code}
                    </Badge>
                  ))}
                  {obj.issues.length > 3 && (
                    <Badge variant="outline" className="text-xs">+{obj.issues.length - 3}</Badge>
                  )}
                </div>
              )}
              {obj.normalization_notes.length > 0 && (
                <p className="mt-1 text-xs text-muted-foreground">
                  {obj.normalization_notes[0]}
                </p>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="py-4 text-center text-sm text-muted-foreground">{emptyMessage}</p>
      )}
    </div>
  );
}
