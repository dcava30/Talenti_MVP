import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/apiClient";
import { authClient } from "@/lib/authClient";

/**
 * Hook for fetching the current candidate's profile.
 * 
 * Retrieves the authenticated user's candidate profile from the database.
 * Returns null if no profile exists.
 * 
 * @returns React Query result with candidate profile data
 * 
 * @example
 * ```tsx
 * const { data: profile, isLoading } = useCandidateProfile();
 * 
 * if (profile) {
 *   return <p>Welcome, {profile.first_name}!</p>;
 * }
 * ```
 */
export function useCandidateProfile() {
  return useQuery({
    queryKey: ["candidate-profile"],
    queryFn: async () => {
      const user = await authClient.me();
      if (!user?.id) return null;
      return apiClient.get(`/api/candidates/${user.id}`);
    },
  });
}

/**
 * Hook for fetching all applications submitted by the current candidate.
 * 
 * Includes related job role information, organisation details, and
 * interview data with scores.
 * 
 * @returns React Query result with array of applications
 * 
 * @example
 * ```tsx
 * const { data: applications, isLoading } = useCandidateApplications();
 * 
 * return (
 *   <ul>
 *     {applications?.map(app => (
 *       <li key={app.id}>
 *         {app.job_roles?.title} at {app.job_roles?.organisations?.name}
 *       </li>
 *     ))}
 *   </ul>
 * );
 * ```
 */
export function useCandidateApplications() {
  return useQuery({
    queryKey: ["candidate-applications"],
    queryFn: async () => {
      const user = await authClient.me();
      if (!user?.id) return [];
      return apiClient.get(`/api/candidates/${user.id}/applications`);
    },
  });
}

/**
 * Hook for fetching pending interview invitations for the current candidate.
 * 
 * Returns only valid invitations that are not expired and have
 * status "sent", "opened", or "pending".
 * 
 * @returns React Query result with array of active invitations
 * 
 * @example
 * ```tsx
 * const { data: invitations } = useCandidateInvitations();
 * 
 * if (invitations?.length > 0) {
 *   return <Badge>You have {invitations.length} pending interview(s)</Badge>;
 * }
 * ```
 */
export function useCandidateInvitations() {
  return useQuery({
    queryKey: ["candidate-invitations"],
    queryFn: async () => {
      const user = await authClient.me();
      if (!user?.id) return [];
      return apiClient.get(`/api/candidates/${user.id}/invitations`);
    },
  });
}

/**
 * Hook for fetching completed interview feedback for the current candidate.
 * 
 * Returns interviews that have been completed and scored, including
 * dimension breakdowns and narrative summaries.
 * 
 * @returns React Query result with array of interview feedback
 * 
 * @example
 * ```tsx
 * const { data: feedback } = useCandidateInterviewFeedback();
 * 
 * return feedback?.map(fb => (
 *   <FeedbackCard
 *     key={fb.id}
 *     role={fb.job_roles?.title}
 *     score={fb.interviews?.[0]?.interview_scores?.[0]?.overall_score}
 *   />
 * ));
 * ```
 */
export function useCandidateInterviewFeedback() {
  return useQuery({
    queryKey: ["candidate-feedback"],
    queryFn: async () => {
      const user = await authClient.me();
      if (!user?.id) return [];
      return apiClient.get(`/api/candidates/${user.id}/feedback`);
    },
  });
}

/**
 * Calculates the completion percentage of a candidate's profile.
 * 
 * Checks a predefined list of important profile fields and returns
 * the percentage that have been filled in.
 * 
 * @param profile - The candidate profile object from the database
 * @returns Percentage of profile completion (0-100)
 * 
 * @example
 * ```tsx
 * const { data: profile } = useCandidateProfile();
 * const completion = calculateProfileCompletion(profile);
 * 
 * return <Progress value={completion} />;
 * ```
 */
export function calculateProfileCompletion(profile: any): number {
  if (!profile) return 0;

  const fields = [
    "first_name",
    "last_name",
    "email",
    "phone",
    "suburb",
    "state",
    "postcode",
    "work_rights",
    "availability",
    "work_mode",
    "cv_file_path",
    "linkedin_url",
  ];

  const filledFields = fields.filter(
    (field) => profile[field] && profile[field].toString().trim() !== ""
  );

  return Math.round((filledFields.length / fields.length) * 100);
}
