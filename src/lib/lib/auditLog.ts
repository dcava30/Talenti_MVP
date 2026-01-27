import { auditApi } from "@/api/audit";
import { authApi } from "@/api/auth";

export type AuditAction = 
  | "profile_unlocked"
  | "rubric_updated"
  | "score_override"
  | "invitation_sent"
  | "role_created"
  | "role_updated"
  | "candidate_shortlisted"
  | "interview_completed";

export type AuditEntityType =
  | "candidate_profile"
  | "job_role"
  | "scoring_rubric"
  | "interview_score"
  | "invitation"
  | "application";

interface LogAuditEventParams {
  action: AuditAction;
  entityType: AuditEntityType;
  entityId?: string;
  organisationId: string;
  oldValues?: Record<string, unknown> | null;
  newValues?: Record<string, unknown> | null;
}

export async function logAuditEvent({
  action,
  entityType,
  entityId,
  organisationId,
  oldValues,
  newValues,
}: LogAuditEventParams): Promise<boolean> {
  try {
    const user = await authApi.me();

    if (!user) {
      console.warn("No authenticated user for audit log");
      return false;
    }

    await auditApi.create({
      user_id: user.id,
      action,
      entity_type: entityType,
      entity_id: entityId || null,
      organisation_id: organisationId,
      old_values: oldValues || null,
      new_values: newValues || null,
    });

    return true;
  } catch (err) {
    console.error("Error logging audit event:", err);
    return false;
  }
}
