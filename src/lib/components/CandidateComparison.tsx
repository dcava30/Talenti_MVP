import { X, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";

interface ScoreDimension {
  id: string;
  dimension: string;
  score: number;
  evidence?: string;
}

interface InterviewScore {
  overall_score: number | null;
  narrative_summary?: string;
}

interface Interview {
  id: string;
  status: string;
  interview_scores?: InterviewScore | InterviewScore[] | null;
  score_dimensions?: ScoreDimension[];
}

interface Application {
  id: string;
  status: string;
  created_at: string;
  interviews?: Interview[];
}

interface CandidateComparisonProps {
  selectedApplications: Application[];
  onRemoveCandidate: (applicationId: string) => void;
  onClose: () => void;
}

export const CandidateComparison = ({
  selectedApplications,
  onRemoveCandidate,
  onClose,
}: CandidateComparisonProps) => {
  // Get all unique dimensions across selected candidates
  const allDimensions = new Set<string>();
  selectedApplications.forEach((app) => {
    const interview = app.interviews?.[0];
    interview?.score_dimensions?.forEach((dim) => {
      allDimensions.add(dim.dimension);
    });
  });
  const dimensionsList = Array.from(allDimensions);

  const getDimensionScore = (application: Application, dimension: string): number | null => {
    const interview = application.interviews?.[0];
    const dim = interview?.score_dimensions?.find((d) => d.dimension === dimension);
    return dim ? Number(dim.score) : null;
  };

  const getOverallScore = (application: Application): number | null => {
    const interview = application.interviews?.[0];
    const scores = interview?.interview_scores;
    if (Array.isArray(scores)) {
      return scores[0]?.overall_score ?? null;
    }
    return scores?.overall_score ?? null;
  };

  const getHighestScoreForDimension = (dimension: string): string | null => {
    let highestScore = -1;
    let highestId: string | null = null;
    selectedApplications.forEach((app) => {
      const score = getDimensionScore(app, dimension);
      if (score !== null && score > highestScore) {
        highestScore = score;
        highestId = app.id;
      }
    });
    return highestId;
  };

  const getHighestOverallScore = (): string | null => {
    let highestScore = -1;
    let highestId: string | null = null;
    selectedApplications.forEach((app) => {
      const score = getOverallScore(app);
      if (score !== null && score > highestScore) {
        highestScore = score;
        highestId = app.id;
      }
    });
    return highestId;
  };

  const highestOverallId = getHighestOverallScore();

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold">Candidate Comparison</h2>
        <Button variant="ghost" size="sm" onClick={onClose}>
          <X className="w-4 h-4 mr-2" />
          Close Comparison
        </Button>
      </div>

      <ScrollArea className="w-full">
        <div className="min-w-max">
          {/* Header row with candidate names */}
          <div className="grid gap-4 mb-6" style={{ gridTemplateColumns: `200px repeat(${selectedApplications.length}, minmax(180px, 1fr))` }}>
            <div className="font-medium text-muted-foreground">Metric</div>
            {selectedApplications.map((app) => (
              <div key={app.id} className="relative">
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute -top-2 -right-2 h-6 w-6"
                  onClick={() => onRemoveCandidate(app.id)}
                >
                  <X className="w-3 h-3" />
                </Button>
                <div className="font-semibold text-center pr-4">
                  Candidate #{app.id.slice(0, 8)}
                </div>
                <div className="text-center">
                  <Badge variant="outline" className="text-xs">
                    {app.status}
                  </Badge>
                </div>
              </div>
            ))}
          </div>

          {/* Overall Score row */}
          <div 
            className="grid gap-4 py-4 border-t border-border items-center"
            style={{ gridTemplateColumns: `200px repeat(${selectedApplications.length}, minmax(180px, 1fr))` }}
          >
            <div className="font-medium flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-primary" />
              Overall Score
            </div>
            {selectedApplications.map((app) => {
              const score = getOverallScore(app);
              const isHighest = app.id === highestOverallId && selectedApplications.length > 1;
              return (
                <div 
                  key={app.id} 
                  className={`text-center ${isHighest ? 'bg-primary/10 rounded-lg p-2 -m-2' : ''}`}
                >
                  {score !== null ? (
                    <span className={`text-2xl font-bold ${isHighest ? 'text-primary' : ''}`}>
                      {Math.round(score)}%
                    </span>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </div>
              );
            })}
          </div>

          {/* Dimension rows */}
          {dimensionsList.map((dimension) => {
            const highestId = getHighestScoreForDimension(dimension);
            return (
              <div 
                key={dimension}
                className="grid gap-4 py-4 border-t border-border items-center"
                style={{ gridTemplateColumns: `200px repeat(${selectedApplications.length}, minmax(180px, 1fr))` }}
              >
                <div className="font-medium capitalize text-muted-foreground">
                  {dimension}
                </div>
                {selectedApplications.map((app) => {
                  const score = getDimensionScore(app, dimension);
                  const isHighest = app.id === highestId && selectedApplications.length > 1;
                  return (
                    <div key={app.id} className="space-y-1">
                      {score !== null ? (
                        <>
                          <div className={`text-center font-medium ${isHighest ? 'text-primary' : ''}`}>
                            {Math.round(score * 10)}/100
                          </div>
                          <Progress 
                            value={score * 10} 
                            className={`h-2 ${isHighest ? '[&>div]:bg-primary' : ''}`} 
                          />
                        </>
                      ) : (
                        <div className="text-center text-muted-foreground">—</div>
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })}

          {dimensionsList.length === 0 && (
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
