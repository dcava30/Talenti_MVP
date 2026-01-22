import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { 
  X, 
  Sparkles, 
  MapPin, 
  Clock, 
  Briefcase,
  CheckCircle,
  Star
} from "lucide-react";
import type { CandidateMatch } from "@/hooks/useShortlist";

interface ShortlistViewProps {
  matches: CandidateMatch[];
  onClose: () => void;
  onSelectCandidate: (applicationId: string) => void;
}

export function ShortlistView({ matches, onClose, onSelectCandidate }: ShortlistViewProps) {
  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-green-500";
    if (score >= 60) return "text-yellow-500";
    return "text-orange-500";
  };

  const getScoreBadgeVariant = (score: number): "default" | "secondary" | "outline" => {
    if (score >= 80) return "default";
    if (score >= 60) return "secondary";
    return "outline";
  };

  return (
    <Card className="p-6 mb-6 border-primary/20 bg-gradient-to-br from-primary/5 to-background">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10">
            <Sparkles className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h3 className="text-lg font-semibold">AI-Powered Shortlist</h3>
            <p className="text-sm text-muted-foreground">
              {matches.length} candidates ranked by semantic match
            </p>
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose}>
          <X className="w-4 h-4" />
        </Button>
      </div>

      <ScrollArea className="h-[500px] pr-4">
        <div className="space-y-4">
          {matches.map((match, index) => (
            <Card 
              key={match.applicationId} 
              className="p-4 hover:bg-accent/50 transition-colors cursor-pointer"
              onClick={() => onSelectCandidate(match.applicationId)}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary/10 text-primary font-semibold text-sm">
                    {index + 1}
                  </div>
                  <div>
                    <h4 className="font-medium">
                      Candidate #{match.applicationId.slice(0, 8)}
                    </h4>
                    <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
                      {match.location !== "Not specified" && (
                        <span className="flex items-center gap-1">
                          <MapPin className="w-3 h-3" />
                          {match.location}
                        </span>
                      )}
                      {match.availability !== "Not specified" && (
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {match.availability}
                        </span>
                      )}
                      {match.workMode !== "Not specified" && (
                        <span className="flex items-center gap-1">
                          <Briefcase className="w-3 h-3" />
                          {match.workMode}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="text-right">
                  <div className={`text-2xl font-bold ${getScoreColor(match.matchScore)}`}>
                    {match.matchScore}%
                  </div>
                  <Badge variant={getScoreBadgeVariant(match.matchScore)} className="mt-1">
                    {match.matchScore >= 80 ? "Strong Match" : 
                     match.matchScore >= 60 ? "Good Match" : "Potential"}
                  </Badge>
                </div>
              </div>

              <Progress 
                value={match.matchScore} 
                className="h-2 mb-3" 
              />

              {/* Skills */}
              {match.skills.length > 0 && match.skills[0] !== "Not specified" && (
                <div className="mb-3">
                  <p className="text-xs text-muted-foreground mb-1.5">Key Skills</p>
                  <div className="flex flex-wrap gap-1.5">
                    {match.skills.slice(0, 5).map((skill, i) => (
                      <Badge key={i} variant="secondary" className="text-xs">
                        {skill}
                      </Badge>
                    ))}
                    {match.skills.length > 5 && (
                      <Badge variant="outline" className="text-xs">
                        +{match.skills.length - 5} more
                      </Badge>
                    )}
                  </div>
                </div>
              )}

              {/* Match Reasons */}
              <div className="space-y-1.5">
                <p className="text-xs text-muted-foreground">AI Match Analysis</p>
                {match.matchReasons.map((reason, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm">
                    <CheckCircle className="w-3.5 h-3.5 text-primary mt-0.5 flex-shrink-0" />
                    <span className="text-muted-foreground">{reason}</span>
                  </div>
                ))}
              </div>

              {/* Experience Preview */}
              {match.experience !== "Not specified" && match.experience !== "No experience listed" && (
                <div className="mt-3 pt-3 border-t border-border/50">
                  <p className="text-xs text-muted-foreground mb-1">Recent Experience</p>
                  <p className="text-sm line-clamp-2">{match.experience}</p>
                </div>
              )}
            </Card>
          ))}

          {matches.length === 0 && (
            <div className="text-center py-8">
              <Star className="w-12 h-12 mx-auto text-muted-foreground/30 mb-3" />
              <p className="text-muted-foreground">No candidates to rank yet</p>
            </div>
          )}
        </div>
      </ScrollArea>
    </Card>
  );
}
