import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, AlertCircle, CheckCircle2, Clock, Briefcase } from "lucide-react";
import { useInvitations } from "@/hooks/useInvitations";
const InviteValidation = () => {
    const { token } = useParams();
    const navigate = useNavigate();
    const { validateInvitation, isValidating } = useInvitations();
    const [status, setStatus] = useState("loading");
    const [error, setError] = useState(null);
    const [invitationData, setInvitationData] = useState(null);
    useEffect(() => {
        if (token) {
            validateToken(token);
        }
    }, [token]);
    const validateToken = async (tokenValue) => {
        const result = await validateInvitation(tokenValue);
        if (result.valid && result.invitation && result.application && result.jobRole) {
            setStatus("valid");
            setInvitationData({
                invitation: result.invitation,
                application: result.application,
                jobRole: result.jobRole,
            });
        }
        else {
            if (result.error?.includes("expired")) {
                setStatus("expired");
            }
            else {
                setStatus("invalid");
            }
            setError(result.error || "Invalid invitation");
        }
    };
    const handleStartInterview = () => {
        if (invitationData) {
            // Navigate to interview lobby with invitation context
            navigate(`/candidate/${invitationData.invitation.id}/lobby`);
        }
    };
    const formatExpiryDate = (dateString) => {
        return new Date(dateString).toLocaleDateString("en-US", {
            weekday: "long",
            year: "numeric",
            month: "long",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
    };
    if (status === "loading" || isValidating) {
        return (<div className="min-h-screen bg-background flex items-center justify-center">
        <Card className="p-8 max-w-md text-center">
          <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto mb-4"/>
          <h2 className="text-xl font-semibold mb-2">Validating Invitation</h2>
          <p className="text-muted-foreground">Please wait while we verify your interview link...</p>
        </Card>
      </div>);
    }
    if (status === "invalid" || status === "expired") {
        return (<div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Card className="p-8 max-w-md text-center">
          <div className={`w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center ${status === "expired" ? "bg-yellow-500/10" : "bg-destructive/10"}`}>
            {status === "expired" ? (<Clock className="w-8 h-8 text-yellow-500"/>) : (<AlertCircle className="w-8 h-8 text-destructive"/>)}
          </div>
          <h2 className="text-xl font-semibold mb-2">
            {status === "expired" ? "Invitation Expired" : "Invalid Invitation"}
          </h2>
          <p className="text-muted-foreground mb-6">
            {error || (status === "expired"
                ? "This interview invitation has expired. Please contact the recruiter for a new link."
                : "This invitation link is invalid or has already been used.")}
          </p>
          <Button variant="outline" onClick={() => navigate("/")}>
            Return Home
          </Button>
        </Card>
      </div>);
    }
    return (<div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border/40 bg-card/30 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold">T</span>
            </div>
            <span className="font-semibold">Talenti Interview</span>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-12 max-w-2xl">
        <Card className="p-8">
          {/* Success indicator */}
          <div className="flex items-center gap-3 mb-6 p-4 rounded-lg bg-green-500/10 border border-green-500/20">
            <CheckCircle2 className="w-6 h-6 text-green-500 flex-shrink-0"/>
            <div>
              <p className="font-medium text-green-700 dark:text-green-400">Valid Invitation</p>
              <p className="text-sm text-muted-foreground">Your interview link has been verified</p>
            </div>
          </div>

          {/* Job Role Info */}
          {invitationData && (<>
              <div className="mb-8">
                <Badge variant="outline" className="mb-4">
                  <Briefcase className="w-3 h-3 mr-1"/>
                  Interview Invitation
                </Badge>
                <h1 className="text-3xl font-bold mb-2">{invitationData.jobRole.title}</h1>
                <p className="text-xl text-muted-foreground">{invitationData.jobRole.organisation.name}</p>
                {invitationData.jobRole.department && (<p className="text-muted-foreground">{invitationData.jobRole.department}</p>)}
              </div>

              {invitationData.jobRole.description && (<div className="mb-8">
                  <h3 className="font-semibold mb-2">About This Role</h3>
                  <p className="text-muted-foreground">{invitationData.jobRole.description}</p>
                </div>)}

              {/* What to Expect */}
              <div className="mb-8 p-4 rounded-lg bg-accent/50">
                <h3 className="font-semibold mb-3">What to Expect</h3>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-primary"/>
                    10-15 minute AI-powered interview
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-primary"/>
                    Voice-based conversation with AI interviewer
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-primary"/>
                    Camera and microphone required
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-primary"/>
                    Interview will be recorded for evaluation
                  </li>
                </ul>
              </div>

              {/* Expiry Notice */}
              <div className="mb-8 p-4 rounded-lg border border-border">
                <div className="flex items-center gap-2 text-sm">
                  <Clock className="w-4 h-4 text-muted-foreground"/>
                  <span className="text-muted-foreground">
                    This invitation expires on{" "}
                    <span className="font-medium text-foreground">
                      {formatExpiryDate(invitationData.invitation.expiresAt)}
                    </span>
                  </span>
                </div>
              </div>

              {/* CTA */}
              <Button size="lg" className="w-full" onClick={handleStartInterview}>
                Proceed to Device Check
              </Button>
              <p className="text-center text-sm text-muted-foreground mt-4">
                You'll be able to test your camera and microphone before starting
              </p>
            </>)}
        </Card>
      </div>
    </div>);
};
export default InviteValidation;
