"use client";

import { BarChart3, Download } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useGenerateReport, useReportTemplates } from "@/hooks/use-intelligence";

export default function ReportsPage() {
  const { data: templates, isLoading } = useReportTemplates();
  const generateReport = useGenerateReport();

  const handleGenerate = async (reportType: string, name: string, format: string) => {
    const { blob, filename } = await generateReport.mutateAsync({ name, reportType, format });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <Header title="Reports" description="Business intelligence and compliance reports" />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-7xl space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {(templates?.templates ?? []).map((template) => (
              <Card key={template.type} className="transition-shadow hover:shadow-md">
                <CardContent className="flex flex-col gap-4 p-6">
                  <div className="flex items-center gap-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                      <BarChart3 className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <h3 className="font-medium">{template.name}</h3>
                      <p className="text-sm text-muted-foreground">
                        {template.formats.join(" · ")}
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {template.formats.slice(0, 2).map((fmt) => (
                      <Button
                        key={fmt}
                        size="sm"
                        variant="outline"
                        className="flex-1"
                        disabled={generateReport.isPending || isLoading}
                        onClick={() => handleGenerate(template.type, template.name, fmt)}
                      >
                        <Download className="mr-1 h-3 w-3" />
                        {fmt.toUpperCase()}
                      </Button>
                    ))}
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
