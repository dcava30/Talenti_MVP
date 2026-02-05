import { useState } from "react";
import { apiClient } from "@/lib/apiClient";
import { useToast } from "@/hooks/use-toast";

/**
 * Parameters required to send an interview invitation.
 */
interface SendInvitationParams {
  /** The UUID of the application to invite for interview */
  applicationId: string;
  /** Email address to send the invitation to */
  candidateEmail: string;
  /** Title of the job role for the email content */
  roleTitle: string;
  /** Name of the hiring company for the email content */
  companyName: string;
}

/**
 * Result of validating an invitation token.
 */
interface ValidateInvitationResult {
  /** Whether the invitation token is valid */
  valid: boolean;
  /** Invitation details if valid */
  invitation?: {
    id: string;
    applicationId: string;
    status: string;
    expiresAt: string;
  };
  /** Application details if valid */
  application?: {
    id: string;
    status: string;
    jobRoleId: string;
  };
  /** Job role and organisation details if valid */
  jobRole?: {
    id: string;
    title: string;
    department: string | null;
    description: string | null;
    organisation: {
      name: string;
    };
  };
  /** Error message if validation failed */
  error?: string;
}

/**
 * Hook for managing interview invitations.
 * 
 * Provides functions to send invitations via email, validate invitation
 * tokens, and mark invitations as completed.
 * 
 * @returns Object with invitation management functions and state
 * 
 * @example
 * ```tsx
 * const { sendInvitation, validateInvitation, isSending } = useInvitations();
 * 
 * // Send an invitation
 * const handleSend = async () => {
 *   const result = await sendInvitation({
 *     applicationId: app.id,
 *     candidateEmail: "candidate@example.com",
 *     roleTitle: "Software Engineer",
 *     companyName: "Acme Corp",
 *   });
 *   if (result.success) {
 *     console.log("Invitation sent!");
 *   }
 * };
 * 
 * // Validate a token from URL
 * const result = await validateInvitation(token);
 * if (result.valid) {
 *   navigateToInterview(result.invitation.id);
 * }
 * ```
 */
export function useInvitations() {
  const [isSending, setIsSending] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const { toast } = useToast();

  /**
   * Sends an interview invitation email to a candidate.
   * 
   * Calls the backend edge function to generate an invitation token
   * and send an email with the interview link.
   * 
   * @param params - Invitation parameters
   * @returns Object with success status and optional error
   */
  const sendInvitation = async (params: SendInvitationParams): Promise<{ success: boolean; data?: any; error?: string }> => {
    setIsSending(true);
    try {
      const data = await apiClient.post("/api/invitations", params);

      toast({
        title: "Invitation Sent",
        description: `Interview invitation sent to ${params.candidateEmail}`,
      });

      return { success: true, data };
    } catch (error: any) {
      console.error("Error sending invitation:", error);
      toast({
        title: "Failed to Send Invitation",
        description: error.message || "An error occurred while sending the invitation",
        variant: "destructive",
      });
      return { success: false, error: error.message };
    } finally {
      setIsSending(false);
    }
  };

  /**
   * Validates an invitation token and retrieves associated data.
   * 
   * Checks if the token exists, hasn't expired, and hasn't been used.
   * If valid, marks the invitation as "opened" on first access.
   * 
   * @param token - The invitation token from the URL
   * @returns Validation result with invitation, application, and job role data
   */
  const validateInvitation = async (token: string): Promise<ValidateInvitationResult> => {
    setIsValidating(true);
    try {
      const result = await apiClient.post<ValidateInvitationResult>("/api/invitations/validate", { token });
      return result;
    } catch (error: any) {
      console.error("Error validating invitation:", error);
      return { valid: false, error: "Failed to validate invitation" };
    } finally {
      setIsValidating(false);
    }
  };

  /**
   * Marks an invitation as completed (delivered).
   * 
   * Called after a candidate has completed their interview.
   * 
   * @param invitationId - The UUID of the invitation to mark complete
   */
  const markInvitationCompleted = async (invitationId: string): Promise<void> => {
    try {
      await apiClient.request(`/api/invitations/${invitationId}`, {
        method: "PATCH",
        body: JSON.stringify({ status: "delivered" }),
      });
    } catch (error) {
      console.error("Error marking invitation completed:", error);
    }
  };

  return {
    /** Sends an interview invitation email */
    sendInvitation,
    /** Validates an invitation token */
    validateInvitation,
    /** Marks an invitation as completed */
    markInvitationCompleted,
    /** Whether an invitation is being sent */
    isSending,
    /** Whether a token is being validated */
    isValidating,
  };
}
