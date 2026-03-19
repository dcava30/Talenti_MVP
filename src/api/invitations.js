import { http } from "./http";

const mapInvitation = (invitation) => {
    if (!invitation) {
        return invitation;
    }
    return {
        ...invitation,
        applicationId: invitation.application_id ?? invitation.applicationId,
        candidateEmail: invitation.candidate_email ?? invitation.candidateEmail,
        claimRequired: invitation.claim_required ?? invitation.claimRequired ?? false,
        profileCompletionRequired: invitation.profile_completion_required ?? invitation.profileCompletionRequired ?? false,
        invitationKind: invitation.invitation_kind ?? invitation.invitationKind,
        expiresAt: invitation.expires_at ?? invitation.expiresAt,
    };
};

const mapValidationResponse = (response) => {
    if (!response) {
        return response;
    }
    return {
        ...response,
        invitation: mapInvitation(response.invitation),
        application: response.application
            ? {
                ...response.application,
                jobRoleId: response.application.job_role_id ?? response.application.jobRoleId,
                candidateProfileId: response.application.candidate_profile_id ?? response.application.candidateProfileId,
                sourceChannel: response.application.source_channel ?? response.application.sourceChannel,
                profileReviewStatus: response.application.profile_review_status ?? response.application.profileReviewStatus,
                profileConfirmedAt: response.application.profile_confirmed_at ?? response.application.profileConfirmedAt,
            }
            : null,
        candidateEmail: response.candidate_email ?? response.candidateEmail,
        claimRequired: response.claim_required ?? response.claimRequired ?? false,
        profileCompletionRequired: response.profile_completion_required ?? response.profileCompletionRequired ?? false,
        accountClaimed: response.account_claimed ?? response.accountClaimed ?? false,
        profileConfirmed: response.profile_confirmed ?? response.profileConfirmed ?? false,
        interviewUnlocked: response.interview_unlocked ?? response.interviewUnlocked ?? false,
    };
};

export const invitationsApi = {
    send(payload) {
        return http.post("/api/invitations", {
            application_id: payload.applicationId ?? payload.application_id,
            candidate_email: payload.candidateEmail ?? payload.candidate_email,
            expires_at: payload.expiresAt ?? payload.expires_at,
            email_template: payload.emailTemplate ?? payload.email_template,
        }).then(mapInvitation);
    },
    validate(token) {
        return http.get("/api/v1/invitations/validate", { token }).then(mapValidationResponse);
    },
    listByApplication(applicationId) {
        return http.get("/api/v1/invitations", { application_id: applicationId }).then((items) => items.map(mapInvitation));
    },
    update(invitationId, payload) {
        return http.patch(`/api/v1/invitations/${invitationId}`, payload).then(mapInvitation);
    },
};
