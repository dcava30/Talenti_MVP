import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { CheckCircle2, Mail, Loader2, TrendingUp, AlertCircle } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { triggerInterviewScoring, getInterviewScore } from "@/lib/scoring";

interface ScoreResult {
  overall_score: number;
  narrative_summary: string;
  candidate_feedback: string;
  anti_cheat_risk_level: string;
  score_dimensions: Array<{
    dimension: string;
    score: number;
  }>;
}

const InterviewComplete = () => {
  const [searchParams] = useSearchParams();
  const interviewId = searchParams.get("interview");
  
  const [scoringStatus, setScoringStatus] = useState<"idle" | "scoring" | "complete" | "error">("idle");
  const [scoreResult, setScoreResult] = useState<ScoreResult | null>(null);

  useEffect(() => {
    if (interviewId) {
      runScoring(interviewId);
    }
  }, [interviewId]);

  const runScoring = async (id: string) => {
    setScoringStatus("scoring");
    
    try {
      // First check if already scored
      const existingScore = await getInterviewScore(id);
      if (existingScore) {
        setScoreResult(existingScore as ScoreResult);
        setScoringStatus("complete");
        return;
      }

      // Trigger scoring
      const result = await triggerInterviewScoring(id);
      
      if (result) {
        // Fetch the saved scores
        const savedScore = await getInterviewScore(id);
        if (savedScore) {
          setScoreResult(savedScore as ScoreResult);
        }
        setScoringStatus("complete");
      } else {
        setScoringStatus("error");
      }
    } catch (error) {
      console.error("Scoring error:", error);
      setScoringStatus("error");
    }
  };

  const formatDimension = (dim: string) => {
    return dim.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="max-w-2xl w-full p-8">
        <div className="text-center space-y-6">
          <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-10 h-10 text-primary" />
          </div>
          
          <div>
            <h1 className="text-3xl font-bold mb-2">Thank You!</h1>
            <p className="text-lg text-muted-foreground">
              Your interview has been successfully submitted
            </p>
          </div>

          {/* Scoring Status */}
          {interviewId && scoringStatus === "scoring" && (
            <Card className="bg-accent/30 p-6">
              <div className="flex items-center justify-center gap-3">
                <Loader2 className="w-5 h-5 animate-spin text-primary" />
                <span className="text-sm">Analyzing your interview responses...</span>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Our AI is evaluating your performance across multiple dimensions
              </p>
            </Card>
          )}

          {/* Score Preview (if available) */}
          {scoreResult && scoringStatus === "complete" && (
            <Card className="bg-gradient-to-br from-primary/5 to-primary/10 p-6 space-y-4">
              <div className="flex items-center justify-center gap-3">
                <TrendingUp className="w-6 h-6 text-primary" />
                <span className="text-2xl font-bold">
                  {Math.round(scoreResult.overall_score)}%
                </span>
                <span className="text-sm text-muted-foreground">Overall Score</span>
              </div>

              {/* Dimension Scores Preview */}
              {scoreResult.score_dimensions && scoreResult.score_dimensions.length > 0 && (
                <div className="space-y-2 pt-4 border-t border-border/50">
                  <p className="text-sm font-medium mb-3">Performance Breakdown</p>
                  <div className="grid grid-cols-2 gap-2 text-left">
                    {scoreResult.score_dimensions.slice(0, 4).map((dim) => (
                      <div key={dim.dimension} className="space-y-1">
                        <div className="flex justify-between text-xs">
                          <span className="text-muted-foreground">{formatDimension(dim.dimension)}</span>
                          <span className="font-medium">{Number(dim.score).toFixed(1)}/10</span>
                        </div>
                        <Progress value={Number(dim.score) * 10} className="h-1.5" />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Candidate Feedback */}
              {scoreResult.candidate_feedback && (
                <div className="pt-4 border-t border-border/50 text-left">
                  <p className="text-sm font-medium mb-2">Feedback for You</p>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {scoreResult.candidate_feedback.slice(0, 300)}
                    {scoreResult.candidate_feedback.length > 300 && "..."}
                  </p>
                </div>
              )}
            </Card>
          )}

          {scoringStatus === "error" && (
            <Card className="bg-destructive/5 p-4">
              <div className="flex items-center justify-center gap-2 text-destructive">
                <AlertCircle className="w-5 h-5" />
                <span className="text-sm">Scoring is processing. Check back later for results.</span>
              </div>
            </Card>
          )}

          <div className="bg-accent/50 rounded-lg p-6 space-y-3 text-left">
            <h2 className="font-semibold text-lg">What happens next?</h2>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <span>Our AI will analyze your responses across multiple dimensions including skills, culture fit, and communication</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <span>The hiring team will review your results within 3-5 business days</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <span>You'll receive an email notification with next steps</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <span>Check your spam folder if you don't hear from us</span>
              </li>
            </ul>
          </div>

          <div className="flex flex-col gap-3 pt-4">
            <Button size="lg" className="w-full" asChild>
              <a href="mailto:support@talenti.ai">
                <Mail className="w-5 h-5 mr-2" />
                Contact Support
              </a>
            </Button>
            <Button size="lg" variant="outline" className="w-full" asChild>
              <Link to="/">Return to Home</Link>
            </Button>
          </div>

          <p className="text-xs text-muted-foreground">
            We appreciate your time and interest in joining our team!
          </p>
        </div>
      </Card>
    </div>
  );
};

export default InterviewComplete;
