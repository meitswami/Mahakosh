"use client";

import { RefreshCw, Upload, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { AccountingOverview } from "@/services/accounting-api";

export function SyncDashboard({
  overview,
  onImport,
  onExport,
  loading,
}: {
  overview: AccountingOverview | undefined;
  onImport: () => void;
  onExport: () => void;
  loading: boolean;
}) {
  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Button size="sm" variant="outline" disabled={loading} onClick={onImport}>
          <Upload className="mr-1 h-3 w-3" />
          Import Masters
        </Button>
        <Button size="sm" variant="outline" disabled={loading} onClick={onExport}>
          <Download className="mr-1 h-3 w-3" />
          Export Trial Balance
        </Button>
        <Button size="sm" variant="ghost" disabled={loading}>
          <RefreshCw className={`mr-1 h-3 w-3 ${loading ? "animate-spin" : ""}`} />
          {loading ? "Syncing…" : "Ready"}
        </Button>
      </div>

      {overview && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <IntelCard label="Ledgers" value={String(overview.ledger_count)} />
          <IntelCard label="Items" value={String(overview.item_count)} />
          <IntelCard label="Vouchers" value={String(overview.voucher_count)} />
          <IntelCard label="Pending Exports" value={String(overview.pending_exports)} />
        </div>
      )}
    </div>
  );
}

function IntelCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-muted/30 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-semibold">{value}</p>
    </div>
  );
}
