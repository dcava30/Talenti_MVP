import { useQuery } from "@tanstack/react-query";
import { organisationsApi } from "@/api/organisations";
import { rolesApi } from "@/api/roles";

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
      const orgUser = await organisationsApi.getCurrentMembership();
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

      const data = await rolesApi.listByOrganisation(organisationId);
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

      const data = await rolesApi.getById(roleId);
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

      const data = await rolesApi.listApplications(roleId);
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

      const stats = await organisationsApi.getStats(organisationId);
      return stats;
    },
    enabled: !!organisationId,
  });
};
