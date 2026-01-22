import { supabase } from "@/integrations/supabase/client";
import type { Json } from "@/integrations/supabase/types";

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
  oldValues?: Json;
  newValues?: Json;
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
    const { data: { user } } = await supabase.auth.getUser();
    
    if (!user) {
      console.warn("No authenticated user for audit log");
      return false;
    }

    const { error } = await supabase.from("audit_log").insert([{
      user_id: user.id,
      action,
      entity_type: entityType,
      entity_id: entityId || null,
      organisation_id: organisationId,
      old_values: oldValues || null,
      new_values: newValues || null,
    }]);

    if (error) {
      console.error("Failed to log audit event:", error);
      return false;
    }

    return true;
  } catch (err) {
    console.error("Error logging audit event:", err);
    return false;
  }
}
