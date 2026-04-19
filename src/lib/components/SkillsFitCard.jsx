import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { CheckCircle, XCircle, AlertTriangle } from "lucide-react";

const outcomeBadge = (outcome) => {
  if (!outcome) return null;
  const upper = outcome.toUpperCase();
  if (upper === "PASS")
    return <Badge className="bg-green-600 text-white">PASS</Badge>;
  if (upper === "REVIEW")
    return <Badge className="bg-amber-500 text-white">REVIEW</Badge>;
  return <Badge variant="destructive">FAIL</Badge>;
};

const scoreColor = (score, threshold = 0.65) => {
  if (score >= threshold) return "text-green-600";
  if (score >= threshold - 0.1) return "text-amber-500";
  return "text-red-500";
};

const progressColor = (score, threshold = 0.65) => {
  if (score >= threshold) return "[&>div]:bg-green-600";
  if (score >= threshold - 0.1) return "[&>div]:bg-amber-500";
  return "[&>div]:bg-red-500";
};

const SkillsFitCard = ({ skillsData }) => {
  if (!skillsData) return null;

  const {
    overall_score,
    outcome,
    skills = {},
    must_haves_passed = [],
    must_haves_failed = [],
    gaps = [],
    summary,
  } = skillsData;

  const totalMustHaves = must_haves_passed.length + must_haves_failed.length;

  // Sort: must-haves first, failed at top
  const sortedSkills = Object.entries(skills).sort(([aName], [bName]) => {
    const aFailed = must_haves_failed.includes(aName);
    const bFailed = must_haves_failed.includes(bName);
    const aMust = must_haves_passed.includes(aName) || aFailed;
    const bMust = must_haves_passed.includes(bName) || bFailed;
    if (aFailed && !bFailed) return -1;
    if (!aFailed && bFailed) return 1;
    if (aMust && !bMust) return -1;
    if (!aMust && bMust) return 1;
    return 0;
  });

  return (
    <Card className="p-6 space-y-6">
      {/* Header: overall score + outcome */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-lg">Skills Fit</h3>
          {totalMustHaves > 0 && (
            <p className="text-sm text-muted-foreground">
              Must-haves: {must_haves_passed.length}/{totalMustHaves} passed
            </p>
          )}
        </div>
        <div className="flex items-center gap-3">
          {outcomeBadge(outcome)}
          <div className="text-right">
            <span className="text-3xl font-bold text-primary">
              {overall_score != null ? Math.round(overall_score) : "—"}
            </span>
            <span className="text-sm text-muted-foreground">/100</span>
          </div>
        </div>
      </div>

      <Progress value={overall_score ?? 0} className="h-3" />

      {/* Per-competency rows */}
      <div className="space-y-4">
        {sortedSkills.map(([name, data]) => {
          const isMust = must_haves_passed.includes(name) || must_haves_failed.includes(name);
          const isFailed = must_haves_failed.includes(name);
          const score = data.score ?? 0;
          const scorePercent = score <= 1 ? score * 100 : score;

          return (
            <div
              key={name}
              className={`p-3 rounded-lg border ${
                isFailed ? "border-red-300 bg-red-50 dark:bg-red-950/20" : "border-border"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  {isFailed ? (
                    <XCircle className="w-4 h-4 text-red-500" />
                  ) : isMust ? (
                    <CheckCircle className="w-4 h-4 text-green-500" />
                  ) : null}
                  <span className="font-medium capitalize">
                    {name.replace(/_/g, " ")}
                  </span>
                  {isMust && (
                    <Badge variant="outline" className="text-xs">
                      Must-have
                    </Badge>
                  )}
                </div>
                <span className={`font-bold ${scoreColor(score)}`}>
                  {Math.round(scorePercent)}%
                </span>
              </div>

              <Progress
                value={scorePercent}
                className={`h-2 ${progressColor(score)}`}
              />

              <div className="flex items-center justify-between mt-2 text-xs text-muted-foreground">
                <div className="flex items-center gap-2">
                  {data.years_detected != null && data.years_detected > 0 && (
                    <span>
                      {data.years_detected} yrs detected
                    </span>
                  )}
                </div>
                <div className="flex flex-wrap gap-1 justify-end">
                  {(data.matched_keywords || []).slice(0, 5).map((kw, i) => (
                    <Badge key={i} variant="secondary" className="text-xs">
                      {kw}
                    </Badge>
                  ))}
                </div>
              </div>

              {data.rationale && (
                <p className="text-xs text-muted-foreground mt-1">{data.rationale}</p>
              )}
            </div>
          );
        })}
      </div>

      {/* Gaps section */}
      {gaps.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium flex items-center gap-1">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            Gaps Identified
          </h4>
          <ul className="text-sm text-muted-foreground space-y-1">
            {gaps.map((gap, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-amber-500 mt-0.5">-</span>
                {gap}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Summary */}
      {summary && (
        <p className="text-sm text-muted-foreground border-t pt-4">{summary}</p>
      )}
    </Card>
  );
};

export default SkillsFitCard;
