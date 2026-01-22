import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, Send, Mail, UserPlus } from "lucide-react";
import { useInvitations } from "@/hooks/useInvitations";
import { supabase } from "@/integrations/supabase/client";
import { useToast } from "@/hooks/use-toast";

interface SendInvitationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  applicationId?: string | null;
  roleId: string;
  roleTitle: string;
  companyName: string;
  onSuccess?: () => void;
}

export function SendInvitationDialog({
  open,
  onOpenChange,
  applicationId,
  roleId,
  roleTitle,
  companyName,
  onSuccess,
}: SendInvitationDialogProps) {
  const [email, setEmail] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const { sendInvitation, isSending } = useInvitations();
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email) return;

    setIsCreating(true);

    try {
      let appId = applicationId;

      // If no applicationId, create a new application for this candidate
      if (!appId) {
        // Get current user
        const { data: { user } } = await supabase.auth.getUser();
        if (!user) throw new Error("Not authenticated");

        // Check if this email already has an application for this role
        // For now, create a placeholder candidate_id using a hash of email
        // In production, this would create/lookup a candidate account
        
        // Create application
        const { data: application, error: appError } = await supabase
          .from("applications")
          .insert({
            job_role_id: roleId,
            candidate_id: user.id, // Temporary - in production this would be the actual candidate
            status: "applied",
          })
          .select()
          .single();

        if (appError) {
          throw new Error(`Failed to create application: ${appError.message}`);
        }

        appId = application.id;
      }

      const result = await sendInvitation({
        applicationId: appId,
        candidateEmail: email,
        roleTitle,
        companyName,
      });

      if (result.success) {
        setEmail("");
        onOpenChange(false);
        onSuccess?.();
      }
    } catch (error: any) {
      console.error("Error:", error);
      toast({
        title: "Error",
        description: error.message || "Failed to send invitation",
        variant: "destructive",
      });
    } finally {
      setIsCreating(false);
    }
  };

  const isLoading = isSending || isCreating;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {applicationId ? <Send className="w-5 h-5" /> : <UserPlus className="w-5 h-5" />}
            {applicationId ? "Send Interview Invitation" : "Invite New Candidate"}
          </DialogTitle>
          <DialogDescription>
            {applicationId 
              ? `Send an AI interview invitation for ${roleTitle} at ${companyName}.`
              : `Add a new candidate and send an AI interview invitation for ${roleTitle}.`
            }
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="email">Candidate Email</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  id="email"
                  type="email"
                  placeholder="candidate@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-10"
                  required
                />
              </div>
            </div>

            <div className="rounded-lg bg-accent/50 p-3 text-sm text-muted-foreground">
              <p>The candidate will receive:</p>
              <ul className="mt-2 space-y-1 list-disc list-inside">
                <li>Email with interview link</li>
                <li>7-day expiration period</li>
                <li>Instructions for the AI interview</li>
              </ul>
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading || !email}>
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  {isCreating ? "Creating..." : "Sending..."}
                </>
              ) : (
                <>
                  <Send className="w-4 h-4 mr-2" />
                  Send Invitation
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
