import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";

/**
 * Represents a single entry in the audit log.
 */
export interface AuditLogEntry {
  /** Unique identifier for the log entry */
  id: string;
  /** ID of the user who performed the action (null for system actions) */
  user_id: string | null;
  /** Type of action performed (e.g., "profile_unlocked", "rubric_updated") */
  action: string;
  /** Type of entity affected (e.g., "candidate_profile", "job_role") */
  entity_type: string;
  /** ID of the affected entity */
  entity_id: string | null;
  /** Previous values before the change (for updates) */
  old_values: Record<string, unknown> | null;
  /** New values after the change (for creates/updates) */
  new_values: Record<string, unknown> | null;
  /** IP address of the user who performed the action */
  ip_address: string | null;
  /** ID of the organisation this log entry belongs to */
  organisation_id: string | null;
  /** Timestamp when the action was performed */
  created_at: string;
}

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
export function useAuditLog(organisationId: string | undefined) {
  return useQuery({
    queryKey: ["audit-log", organisationId],
    queryFn: async (): Promise<AuditLogEntry[]> => {
      if (!organisationId) return [];

      const { data, error } = await supabase
        .from("audit_log")
        .select("*")
        .eq("organisation_id", organisationId)
        .order("created_at", { ascending: false })
        .limit(100);

      if (error) throw error;
      return (data || []) as AuditLogEntry[];
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
export function formatActionType(action: string): string {
  const actionMap: Record<string, string> = {
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
export function formatEntityType(entityType: string): string {
  const entityMap: Record<string, string> = {
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
export function getActionIconType(action: string): "unlock" | "edit" | "score" | "send" | "create" | "default" {
  if (action.includes("unlock")) return "unlock";
  if (action.includes("update") || action.includes("change") || action.includes("edit")) return "edit";
  if (action.includes("score") || action.includes("override")) return "score";
  if (action.includes("send") || action.includes("invite")) return "send";
  if (action.includes("create") || action.includes("add")) return "create";
  return "default";
}
