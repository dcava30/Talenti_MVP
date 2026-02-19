import { useState } from "react";
import { invitationsApi } from "@/api/invitations";
import { useToast } from "@/hooks/use-toast";
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
     * Calls the backend API to generate an invitation token
     * and send an email with the interview link.
     *
     * @param params - Invitation parameters
     * @returns Object with success status and optional error
     */
    const sendInvitation = async (params) => {
        setIsSending(true);
        try {
            const data = await invitationsApi.send(params);
            toast({
                title: "Invitation Sent",
                description: `Interview invitation sent to ${params.candidateEmail}`,
            });
            return { success: true, data };
        }
        catch (error) {
            console.error("Error sending invitation:", error);
            toast({
                title: "Failed to Send Invitation",
                description: error.message || "An error occurred while sending the invitation",
                variant: "destructive",
            });
            return { success: false, error: error.message };
        }
        finally {
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
    const validateInvitation = async (token) => {
        setIsValidating(true);
        try {
            const response = await invitationsApi.validate(token);
            return response;
        }
        catch (error) {
            console.error("Error validating invitation:", error);
            return { valid: false, error: "Failed to validate invitation" };
        }
        finally {
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
    const markInvitationCompleted = async (invitationId) => {
        try {
            await invitationsApi.update(invitationId, { status: "delivered" });
        }
        catch (error) {
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
