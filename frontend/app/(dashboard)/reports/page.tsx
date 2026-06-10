import { BarChart3 } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";

const templates = [
  "GST Summary Report",
  "Vendor Ledger",
  "Purchase Register",
  "Sales Register",
  "ITC Reconciliation",
];

export default function ReportsPage() {
  return (
    <>
      <Header title="Reports" description="Business intelligence and compliance reports" />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-7xl space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {templates.map((template) => (
              <Card key={template} className="cursor-pointer transition-shadow hover:shadow-md">
                <CardContent className="flex items-center gap-4 p-6">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                    <BarChart3 className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-medium">{template}</h3>
                    <p className="text-sm text-muted-foreground">Generate report</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
