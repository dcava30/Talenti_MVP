import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Link, useSearchParams } from "react-router-dom";
import { candidatesApi } from "@/api/candidates";
import { 
  CheckCircle2, 
  Clock, 
  MessageSquare, 
  ArrowRight,
  RotateCcw,
  Target,
  Lightbulb,
  Loader2
} from "lucide-react";

interface PracticeFeedback {
  questionsAnswered: number;
  totalDuration: number;
  strengths?: string[];
  improvements?: string[];
}

const PracticeInterviewComplete = () => {
  const [searchParams] = useSearchParams();
  const practiceId = searchParams.get("practiceId");
  const [practice, setPractice] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (practiceId) {
      loadPracticeData();
    } else {
      setIsLoading(false);
    }
  }, [practiceId]);

  const loadPracticeData = async () => {
    try {
      const data = await candidatesApi.getPracticeInterview(practiceId);
      if (data) {
        setPractice(data);
      }
    } catch (error) {
      console.error("Failed to load practice interview:", error);
    }
    setIsLoading(false);
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const feedback = practice?.feedback as PracticeFeedback | undefined;

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="max-w-2xl w-full p-8">
        <div className="text-center mb-8">
          <div className="w-20 h-20 rounded-full bg-green-500/10 flex items-center justify-center mx-auto mb-4">
            <CheckCircle2 className="w-10 h-10 text-green-500" />
          </div>
          <h1 className="text-3xl font-bold mb-2">Practice Complete!</h1>
          <p className="text-muted-foreground">
            Great job completing your practice interview. Here's how you did.
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4 mb-8">
          <Card className="p-4 text-center">
            <Clock className="w-6 h-6 text-primary mx-auto mb-2" />
            <p className="text-2xl font-bold">
              {feedback?.totalDuration ? formatDuration(feedback.totalDuration) : "N/A"}
            </p>
            <p className="text-sm text-muted-foreground">Duration</p>
          </Card>
          <Card className="p-4 text-center">
            <MessageSquare className="w-6 h-6 text-primary mx-auto mb-2" />
            <p className="text-2xl font-bold">{feedback?.questionsAnswered || 0}</p>
            <p className="text-sm text-muted-foreground">Questions Answered</p>
          </Card>
        </div>

        {/* Practice Tips */}
        <Card className="p-6 mb-8 bg-primary/5 border-primary/20">
          <h3 className="font-semibold flex items-center gap-2 mb-4">
            <Lightbulb className="w-5 h-5 text-primary" />
            Tips for Improvement
          </h3>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li className="flex items-start gap-2">
              <Target className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
              Use the STAR method (Situation, Task, Action, Result) for behavioral questions
            </li>
            <li className="flex items-start gap-2">
              <Target className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
              Keep your answers concise - aim for 1-2 minutes per response
            </li>
            <li className="flex items-start gap-2">
              <Target className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
              Prepare specific examples from your experience beforehand
            </li>
            <li className="flex items-start gap-2">
              <Target className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
              Practice speaking clearly and at a moderate pace
            </li>
          </ul>
        </Card>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-4">
          <Button asChild className="flex-1">
            <Link to="/candidate/portal">
              <ArrowRight className="w-4 h-4 mr-2" />
              Back to Portal
            </Link>
          </Button>
          <Button variant="outline" asChild className="flex-1">
            <Link to="/candidate/portal?tab=practice">
              <RotateCcw className="w-4 h-4 mr-2" />
              Try Another Practice
            </Link>
          </Button>
        </div>
      </Card>
    </div>
  );
};

export default PracticeInterviewComplete;
