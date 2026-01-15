# Disaster Recovery & Backup Procedures

> **Version:** 1.0.0  
> **Last Updated:** January 2026  
> **Classification:** Internal Operations

## Overview

This document outlines backup strategies, disaster recovery procedures, and business continuity plans for the Talenti AI Interview Platform.

---

## Table of Contents

1. [Recovery Objectives](#recovery-objectives)
2. [Backup Strategy](#backup-strategy)
3. [Disaster Scenarios](#disaster-scenarios)
4. [Recovery Procedures](#recovery-procedures)
5. [Business Continuity](#business-continuity)
6. [Testing & Drills](#testing--drills)

---

## Recovery Objectives

### Recovery Time Objective (RTO)

| Tier | Systems | RTO Target |
|------|---------|------------|
| Tier 1 | Authentication, Core API | 1 hour |
| Tier 2 | Interview functionality | 4 hours |
| Tier 3 | Reporting, Analytics | 24 hours |
| Tier 4 | Non-critical features | 72 hours |

### Recovery Point Objective (RPO)

| Data Type | RPO Target | Backup Frequency |
|-----------|------------|------------------|
| User accounts | 0 (real-time) | Continuous |
| Interview data | 1 hour | Hourly snapshots |
| Recordings | 24 hours | Daily backup |
| Analytics | 24 hours | Daily export |

---

## Backup Strategy

### Database Backups (Automatic)

Lovable Cloud (Supabase) provides automatic backups:

| Plan | Point-in-Time Recovery | Backup Retention |
|------|------------------------|------------------|
| Free | Daily backups | 7 days |
| Pro | Point-in-time (any point) | 7 days |
| Team | Point-in-time | 14 days |
| Enterprise | Point-in-time | 30 days |

### Manual Backup Procedures

#### Export Critical Data

```sql
-- Export organisations
COPY (
  SELECT * FROM organisations 
  WHERE updated_at > NOW() - INTERVAL '24 hours'
) TO '/tmp/organisations_backup.csv' WITH CSV HEADER;

-- Export job roles
COPY (
  SELECT * FROM job_roles 
  WHERE updated_at > NOW() - INTERVAL '24 hours'
) TO '/tmp/job_roles_backup.csv' WITH CSV HEADER;

-- Export applications with interviews
COPY (
  SELECT 
    a.*,
    i.status as interview_status,
    i.started_at,
    i.ended_at,
    i.duration_seconds,
    s.overall_score
  FROM applications a
  LEFT JOIN interviews i ON i.application_id = a.id
  LEFT JOIN interview_scores s ON s.interview_id = i.id
  WHERE a.updated_at > NOW() - INTERVAL '24 hours'
) TO '/tmp/applications_backup.csv' WITH CSV HEADER;
```

#### Storage Backup

Interview recordings and CVs are stored in Supabase Storage:

```typescript
// List all files for backup
const { data: recordings } = await supabase.storage
  .from('recordings')
  .list();

const { data: cvs } = await supabase.storage
  .from('candidate-cvs')
  .list();

// Download files for offline backup
for (const file of recordings) {
  const { data } = await supabase.storage
    .from('recordings')
    .download(file.name);
  // Save to backup location
}
```

### Backup Verification

Weekly verification checklist:

- [ ] Database backup completed successfully
- [ ] Point-in-time recovery tested (staging)
- [ ] Storage files accessible
- [ ] Edge function code in version control
- [ ] Secrets documented (not stored) in secure location

---

## Disaster Scenarios

### Scenario 1: Database Corruption

**Symptoms:**
- Query errors
- Data inconsistencies
- Missing records

**Impact:** High - Core functionality affected

**Recovery:**
1. Identify corruption scope
2. Restore from point-in-time backup
3. Replay transactions from audit log if needed
4. Verify data integrity

### Scenario 2: Supabase/Lovable Outage

**Symptoms:**
- API timeouts
- Authentication failures
- Dashboard inaccessible

**Impact:** Critical - Complete outage

**Recovery:**
1. Check Supabase status page
2. Notify users of outage
3. Wait for service restoration
4. Verify all functions operational

### Scenario 3: Edge Function Failure

**Symptoms:**
- Specific features not working
- 500 errors from functions

**Impact:** Medium - Feature-specific

**Recovery:**
1. Check function logs
2. Identify breaking change
3. Roll back to previous version
4. Deploy fix

### Scenario 4: Secret Compromise

**Symptoms:**
- Unexpected API usage
- Unauthorized access
- Cost spikes

**Impact:** Critical - Security breach

**Recovery:**
1. Immediately rotate compromised secrets
2. Review access logs
3. Notify affected parties
4. Conduct security review

### Scenario 5: Data Breach

**Symptoms:**
- Unauthorized data access
- PII exposure detected

**Impact:** Critical - Legal/compliance

**Recovery:**
1. Isolate affected systems
2. Assess breach scope
3. Notify authorities (within 72 hours per GDPR)
4. Notify affected users
5. Implement additional controls

---

## Recovery Procedures

### Database Recovery

#### Point-in-Time Recovery (PITR)

1. Access Lovable Cloud dashboard
2. Navigate to Database → Backups
3. Select recovery point (timestamp)
4. Click "Restore"
5. Verify data integrity after restore

#### Selective Table Recovery

```sql
-- Restore specific table from backup
-- 1. Create temporary connection to backup
-- 2. Copy data to production

INSERT INTO production.interviews 
SELECT * FROM backup.interviews 
WHERE id NOT IN (SELECT id FROM production.interviews);
```

### Edge Function Recovery

1. Functions are versioned in Git repository
2. Identify last working commit
3. Revert changes: `git revert <commit>`
4. Push to trigger auto-deploy
5. Verify function operational

### Storage Recovery

1. Access Storage section in dashboard
2. Check if files exist in "Deleted" section
3. Restore from deleted (30-day retention)
4. Or restore from external backup

### Secrets Recovery

1. Access Lovable Cloud → Secrets
2. Update secret value with new key
3. Rotate related credentials at source
4. Verify edge functions working
5. Revoke old credentials

---

## Business Continuity

### Communication Plan

| Audience | Channel | Responsibility | Timeline |
|----------|---------|----------------|----------|
| Internal Team | Slack/Email | Tech Lead | Immediate |
| Affected Users | In-app banner | Product | Within 1 hour |
| All Users | Status page | DevOps | Within 2 hours |
| Enterprise Clients | Direct email | Account Manager | Within 4 hours |

### Degraded Operation Modes

#### Mode 1: Read-Only

When database writes are affected:
- Disable new applications
- Disable interview starts
- Allow viewing existing data

#### Mode 2: No AI

When AI gateway is down:
- Disable AI interviewer
- Disable resume parsing
- Enable manual shortlisting

#### Mode 3: No Video

When Azure services are down:
- Disable live interviews
- Enable asynchronous video uploads (if implemented)
- Offer rescheduling

### Essential Contacts

| Role | Contact | Escalation |
|------|---------|------------|
| On-Call Engineer | Team rotation | 15 min |
| Tech Lead | Direct | 30 min |
| Product Manager | Direct | 1 hour |
| Security Lead | Direct | Immediate (breach) |

---

## Testing & Drills

### Quarterly Drill Schedule

| Quarter | Drill Type | Scenario |
|---------|------------|----------|
| Q1 | Database | Point-in-time recovery |
| Q2 | Function | Edge function rollback |
| Q3 | Full | Multi-component failure |
| Q4 | Security | Secret rotation |

### Drill Procedure

1. **Announce**: Notify team of planned drill
2. **Simulate**: Create failure condition (staging)
3. **Respond**: Execute recovery procedures
4. **Document**: Record time and issues
5. **Review**: Post-drill analysis
6. **Improve**: Update procedures

### Recovery Time Tracking

| Date | Scenario | RTO Target | Actual | Status |
|------|----------|------------|--------|--------|
| 2026-01-XX | DB Recovery Drill | 1 hour | TBD | Scheduled |

### Drill Checklist

```markdown
## Pre-Drill
- [ ] Notify stakeholders
- [ ] Confirm staging environment ready
- [ ] Have runbook accessible
- [ ] Assign roles

## During Drill
- [ ] Start timer
- [ ] Log all actions
- [ ] Note any blockers
- [ ] Test verification steps

## Post-Drill
- [ ] Record completion time
- [ ] Document issues found
- [ ] Update procedures
- [ ] Share learnings
```

---

## Appendix: Runbook Templates

### Database Recovery Runbook

```markdown
# Database Recovery

## Trigger
- Data corruption detected
- Accidental deletion
- Required rollback

## Steps
1. [ ] Assess scope of data loss
2. [ ] Identify recovery point needed
3. [ ] Navigate to Lovable Cloud → Database → Backups
4. [ ] Select appropriate backup/timestamp
5. [ ] Initiate recovery (note: may cause brief outage)
6. [ ] Verify data integrity with spot checks
7. [ ] Test critical flows (login, interview start)
8. [ ] Notify team of completion

## Verification Queries
```sql
SELECT COUNT(*) FROM organisations;
SELECT COUNT(*) FROM interviews WHERE created_at > NOW() - INTERVAL '1 day';
SELECT MAX(created_at) FROM applications;
```

## Escalation
- If recovery fails: Contact Supabase support
- If data loss confirmed: Initiate breach procedure
```

### Secret Rotation Runbook

```markdown
# Secret Rotation

## Trigger
- Scheduled rotation
- Suspected compromise
- Employee departure

## Steps
1. [ ] Generate new secret/key at source
2. [ ] Update secret in Lovable Cloud → Secrets
3. [ ] Trigger function redeployment
4. [ ] Verify functions working with new secret
5. [ ] Revoke old secret at source
6. [ ] Update documentation
7. [ ] Log rotation in security log

## Secrets Checklist
- [ ] ACS_CONNECTION_STRING
- [ ] ACS_WEBHOOK_SECRET
- [ ] AZURE_SPEECH_KEY
- [ ] RESEND_API_KEY

## Verification
- Test ACS token generation
- Send test invitation email
- Test speech-to-text
```

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-13 | System | Initial version |

**Next Review Date:** 2026-04-13 (Quarterly)
