# Migration Plan + Mapping

## Edge Function → FastAPI Route Mapping

| Supabase Edge Function | FastAPI Route | Inputs / Outputs | Auth Rules | Tables | Frontend Call Sites |
| --- | --- | --- | --- | --- | --- |
| `ai-interviewer` | `POST /api/v1/interview/chat` | Input: interview context + messages. Output: streamed chat response. | Auth required (org member + interview access). | `interviews`, `applications`, `job_roles`, `candidate_profiles`, `transcript_segments` | `src/hooks/useInterviewChat.ts`, `src/hooks/useAcsCall.ts` |
| `score-interview` | `POST /api/v1/scoring/analyze` | Input: transcript + rubric + role details. Output: score summary + dimensions. | Auth required (org member). | `interviews`, `interview_scores`, `score_dimensions`, `job_roles` | `src/hooks/useInterviewScoring.ts` |
| `parse-resume` | `POST /api/v1/candidates/parse-resume` | Input: file reference or blob path. Output: parsed resume JSON. | Auth required (org member). | `candidate_profiles`, `candidate_skills`, `education`, `employment_history` | `src/hooks/useResumeParser.ts` |
| `extract-requirements` | `POST /api/v1/roles/extract-requirements` | Input: job description. Output: requirements JSON. | Auth required (org member). | `job_roles` | `src/hooks/useRoleRequirements.ts` |
| `generate-shortlist` | `POST /api/v1/shortlist/generate` | Input: role + applications. Output: ranked shortlist. | Auth required (org member). | `applications`, `job_roles`, `candidate_profiles` | `src/hooks/useShortlist.ts` |
| `acs-token-generator` | `POST /api/v1/acs/token` | Input: user identity. Output: ACS token + identity. | Auth required. | `interviews` | `src/hooks/useAcsToken.ts` |
| `acs-webhook-handler` | `POST /api/v1/acs/webhook` | Input: ACS event payload. Output: 200 OK. | Webhook key/validation. | `interviews`, `transcript_segments` | N/A (server-side webhook) |
| `azure-speech-token` | `POST /api/v1/speech/token` | Input: none. Output: speech token + region. | Auth optional (depending on client usage). | None | `src/hooks/useAzureSpeech.ts` |
| `send-invitation` | `POST /api/invitations` | Input: application ID + candidate email. Output: invitation token. | Auth required (org member). | `invitations`, `applications` | `src/hooks/useInvitation.ts` |
| `create-organisation` | `POST /api/orgs` | Input: org details. Output: org record. | Auth required. | `organisations`, `org_users`, `user_roles` | `src/hooks/useCreateOrganisation.ts` |
| `data-retention-cleanup` | `POST /api/v1/data-retention/cleanup` | Input: retention days. Output: cleanup report. | Admin-only (service). | `interviews`, `applications`, `candidate_profiles`, `data_deletion_requests` | N/A (scheduled job) |

## Supabase Table → SQLite Table Mapping

| Supabase Table | SQLite Table | Key Types / Indexes | Notes |
| --- | --- | --- | --- |
| `auth.users` | `users` | `id TEXT PK`, `email TEXT UNIQUE`, `password_hash TEXT` | Replace Supabase Auth with local user table + JWT.
| `organisations` | `organisations` | `id TEXT PK` | JSONB columns stored as `TEXT`.
| `org_users` | `org_users` | `organisation_id TEXT`, `user_id TEXT`, UNIQUE(org, user) | App-layer RLS checks in API.
| `job_roles` | `job_roles` | `organisation_id TEXT` index | JSONB fields stored as `TEXT`.
| `candidate_profiles` | `candidate_profiles` | `user_id TEXT UNIQUE` | Store visibility JSON as `TEXT`.
| `candidate_skills` | `candidate_skills` | `user_id TEXT` index | Straight mapping.
| `education` | `education` | `user_id TEXT` | Date fields stored as ISO strings.
| `employment_history` | `employment_history` | `user_id TEXT` | Date fields stored as ISO strings.
| `candidate_dei` | `candidate_dei` | `user_id TEXT` | Optional demographic fields.
| `applications` | `applications` | `job_role_id TEXT`, `candidate_profile_id TEXT` | Status stored as `TEXT`.
| `interviews` | `interviews` | `application_id TEXT` | Includes recording URL and status fields.
| `transcript_segments` | `transcript_segments` | `interview_id TEXT` | Ordered by `sequence`.
| `score_dimensions` | `score_dimensions` | `interview_id TEXT` | Score fields stored as `INTEGER`.
| `interview_scores` | `interview_scores` | `interview_id TEXT UNIQUE` | One summary per interview.
| `invitations` | `invitations` | `token TEXT UNIQUE`, `application_id TEXT` | Token index for lookup.
| `practice_interviews` | `practice_interviews` | `user_id TEXT` | JSON feedback stored as `TEXT`.
| `user_roles` | `user_roles` | `user_id TEXT` index | App-level roles (admin/recruiter/etc).
| `audit_log` | `audit_log` | `organisation_id TEXT`, `created_at` index | JSON before/after stored as `TEXT`.
| `data_deletion_requests` | `data_deletion_requests` | `user_id TEXT` | Track GDPR requests.
| `files` | `files` | `blob_path TEXT UNIQUE` | Azure Blob metadata, replaces Supabase Storage.
