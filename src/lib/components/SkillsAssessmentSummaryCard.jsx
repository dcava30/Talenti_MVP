import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { formatSkillsSummaryTimestamp } from "@/lib/tdsRecruiterSkillsSummaryUi";

const STATUS_MESSAGES = {
  loading: "Loading Skills Assessment Summary...",
  unavailable: "No Skills Assessment Summary is available yet.",
  forbidden: "You do not have access to this Skills Assessment Summary.",
  error: "Skills Assessment Summary could not be loaded.",
};

const BLOCKED_TEXT_PATTERNS = [
  /decision outcome/gi,
  /decision_state/gi,
  /decision_valid/gi,
  /confidence_gate_passed/gi,
  /integrity_status/gi,
  /proceed with conditions/gi,
  /do not proceed/gi,
  /insufficient evidence/gi,
  /\bproceed\b/gi,
  /risk_stack/gi,
  /behavioural rationale/gi,
  /match score/gi,
  /match_score/gi,
  /skills fit score/gi,
  /shortlist position/gi,
  /best skilled candidate/gi,
  /best candidate/gi,
  /\branking\b/gi,
  /\bpass\b/gi,
  /\breview\b/gi,
  /\bfail\b/gi,
];

const BLOCKED_KEYS = new Set([
  "decision_state",
  "decision_valid",
  "confidence_gate_passed",
  "integrity_status",
  "risk_stack",
  "behavioural_rationale",
  "rationale",
  "match_score",
  "ranking",
  "best_candidate",
  "best_skilled_candidate",
  "shortlist_position",
  "skills_fit_score",
  "skills_outcome",
  "outcome",
  "raw_hiring_label",
  "raw_review_marker",
  "raw_fail_marker",
]);

function sanitizeDisplayText(value) {
  if (typeof value !== "string") {
    return null;
  }

  let sanitized = value;
  for (const pattern of BLOCKED_TEXT_PATTERNS) {
    sanitized = sanitized.replace(pattern, " ");
  }

  sanitized = sanitized.replace(/\s+/g, " ").trim();
  if (!sanitized || !/[a-z0-9]/i.test(sanitized)) {
    return null;
  }

  return sanitized;
}

function formatLabel(value) {
  if (typeof value !== "string" || value.trim() === "") {
    return null;
  }

  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function isBlockedKey(key) {
  return typeof key === "string" && BLOCKED_KEYS.has(key.trim().toLowerCase());
}

function formatPrimitive(value) {
  if (typeof value === "string") {
    return sanitizeDisplayText(value);
  }

  if (typeof value === "number") {
    return String(value);
  }

  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }

  return null;
}

function StructuredList({ items }) {
  if (!Array.isArray(items) || items.length === 0) {
    return null;
  }

  const renderedItems = items
    .map((item, index) => {
      const content = renderStructuredValue(item, `list-${index}`);
      if (!content) {
        return null;
      }

      return (
        <li key={`item-${index}`} className="rounded-md bg-muted/40 px-3 py-2">
          {content}
        </li>
      );
    })
    .filter(Boolean);

  if (renderedItems.length === 0) {
    return null;
  }

  return <ul className="space-y-2 text-sm text-muted-foreground">{renderedItems}</ul>;
}

function StructuredObject({ value }) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  const entries = Object.entries(value)
    .filter(([key, entryValue]) => !isBlockedKey(key) && entryValue !== null && entryValue !== undefined && entryValue !== "")
    .map(([key, entryValue]) => {
      const content = renderStructuredValue(entryValue, key);
      if (!content) {
        return null;
      }

      return (
        <div key={key} className="space-y-1 rounded-md bg-muted/30 px-3 py-2">
          <p className="text-sm font-medium text-foreground">{formatLabel(key) ?? key}</p>
          <div className="text-sm text-muted-foreground">{content}</div>
        </div>
      );
    })
    .filter(Boolean);

  if (entries.length === 0) {
    return null;
  }

  return <div className="space-y-2">{entries}</div>;
}

function renderStructuredValue(value, key) {
  const primitive = formatPrimitive(value);
  if (primitive) {
    return <span>{primitive}</span>;
  }

  if (Array.isArray(value)) {
    return <StructuredList items={value} />;
  }

  if (value && typeof value === "object") {
    if (typeof value.competency === "string") {
      const competency = sanitizeDisplayText(value.competency);
      const details = Object.entries(value)
        .filter(([entryKey]) => entryKey !== "competency" && !isBlockedKey(entryKey))
        .map(([entryKey, entryValue]) => {
          const entryPrimitive = formatPrimitive(entryValue);
          if (entryPrimitive) {
            return `${formatLabel(entryKey)}: ${entryPrimitive}`;
          }

          if (Array.isArray(entryValue)) {
            const safeItems = entryValue
              .map((item) => formatPrimitive(item))
              .filter(Boolean)
              .join(", ");

            return safeItems ? `${formatLabel(entryKey)}: ${safeItems}` : null;
          }

          return null;
        })
        .filter(Boolean);

      return (
        <div className="space-y-1">
          <p className="font-medium text-foreground">{competency ?? "Observed competency"}</p>
          {details.length > 0 && <p>{details.join(" | ")}</p>}
        </div>
      );
    }

    return <StructuredObject value={value} />;
  }

  if (typeof key === "string") {
    return <span>{formatLabel(key) ?? key}</span>;
  }

  return null;
}

function Detail({ label, value, badge = false }) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  return (
    <div className="space-y-2">
      <p className="text-sm font-medium text-foreground">{label}</p>
      {badge ? (
        <Badge variant={value === "Yes" ? "secondary" : "outline"}>{value}</Badge>
      ) : (
        <p className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">{value}</p>
      )}
    </div>
  );
}

function Section({ label, value }) {
  const content = renderStructuredValue(value, label);
  if (!content) {
    return null;
  }

  return (
    <div className="space-y-2">
      <p className="text-sm font-medium text-foreground">{label}</p>
      <div className="text-sm text-muted-foreground">{content}</div>
    </div>
  );
}

export default function SkillsAssessmentSummaryCard({ summary = null, status = "success" }) {
  const createdAt = formatSkillsSummaryTimestamp(summary?.created_at);
  const humanReadableSummary = sanitizeDisplayText(summary?.human_readable_summary);

  if (status !== "success") {
    return (
      <Card className="p-6 space-y-3">
        <div className="space-y-2">
          <h2 className="text-lg font-semibold">Skills Assessment Summary</h2>
          <p className="text-sm text-muted-foreground">
            This summary is not used in the behavioural TDS decision outcome.
          </p>
          <p className="text-sm text-muted-foreground">{STATUS_MESSAGES[status] ?? STATUS_MESSAGES.error}</p>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-6 space-y-6">
      <div className="space-y-2">
        <h2 className="text-lg font-semibold">Skills Assessment Summary</h2>
        <p className="text-sm text-muted-foreground">
          This summary is not used in the behavioural TDS decision outcome.
        </p>
      </div>

      <Section label="Observed Skills Evidence" value={summary?.observed_competencies} />
      <Section label="Competency Coverage" value={summary?.competency_coverage} />
      <Section label="Skills Gaps" value={summary?.skill_gaps} />

      <div className="grid gap-4 md:grid-cols-2">
        <Detail label="Evidence Strength" value={formatLabel(summary?.evidence_strength)} />
        <Detail label="Confidence" value={formatLabel(summary?.confidence)} />
        <Detail
          label="Requires Human Review"
          value={typeof summary?.requires_human_review === "boolean"
            ? formatPrimitive(summary.requires_human_review)
            : null}
          badge
        />
        <Detail label="Model Version" value={formatPrimitive(summary?.model_version)} />
        <Detail label="Created" value={createdAt} />
      </div>

      <Section label="Source References" value={summary?.source_references} />
      <Detail label="Summary" value={humanReadableSummary} />
    </Card>
  );
}
