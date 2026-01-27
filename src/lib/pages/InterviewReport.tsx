import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  ArrowLeft,
  FileText,
  TrendingUp,
  MessageSquare,
  AlertTriangle,
  CheckCircle,
  Clock,
  Edit2,
  Save,
  X,
  Loader2,
  Download,
  Play,
  User,
  Bot,
} from "lucide-react";
import { interviewsApi } from "@/api/interviews";
import { toast } from "sonner";
import { downloadInterviewReport } from "@/lib/generateInterviewReport";

interface InterviewData {
  id: string;
  status: string;
  started_at: string | null;
  ended_at: string | null;
  duration_seconds: number | null;
  recording_url: string | null;
  anti_cheat_signals: any;
  application: {
    id: string;
    candidate_id: string;
    job_role: {
      id: string;
      title: string;
      organisation: {
        id: string;
        name: string;
      };
    };
  };
}

interface ScoreData {
  id: string;
  overall_score: number | null;
  narrative_summary: string | null;
  candidate_feedback: string | null;
  anti_cheat_risk_level: string | null;
  human_override: boolean;
  human_override_reason: string | null;
  model_version: string | null;
  created_at: string;
}

interface DimensionData {
  id: string;
  dimension: string;
  score: number;
  weight: number | null;
  evidence: string | null;
  cited_quotes: any;
}

interface TranscriptSegment {
  id: string;
  speaker: string;
  content: string;
  start_time_ms: number;
  end_time_ms: number | null;
}

const formatTime = (ms: number): string => {
  const minutes = Math.floor(ms / 60000);
  const seconds = Math.floor((ms % 60000) / 1000);
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
};

const formatDuration = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}m ${secs}s`;
};

const formatDimension = (dim: string): string => {
  return dim
    .replace(/_/g, " ")
    .replace(/\b\w/g, (l) => l.toUpperCase());
};

const InterviewReport = () => {
  const { interviewId } = useParams();
  const [isLoading, setIsLoading] = useState(true);
  const [interview, setInterview] = useState<InterviewData | null>(null);
  const [score, setScore] = useState<ScoreData | null>(null);
  const [dimensions, setDimensions] = useState<DimensionData[]>([]);
  const [transcripts, setTranscripts] = useState<TranscriptSegment[]>([]);

  const [isEditing, setIsEditing] = useState(false);
  const [editedScore, setEditedScore] = useState<number | null>(null);
  const [overrideReason, setOverrideReason] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [showOverrideDialog, setShowOverrideDialog] = useState(false);
  const [downloadingPDF, setDownloadingPDF] = useState(false);

  useEffect(() => {
    if (interviewId) {
      loadInterviewData();
    }
  }, [interviewId]);

  const loadInterviewData = async () => {
    if (!interviewId) return;

    setIsLoading(true);

    try {
      const interviewData = await interviewsApi.getById(interviewId);

      if (interviewData) {
        setInterview(interviewData);
      }

      const scoreData = await interviewsApi.getScore(interviewId);
      if (scoreData) {
        setScore(scoreData);
        setEditedScore(scoreData.overall_score);
      }

      const dimensionData = await interviewsApi.listDimensions(interviewId);
      if (dimensionData) {
        setDimensions(dimensionData);
      }

      const transcriptData = await interviewsApi.listTranscripts(interviewId);
      if (transcriptData) {
        setTranscripts(transcriptData);
      }
    } catch (error) {
      console.error("Error loading interview data:", error);
      toast.error("Failed to load interview data");
    }

    setIsLoading(false);
  };

  const handleSaveOverride = async () => {
    if (!score || editedScore === null) return;

    setIsSaving(true);

    try {
      await interviewsApi.updateScore(score.id, {
        overall_score: editedScore,
        human_override: true,
        human_override_reason: overrideReason,
      });

      setScore({
        ...score,
        overall_score: editedScore,
        human_override: true,
        human_override_reason: overrideReason,
      });

      setIsEditing(false);
      setShowOverrideDialog(false);
      toast.success("Score updated successfully");
    } catch (error) {
      console.error("Error saving override:", error);
      toast.error("Failed to save score override");
    }

    setIsSaving(false);
  };

  const handleDownloadPDF = async () => {
    if (!interview) return;

    setDownloadingPDF(true);
    try {
      const success = await downloadInterviewReport(
        interview.id,
        interview.application.job_role.title,
        interview.application.job_role.organisation.name
      );
      if (success) {
        toast.success("PDF report downloaded");
      } else {
        toast.error("Failed to generate PDF");
      }
    } catch (error) {
      toast.error("Error generating PDF");
    }
    setDownloadingPDF(false);
  };

  const getRiskBadge = (level: string | null) => {
    if (!level) return null;
    const variants: Record<string, { variant: "default" | "secondary" | "destructive"; icon: any }> = {
      low: { variant: "secondary", icon: CheckCircle },
      medium: { variant: "default", icon: AlertTriangle },
      high: { variant: "destructive", icon: AlertTriangle },
    };
    const config = variants[level] || variants.low;
    const Icon = config.icon;
    return (
      <Badge variant={config.variant} className="gap-1">
        <Icon className="w-3 h-3" />
        {level.charAt(0).toUpperCase() + level.slice(1)} Risk
      </Badge>
    );
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!interview) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Card className="p-8 max-w-md text-center">
          <h2 className="text-xl font-semibold mb-4">Interview Not Found</h2>
          <p className="text-muted-foreground mb-6">
            This interview doesn't exist or you don't have access to it.
          </p>
          <Button asChild>
            <Link to="/org">Back to Dashboard</Link>
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border/40 bg-card/30 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" asChild>
              <Link to={`/org/roles/${interview.application.job_role.id}`}>
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Role
              </Link>
            </Button>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownloadPDF}
              disabled={downloadingPDF}
            >
              {downloadingPDF ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Download className="w-4 h-4 mr-2" />
              )}
              Download PDF
            </Button>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        {/* Interview Header */}
        <div className="mb-8">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold mb-2">Interview Report</h1>
              <div className="flex items-center gap-3 text-muted-foreground">
                <span>{interview.application.job_role.title}</span>
                <span>•</span>
                <span>{interview.application.job_role.organisation.name}</span>
                <span>•</span>
                <span>Candidate #{interview.application.candidate_id.slice(0, 8)}</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="secondary">
                {interview.status.charAt(0).toUpperCase() + interview.status.slice(1)}
              </Badge>
              {score && getRiskBadge(score.anti_cheat_risk_level)}
            </div>
          </div>

          {/* Interview Meta */}
          <div className="flex gap-6 text-sm text-muted-foreground">
            {interview.started_at && (
              <div className="flex items-center gap-1">
                <Clock className="w-4 h-4" />
                {new Date(interview.started_at).toLocaleDateString()}
              </div>
            )}
            {interview.duration_seconds && (
              <div className="flex items-center gap-1">
                <Clock className="w-4 h-4" />
                Duration: {formatDuration(interview.duration_seconds)}
              </div>
            )}
            {interview.recording_url && (
              <Button variant="link" size="sm" className="h-auto p-0" asChild>
                <a href={interview.recording_url} target="_blank" rel="noopener noreferrer">
                  <Play className="w-4 h-4 mr-1" />
                  View Recording
                </a>
              </Button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            <Tabs defaultValue="summary" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="summary">Summary</TabsTrigger>
                <TabsTrigger value="dimensions">Score Details</TabsTrigger>
                <TabsTrigger value="transcript">Transcript</TabsTrigger>
              </TabsList>

              <TabsContent value="summary" className="space-y-6 mt-6">
                {score?.narrative_summary && (
                  <Card className="p-6">
                    <h3 className="font-semibold mb-4 flex items-center gap-2">
                      <FileText className="w-5 h-5" />
                      AI Summary
                    </h3>
                    <p className="text-muted-foreground leading-relaxed whitespace-pre-wrap">
                      {score.narrative_summary}
                    </p>
                  </Card>
                )}

                {score?.candidate_feedback && (
                  <Card className="p-6">
                    <h3 className="font-semibold mb-4 flex items-center gap-2">
                      <MessageSquare className="w-5 h-5" />
                      Candidate Feedback
                    </h3>
                    <p className="text-muted-foreground leading-relaxed whitespace-pre-wrap">
                      {score.candidate_feedback}
                    </p>
                  </Card>
                )}

                {score?.human_override && (
                  <Card className="p-6 border-primary/50 bg-primary/5">
                    <h3 className="font-semibold mb-2 flex items-center gap-2">
                      <Edit2 className="w-5 h-5" />
                      Human Override Applied
                    </h3>
                    <p className="text-muted-foreground">
                      {score.human_override_reason || "No reason provided"}
                    </p>
                  </Card>
                )}
              </TabsContent>

              <TabsContent value="dimensions" className="mt-6">
                <Card className="p-6">
                  <h3 className="font-semibold mb-6">Score Breakdown by Dimension</h3>
                  <div className="space-y-6">
                    {dimensions.map((dim) => (
                      <div key={dim.id} className="space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="font-medium">{formatDimension(dim.dimension)}</span>
                          <span className="text-lg font-bold text-primary">
                            {Math.round(Number(dim.score) * 10)}/100
                          </span>
                        </div>
                        <Progress value={Number(dim.score) * 10} className="h-3" />
                        {dim.evidence && (
                          <p className="text-sm text-muted-foreground">{dim.evidence}</p>
                        )}
                        {dim.cited_quotes && Array.isArray(dim.cited_quotes) && dim.cited_quotes.length > 0 && (
                          <div className="mt-2 space-y-2">
                            <p className="text-xs font-medium text-muted-foreground">Supporting Quotes:</p>
                            {dim.cited_quotes.map((quote: string, idx: number) => (
                              <blockquote
                                key={idx}
                                className="border-l-2 border-primary/50 pl-3 text-sm italic text-muted-foreground"
                              >
                                "{quote}"
                              </blockquote>
                            ))}
                          </div>
                        )}
                        <Separator />
                      </div>
                    ))}

                    {dimensions.length === 0 && (
                      <p className="text-center text-muted-foreground py-8">
                        No dimension scores available
                      </p>
                    )}
                  </div>
                </Card>
              </TabsContent>

              <TabsContent value="transcript" className="mt-6">
                <Card className="p-6">
                  <h3 className="font-semibold mb-6">Interview Transcript</h3>
                  <ScrollArea className="h-[600px] pr-4">
                    <div className="space-y-4">
                      {transcripts.map((segment) => {
                        const isAI = segment.speaker.toLowerCase() === "ai" || 
                                    segment.speaker.toLowerCase() === "interviewer";
                        return (
                          <div
                            key={segment.id}
                            className={`flex gap-3 ${isAI ? "" : "flex-row-reverse"}`}
                          >
                            <div
                              className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                                isAI ? "bg-primary text-primary-foreground" : "bg-secondary"
                              }`}
                            >
                              {isAI ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
                            </div>
                            <div
                              className={`flex-1 max-w-[80%] ${
                                isAI ? "" : "text-right"
                              }`}
                            >
                              <div className="flex items-center gap-2 mb-1">
                                <span className="text-xs font-medium">
                                  {isAI ? "AI Interviewer" : "Candidate"}
                                </span>
                                <span className="text-xs text-muted-foreground">
                                  {formatTime(segment.start_time_ms)}
                                </span>
                              </div>
                              <div
                                className={`p-3 rounded-lg ${
                                  isAI
                                    ? "bg-primary/10 text-foreground"
                                    : "bg-secondary text-foreground"
                                }`}
                              >
                                <p className="text-sm">{segment.content}</p>
                              </div>
                            </div>
                          </div>
                        );
                      })}

                      {transcripts.length === 0 && (
                        <p className="text-center text-muted-foreground py-8">
                          No transcript available
                        </p>
                      )}
                    </div>
                  </ScrollArea>
                </Card>
              </TabsContent>
            </Tabs>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Overall Score Card */}
            <Card className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold flex items-center gap-2">
                  <TrendingUp className="w-5 h-5" />
                  Overall Score
                </h3>
                {score && !isEditing && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsEditing(true)}
                  >
                    <Edit2 className="w-4 h-4" />
                  </Button>
                )}
              </div>

              {score ? (
                <div className="text-center">
                  {isEditing ? (
                    <div className="space-y-4">
                      <Input
                        type="number"
                        min="0"
                        max="100"
                        value={editedScore ?? ""}
                        onChange={(e) => setEditedScore(Number(e.target.value))}
                        className="text-center text-2xl font-bold"
                      />
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className="flex-1"
                          onClick={() => {
                            setIsEditing(false);
                            setEditedScore(score.overall_score);
                          }}
                        >
                          <X className="w-4 h-4 mr-1" />
                          Cancel
                        </Button>
                        <Button
                          size="sm"
                          className="flex-1"
                          onClick={() => setShowOverrideDialog(true)}
                        >
                          <Save className="w-4 h-4 mr-1" />
                          Save
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="text-5xl font-bold text-primary mb-2">
                        {score.overall_score !== null
                          ? `${Math.round(score.overall_score)}%`
                          : "N/A"}
                      </div>
                      <p className="text-sm text-muted-foreground">Overall Match</p>
                      {score.human_override && (
                        <Badge variant="outline" className="mt-2">
                          Human Override
                        </Badge>
                      )}
                    </>
                  )}
                </div>
              ) : (
                <p className="text-center text-muted-foreground">
                  Score not available
                </p>
              )}

              {score?.model_version && (
                <p className="text-xs text-muted-foreground text-center mt-4">
                  Scored by: {score.model_version}
                </p>
              )}
            </Card>

            {/* Quick Dimensions */}
            <Card className="p-6">
              <h3 className="font-semibold mb-4">Dimension Scores</h3>
              <div className="space-y-3">
                {dimensions.slice(0, 5).map((dim) => (
                  <div key={dim.id} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground truncate">
                        {formatDimension(dim.dimension)}
                      </span>
                      <span className="font-medium">
                        {Math.round(Number(dim.score) * 10)}
                      </span>
                    </div>
                    <Progress value={Number(dim.score) * 10} className="h-2" />
                  </div>
                ))}
              </div>
            </Card>

            {/* Anti-Cheat Info */}
            {score?.anti_cheat_risk_level && (
              <Card className="p-6">
                <h3 className="font-semibold mb-4 flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5" />
                  Integrity Check
                </h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Risk Level</span>
                    {getRiskBadge(score.anti_cheat_risk_level)}
                  </div>
                  {interview.anti_cheat_signals &&
                    Array.isArray(interview.anti_cheat_signals) &&
                    interview.anti_cheat_signals.length > 0 && (
                      <div className="mt-2">
                        <p className="text-sm text-muted-foreground mb-2">Signals:</p>
                        <ul className="text-sm space-y-1">
                          {interview.anti_cheat_signals.map((signal: any, idx: number) => (
                            <li key={idx} className="text-muted-foreground">
                              • {typeof signal === "string" ? signal : JSON.stringify(signal)}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                </div>
              </Card>
            )}
          </div>
        </div>
      </div>

      {/* Override Reason Dialog */}
      <Dialog open={showOverrideDialog} onOpenChange={setShowOverrideDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Override Score</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>New Score</Label>
              <p className="text-2xl font-bold text-primary">{editedScore}%</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="reason">Reason for Override</Label>
              <Textarea
                id="reason"
                placeholder="Explain why you're overriding the AI score..."
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                rows={4}
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowOverrideDialog(false)}
              disabled={isSaving}
            >
              Cancel
            </Button>
            <Button onClick={handleSaveOverride} disabled={isSaving}>
              {isSaving ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Save className="w-4 h-4 mr-2" />
              )}
              Confirm Override
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default InterviewReport;
