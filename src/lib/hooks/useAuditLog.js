import { useQuery } from "@tanstack/react-query";
import { auditApi } from "@/api/audit";
/**
 * Hook for fetching audit log entries for an organisation.
 *
 * Retrieves the most recent 100 audit log entries for compliance
 * and security monitoring purposes.
 *
 * @param organisationId - The UUID of the organisation to fetch logs for
 * @returns React Query result with array of audit log entries
 *
 * @example
 * ```tsx
 * const { data: logs, isLoading } = useAuditLog(orgId);
 *
 * return (
 *   <table>
 *     {logs?.map(log => (
 *       <tr key={log.id}>
 *         <td>{formatActionType(log.action)}</td>
 *         <td>{log.created_at}</td>
 *       </tr>
 *     ))}
 *   </table>
 * );
 * ```
 */
export function useAuditLog(organisationId) {
    return useQuery({
        queryKey: ["audit-log", organisationId],
        queryFn: async () => {
            if (!organisationId)
                return [];
            const data = await auditApi.list(organisationId);
            return (data || []);
        },
        enabled: !!organisationId,
    });
}
/**
 * Formats an action type string for user-friendly display.
 *
 * @param action - The raw action type from the database
 * @returns Human-readable action label
 *
 * @example
 * ```ts
 * formatActionType("profile_unlocked") // => "Profile Unlocked"
 * formatActionType("custom_action")    // => "Custom Action"
 * ```
 */
export function formatActionType(action) {
    const actionMap = {
        profile_unlocked: "Profile Unlocked",
        rubric_updated: "Rubric Updated",
        score_override: "Score Override",
        invitation_sent: "Invitation Sent",
        role_created: "Role Created",
        role_updated: "Role Updated",
        candidate_shortlisted: "Candidate Shortlisted",
        interview_completed: "Interview Completed",
    };
    return actionMap[action] || action.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
}
/**
 * Formats an entity type string for user-friendly display.
 *
 * @param entityType - The raw entity type from the database
 * @returns Human-readable entity label
 *
 * @example
 * ```ts
 * formatEntityType("candidate_profile") // => "Candidate Profile"
 * formatEntityType("job_role")          // => "Job Role"
 * ```
 */
export function formatEntityType(entityType) {
    const entityMap = {
        candidate_profile: "Candidate Profile",
        job_role: "Job Role",
        scoring_rubric: "Scoring Rubric",
        interview_score: "Interview Score",
        invitation: "Invitation",
        application: "Application",
    };
    return entityMap[entityType] || entityType.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
}
/**
 * Gets the icon type for a given action.
 *
 * Used to determine which icon to display in the audit log UI.
 *
 * @param action - The action type string
 * @returns Icon identifier for the action
 *
 * @example
 * ```ts
 * getActionIconType("profile_unlocked") // => "unlock"
 * getActionIconType("score_override")   // => "score"
 * getActionIconType("unknown_action")   // => "default"
 * ```
 */
export function getActionIconType(action) {
    if (action.includes("unlock"))
        return "unlock";
    if (action.includes("update") || action.includes("change") || action.includes("edit"))
        return "edit";
    if (action.includes("score") || action.includes("override"))
        return "score";
    if (action.includes("send") || action.includes("invite"))
        return "send";
    if (action.includes("create") || action.includes("add"))
        return "create";
    return "default";
}
