"use client";

import { Badge } from "@/components/ui/badge";

interface DataRow {
  id: string;
  name: string;
  subtitle?: string | null;
  meta?: string | null;
  badge?: string;
}

export function DataBrowser({
  title,
  rows,
  emptyMessage,
}: {
  title: string;
  rows: DataRow[];
  emptyMessage: string;
}) {
  return (
    <div>
      <p className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</p>
      {rows.length ? (
        <div className="space-y-2">
          {rows.map((row) => (
            <div key={row.id} className="flex items-center justify-between rounded-lg border px-3 py-2">
              <div>
                <p className="text-sm font-medium">{row.name}</p>
                {row.subtitle && <p className="text-xs text-muted-foreground">{row.subtitle}</p>}
              </div>
              <div className="flex items-center gap-2">
                {row.meta && <span className="text-xs text-muted-foreground">{row.meta}</span>}
                {row.badge && <Badge variant="secondary">{row.badge}</Badge>}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="py-4 text-center text-sm text-muted-foreground">{emptyMessage}</p>
      )}
    </div>
  );
}
