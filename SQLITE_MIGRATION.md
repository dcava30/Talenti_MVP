# SQLite Migration Document

This document provides a complete reference for migrating the Talenti Supabase database schema to SQLite. It includes all tables, columns, relationships, and security policies that would need to be reimplemented.

> **Important Notes:**
> - SQLite does not support Row-Level Security (RLS) natively. Security must be implemented at the application layer.
> - SQLite uses different data types. This document includes type mappings.
> - UUIDs are stored as TEXT in SQLite.
> - JSONB columns become TEXT with JSON validation in the application.
> - Enums become TEXT with CHECK constraints or application-level validation.

---

## Table of Contents

1. [Type Mappings](#type-mappings)
2. [Enums](#enums)
3. [Tables](#tables)
4. [Foreign Keys](#foreign-keys)
5. [Indexes](#indexes)
6. [Functions (Application Layer)](#functions-application-layer)
7. [RLS Policies (Application Layer)](#rls-policies-application-layer)
8. [Triggers](#triggers)

---

## Type Mappings

| PostgreSQL Type | SQLite Type | Notes |
|-----------------|-------------|-------|
| `uuid` | `TEXT` | Store as lowercase hex with hyphens |
| `text` | `TEXT` | Direct mapping |
| `integer` | `INTEGER` | Direct mapping |
| `numeric` | `REAL` | SQLite uses REAL for decimals |
| `boolean` | `INTEGER` | 0 = false, 1 = true |
| `jsonb` | `TEXT` | Store as JSON string, parse in app |
| `timestamp with time zone` | `TEXT` | Store as ISO 8601 string |
| `date` | `TEXT` | Store as YYYY-MM-DD |
| `USER-DEFINED` (enum) | `TEXT` | Use CHECK constraints |

---

## Enums

### app_role
```sql
-- PostgreSQL
CREATE TYPE app_role AS ENUM ('org_admin', 'org_recruiter', 'org_viewer', 'candidate');

-- SQLite equivalent (use CHECK constraint on columns)
CHECK (role IN ('org_admin', 'org_recruiter', 'org_viewer', 'candidate'))
```

### interview_status
```sql
-- PostgreSQL
CREATE TYPE interview_status AS ENUM (
  'invited', 'scheduled', 'in_progress', 'completed', 'cancelled', 'expired'
);

-- SQLite equivalent
CHECK (status IN ('invited', 'scheduled', 'in_progress', 'completed', 'cancelled', 'expired'))
```

### invitation_status
```sql
-- PostgreSQL
CREATE TYPE invitation_status AS ENUM (
  'pending', 'sent', 'delivered', 'opened', 'bounced', 'expired'
);

-- SQLite equivalent
CHECK (status IN ('pending', 'sent', 'delivered', 'opened', 'bounced', 'expired'))
```

### job_role_status
```sql
-- PostgreSQL
CREATE TYPE job_role_status AS ENUM ('draft', 'active', 'paused', 'closed');

-- SQLite equivalent
CHECK (status IN ('draft', 'active', 'paused', 'closed'))
```

---

## Tables

### organisations

```sql
CREATE TABLE organisations (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
  name TEXT NOT NULL,
  industry TEXT,
  website TEXT,
  logo_url TEXT,
  description TEXT,
  billing_email TEXT,
  billing_address TEXT,
  values_framework TEXT, -- JSON string
  recording_retention_days INTEGER DEFAULT 60,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_organisations_name ON organisations(name);
```

### org_users

```sql
CREATE TABLE org_users (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
  user_id TEXT NOT NULL,
  organisation_id TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'recruiter' CHECK (role IN ('admin', 'recruiter', 'hiring_manager', 'viewer')),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (organisation_id) REFERENCES organisations(id) ON DELETE CASCADE,
  UNIQUE (user_id, organisation_id)
);

CREATE INDEX idx_org_users_user_id ON org_users(user_id);
CREATE INDEX idx_org_users_org_id ON org_users(organisation_id);
```

### user_roles

```sql
CREATE TABLE user_roles (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
  user_id TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('org_admin', 'org_recruiter', 'org_viewer', 'candidate')),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (user_id, role)
);

CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);
```

### job_roles

```sql
CREATE TABLE job_roles (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
  organisation_id TEXT NOT NULL,
  title TEXT NOT NULL,
  department TEXT,
  industry TEXT,
  work_type TEXT,
  location TEXT,
  employment_type TEXT,
  description TEXT,
  salary_range_min INTEGER,
  salary_range_max INTEGER,
  requirements TEXT, -- JSON string
  interview_structure TEXT, -- JSON string
  scoring_rubric TEXT, -- JSON string
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'paused', 'closed')),
  created_by TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (organisation_id) REFERENCES organisations(id) ON DELETE CASCADE
);

CREATE INDEX idx_job_roles_org_id ON job_roles(organisation_id);
CREATE INDEX idx_job_roles_status ON job_roles(status);
CREATE INDEX idx_job_roles_created_at ON job_roles(created_at);
```

### candidate_profiles

```sql
CREATE TABLE candidate_profiles (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
  user_id TEXT NOT NULL UNIQUE,
  first_name TEXT,
  last_name TEXT,
  email TEXT,
  phone TEXT,
  suburb TEXT,
  postcode TEXT,
  state TEXT,
  country TEXT DEFAULT 'Australia',
  work_rights TEXT,
  availability TEXT,
  work_mode TEXT,
  portfolio_url TEXT,
  linkedin_url TEXT,
  cv_file_path TEXT,
  cv_uploaded_at TEXT,
  gpa_wam REAL,
  profile_visibility TEXT DEFAULT 'visible',
  visibility_settings TEXT DEFAULT '{"name": true, "email": false, "phone": false, "skills": true, "linkedin": true, "location": true, "education": true, "portfolio": true, "employment": true}', -- JSON string
  paused_at TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_candidate_profiles_user_id ON candidate_profiles(user_id);
CREATE INDEX idx_candidate_profiles_visibility ON candidate_profiles(profile_visibility);
```

### candidate_skills

```sql
CREATE TABLE candidate_skills (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
  user_id TEXT NOT NULL,
  skill_name TEXT NOT NULL,
  skill_type TEXT NOT NULL CHECK (skill_type IN ('hard', 'soft', 'technical', 'language')),
  proficiency_level TEXT CHECK (proficiency_level IN ('beginner', 'intermediate', 'advanced', 'expert')),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (user_id, skill_name)
);

CREATE INDEX idx_candidate_skills_user_id ON candidate_skills(user_id);
```

### employment_history

```sql
CREATE TABLE employment_history (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
  user_id TEXT NOT NULL,
  job_title TEXT NOT NULL,
  company_name TEXT NOT NULL,
  description TEXT,
  start_date TEXT NOT NULL, -- YYYY-MM-DD
  end_date TEXT, -- YYYY-MM-DD
  is_current INTEGER DEFAULT 0, -- boolean
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_employment_history_user_id ON employment_history(user_id);
CREATE INDEX idx_employment_history_start_date ON employment_history(start_date);
```

### education

```sql
CREATE TABLE education (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
  user_id TEXT NOT NULL,
  institution TEXT NOT NULL,
  degree TEXT NOT NULL,
  field_of_study TEXT,
  start_date TEXT, -- YYYY-MM-DD
  end_date TEXT, -- YYYY-MM-DD
  is_current INTEGER DEFAULT 0, -- boolean
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_education_user_id ON education(user_id);
```

### candidate_dei

```sql
CREATE TABLE candidate_dei (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
  user_id TEXT NOT NULL UNIQUE,
  gender TEXT,
  ethnicity TEXT,
  disability_status TEXT,
  veteran_status TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_candidate_dei_user_id ON candidate_dei(user_id);
```

### applications

```sql
CREATE TABLE applications (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
  candidate_id TEXT NOT NULL,
  job_role_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'applied',
  match_score REAL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (job_role_id) REFERENCES job_roles(id) ON DELETE CASCADE,
  UNIQUE (candidate_id, job_role_id)
);

CREATE INDEX idx_applications_candidate_id ON applications(candidate_id);
CREATE INDEX idx_applications_job_role_id ON applications(job_role_id);
CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_applications_created_at ON applications(created_at);
```

### invitations

```sql
CREATE TABLE invitations (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
  application_id TEXT NOT NULL,
  token TEXT NOT NULL UNIQUE,
  email_template TEXT,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'delivered', 'opened', 'bounced', 'expired')),
  sent_at TEXT,
  opened_at TEXT,
  expires_at TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
);

CREATE INDEX idx_invitations_application_id ON invitations(application_id);
CREATE INDEX idx_invitations_token ON invitations(token);
CREATE INDEX idx_invitations_status ON invitations(status);
CREATE INDEX idx_invitations_expires_at ON invitations(expires_at);
```

### interviews

```sql
CREATE TABLE interviews (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
  application_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'invited' CHECK (status IN ('invited', 'scheduled', 'in_progress', 'completed', 'cancelled', 'expired')),
  started_at TEXT,
  ended_at TEXT,
  duration_seconds INTEGER,
  recording_url TEXT,
  recording_deleted_at TEXT,
  anti_cheat_signals TEXT DEFAULT '[]', -- JSON array
  metadata TEXT DEFAULT '{}', -- JSON object
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
);

CREATE INDEX idx_interviews_application_id ON interviews(application_id);
CREATE INDEX idx_interviews_status ON interviews(status);
CREATE INDEX idx_interviews_created_at ON interviews(created_at);
```

### interview_scores

```sql
CREATE TABLE interview_scores (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
  interview_id TEXT NOT NULL UNIQUE,
  overall_score REAL,
  narrative_summary TEXT,
  candidate_feedback TEXT,
  anti_cheat_risk_level TEXT,
  scored_by TEXT DEFAULT 'ai',
  model_version TEXT,
  prompt_version TEXT,
  rubric_version TEXT,
  human_override INTEGER DEFAULT 0, -- boolean
  human_override_by TEXT,
  human_override_reason TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (interview_id) REFERENCES interviews(id) ON DELETE CASCADE
);

CREATE INDEX idx_interview_scores_interview_id ON interview_scores(interview_id);
CREATE INDEX idx_interview_scores_overall_score ON interview_scores(overall_score);
```

### score_dimensions

```sql
CREATE TABLE score_dimensions (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
  interview_id TEXT NOT NULL,
  dimension TEXT NOT NULL,
  score REAL NOT NULL,
  weight REAL DEFAULT 1.0,
  evidence TEXT,
  cited_quotes TEXT DEFAULT '[]', -- JSON array
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (interview_id) REFERENCES interviews(id) ON DELETE CASCADE,
  UNIQUE (interview_id, dimension)
);

CREATE INDEX idx_score_dimensions_interview_id ON score_dimensions(interview_id);
```

### transcript_segments

```sql
CREATE TABLE transcript_segments (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
  interview_id TEXT NOT NULL,
  speaker TEXT NOT NULL CHECK (speaker IN ('ai', 'candidate')),
  content TEXT NOT NULL,
  start_time_ms INTEGER NOT NULL,
  end_time_ms INTEGER,
  confidence REAL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (interview_id) REFERENCES interviews(id) ON DELETE CASCADE
);

CREATE INDEX idx_transcript_segments_interview_id ON transcript_segments(interview_id);
CREATE INDEX idx_transcript_segments_start_time ON transcript_segments(start_time_ms);
```

### practice_interviews

```sql
CREATE TABLE practice_interviews (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
  user_id TEXT NOT NULL,
  sample_role_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'not_started',
  started_at TEXT,
  ended_at TEXT,
  duration_seconds INTEGER,
  feedback TEXT DEFAULT '{}', -- JSON object
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_practice_interviews_user_id ON practice_interviews(user_id);
CREATE INDEX idx_practice_interviews_status ON practice_interviews(status);
```

### audit_log

```sql
CREATE TABLE audit_log (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
  user_id TEXT,
  organisation_id TEXT,
  action TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id TEXT,
  old_values TEXT, -- JSON object
  new_values TEXT, -- JSON object
  ip_address TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (organisation_id) REFERENCES organisations(id) ON DELETE SET NULL
);

CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_org_id ON audit_log(organisation_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_entity_type ON audit_log(entity_type);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);
```

### data_deletion_requests

```sql
CREATE TABLE data_deletion_requests (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
  user_id TEXT NOT NULL,
  request_type TEXT NOT NULL DEFAULT 'full_deletion' CHECK (request_type IN ('full_deletion', 'recording_only', 'anonymize')),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'completed', 'rejected')),
  reason TEXT,
  notes TEXT,
  processed_by TEXT,
  requested_at TEXT NOT NULL DEFAULT (datetime('now')),
  processed_at TEXT
);

CREATE INDEX idx_deletion_requests_user_id ON data_deletion_requests(user_id);
CREATE INDEX idx_deletion_requests_status ON data_deletion_requests(status);
```

---

## Foreign Keys Summary

| Table | Column | References |
|-------|--------|------------|
| `org_users` | `organisation_id` | `organisations(id)` |
| `job_roles` | `organisation_id` | `organisations(id)` |
| `applications` | `job_role_id` | `job_roles(id)` |
| `invitations` | `application_id` | `applications(id)` |
| `interviews` | `application_id` | `applications(id)` |
| `interview_scores` | `interview_id` | `interviews(id)` |
| `score_dimensions` | `interview_id` | `interviews(id)` |
| `transcript_segments` | `interview_id` | `interviews(id)` |
| `audit_log` | `organisation_id` | `organisations(id)` |

---

## Functions (Application Layer)

These PostgreSQL functions must be reimplemented in your application code:

### user_belongs_to_org(user_id, org_id) → boolean

```javascript
// JavaScript/TypeScript implementation
async function userBelongsToOrg(db, userId, orgId) {
  const result = await db.get(
    'SELECT 1 FROM org_users WHERE user_id = ? AND organisation_id = ?',
    [userId, orgId]
  );
  return !!result;
}
```

### user_org_role(user_id, org_id) → text

```javascript
async function userOrgRole(db, userId, orgId) {
  const result = await db.get(
    'SELECT role FROM org_users WHERE user_id = ? AND organisation_id = ? LIMIT 1',
    [userId, orgId]
  );
  return result?.role || null;
}
```

### get_user_org_id(user_id) → uuid

```javascript
async function getUserOrgId(db, userId) {
  const result = await db.get(
    'SELECT organisation_id FROM org_users WHERE user_id = ? LIMIT 1',
    [userId]
  );
  return result?.organisation_id || null;
}
```

### has_role(user_id, role) → boolean

```javascript
async function hasRole(db, userId, role) {
  const result = await db.get(
    'SELECT 1 FROM user_roles WHERE user_id = ? AND role = ?',
    [userId, role]
  );
  return !!result;
}
```

### update_updated_at_column() - Trigger Function

```javascript
// Implement as middleware or use SQLite triggers
// See Triggers section below
```

---

## RLS Policies (Application Layer)

SQLite does not support Row-Level Security. These policies must be implemented in your application's data access layer.

### Authorization Middleware Pattern

```typescript
// Example middleware for checking access
interface AuthContext {
  userId: string;
  orgId?: string;
  role?: string;
}

class DataAccessLayer {
  constructor(private db: Database, private auth: AuthContext) {}

  // organisations
  async getOrganisation(id: string) {
    // Check: user belongs to org OR user has application for a role in org
    const belongsToOrg = await userBelongsToOrg(this.db, this.auth.userId, id);
    const hasApplication = await this.db.get(`
      SELECT 1 FROM applications a
      JOIN job_roles jr ON jr.id = a.job_role_id
      WHERE a.candidate_id = ? AND jr.organisation_id = ?
    `, [this.auth.userId, id]);
    
    if (!belongsToOrg && !hasApplication) {
      throw new Error('Unauthorized');
    }
    
    return this.db.get('SELECT * FROM organisations WHERE id = ?', [id]);
  }

  // job_roles
  async getJobRoles(orgId: string) {
    const belongsToOrg = await userBelongsToOrg(this.db, this.auth.userId, orgId);
    if (!belongsToOrg) {
      // Only return active roles for non-members
      return this.db.all(
        'SELECT * FROM job_roles WHERE organisation_id = ? AND status = ?',
        [orgId, 'active']
      );
    }
    return this.db.all(
      'SELECT * FROM job_roles WHERE organisation_id = ?',
      [orgId]
    );
  }

  // applications
  async getApplications(roleId: string) {
    // Check if user is org member for this role
    const role = await this.db.get(
      'SELECT organisation_id FROM job_roles WHERE id = ?',
      [roleId]
    );
    const belongsToOrg = await userBelongsToOrg(
      this.db, this.auth.userId, role.organisation_id
    );
    
    if (!belongsToOrg) {
      // Only return user's own applications
      return this.db.all(
        'SELECT * FROM applications WHERE job_role_id = ? AND candidate_id = ?',
        [roleId, this.auth.userId]
      );
    }
    return this.db.all(
      'SELECT * FROM applications WHERE job_role_id = ?',
      [roleId]
    );
  }

  // candidate_profiles
  async getCandidateProfile(userId: string) {
    // Owner can always view
    if (userId === this.auth.userId) {
      return this.db.get(
        'SELECT * FROM candidate_profiles WHERE user_id = ?',
        [userId]
      );
    }
    
    // Org members can view if candidate has application for their roles
    const hasAccess = await this.db.get(`
      SELECT 1 FROM applications a
      JOIN job_roles jr ON jr.id = a.job_role_id
      JOIN org_users ou ON ou.organisation_id = jr.organisation_id
      WHERE a.candidate_id = ? AND ou.user_id = ?
    `, [userId, this.auth.userId]);
    
    if (!hasAccess) {
      throw new Error('Unauthorized');
    }
    
    // Return with visibility settings applied
    const profile = await this.db.get(
      'SELECT * FROM candidate_profiles WHERE user_id = ?',
      [userId]
    );
    return this.applyVisibilitySettings(profile);
  }

  private applyVisibilitySettings(profile: any) {
    const settings = JSON.parse(profile.visibility_settings || '{}');
    const filtered = { ...profile };
    
    if (!settings.email) filtered.email = null;
    if (!settings.phone) filtered.phone = null;
    // ... apply other visibility rules
    
    return filtered;
  }
}
```

### Policy Reference by Table

#### organisations
| Operation | Policy |
|-----------|--------|
| SELECT | User belongs to org OR user has application for role in org |
| INSERT | User is authenticated |
| UPDATE | User is org admin |
| DELETE | Not allowed |

#### org_users
| Operation | Policy |
|-----------|--------|
| SELECT | User belongs to org |
| INSERT | User is org admin OR first user in org |
| UPDATE | User is org admin |
| DELETE | User is org admin |

#### job_roles
| Operation | Policy |
|-----------|--------|
| SELECT | User belongs to org OR status = 'active' |
| INSERT | User role is admin/recruiter/hiring_manager |
| UPDATE | User role is admin/recruiter/hiring_manager |
| DELETE | User is org admin |

#### candidate_profiles
| Operation | Policy |
|-----------|--------|
| SELECT | Owner OR org member with application |
| INSERT | Owner only |
| UPDATE | Owner only |
| DELETE | Owner only |

#### applications
| Operation | Policy |
|-----------|--------|
| SELECT | Owner OR org member |
| INSERT | Owner only |
| UPDATE | Org member |
| DELETE | Not allowed |

#### interviews
| Operation | Policy |
|-----------|--------|
| SELECT | Owner (via application) OR org member |
| INSERT | Owner (via application) |
| UPDATE | Owner OR org member |
| DELETE | Not allowed |

#### interview_scores
| Operation | Policy |
|-----------|--------|
| SELECT | Owner OR org member |
| INSERT | Owner OR org member |
| UPDATE | Org admin/recruiter/hiring_manager |
| DELETE | Not allowed |

---

## Triggers

### updated_at Trigger

```sql
-- Create trigger for each table with updated_at column
CREATE TRIGGER update_organisations_updated_at 
  AFTER UPDATE ON organisations
  FOR EACH ROW
  BEGIN
    UPDATE organisations SET updated_at = datetime('now') WHERE id = NEW.id;
  END;

CREATE TRIGGER update_job_roles_updated_at 
  AFTER UPDATE ON job_roles
  FOR EACH ROW
  BEGIN
    UPDATE job_roles SET updated_at = datetime('now') WHERE id = NEW.id;
  END;

CREATE TRIGGER update_candidate_profiles_updated_at 
  AFTER UPDATE ON candidate_profiles
  FOR EACH ROW
  BEGIN
    UPDATE candidate_profiles SET updated_at = datetime('now') WHERE id = NEW.id;
  END;

CREATE TRIGGER update_applications_updated_at 
  AFTER UPDATE ON applications
  FOR EACH ROW
  BEGIN
    UPDATE applications SET updated_at = datetime('now') WHERE id = NEW.id;
  END;

CREATE TRIGGER update_interviews_updated_at 
  AFTER UPDATE ON interviews
  FOR EACH ROW
  BEGIN
    UPDATE interviews SET updated_at = datetime('now') WHERE id = NEW.id;
  END;

CREATE TRIGGER update_interview_scores_updated_at 
  AFTER UPDATE ON interview_scores
  FOR EACH ROW
  BEGIN
    UPDATE interview_scores SET updated_at = datetime('now') WHERE id = NEW.id;
  END;
```

---

## Migration Script

Here's a complete SQLite migration script that creates all tables:

```sql
-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- Run all CREATE TABLE statements from above in order:
-- 1. organisations (no dependencies)
-- 2. org_users (depends on organisations)
-- 3. user_roles (no dependencies)
-- 4. job_roles (depends on organisations)
-- 5. candidate_profiles (no dependencies)
-- 6. candidate_skills (no dependencies)
-- 7. employment_history (no dependencies)
-- 8. education (no dependencies)
-- 9. candidate_dei (no dependencies)
-- 10. applications (depends on job_roles)
-- 11. invitations (depends on applications)
-- 12. interviews (depends on applications)
-- 13. interview_scores (depends on interviews)
-- 14. score_dimensions (depends on interviews)
-- 15. transcript_segments (depends on interviews)
-- 16. practice_interviews (no dependencies)
-- 17. audit_log (depends on organisations)
-- 18. data_deletion_requests (no dependencies)

-- Then create all indexes
-- Then create all triggers
```

---

## Data Migration

To migrate existing data from Supabase PostgreSQL to SQLite:

1. Export data from each table as JSON or CSV
2. Transform UUIDs to lowercase TEXT
3. Transform timestamps to ISO 8601 strings
4. Transform JSONB to JSON strings
5. Transform booleans to 0/1
6. Import into SQLite tables in dependency order

```bash
# Example using pg_dump and conversion
pg_dump -t table_name --data-only --column-inserts > table_data.sql
# Then convert PostgreSQL syntax to SQLite syntax
```

---

## Additional Considerations

### Authentication
- Supabase Auth is not available in SQLite
- Implement your own auth system or use a library like Passport.js, Auth.js
- Store user sessions in a separate `sessions` table

### File Storage
- Supabase Storage is not available
- Use local filesystem or S3-compatible storage
- Update `cv_file_path` to reference new storage location

### Real-time
- Supabase Realtime is not available
- Use WebSockets with libraries like Socket.io
- Or implement polling for real-time updates

### Edge Functions
- Supabase Edge Functions are not available
- Deploy as regular API endpoints (Express, Fastify, etc.)
- Or use serverless platforms (Vercel, Netlify, AWS Lambda)
