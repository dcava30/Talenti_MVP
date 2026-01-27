import { auditApi } from "@/api/audit";
import { authApi } from "@/api/auth";
export async function logAuditEvent({ action, entityType, entityId, organisationId, oldValues, newValues, }) {
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
    }
    catch (err) {
        console.error("Error logging audit event:", err);
        return false;
    }
}
