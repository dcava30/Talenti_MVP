import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Upload, Send, Download, TrendingUp, Loader2, Users, FileText, Sliders, GitCompare, Sparkles } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { Checkbox } from "@/components/ui/checkbox";
import { useJobRole, useRoleApplications } from "@/hooks/useOrgData";
import { useCurrentOrg } from "@/hooks/useOrgData";
import { formatDistanceToNow } from "date-fns";
import { SendInvitationDialog } from "@/components/SendInvitationDialog";
import { CandidateComparison } from "@/components/CandidateComparison";
import { ShortlistView } from "@/components/ShortlistView";
import { useShortlist } from "@/hooks/useShortlist";
import { useQueryClient } from "@tanstack/react-query";
import { downloadInterviewReport } from "@/lib/generateInterviewReport";
import { toast } from "sonner";
const RoleDetails = () => {
    const { roleId } = useParams();
    const { data: role, isLoading: roleLoading } = useJobRole(roleId);
    const { data: applications, isLoading: applicationsLoading } = useRoleApplications(roleId);
    const { data: orgData } = useCurrentOrg();
    const queryClient = useQueryClient();
    const [invitationDialogOpen, setInvitationDialogOpen] = useState(false);
    const [selectedApplicationId, setSelectedApplicationId] = useState(null);
    const [downloadingPDF, setDownloadingPDF] = useState(null);
    const [selectedForComparison, setSelectedForComparison] = useState([]);
    const [showComparison, setShowComparison] = useState(false);
    const [showShortlist, setShowShortlist] = useState(false);
    const { generateShortlist, isGenerating, shortlistData, clearShortlist } = useShortlist();
    const toggleCandidateSelection = (applicationId) => {
        setSelectedForComparison((prev) => prev.includes(applicationId)
            ? prev.filter((id) => id !== applicationId)
            : [...prev, applicationId]);
    };
    const selectedApplicationsForComparison = applications?.filter((app) => selectedForComparison.includes(app.id)) || [];
    const handleGenerateShortlist = async () => {
        if (!roleId)
            return;
        const result = await generateShortlist(roleId);
        if (result) {
            setShowShortlist(true);
            // Refresh applications to get updated match scores
            queryClient.invalidateQueries({ queryKey: ["role-applications", roleId] });
        }
    };
    const handleDownloadPDF = async (interviewId) => {
        if (!role || !orgData?.organisation)
            return;
        setDownloadingPDF(interviewId);
        try {
            const success = await downloadInterviewReport(interviewId, role.title, orgData.organisation.name);
            if (success) {
                toast.success("PDF report downloaded successfully");
            }
            else {
                toast.error("Failed to generate PDF report");
            }
        }
        catch (error) {
            toast.error("Error generating PDF report");
        }
        finally {
            setDownloadingPDF(null);
        }
    };
    const isLoading = roleLoading || applicationsLoading;
    const getStatusBadge = (status) => {
        const variants = {
            interviewed: { label: "Completed", variant: "default" },
            scoring: { label: "Scoring", variant: "default" },
            reviewed: { label: "Reviewed", variant: "default" },
            invited: { label: "Invited", variant: "outline" },
            applied: { label: "Applied", variant: "secondary" },
            shortlisted: { label: "Shortlisted", variant: "secondary" },
            rejected: { label: "Rejected", variant: "outline" },
            hired: { label: "Hired", variant: "default" },
        };
        const { label, variant } = variants[status] || { label: status, variant: "secondary" };
        return <Badge variant={variant}>{label}</Badge>;
    };
    // Sort applications by match score if available
    const sortedApplications = applications?.slice().sort((a, b) => {
        const scoreA = a.match_score ?? 0;
        const scoreB = b.match_score ?? 0;
        return scoreB - scoreA;
    });
    if (isLoading) {
        return (<div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary"/>
      </div>);
    }
    if (!role) {
        return (<div className="min-h-screen bg-background flex items-center justify-center">
        <Card className="p-8 max-w-md text-center">
          <h2 className="text-xl font-semibold mb-4">Role Not Found</h2>
          <p className="text-muted-foreground mb-6">
            This role doesn't exist or you don't have access to it.
          </p>
          <Button asChild>
            <Link to="/org">Back to Dashboard</Link>
          </Button>
        </Card>
      </div>);
    }
    return (<div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border/40 bg-card/30 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" asChild>
              <Link to="/org">
                <ArrowLeft className="w-4 h-4 mr-2"/>
                Back to Dashboard
              </Link>
            </Button>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold">T</span>
            </div>
            <span className="text-xl font-bold">Talenti</span>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        {/* Role Header */}
        <div className="mb-8">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h1 className="text-3xl font-bold mb-2">{role.title}</h1>
              <div className="flex items-center gap-3 text-muted-foreground">
                {role.department && <span>{role.department}</span>}
                {role.department && <span>•</span>}
                {role.location && <span>{role.location}</span>}
                {role.location && <span>•</span>}
                <span>{applications?.length || 0} candidates</span>
              </div>
            </div>
            <Badge variant="secondary">{role.status}</Badge>
          </div>

          {role.description && (<p className="text-muted-foreground mb-4 max-w-2xl">{role.description}</p>)}

          <div className="flex flex-wrap gap-3">
            <Button onClick={handleGenerateShortlist} disabled={isGenerating || !applications?.length} className="bg-gradient-to-r from-primary to-primary/80">
              {isGenerating ? (<Loader2 className="w-4 h-4 mr-2 animate-spin"/>) : (<Sparkles className="w-4 h-4 mr-2"/>)}
              {isGenerating ? "Generating..." : "AI Shortlist"}
            </Button>
            <Button variant="outline">
              <Upload className="w-4 h-4 mr-2"/>
              Upload Resumes
            </Button>
            <Button variant="outline" onClick={() => {
            setSelectedApplicationId(null);
            setInvitationDialogOpen(true);
        }}>
              <Send className="w-4 h-4 mr-2"/>
              Send Invitations
            </Button>
            <Button variant="outline" asChild>
              <Link to={`/org/role/${roleId}/rubric`}>
                <Sliders className="w-4 h-4 mr-2"/>
                Customize Rubric
              </Link>
            </Button>
            {selectedForComparison.length >= 2 && (<Button variant="outline" onClick={() => setShowComparison(true)}>
                <GitCompare className="w-4 h-4 mr-2"/>
                Compare ({selectedForComparison.length})
              </Button>)}
            <Button variant="outline">
              <Download className="w-4 h-4 mr-2"/>
              Export Report
            </Button>
          </div>
        </div>

        {/* AI Shortlist View */}
        {showShortlist && shortlistData && (<ShortlistView matches={shortlistData.matches} onClose={() => {
                setShowShortlist(false);
                clearShortlist();
            }} onSelectCandidate={(appId) => {
                // Scroll to the candidate in the list
                const element = document.getElementById(`candidate-${appId}`);
                if (element) {
                    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    element.classList.add('ring-2', 'ring-primary');
                    setTimeout(() => element.classList.remove('ring-2', 'ring-primary'), 2000);
                }
            }}/>)}

        {/* Comparison View */}
        {showComparison && selectedApplicationsForComparison.length >= 2 && (<div className="mb-6">
            <CandidateComparison selectedApplications={selectedApplicationsForComparison} onRemoveCandidate={(id) => {
                toggleCandidateSelection(id);
                if (selectedForComparison.length <= 2) {
                    setShowComparison(false);
                }
            }} onClose={() => setShowComparison(false)}/>
          </div>)}

        {/* Candidates List */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold">Candidates</h2>
            <div className="flex items-center gap-4">
              {selectedForComparison.length > 0 && (<span className="text-sm text-muted-foreground">
                  {selectedForComparison.length} selected for comparison
                </span>)}
              {sortedApplications?.some(a => a.match_score !== null) && (<Badge variant="outline" className="gap-1">
                  <Sparkles className="w-3 h-3"/>
                  Sorted by AI Match
                </Badge>)}
            </div>
          </div>

          {sortedApplications && sortedApplications.length > 0 ? (<div className="space-y-4">
              {sortedApplications.map((application) => {
                const interview = application.interviews?.[0];
                const score = interview?.interview_scores?.[0];
                const dimensions = interview?.score_dimensions || [];
                const matchScore = application.match_score;
                const isSelected = selectedForComparison.includes(application.id);
                return (<div id={`candidate-${application.id}`} key={application.id} className={`p-6 rounded-lg border transition-all ${isSelected
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:bg-accent/30'}`}>
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-start gap-4 flex-1">
                        <Checkbox checked={isSelected} onCheckedChange={() => toggleCandidateSelection(application.id)} className="mt-1"/>
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <h3 className="font-semibold text-lg">
                              Candidate #{application.id.slice(0, 8)}
                            </h3>
                            {getStatusBadge(application.status)}
                            {matchScore !== null && matchScore !== undefined && (<Badge variant="outline" className="gap-1 text-primary border-primary/30">
                                <Sparkles className="w-3 h-3"/>
                                {Math.round(matchScore)}% Match
                              </Badge>)}
                          </div>
                          <p className="text-xs text-muted-foreground">
                            Applied {formatDistanceToNow(new Date(application.created_at), { addSuffix: true })}
                          </p>
                        </div>
                      </div>

                      {score?.overall_score !== null && score?.overall_score !== undefined && (<div className="text-right">
                          <div className="flex items-center gap-2 mb-1">
                            <TrendingUp className="w-5 h-5 text-primary"/>
                            <span className="text-3xl font-bold text-primary">
                              {Math.round(score.overall_score)}%
                            </span>
                          </div>
                          <p className="text-sm text-muted-foreground">Interview Score</p>
                        </div>)}
                    </div>

                    {dimensions.length > 0 && (<div className="space-y-3 mb-4">
                        {dimensions.slice(0, 4).map((dim) => (<div key={dim.id} className="space-y-1">
                            <div className="flex items-center justify-between text-sm">
                              <span className="text-muted-foreground capitalize">{dim.dimension}</span>
                              <span className="font-medium">{Math.round(Number(dim.score) * 10)}/100</span>
                            </div>
                            <Progress value={Number(dim.score) * 10} className="h-2"/>
                          </div>))}
                      </div>)}

                    {interview?.status === "completed" && (<div className="flex gap-2">
                        <Button size="sm" asChild>
                          <Link to={`/org/interview/${interview.id}`}>View Full Report</Link>
                        </Button>
                        <Button size="sm" variant="outline" disabled={downloadingPDF === interview.id} onClick={() => handleDownloadPDF(interview.id)}>
                          {downloadingPDF === interview.id ? (<Loader2 className="w-4 h-4 mr-2 animate-spin"/>) : (<FileText className="w-4 h-4 mr-2"/>)}
                          Download PDF
                        </Button>
                        {interview.recording_url && (<Button size="sm" variant="outline">
                            View Recording
                          </Button>)}
                      </div>)}

                    {application.status === "invited" && (<Button size="sm" variant="outline" onClick={() => {
                            setSelectedApplicationId(application.id);
                            setInvitationDialogOpen(true);
                        }}>
                        Resend Invitation
                      </Button>)}

                    {application.status === "applied" && (<Button size="sm" variant="outline" onClick={() => {
                            setSelectedApplicationId(application.id);
                            setInvitationDialogOpen(true);
                        }}>
                        <Send className="w-4 h-4 mr-2"/>
                        Send Invitation
                      </Button>)}
                  </div>);
            })}
            </div>) : (<div className="text-center py-12">
              <Users className="w-12 h-12 mx-auto text-muted-foreground/50 mb-4"/>
              <h3 className="text-lg font-medium mb-2">No candidates yet</h3>
              <p className="text-muted-foreground mb-4">Upload resumes or send invitations to add candidates</p>
              <div className="flex gap-3 justify-center">
                <Button>
                  <Upload className="w-4 h-4 mr-2"/>
                  Upload Resumes
                </Button>
                <Button variant="outline" onClick={() => setInvitationDialogOpen(true)}>
                  <Send className="w-4 h-4 mr-2"/>
                  Send Invitations
                </Button>
              </div>
            </div>)}
        </Card>
      </div>

      {/* Invitation Dialog */}
      {role && orgData?.organisation && (<SendInvitationDialog open={invitationDialogOpen} onOpenChange={setInvitationDialogOpen} applicationId={selectedApplicationId} roleId={role.id} roleTitle={role.title} companyName={orgData.organisation.name} onSuccess={() => {
                queryClient.invalidateQueries({ queryKey: ["role-applications", roleId] });
            }}/>)}
    </div>);
};
export default RoleDetails;
