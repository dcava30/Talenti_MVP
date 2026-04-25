import { X, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";
import { isTdsRankingAndShortlistQuarantineEnabled } from "@/lib/tdsRankingQuarantine";

export const CandidateComparison = ({
  selectedApplications,
  onRemoveCandidate,
  onClose,
  quarantineEnabled = isTdsRankingAndShortlistQuarantineEnabled(),
}) => {
  const allDimensions = new Set();
  selectedApplications.forEach((application) => {
    const interview = application.interviews?.[0];
    interview?.score_dimensions?.forEach((dimension) => {
      allDimensions.add(dimension.dimension);
    });
  });
  const dimensionsList = Array.from(allDimensions);

  const allSkills = new Set();
  selectedApplications.forEach((application) => {
    const interview = application.interviews?.[0];
    const service2 = interview?.interview_scores?.[0]?.service2_raw;
    if (service2?.scores) {
      Object.keys(service2.scores).forEach((skill) => allSkills.add(skill));
    }
  });
  const skillsList = Array.from(allSkills);

  const getSkillsScore = (application) => {
    const interview = application.interviews?.[0];
    const service2 = interview?.interview_scores?.[0]?.service2_raw;
    return service2?.overall_score ?? null;
  };

  const getSkillsOutcome = (application) => {
    const interview = application.interviews?.[0];
    const service2 = interview?.interview_scores?.[0]?.service2_raw;
    return service2?.outcome ?? null;
  };

  const getSkillCompetencyScore = (application, skill) => {
    const interview = application.interviews?.[0];
    const service2 = interview?.interview_scores?.[0]?.service2_raw;
    const data = service2?.scores?.[skill];
    if (!data) {
      return null;
    }

    const score = data.score ?? 0;
    return score <= 1 ? score * 100 : score;
  };

  const getDimensionScore = (application, dimension) => {
    const interview = application.interviews?.[0];
    const item = interview?.score_dimensions?.find((scoreDimension) => scoreDimension.dimension === dimension);
    return item ? Number(item.score) : null;
  };

  const getOverallScore = (application) => {
    const interview = application.interviews?.[0];
    const scores = interview?.interview_scores;
    if (Array.isArray(scores)) {
      return scores[0]?.overall_score ?? null;
    }
    return scores?.overall_score ?? null;
  };

  const highlightScores = !quarantineEnabled && selectedApplications.length > 1;

  const getHighestSkillScore = () => {
    let highest = -1;
    let id = null;
    selectedApplications.forEach((application) => {
      const score = getSkillsScore(application);
      if (score !== null && score > highest) {
        highest = score;
        id = application.id;
      }
    });
    return id;
  };

  const getHighestCompetencyScore = (skill) => {
    let highest = -1;
    let id = null;
    selectedApplications.forEach((application) => {
      const score = getSkillCompetencyScore(application, skill);
      if (score !== null && score > highest) {
        highest = score;
        id = application.id;
      }
    });
    return id;
  };

  const getHighestScoreForDimension = (dimension) => {
    let highest = -1;
    let id = null;
    selectedApplications.forEach((application) => {
      const score = getDimensionScore(application, dimension);
      if (score !== null && score > highest) {
        highest = score;
        id = application.id;
      }
    });
    return id;
  };

  const getHighestOverallScore = () => {
    let highest = -1;
    let id = null;
    selectedApplications.forEach((application) => {
      const score = getOverallScore(application);
      if (score !== null && score > highest) {
        highest = score;
        id = application.id;
      }
    });
    return id;
  };

  const highestSkillsId = highlightScores ? getHighestSkillScore() : null;
  const highestOverallId = highlightScores ? getHighestOverallScore() : null;

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6 gap-4">
        <div>
          <h2 className="text-xl font-semibold">
            {quarantineEnabled ? "Candidate Evidence Review" : "Candidate Comparison"}
          </h2>
          {quarantineEnabled && (
            <p className="text-sm text-muted-foreground mt-1">
              Decision evidence only. Candidates are evaluated against role and environment requirements, not against each other.
            </p>
          )}
        </div>
        <Button variant="ghost" size="sm" onClick={onClose}>
          <X className="w-4 h-4 mr-2" />
          {quarantineEnabled ? "Close Evidence Review" : "Close Comparison"}
        </Button>
      </div>

      <ScrollArea className="w-full">
        <div className="min-w-max">
          <div
            className="grid gap-4 mb-6"
            style={{ gridTemplateColumns: `200px repeat(${selectedApplications.length}, minmax(180px, 1fr))` }}
          >
            <div className="font-medium text-muted-foreground">Metric</div>
            {selectedApplications.map((application) => (
              <div key={application.id} className="relative">
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute -top-2 -right-2 h-6 w-6"
                  onClick={() => onRemoveCandidate(application.id)}
                >
                  <X className="w-3 h-3" />
                </Button>
                <div className="font-semibold text-center pr-4">
                  Candidate #{application.id.slice(0, 8)}
                </div>
                <div className="text-center">
                  <Badge variant="outline" className="text-xs">
                    {application.status}
                  </Badge>
                </div>
              </div>
            ))}
          </div>

          {!quarantineEnabled && (
            <div
              className="grid gap-4 py-4 border-t border-border items-center"
              style={{ gridTemplateColumns: `200px repeat(${selectedApplications.length}, minmax(180px, 1fr))` }}
            >
              <div className="font-medium flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-primary" />
                Overall Score
              </div>
              {selectedApplications.map((application) => {
                const score = getOverallScore(application);
                const isHighest = application.id === highestOverallId && highlightScores;
                return (
                  <div
                    key={application.id}
                    className={`text-center ${isHighest ? "bg-primary/10 rounded-lg p-2 -m-2" : ""}`}
                  >
                    {score !== null ? (
                      <span className={`text-2xl font-bold ${isHighest ? "text-primary" : ""}`}>
                        {Math.round(score)}%
                      </span>
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {dimensionsList.map((dimension) => {
            const highestId = highlightScores ? getHighestScoreForDimension(dimension) : null;
            return (
              <div
                key={dimension}
                className="grid gap-4 py-4 border-t border-border items-center"
                style={{ gridTemplateColumns: `200px repeat(${selectedApplications.length}, minmax(180px, 1fr))` }}
              >
                <div className="font-medium capitalize text-muted-foreground">{dimension}</div>
                {selectedApplications.map((application) => {
                  const score = getDimensionScore(application, dimension);
                  const isHighest = application.id === highestId && highlightScores;
                  return (
                    <div key={application.id} className="space-y-1">
                      {score !== null ? (
                        <>
                          <div className={`text-center font-medium ${isHighest ? "text-primary" : ""}`}>
                            {Math.round(score * 10)}/100
                          </div>
                          <Progress value={score * 10} className={`h-2 ${isHighest ? "[&>div]:bg-primary" : ""}`} />
                        </>
                      ) : (
                        <div className="text-center text-muted-foreground">-</div>
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })}

          {skillsList.length > 0 && (
            <>
              {!quarantineEnabled && (
                <div
                  className="grid gap-4 py-4 border-t-2 border-primary/20 items-center"
                  style={{ gridTemplateColumns: `200px repeat(${selectedApplications.length}, minmax(180px, 1fr))` }}
                >
                  <div className="font-medium flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-primary" />
                    Skills Fit
                  </div>
                  {selectedApplications.map((application) => {
                    const score = getSkillsScore(application);
                    const outcome = getSkillsOutcome(application);
                    const isHighest = application.id === highestSkillsId && highlightScores;
                    return (
                      <div
                        key={application.id}
                        className={`text-center ${isHighest ? "bg-primary/10 rounded-lg p-2 -m-2" : ""}`}
                      >
                        {score !== null ? (
                          <>
                            <span className={`text-xl font-bold ${isHighest ? "text-primary" : ""}`}>
                              {Math.round(score)}%
                            </span>
                            {outcome && (
                              <Badge
                                variant={
                                  outcome.toUpperCase() === "PASS"
                                    ? "default"
                                    : outcome.toUpperCase() === "FAIL"
                                      ? "destructive"
                                      : "secondary"
                                }
                                className="ml-2 text-xs"
                              >
                                {outcome}
                              </Badge>
                            )}
                          </>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {skillsList.map((skill) => {
                const highestId = highlightScores ? getHighestCompetencyScore(skill) : null;
                return (
                  <div
                    key={skill}
                    className="grid gap-4 py-4 border-t border-border items-center"
                    style={{ gridTemplateColumns: `200px repeat(${selectedApplications.length}, minmax(180px, 1fr))` }}
                  >
                    <div className="font-medium capitalize text-muted-foreground pl-4">
                      {skill.replace(/_/g, " ")}
                    </div>
                    {selectedApplications.map((application) => {
                      const score = getSkillCompetencyScore(application, skill);
                      const isHighest = application.id === highestId && highlightScores;
                      return (
                        <div key={application.id} className="space-y-1">
                          {score !== null ? (
                            <>
                              <div className={`text-center font-medium ${isHighest ? "text-primary" : ""}`}>
                                {Math.round(score)}/100
                              </div>
                              <Progress value={score} className={`h-2 ${isHighest ? "[&>div]:bg-primary" : ""}`} />
                            </>
                          ) : (
                            <div className="text-center text-muted-foreground">-</div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                );
              })}
            </>
          )}

          {dimensionsList.length === 0 && skillsList.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              No scoring data available for comparison. Select candidates with completed interviews.
            </div>
          )}
        </div>
        <ScrollBar orientation="horizontal" />
      </ScrollArea>
    </Card>
  );
};
