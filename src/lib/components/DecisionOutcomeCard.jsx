import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  formatDecisionTimestamp,
  getDecisionStateLabel,
  getIntegrityStatusLabel,
} from "@/lib/tdsRecruiterDecisionUi";

function DecisionDetail({ label, value }) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  return (
    <div className="space-y-1">
      <p className="text-sm font-medium text-foreground">{label}</p>
      <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">{value}</p>
    </div>
  );
}

function DecisionList({ label, items, renderItem = (item) => item }) {
  if (!Array.isArray(items) || items.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      <p className="text-sm font-medium text-foreground">{label}</p>
      <ul className="space-y-2 text-sm text-muted-foreground">
        {items.map((item, index) => (
          <li key={`${label}-${index}`} className="rounded-md bg-muted/40 px-3 py-2">
            {renderItem(item)}
          </li>
        ))}
      </ul>
    </div>
  );
}

function booleanLabel(value, truthyLabel, falsyLabel) {
  return value ? truthyLabel : falsyLabel;
}

function renderEvidenceSummary(item) {
  if (!item || typeof item !== "object") {
    return typeof item === "string" ? item : "";
  }

  const dimension = typeof item.dimension === "string"
    ? item.dimension.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase())
    : "Behavioural Evidence";
  const evidenceSummary = Array.isArray(item.evidence_summary)
    ? item.evidence_summary.filter(Boolean).join("; ")
    : item.evidence_summary;

  return (
    <div className="space-y-1">
      <p className="font-medium text-foreground">{dimension}</p>
      <p>{evidenceSummary || "No behavioural evidence summary available."}</p>
    </div>
  );
}

const STATUS_MESSAGES = {
  loading: "Loading decision outcome...",
  unavailable: "No behavioural decision outcome is available yet.",
  forbidden: "You do not have access to this decision outcome.",
  error: "Decision outcome could not be loaded.",
};

function DecisionStateBadge({ decision }) {
  const label = getDecisionStateLabel(decision);
  const variant = {
    PROCEED: "default",
    PROCEED_WITH_CONDITIONS: "secondary",
    DO_NOT_PROCEED: "destructive",
    INSUFFICIENT_EVIDENCE: "outline",
  }[decision?.decision_state] ?? "outline";

  return <Badge variant={variant}>{label}</Badge>;
}

export default function DecisionOutcomeCard({ decision = null, status = "success" }) {
  if (status !== "success") {
    return (
      <Card className="p-6">
        <div className="space-y-2">
          <h2 className="text-lg font-semibold">Decision Outcome</h2>
          <p className="text-sm text-muted-foreground">{STATUS_MESSAGES[status] ?? STATUS_MESSAGES.error}</p>
        </div>
      </Card>
    );
  }

  const createdAt = formatDecisionTimestamp(decision?.created_at);

  return (
    <Card className="p-6 space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <h2 className="text-lg font-semibold">Decision Outcome</h2>
          <p className="text-sm text-muted-foreground">{decision?.decision_summary || "No behavioural decision summary is available."}</p>
        </div>
        <DecisionStateBadge decision={decision} />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <DecisionDetail
          label="Decision Validity"
          value={booleanLabel(Boolean(decision?.decision_valid), "Valid", "Not Valid")}
        />
        <DecisionDetail
          label="Confidence Validity"
          value={booleanLabel(Boolean(decision?.confidence_gate_passed), "Passed", "Not Passed")}
        />
        <DecisionDetail
          label="Integrity Status"
          value={getIntegrityStatusLabel(decision?.integrity_status)}
        />
        <DecisionDetail label="Created" value={createdAt} />
      </div>

      <DecisionList label="Risk Summary" items={decision?.risk_summary} />
      <DecisionList label="Evidence Summary" items={decision?.evidence_summary} renderItem={renderEvidenceSummary} />
      <DecisionList label="Evidence Gaps" items={decision?.evidence_gaps} />
      <DecisionList label="Conflict Flags" items={decision?.conflict_flags} />
      <DecisionList label="Conditions" items={decision?.conditions} />
      <DecisionDetail label="Trade-off" value={decision?.trade_off_statement} />
      <DecisionDetail label="Rationale" value={decision?.rationale} />
    </Card>
  );
}
