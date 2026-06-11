"use client";

import { Badge } from "@/components/ui/badge";
import type { Mapping } from "@/services/accounting-api";

export function MappingCenter({
  ledgerMappings,
  itemMappings,
}: {
  ledgerMappings: Mapping[] | undefined;
  itemMappings: Mapping[] | undefined;
}) {
  const all = [
    ...(ledgerMappings ?? []).map((m) => ({ ...m, kind: "ledger" as const })),
    ...(itemMappings ?? []).map((m) => ({ ...m, kind: "item" as const })),
  ];

  if (!all.length) {
    return (
      <p className="py-4 text-center text-sm text-muted-foreground">
        No mappings yet. Run a sync to generate smart matches.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {all.map((m) => (
        <div key={m.id} className="flex items-center justify-between rounded-lg border px-3 py-2">
          <div>
            <p className="text-sm font-medium">{m.external_name}</p>
            <p className="text-xs text-muted-foreground">{m.reasoning || "No reasoning"}</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary">{m.kind}</Badge>
            <Badge variant={m.match_type === "exact" ? "success" : "default"}>{m.match_type}</Badge>
            <span className="text-xs font-medium">{m.confidence}%</span>
          </div>
        </div>
      ))}
    </div>
  );
}
