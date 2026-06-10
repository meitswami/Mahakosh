"use client";

import type { ApprovalItem } from "@/services/workflows-api";
import { Badge } from "@/components/ui/badge";
import { Shield, Clock } from "lucide-react";

export function ApprovalCenter({
  pending,
  history,
}: {
  pending: ApprovalItem[] | undefined;
  history: ApprovalItem[] | undefined;
}) {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div>
        <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold">
          <Shield className="h-4 w-4" />
          Pending Approvals ({pending?.length ?? 0})
        </h4>
        <div className="space-y-2">
          {pending?.length ? (
            pending.map((item) => (
              <div key={item.id} className="rounded-lg border p-3">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-medium">{item.title}</p>
                  <Badge variant="warning">pending</Badge>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{item.action}</p>
                {item.created_at && (
                  <p className="mt-1 flex items-center gap-1 text-[10px] text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    {new Date(item.created_at).toLocaleString()}
                  </p>
                )}
              </div>
            ))
          ) : (
            <p className="text-sm text-muted-foreground">No pending approvals.</p>
          )}
        </div>
      </div>
      <div>
        <h4 className="mb-3 text-sm font-semibold">Approval History</h4>
        <div className="space-y-2">
          {history?.length ? (
            history.slice(0, 8).map((item) => (
              <div key={item.id} className="rounded-lg border p-3">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-medium">{item.title}</p>
                  <Badge
                    variant={
                      item.status === "approved"
                        ? "success"
                        : item.status === "rejected"
                          ? "destructive"
                          : "secondary"
                    }
                  >
                    {item.status}
                  </Badge>
                </div>
                {item.review_notes && (
                  <p className="mt-1 text-xs text-muted-foreground">{item.review_notes}</p>
                )}
              </div>
            ))
          ) : (
            <p className="text-sm text-muted-foreground">No approval history.</p>
          )}
        </div>
      </div>
    </div>
  );
}
