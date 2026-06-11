"use client";

import { Building2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { TallyCompany } from "@/services/accounting-api";

export function CompanyBrowser({ companies }: { companies: TallyCompany[] | undefined }) {
  if (!companies?.length) {
    return <p className="py-4 text-center text-sm text-muted-foreground">No companies discovered yet.</p>;
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {companies.map((company) => (
        <div key={company.id} className="rounded-lg border p-4">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <Building2 className="h-4 w-4 text-primary" />
              <p className="font-medium">{company.name}</p>
            </div>
            <Badge variant={company.is_active ? "success" : "secondary"}>
              {company.books_status || "open"}
            </Badge>
          </div>
          <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
            <div className="rounded bg-muted/50 p-2">
              <p className="font-semibold">{company.ledger_count}</p>
              <p className="text-muted-foreground">Ledgers</p>
            </div>
            <div className="rounded bg-muted/50 p-2">
              <p className="font-semibold">{company.voucher_count}</p>
              <p className="text-muted-foreground">Vouchers</p>
            </div>
            <div className="rounded bg-muted/50 p-2">
              <p className="font-semibold">{company.inventory_count}</p>
              <p className="text-muted-foreground">Items</p>
            </div>
          </div>
          {company.financial_year && (
            <p className="mt-2 text-xs text-muted-foreground">FY {company.financial_year}</p>
          )}
        </div>
      ))}
    </div>
  );
}
