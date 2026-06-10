import { FileText, Upload } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export default function DocumentsPage() {
  return (
    <>
      <Header title="Documents" description="Upload, process, and manage business documents" />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-7xl space-y-6">
          <div className="flex items-center justify-between">
            <div />
            <Button>
              <Upload className="mr-2 h-4 w-4" />
              Upload Document
            </Button>
          </div>

          <Card>
            <CardContent className="flex flex-col items-center justify-center py-16">
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
                <FileText className="h-7 w-7 text-primary" />
              </div>
              <h3 className="mt-4 text-lg font-semibold">No documents yet</h3>
              <p className="mt-1 max-w-sm text-center text-sm text-muted-foreground">
                Upload invoices, receipts, purchase orders, and bank statements to begin intelligent processing.
              </p>
              <Button className="mt-6">
                <Upload className="mr-2 h-4 w-4" />
                Upload your first document
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}
