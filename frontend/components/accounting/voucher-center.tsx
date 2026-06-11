"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Voucher } from "@/services/accounting-api";

const STATUS_COLORS: Record<string, "success" | "destructive" | "warning" | "secondary" | "default"> = {
  approved: "success",
  draft: "secondary",
  rejected: "destructive",
  exported: "default",
};

export function VoucherCenter({
  vouchers,
  onApprove,
  approving,
}: {
  vouchers: Voucher[] | undefined;
  onApprove: (id: string) => void;
  approving: boolean;
}) {
  if (!vouchers?.length) {
    return <p className="py-4 text-center text-sm text-muted-foreground">No voucher drafts yet.</p>;
  }

  return (
    <div className="space-y-2">
      {vouchers.map((v) => (
        <div key={v.id} className="flex items-center justify-between rounded-lg border p-3">
          <div>
            <p className="text-sm font-medium">
              {v.voucher_type} — {v.party_name || "No party"}
            </p>
            <p className="text-xs text-muted-foreground">
              ₹{v.total_amount.toLocaleString("en-IN")} · {v.voucher_date}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={STATUS_COLORS[v.status] || "secondary"}>{v.status}</Badge>
            {v.status === "draft" && (
              <Button size="sm" variant="outline" disabled={approving} onClick={() => onApprove(v.id)}>
                Approve
              </Button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
