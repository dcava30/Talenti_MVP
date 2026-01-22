import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";

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
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return null;

      const { data, error } = await supabase
        .from("candidate_profiles")
        .select("*")
        .eq("user_id", user.id)
        .maybeSingle();

      if (error) throw error;
      return data;
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
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return [];

      const { data, error } = await supabase
        .from("applications")
        .select(`
          *,
          job_roles (
            id,
            title,
            department,
            location,
            organisations (
              id,
              name
            )
          ),
          interviews (
            id,
            status,
            started_at,
            ended_at,
            interview_scores (
              overall_score,
              candidate_feedback,
              narrative_summary
            )
          )
        `)
        .eq("candidate_id", user.id)
        .order("created_at", { ascending: false });

      if (error) throw error;
      return data || [];
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
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return [];

      // Get applications for this user
      const { data: applications } = await supabase
        .from("applications")
        .select("id")
        .eq("candidate_id", user.id);

      if (!applications || applications.length === 0) return [];

      const applicationIds = applications.map(a => a.id);

      // Get pending invitations for these applications
      const { data, error } = await supabase
        .from("invitations")
        .select(`
          *,
          applications (
            id,
            job_roles (
              id,
              title,
              organisations (
                name
              )
            )
          )
        `)
        .in("application_id", applicationIds)
        .in("status", ["sent", "opened", "pending"])
        .gt("expires_at", new Date().toISOString())
        .order("created_at", { ascending: false });

      if (error) throw error;
      return data || [];
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
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return [];

      const { data, error } = await supabase
        .from("applications")
        .select(`
          id,
          job_roles (
            title,
            organisations (
              name
            )
          ),
          interviews!inner (
            id,
            status,
            ended_at,
            interview_scores (
              overall_score,
              candidate_feedback,
              narrative_summary,
              created_at
            ),
            score_dimensions (
              dimension,
              score,
              evidence
            )
          )
        `)
        .eq("candidate_id", user.id)
        .eq("interviews.status", "completed")
        .order("created_at", { ascending: false });

      if (error) throw error;
      return data || [];
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
