"use client";

import { Badge } from "@/components/ui/badge";
import type { OCRField } from "@/services/ocr-api";

const levelVariant: Record<string, "success" | "warning" | "destructive"> = {
  high: "success",
  medium: "warning",
  low: "destructive",
};

const DISPLAY_FIELDS = [
  "invoice_number",
  "invoice_date",
  "vendor_name",
  "customer_name",
  "gstin",
  "vendor_gstin",
  "customer_gstin",
  "subtotal",
  "cgst",
  "sgst",
  "igst",
  "gst_amount",
  "grand_total",
  "hsn_codes",
];

interface ExtractedFieldsProps {
  fields: OCRField[];
}

export function ExtractedFields({ fields }: ExtractedFieldsProps) {
  const displayFields = fields.filter((f) => DISPLAY_FIELDS.includes(f.field_name));

  if (displayFields.length === 0) {
    return <p className="text-sm text-muted-foreground">No fields extracted yet.</p>;
  }

  return (
    <div className="space-y-3">
      {displayFields.map((field) => (
        <div key={field.field_name} className="rounded-lg border p-3">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              {field.field_name.replace(/_/g, " ")}
            </span>
            <Badge variant={levelVariant[field.confidence_level] || "secondary"}>
              {field.confidence_level}
            </Badge>
          </div>
          <p className="mt-1 text-sm font-medium">{field.field_value || "—"}</p>
          {(field.paddle_value || field.surya_value) && (
            <div className="mt-2 space-y-1 border-t pt-2">
              {field.paddle_value && (
                <p className="text-xs text-muted-foreground">
                  <span className="font-medium">Paddle:</span> {field.paddle_value}
                </p>
              )}
              {field.surya_value && (
                <p className="text-xs text-muted-foreground">
                  <span className="font-medium">Surya:</span> {field.surya_value}
                </p>
              )}
              {field.source_engine && (
                <p className="text-xs text-primary">Selected: {field.source_engine}</p>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
