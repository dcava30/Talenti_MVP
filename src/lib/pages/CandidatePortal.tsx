import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Link, useNavigate } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";
import { useToast } from "@/hooks/use-toast";
import {
  useCandidateProfile,
  useCandidateApplications,
  useCandidateInvitations,
  useCandidateInterviewFeedback,
  calculateProfileCompletion,
} from "@/hooks/useCandidateData";
import {
  User,
  Video,
  MessageSquare,
  Bell,
  Settings,
  LogOut,
  ChevronRight,
  Clock,
  Briefcase,
  Loader2,
  CheckCircle2,
  TrendingUp,
  Shield,
} from "lucide-react";
import { DataRetentionSettings } from "@/components/DataRetentionSettings";
import { formatDistanceToNow, format } from "date-fns";

const CandidatePortal = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const { data: profile, isLoading: profileLoading } = useCandidateProfile();
  const { data: applications, isLoading: applicationsLoading } = useCandidateApplications();
  const { data: invitations } = useCandidateInvitations();
  const { data: feedbackData, isLoading: feedbackLoading } = useCandidateInterviewFeedback();

  const profileCompletion = calculateProfileCompletion(profile);
  const isLoading = profileLoading || applicationsLoading;

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    navigate("/");
  };

  // Check auth
  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (!user) {
        navigate("/auth?type=candidate");
      }
    });
  }, [navigate]);

  const getStatusBadge = (status: string) => {
    const statusMap: Record<string, { label: string; className: string }> = {
      applied: { label: "Applied", className: "bg-blue-500/10 text-blue-500 border-blue-500/20" },
      invited: { label: "Interview Pending", className: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20" },
      interviewing: { label: "In Progress", className: "bg-purple-500/10 text-purple-500 border-purple-500/20" },
      scoring: { label: "Scoring", className: "bg-orange-500/10 text-orange-500 border-orange-500/20" },
      reviewed: { label: "Reviewed", className: "bg-green-500/10 text-green-500 border-green-500/20" },
      shortlisted: { label: "Shortlisted", className: "bg-primary/10 text-primary border-primary/20" },
      rejected: { label: "Not Selected", className: "bg-muted text-muted-foreground" },
      hired: { label: "Hired", className: "bg-green-600/10 text-green-600 border-green-600/20" },
    };
    
    const config = statusMap[status] || { label: status, className: "" };
    return <Badge className={config.className}>{config.label}</Badge>;
  };

  const getInterviewLink = (application: any) => {
    // Check for pending invitation
    const invitation = invitations?.find(
      (inv: any) => inv.application_id === application.id
    );
    if (invitation) {
      return `/invite/${invitation.token}`;
    }
    
    // Check for in-progress interview
    const interview = application.interviews?.[0];
    if (interview && interview.status === "in_progress") {
      return `/candidate/${invitation?.id || interview.id}/lobby`;
    }
    
    return null;
  };

  const practiceInterviews = [
    { id: "practice-1", title: "Software Engineer Interview", duration: "15 min", difficulty: "Medium" },
    { id: "practice-2", title: "Technical Problem Solving", duration: "10 min", difficulty: "Hard" },
    { id: "practice-3", title: "Behavioral Questions", duration: "12 min", difficulty: "Easy" },
  ];

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border/40 bg-card/30 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold">T</span>
            </div>
            <span className="text-xl font-bold">Talenti</span>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon">
              <Bell className="w-5 h-5" />
            </Button>
            <Button variant="ghost" size="icon">
              <Settings className="w-5 h-5" />
            </Button>
            <Button variant="ghost" size="sm" onClick={handleSignOut}>
              <LogOut className="w-4 h-4 mr-2" />
              Sign Out
            </Button>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        {/* Welcome & Profile Completion */}
        <div className="grid lg:grid-cols-3 gap-6 mb-8">
          <Card className="lg:col-span-2 p-6">
            <h1 className="text-2xl font-bold mb-2">
              Welcome back{profile?.first_name ? `, ${profile.first_name}` : ""}!
            </h1>
            <p className="text-muted-foreground mb-6">
              Manage your profile, complete interviews, and track your applications.
            </p>
            
            <div className="flex flex-wrap gap-4">
              <Button asChild>
                <Link to="/candidate/profile">
                  <User className="w-4 h-4 mr-2" />
                  Edit Profile
                </Link>
              </Button>
              <Button variant="outline" asChild>
                <Link to="/candidate/practice?role=software-engineer">
                  <Video className="w-4 h-4 mr-2" />
                  Practice Interview
                </Link>
              </Button>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold">Profile Completion</h3>
              <span className="text-2xl font-bold text-primary">{profileCompletion}%</span>
            </div>
            <Progress value={profileCompletion} className="h-2 mb-4" />
            <p className="text-sm text-muted-foreground mb-4">
              {profileCompletion < 100 
                ? "Complete your profile to increase visibility to employers"
                : "Your profile is complete!"
              }
            </p>
            <Button variant="outline" size="sm" className="w-full" asChild>
              <Link to="/candidate/profile">
                {profileCompletion < 100 ? "Complete Profile" : "View Profile"}
                <ChevronRight className="w-4 h-4 ml-2" />
              </Link>
            </Button>
          </Card>
        </div>

        {/* Main Content Tabs */}
        <Tabs defaultValue="applications" className="space-y-6">
          <TabsList>
            <TabsTrigger value="applications" className="flex items-center gap-2">
              <Briefcase className="w-4 h-4" />
              Applications ({applications?.length || 0})
            </TabsTrigger>
            <TabsTrigger value="practice" className="flex items-center gap-2">
              <Video className="w-4 h-4" />
              Practice
            </TabsTrigger>
            <TabsTrigger value="feedback" className="flex items-center gap-2">
              <MessageSquare className="w-4 h-4" />
              Feedback
            </TabsTrigger>
            <TabsTrigger value="privacy" className="flex items-center gap-2">
              <Shield className="w-4 h-4" />
              Privacy
            </TabsTrigger>
          </TabsList>

          <TabsContent value="applications">
            <Card className="p-6">
              <h2 className="text-xl font-semibold mb-6">Your Applications</h2>
              
              {!applications || applications.length === 0 ? (
                <div className="text-center py-12">
                  <Briefcase className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="font-semibold mb-2">No applications yet</h3>
                  <p className="text-muted-foreground mb-4">
                    When employers invite you to interview, they'll appear here.
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {applications.map((app: any) => {
                    const jobRole = app.job_roles;
                    const org = jobRole?.organisations;
                    const interview = app.interviews?.[0];
                    const interviewLink = getInterviewLink(app);
                    const score = interview?.interview_scores?.[0];

                    return (
                      <div
                        key={app.id}
                        className="flex items-center justify-between p-4 rounded-lg border border-border hover:bg-accent/50 transition-colors"
                      >
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <h3 className="font-semibold">{jobRole?.title || "Unknown Role"}</h3>
                            {getStatusBadge(app.status)}
                          </div>
                          <div className="flex items-center gap-4 text-sm text-muted-foreground">
                            <span>{org?.name || "Unknown Company"}</span>
                            <span>•</span>
                            <span>Applied {formatDistanceToNow(new Date(app.created_at), { addSuffix: true })}</span>
                            {score?.overall_score && (
                              <>
                                <span>•</span>
                                <span className="flex items-center gap-1 text-primary">
                                  <TrendingUp className="w-3 h-3" />
                                  Score: {Math.round(score.overall_score)}%
                                </span>
                              </>
                            )}
                          </div>
                        </div>
                        
                        {interviewLink && app.status === "invited" && (
                          <Button asChild>
                            <Link to={interviewLink}>
                              Start Interview
                              <ChevronRight className="w-4 h-4 ml-2" />
                            </Link>
                          </Button>
                        )}
                        
                        {app.status === "reviewed" && score && (
                          <Button variant="outline" asChild>
                            <Link to={`/candidate/complete?interviewId=${interview?.id}`}>
                              View Results
                              <ChevronRight className="w-4 h-4 ml-2" />
                            </Link>
                          </Button>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </Card>
          </TabsContent>

          <TabsContent value="practice">
            <Card className="p-6">
              <h2 className="text-xl font-semibold mb-2">Practice Interviews</h2>
              <p className="text-muted-foreground mb-6">
                Prepare for your real interviews with AI-powered practice sessions.
              </p>

              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {practiceInterviews.map((interview) => (
                  <Card key={interview.id} className="p-4 hover:shadow-lg transition-shadow">
                    <div className="flex items-start justify-between mb-3">
                      <Video className="w-8 h-8 text-primary" />
                      <Badge variant="outline">{interview.difficulty}</Badge>
                    </div>
                    <h3 className="font-semibold mb-1">{interview.title}</h3>
                    <p className="text-sm text-muted-foreground mb-4">
                      Duration: {interview.duration}
                    </p>
                    <Button variant="outline" size="sm" className="w-full" asChild>
                      <Link to={`/candidate/practice?role=${interview.id.replace('practice-', '')}`}>
                        Start Practice
                      </Link>
                    </Button>
                  </Card>
                ))}
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="feedback">
            <Card className="p-6">
              <h2 className="text-xl font-semibold mb-2">Interview Feedback</h2>
              <p className="text-muted-foreground mb-6">
                View feedback from your completed interviews.
              </p>

              {feedbackLoading ? (
                <div className="flex justify-center py-12">
                  <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                </div>
              ) : !feedbackData || feedbackData.length === 0 ? (
                <div className="text-center py-12">
                  <MessageSquare className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="font-semibold mb-2">No feedback yet</h3>
                  <p className="text-muted-foreground">
                    Complete an interview to receive AI-generated feedback.
                  </p>
                </div>
              ) : (
                <div className="space-y-6">
                  {feedbackData.map((item: any) => {
                    const interview = item.interviews?.[0];
                    const score = interview?.interview_scores?.[0];
                    const dimensions = interview?.score_dimensions || [];
                    
                    if (!score) return null;

                    return (
                      <Card key={item.id} className="p-6 border-primary/20">
                        <div className="flex items-start justify-between mb-4">
                          <div>
                            <h3 className="font-semibold text-lg">{item.job_roles?.title}</h3>
                            <p className="text-sm text-muted-foreground">
                              {item.job_roles?.organisations?.name}
                            </p>
                          </div>
                          <div className="text-right">
                            <div className="flex items-center gap-2">
                              <TrendingUp className="w-5 h-5 text-primary" />
                              <span className="text-2xl font-bold text-primary">
                                {Math.round(score.overall_score)}%
                              </span>
                            </div>
                            <p className="text-xs text-muted-foreground">
                              {interview.ended_at && format(new Date(interview.ended_at), "MMM d, yyyy")}
                            </p>
                          </div>
                        </div>

                        {score.candidate_feedback && (
                          <div className="mb-4 p-4 rounded-lg bg-accent/50">
                            <h4 className="font-medium mb-2 flex items-center gap-2">
                              <CheckCircle2 className="w-4 h-4 text-primary" />
                              Feedback for You
                            </h4>
                            <p className="text-sm text-muted-foreground">{score.candidate_feedback}</p>
                          </div>
                        )}

                        {dimensions.length > 0 && (
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                            {dimensions.slice(0, 4).map((dim: any) => (
                              <div key={dim.dimension} className="text-center p-3 rounded-lg bg-muted/50">
                                <p className="text-sm text-muted-foreground capitalize mb-1">
                                  {dim.dimension.replace(/_/g, " ")}
                                </p>
                                <p className="text-lg font-semibold">
                                  {Math.round(Number(dim.score) * 10)}/100
                                </p>
                              </div>
                            ))}
                          </div>
                        )}
                      </Card>
                    );
                  })}
                </div>
              )}
            </Card>
          </TabsContent>

          <TabsContent value="privacy">
            <DataRetentionSettings />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default CandidatePortal;
