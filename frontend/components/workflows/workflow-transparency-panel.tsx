"use client";

import {
  Bot,
  ChevronDown,
  ChevronUp,
  Eye,
  FileText,
  GitBranch,
  HelpCircle,
  Shield,
  UserCheck,
} from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { WorkflowTransparency } from "@/services/workflows-api";

interface WorkflowTransparencyPanelProps {
  transparency: WorkflowTransparency | null | undefined;
  compact?: boolean;
  defaultOpen?: boolean;
}

export function WorkflowTransparencyPanel({
  transparency,
  compact = false,
  defaultOpen = true,
}: WorkflowTransparencyPanelProps) {
  const [open, setOpen] = useState(defaultOpen);

  if (!transparency) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-6 text-center text-sm text-muted-foreground">
          <Eye className="mx-auto mb-2 h-5 w-5" />
          Transparency manifest will appear once the workflow executes
        </CardContent>
      </Card>
    );
  }

  const levelColor =
    transparency.confidence_level === "high"
      ? "text-emerald-600"
      : transparency.confidence_level === "medium"
        ? "text-amber-600"
        : "text-orange-600";

  const questions = [
    { q: "What happened?", a: transparency.questions.what_happened, icon: HelpCircle },
    { q: "Why did it happen?", a: transparency.questions.why_did_it_happen, icon: GitBranch },
    { q: "Which agent executed it?", a: transparency.questions.which_agent_executed, icon: Bot },
    { q: "Which documents were used?", a: transparency.questions.which_documents_were_used, icon: FileText },
    { q: "Which validations were performed?", a: transparency.questions.which_validations_were_performed, icon: Shield },
    { q: "Who approved it?", a: transparency.questions.who_approved_it, icon: UserCheck },
  ];

  if (compact) {
    return (
      <div className="rounded-lg border border-dashed p-3">
        <button
          type="button"
          className="flex w-full items-center justify-between text-left text-sm"
          onClick={() => setOpen(!open)}
        >
          <span className="flex items-center gap-2 font-medium">
            <Eye className="h-4 w-4 text-primary" />
            Workflow Transparency
          </span>
          <span className="flex items-center gap-2">
            <Badge variant="secondary">{transparency.confidence_display}</Badge>
            {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </span>
        </button>
        {open && (
          <div className="mt-3 space-y-3 border-t pt-3">
            <TransparencyBody transparency={transparency} questions={questions} compact />
          </div>
        )}
      </div>
    );
  }

  return (
    <Card className="border-primary/20">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <Eye className="h-5 w-5 text-primary" />
            Workflow Transparency
          </CardTitle>
          <Badge variant="secondary" className={levelColor}>
            {transparency.confidence_display}
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground">{transparency.summary}</p>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-3 sm:grid-cols-2">
          {questions.map(({ q, a, icon: Icon }) => (
            <div key={q} className="rounded-lg border bg-muted/30 p-3">
              <p className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                <Icon className="h-3.5 w-3.5" />
                {q}
              </p>
              <p className="text-sm leading-relaxed">{a}</p>
            </div>
          ))}
        </div>
        <TransparencyBody transparency={transparency} questions={questions} />
      </CardContent>
    </Card>
  );
}

function TransparencyBody({
  transparency,
  questions,
  compact = false,
}: {
  transparency: WorkflowTransparency;
  questions: Array<{ q: string; a: string; icon: React.ElementType }>;
  compact?: boolean;
}) {
  if (compact) {
    return (
      <div className="space-y-2">
        {questions.map(({ q, a }) => (
          <div key={q}>
            <p className="text-xs font-medium text-muted-foreground">{q}</p>
            <p className="text-xs">{a}</p>
          </div>
        ))}
      </div>
    );
  }

  return (
    <>
      <Section icon={Bot} title="Agents Executed">
        {transparency.agents_executed.length === 0 ? (
          <p className="text-sm text-muted-foreground">No agents executed yet</p>
        ) : (
          <ul className="space-y-2">
            {transparency.agents_executed.map((agent) => (
              <li key={`${agent.step_name}-${agent.name}`} className="rounded-lg border p-3 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium">
                    {agent.name}{" "}
                    <span className="font-normal text-muted-foreground">· {agent.step_name}</span>
                  </span>
                  <Badge variant="outline">{agent.status}</Badge>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{agent.purpose}</p>
                <p className="mt-1 text-xs">{agent.reasoning}</p>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section icon={FileText} title="Documents Used">
        {transparency.documents_used.length === 0 ? (
          <p className="text-sm text-muted-foreground">No documents referenced</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {transparency.documents_used.map((doc) => (
              <li key={doc.document_id}>
                <span className="font-medium">{doc.title}</span>
                <span className="text-muted-foreground">
                  {" "}
                  · steps: {doc.used_in_steps.join(", ") || "input"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section icon={Shield} title="Validations Performed">
        {transparency.validations_performed.length === 0 ? (
          <p className="text-sm text-muted-foreground">No validation steps</p>
        ) : (
          <ul className="space-y-2">
            {transparency.validations_performed.map((v) => (
              <li key={v.step_name} className="rounded border p-2 text-sm">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{v.step_name}</span>
                  <Badge variant={v.is_valid ? "success" : "destructive"}>
                    {v.is_valid ? "valid" : "invalid"}
                  </Badge>
                </div>
                {v.checks_passed.length > 0 && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    Passed: {v.checks_passed.join(", ")}
                  </p>
                )}
                {v.issues.length > 0 && (
                  <p className="mt-1 text-xs text-red-600">
                    {v.issues.length} issue(s) found
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section icon={UserCheck} title="Approvals">
        {transparency.approvals.length === 0 ? (
          <p className="text-sm text-muted-foreground">No approvals required</p>
        ) : (
          <ul className="space-y-2">
            {transparency.approvals.map((a) => (
              <li key={a.approval_id || a.title} className="rounded border p-2 text-sm">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{a.title}</span>
                  <Badge variant="outline">{a.status}</Badge>
                </div>
                {a.reviewed_by && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    Reviewed by {a.reviewed_by}
                    {a.reviewed_at && ` · ${new Date(a.reviewed_at).toLocaleString()}`}
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </Section>

      {transparency.reasoning_path.length > 0 && (
        <Section icon={GitBranch} title="Reasoning Path">
          <ol className="space-y-2">
            {transparency.reasoning_path.map((step, i) => (
              <li key={i} className="flex gap-2 text-sm">
                <span className="font-mono text-muted-foreground">{i + 1}.</span>
                <div>
                  <span className="font-medium">{step.label}</span>
                  <p className="text-muted-foreground">{step.detail}</p>
                </div>
              </li>
            ))}
          </ol>
        </Section>
      )}
    </>
  );
}

function Section({
  icon: Icon,
  title,
  children,
}: {
  icon: React.ElementType;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <p className="mb-2 flex items-center gap-2 text-sm font-semibold">
        <Icon className="h-4 w-4 text-primary" />
        {title}
      </p>
      {children}
    </div>
  );
}
