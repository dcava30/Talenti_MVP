import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, AlertCircle, CheckCircle2, Clock, Briefcase, Lock, UserCheck } from "lucide-react";
import { useInvitations } from "@/hooks/useInvitations";
import { authApi } from "@/api/auth";
import { useToast } from "@/hooks/use-toast";

const InviteValidation = () => {
    const { token } = useParams();
    const navigate = useNavigate();
    const { toast } = useToast();
    const { validateInvitation, isValidating } = useInvitations();
    const [status, setStatus] = useState("loading");
    const [error, setError] = useState(null);
    const [invitationData, setInvitationData] = useState(null);
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [isClaiming, setIsClaiming] = useState(false);

    useEffect(() => {
        if (token) {
            validateToken(token);
        }
    }, [token]);

    const validateToken = async (tokenValue) => {
        const result = await validateInvitation(tokenValue);
        if (result.valid && result.invitation && result.application && result.jobRole) {
            setStatus("valid");
            setInvitationData(result);
        }
        else {
            setStatus("invalid");
            setError(result.error || "Invalid invitation");
        }
    };

    const formatExpiryDate = (dateString) => new Date(dateString).toLocaleDateString("en-US", {
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });

    const handleClaimInvite = async () => {
        if (!token || !invitationData?.candidateEmail) {
            return;
        }
        if (password.length < 8) {
            toast({
                title: "Password too short",
                description: "Choose a password with at least 8 characters.",
                variant: "destructive",
            });
            return;
        }
        if (password !== confirmPassword) {
            toast({
                title: "Passwords do not match",
                description: "Please re-enter the same password to continue.",
                variant: "destructive",
            });
            return;
        }
        setIsClaiming(true);
        try {
            await authApi.claimInvite({
                token,
                email: invitationData.candidateEmail,
                password,
            });
            toast({
                title: "Account claimed",
                description: "Your prefilled candidate account is ready. Review your profile before starting the interview.",
            });
            await validateToken(token);
            navigate(`/candidate/profile?invitation_token=${token}&application_id=${invitationData.application.id}&mode=confirm`);
        }
        catch (claimError) {
            toast({
                title: "Could not claim account",
                description: claimError.message || "Please try the invitation link again.",
                variant: "destructive",
            });
        }
        finally {
            setIsClaiming(false);
        }
    };

    const handleProfileReview = () => {
        if (!token || !invitationData?.application?.id) {
            return;
        }
        navigate(`/candidate/profile?invitation_token=${token}&application_id=${invitationData.application.id}&mode=confirm`);
    };

    const handleProceedToLobby = () => {
        if (token) {
            navigate(`/candidate/${token}/lobby`);
        }
    };

    if (status === "loading" || isValidating) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center">
                <Card className="p-8 max-w-md text-center">
                    <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto mb-4" />
                    <h2 className="text-xl font-semibold mb-2">Validating Invitation</h2>
                    <p className="text-muted-foreground">Please wait while we verify your interview link...</p>
                </Card>
            </div>
        );
    }

    if (status === "invalid") {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center p-4">
                <Card className="p-8 max-w-md text-center">
                    <div className="w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center bg-destructive/10">
                        <AlertCircle className="w-8 h-8 text-destructive" />
                    </div>
                    <h2 className="text-xl font-semibold mb-2">Invalid Invitation</h2>
                    <p className="text-muted-foreground mb-6">{error || "This invitation link is not valid."}</p>
                    <Button variant="outline" onClick={() => navigate("/")}>
                        Return Home
                    </Button>
                </Card>
            </div>
        );
    }

    const showClaimStep = invitationData?.claimRequired && !invitationData?.accountClaimed;
    const showProfileReviewStep = !showClaimStep && invitationData?.profileCompletionRequired && !invitationData?.profileConfirmed;
    const showInterviewStep = invitationData?.interviewUnlocked;

    return (
        <div className="min-h-screen bg-background">
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
                <Card className="p-8 space-y-8">
                    <div className="flex items-center gap-3 p-4 rounded-lg bg-green-500/10 border border-green-500/20">
                        <CheckCircle2 className="w-6 h-6 text-green-500 flex-shrink-0" />
                        <div>
                            <p className="font-medium text-green-700 dark:text-green-400">Invitation verified</p>
                            <p className="text-sm text-muted-foreground">Your Talenti interview pathway is ready.</p>
                        </div>
                    </div>

                    {invitationData && (
                        <>
                            <div>
                                <Badge variant="outline" className="mb-4">
                                    <Briefcase className="w-3 h-3 mr-1" />
                                    Interview Invitation
                                </Badge>
                                <h1 className="text-3xl font-bold mb-2">{invitationData.jobRole.title}</h1>
                                <p className="text-xl text-muted-foreground">{invitationData.jobRole.organisation?.name}</p>
                            </div>

                            <div className="rounded-lg border border-border p-4 text-sm">
                                <div className="flex items-center gap-2">
                                    <Clock className="w-4 h-4 text-muted-foreground" />
                                    <span className="text-muted-foreground">
                                        Invitation expires on <span className="font-medium text-foreground">{formatExpiryDate(invitationData.invitation.expiresAt)}</span>
                                    </span>
                                </div>
                            </div>

                            {showClaimStep && (
                                <div className="space-y-4 rounded-lg bg-accent/40 p-5">
                                    <div className="flex items-start gap-3">
                                        <UserCheck className="w-5 h-5 text-primary mt-1" />
                                        <div>
                                            <h2 className="font-semibold">Claim your prefilled candidate account</h2>
                                            <p className="text-sm text-muted-foreground mt-1">
                                                Your organisation created a nearly complete Talenti profile from your resume. Use the email from your resume to claim it.
                                            </p>
                                        </div>
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Resume email</Label>
                                        <Input value={invitationData.candidateEmail || ""} readOnly />
                                    </div>
                                    <div className="grid gap-4 sm:grid-cols-2">
                                        <div className="space-y-2">
                                            <Label htmlFor="password">Set password</Label>
                                            <div className="relative">
                                                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                                <Input id="password" type="password" className="pl-9" value={password} onChange={(event) => setPassword(event.target.value)} />
                                            </div>
                                        </div>
                                        <div className="space-y-2">
                                            <Label htmlFor="confirm-password">Confirm password</Label>
                                            <Input id="confirm-password" type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} />
                                        </div>
                                    </div>
                                    <Button className="w-full" onClick={handleClaimInvite} disabled={isClaiming}>
                                        {isClaiming ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                                        Claim Account
                                    </Button>
                                </div>
                            )}

                            {showProfileReviewStep && (
                                <div className="space-y-4 rounded-lg bg-accent/40 p-5">
                                    <h2 className="font-semibold">Review your prefilled profile</h2>
                                    <p className="text-sm text-muted-foreground">
                                        Your profile has been prepared from your resume. Review or update the details, then confirm it to unlock the interview.
                                    </p>
                                    <Button className="w-full" onClick={handleProfileReview}>
                                        Review Profile Before Interview
                                    </Button>
                                </div>
                            )}

                            {showInterviewStep && (
                                <>
                                    <div className="space-y-3 rounded-lg bg-accent/40 p-5">
                                        <h2 className="font-semibold">Your interview is ready</h2>
                                        <ul className="space-y-2 text-sm text-muted-foreground">
                                            <li className="flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-primary" /> 10-15 minute AI-powered interview</li>
                                            <li className="flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-primary" /> Camera and microphone required</li>
                                            <li className="flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-primary" /> Interview will be recorded for evaluation</li>
                                        </ul>
                                    </div>
                                    <Button size="lg" className="w-full" onClick={handleProceedToLobby}>
                                        Proceed to Device Check
                                    </Button>
                                </>
                            )}
                        </>
                    )}
                </Card>
            </div>
        </div>
    );
};

export default InviteValidation;
