"use client";

import { useCallback, useRef, useState } from "react";
import { Upload, ScanText, FileCheck, AlertTriangle } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { JobList } from "@/components/ocr/job-list";
import { PipelineProgress } from "@/components/ocr/pipeline-progress";
import { ExtractedFields } from "@/components/ocr/extracted-fields";
import {
  useOCRJobs,
  useOCRJobStatus,
  useOCRResult,
  useOCRValidation,
  useOCRUpload,
  useOCRProcess,
} from "@/hooks/use-ocr";

export default function OCRDashboardPage() {
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: jobsData } = useOCRJobs();
  const { data: status } = useOCRJobStatus(selectedJobId);
  const { data: result } = useOCRResult(
    selectedJobId && status?.status === "completed" ? selectedJobId : null,
  );
  const { data: validation } = useOCRValidation(
    selectedJobId && status?.status === "completed" ? selectedJobId : null,
  );

  const uploadMutation = useOCRUpload();
  const processMutation = useOCRProcess();

  const handleUpload = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      const res = await uploadMutation.mutateAsync({ file });
      setSelectedJobId(res.job_id);
      await processMutation.mutateAsync(res.job_id);
      if (fileInputRef.current) fileInputRef.current.value = "";
    },
    [uploadMutation, processMutation],
  );

  const confidenceScores = result?.confidence_scores || [];
  const docConfidence = confidenceScores.find((c) => c.score_type === "document");
  const ocrConfidence = confidenceScores.find((c) => c.score_type === "ocr");

  return (
    <>
      <Header
        title="OCR Intelligence"
        description="Dual-engine OCR with PaddleOCR + Surya consensus for Indian business documents"
      />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-7xl space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ScanText className="h-5 w-5 text-primary" />
              <span className="text-sm text-muted-foreground">
                PDF · JPG · PNG · TIFF · Multi-page · Scanned · Mobile · WhatsApp
              </span>
            </div>
            <div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.jpg,.jpeg,.png,.tiff,.tif,.webp"
                className="hidden"
                onChange={handleUpload}
              />
              <Button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploadMutation.isPending || processMutation.isPending}
              >
                <Upload className="mr-2 h-4 w-4" />
                {uploadMutation.isPending ? "Uploading..." : "Upload & Process"}
              </Button>
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-12">
            <Card className="lg:col-span-3">
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Documents</CardTitle>
              </CardHeader>
              <CardContent>
                <JobList
                  jobs={jobsData?.items || []}
                  selectedId={selectedJobId}
                  onSelect={setSelectedJobId}
                />
              </CardContent>
            </Card>

            <div className="space-y-6 lg:col-span-9">
              {selectedJobId ? (
                <>
                  <div className="grid gap-4 sm:grid-cols-4">
                    <Card>
                      <CardContent className="p-4">
                        <p className="text-xs text-muted-foreground">Status</p>
                        <Badge className="mt-1 capitalize" variant={status?.status === "completed" ? "success" : "secondary"}>
                          {status?.status || "—"}
                        </Badge>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardContent className="p-4">
                        <p className="text-xs text-muted-foreground">Document Type</p>
                        <p className="mt-1 text-sm font-medium capitalize">
                          {status?.document_class?.replace(/_/g, " ") || "—"}
                        </p>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardContent className="p-4">
                        <p className="text-xs text-muted-foreground">OCR Confidence</p>
                        <p className="mt-1 text-sm font-medium">
                          {ocrConfidence ? `${(ocrConfidence.score * 100).toFixed(0)}% (${ocrConfidence.level})` : "—"}
                        </p>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardContent className="p-4">
                        <p className="text-xs text-muted-foreground">Validation</p>
                        <div className="mt-1 flex items-center gap-1">
                          {validation ? (
                            <>
                              <FileCheck className={`h-4 w-4 ${validation.is_valid ? "text-emerald-600" : "text-amber-600"}`} />
                              <span className="text-sm font-medium">{validation.is_valid ? "Valid" : "Issues found"}</span>
                            </>
                          ) : (
                            <span className="text-sm text-muted-foreground">—</span>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  </div>

                  <div className="grid gap-6 lg:grid-cols-2">
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">Pipeline Progress</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <PipelineProgress stages={result?.pipeline_stages || []} />
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">Extracted Fields</CardTitle>
                      </CardHeader>
                      <CardContent className="max-h-96 overflow-y-auto">
                        <ExtractedFields fields={result?.fields || []} />
                      </CardContent>
                    </Card>
                  </div>

                  {result?.tables && result.tables.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">Extracted Tables ({result.tables.length})</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-4">
                          {result.tables.map((table, idx) => (
                            <div key={idx} className="rounded-lg border p-3">
                              <div className="mb-2 flex items-center justify-between">
                                <span className="text-sm font-medium capitalize">{table.table_type.replace(/_/g, " ")}</span>
                                <Badge variant="secondary">{table.extraction_method}</Badge>
                              </div>
                              <div className="overflow-x-auto">
                                <table className="w-full text-xs">
                                  <thead>
                                    <tr className="border-b">
                                      {table.headers.map((h, i) => (
                                        <th key={i} className="px-2 py-1 text-left font-medium">{h}</th>
                                      ))}
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {table.rows.slice(0, 5).map((row, ri) => (
                                      <tr key={ri} className="border-b border-muted/50">
                                        {row.map((cell, ci) => (
                                          <td key={ci} className="px-2 py-1">{cell}</td>
                                        ))}
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                                {table.rows.length > 5 && (
                                  <p className="mt-1 text-xs text-muted-foreground">+{table.rows.length - 5} more rows</p>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {validation && validation.issues.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-base">
                          <AlertTriangle className="h-4 w-4 text-amber-600" />
                          Validation Issues
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2">
                          {validation.issues.map((issue, idx) => (
                            <div key={idx} className="rounded border px-3 py-2 text-sm">
                              <span className="font-medium capitalize">{issue.severity}</span>
                              <span className="mx-2 text-muted-foreground">·</span>
                              {issue.message}
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {result?.pages?.[0]?.consensus_text && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">Document Preview (OCR Text)</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <pre className="max-h-64 overflow-y-auto whitespace-pre-wrap rounded-lg bg-muted/50 p-4 text-xs font-mono">
                          {result.pages[0].consensus_text.slice(0, 3000)}
                        </pre>
                      </CardContent>
                    </Card>
                  )}
                </>
              ) : (
                <Card>
                  <CardContent className="flex flex-col items-center justify-center py-20">
                    <ScanText className="h-12 w-12 text-muted-foreground/50" />
                    <h3 className="mt-4 text-lg font-semibold">OCR Intelligence Engine</h3>
                    <p className="mt-1 max-w-md text-center text-sm text-muted-foreground">
                      Upload an invoice, bank statement, or business document. The dual-engine pipeline
                      runs PaddleOCR + Surya with consensus validation.
                    </p>
                    <Button className="mt-6" onClick={() => fileInputRef.current?.click()}>
                      <Upload className="mr-2 h-4 w-4" />
                      Upload Document
                    </Button>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
