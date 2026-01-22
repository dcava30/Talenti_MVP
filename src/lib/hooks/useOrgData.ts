import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";

/**
 * Hook for fetching the current user's organisation and role.
 * 
 * Returns the user's role within the organisation and full organisation details.
 * Used for determining permissions and displaying org-specific content.
 * 
 * @returns React Query result with org user data including role and organisation
 * 
 * @example
 * ```tsx
 * const { data: orgData, isLoading } = useCurrentOrg();
 * 
 * if (orgData?.role === 'org_admin') {
 *   return <AdminDashboard org={orgData.organisation} />;
 * }
 * ```
 */
export const useCurrentOrg = () => {
  return useQuery({
    queryKey: ["current-org"],
    queryFn: async () => {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return null;

      const { data: orgUser, error } = await supabase
        .from("org_users")
        .select(`
          role,
          organisation:organisations(*)
        `)
        .eq("user_id", user.id)
        .maybeSingle();

      if (error) throw error;
      return orgUser;
    },
  });
};

/**
 * Hook for fetching all job roles for an organisation.
 * 
 * Returns roles ordered by creation date (newest first).
 * Only enabled when organisationId is provided.
 * 
 * @param organisationId - The UUID of the organisation to fetch roles for
 * @returns React Query result with array of job roles
 * 
 * @example
 * ```tsx
 * const { data: roles, isLoading } = useJobRoles(orgId);
 * 
 * return (
 *   <ul>
 *     {roles?.map(role => (
 *       <li key={role.id}>{role.title} - {role.status}</li>
 *     ))}
 *   </ul>
 * );
 * ```
 */
export const useJobRoles = (organisationId: string | undefined) => {
  return useQuery({
    queryKey: ["job-roles", organisationId],
    queryFn: async () => {
      if (!organisationId) return [];

      const { data, error } = await supabase
        .from("job_roles")
        .select("*")
        .eq("organisation_id", organisationId)
        .order("created_at", { ascending: false });

      if (error) throw error;
      return data;
    },
    enabled: !!organisationId,
  });
};

/**
 * Hook for fetching a single job role by ID.
 * 
 * @param roleId - The UUID of the job role to fetch
 * @returns React Query result with the job role or null
 * 
 * @example
 * ```tsx
 * const { data: role, isLoading } = useJobRole(roleId);
 * 
 * if (role) {
 *   return <RoleDetailsCard role={role} />;
 * }
 * ```
 */
export const useJobRole = (roleId: string | undefined) => {
  return useQuery({
    queryKey: ["job-role", roleId],
    queryFn: async () => {
      if (!roleId) return null;

      const { data, error } = await supabase
        .from("job_roles")
        .select("*")
        .eq("id", roleId)
        .maybeSingle();

      if (error) throw error;
      return data;
    },
    enabled: !!roleId,
  });
};

/**
 * Hook for fetching all applications for a specific job role.
 * 
 * Includes related interview data with scores and dimension breakdowns.
 * Returns applications ordered by creation date (newest first).
 * 
 * @param roleId - The UUID of the job role to fetch applications for
 * @returns React Query result with array of applications
 * 
 * @example
 * ```tsx
 * const { data: applications } = useRoleApplications(roleId);
 * 
 * return applications?.map(app => (
 *   <CandidateCard
 *     key={app.id}
 *     application={app}
 *     latestInterview={app.interviews?.[0]}
 *   />
 * ));
 * ```
 */
export const useRoleApplications = (roleId: string | undefined) => {
  return useQuery({
    queryKey: ["role-applications", roleId],
    queryFn: async () => {
      if (!roleId) return [];

      const { data, error } = await supabase
        .from("applications")
        .select(`
          *,
          interviews(
            *,
            interview_scores(*),
            score_dimensions(*)
          )
        `)
        .eq("job_role_id", roleId)
        .order("created_at", { ascending: false });

      if (error) throw error;
      return data;
    },
    enabled: !!roleId,
  });
};

/**
 * Statistics object for an organisation's recruitment activity.
 */
interface OrgStats {
  /** Number of job roles with "active" status */
  activeRoles: number;
  /** Total number of candidate applications across all roles */
  totalCandidates: number;
  /** Number of interviews with "completed" status */
  completedInterviews: number;
  /** Average overall interview score (0-100) */
  avgMatchScore: number;
}

/**
 * Hook for fetching aggregate statistics for an organisation.
 * 
 * Calculates counts for active roles, candidates, interviews,
 * and computes average interview scores.
 * 
 * @param organisationId - The UUID of the organisation to get stats for
 * @returns React Query result with organisation statistics
 * 
 * @example
 * ```tsx
 * const { data: stats } = useOrgStats(orgId);
 * 
 * return (
 *   <div className="grid grid-cols-4 gap-4">
 *     <StatCard title="Active Roles" value={stats?.activeRoles} />
 *     <StatCard title="Total Candidates" value={stats?.totalCandidates} />
 *     <StatCard title="Completed Interviews" value={stats?.completedInterviews} />
 *     <StatCard title="Avg Score" value={`${stats?.avgMatchScore}%`} />
 *   </div>
 * );
 * ```
 */
export const useOrgStats = (organisationId: string | undefined) => {
  return useQuery({
    queryKey: ["org-stats", organisationId],
    queryFn: async (): Promise<OrgStats | null> => {
      if (!organisationId) return null;

      // Get active roles count
      const { count: activeRolesCount } = await supabase
        .from("job_roles")
        .select("*", { count: "exact", head: true })
        .eq("organisation_id", organisationId)
        .eq("status", "active");

      // Get all role IDs for this org
      const { data: roles } = await supabase
        .from("job_roles")
        .select("id")
        .eq("organisation_id", organisationId);

      const roleIds = roles?.map(r => r.id) || [];

      if (roleIds.length === 0) {
        return {
          activeRoles: 0,
          totalCandidates: 0,
          completedInterviews: 0,
          avgMatchScore: 0,
        };
      }

      // Get total candidates
      const { count: totalCandidates } = await supabase
        .from("applications")
        .select("*", { count: "exact", head: true })
        .in("job_role_id", roleIds);

      // Get application IDs
      const { data: applications } = await supabase
        .from("applications")
        .select("id")
        .in("job_role_id", roleIds);

      const applicationIds = applications?.map(a => a.id) || [];

      let completedInterviews = 0;
      let avgMatchScore = 0;

      if (applicationIds.length > 0) {
        // Get completed interviews count
        const { count: completedCount } = await supabase
          .from("interviews")
          .select("*", { count: "exact", head: true })
          .in("application_id", applicationIds)
          .eq("status", "completed");

        completedInterviews = completedCount || 0;

        // Get average score
        const { data: scores } = await supabase
          .from("interviews")
          .select("interview_scores(overall_score)")
          .in("application_id", applicationIds)
          .eq("status", "completed");

        if (scores && scores.length > 0) {
          const validScores = scores
            .map(s => s.interview_scores?.[0]?.overall_score)
            .filter((s): s is number => s !== null && s !== undefined);
          
          if (validScores.length > 0) {
            avgMatchScore = Math.round(
              validScores.reduce((a, b) => a + b, 0) / validScores.length
            );
          }
        }
      }

      return {
        activeRoles: activeRolesCount || 0,
        totalCandidates: totalCandidates || 0,
        completedInterviews,
        avgMatchScore,
      };
    },
    enabled: !!organisationId,
  });
};
