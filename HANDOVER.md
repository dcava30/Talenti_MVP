# Handover Document: Talenti AI Recruitment Platform

## 1. Executive Summary

This document provides a complete handover for the **Talenti** application - an AI-powered recruitment platform built with React, TypeScript, Vite, and Tailwind CSS on the frontend, with a Supabase backend (via Lovable Cloud) providing database, authentication, storage, and edge functions.

The platform enables:
- **Organisations** to create job roles, manage candidates, send interview invitations, and review AI-scored interviews
- **Candidates** to complete AI-powered video interviews, manage their profiles, and practice interviews

---

## 2. Technology Stack

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| React | ^18.3.1 | UI framework |
| TypeScript | - | Type safety |
| Vite | - | Build tooling |
| Tailwind CSS | - | Utility-first styling |
| shadcn/ui | - | Component library (Radix UI) |
| TanStack React Query | ^5.83.0 | Data fetching and caching |
| React Router DOM | ^6.30.1 | Client-side routing |
| Zod | ^3.25.76 | Schema validation |
| React Hook Form | ^7.61.1 | Form management |

### Backend (Lovable Cloud / Supabase)
- **PostgreSQL Database** with Row-Level Security (RLS)
- **Supabase Auth** for user authentication
- **Supabase Storage** for CV uploads
- **Edge Functions** (Deno runtime) for serverless backend logic

### AI/Communication Services
| Service | Purpose |
|---------|---------|
| Lovable AI Gateway | AI features (Gemini 2.5 Flash) |
| Azure Communication Services (ACS) | Video calling |
| Azure Speech SDK | Speech-to-text and text-to-speech |
| Azure AI Avatar | Animated interviewer avatar |
| Resend | Email delivery |

---

## 3. Application Structure

### 3.1 Entry Points

| File | Purpose |
|------|---------|
| `src/main.tsx` | React DOM render entry point, wraps App with QueryClientProvider |
| `src/App.tsx` | Root component with BrowserRouter, Toaster, and all route definitions |
| `index.html` | HTML shell with meta tags and root div |

### 3.2 Route Configuration (src/App.tsx)

#### Public Routes
| Route | Component | Description |
|-------|-----------|-------------|
| `/` | `Index` | Landing page with features, hero section |
| `/auth` | `Auth` | Authentication (sign up/sign in) |
| `/invite/:token` | `InviteValidation` | Validates invitation tokens |

#### Organisation Routes
| Route | Component | Description |
|-------|-----------|-------------|
| `/org` | `OrgDashboard` | Organisation dashboard with stats |
| `/org/onboarding` | `OrgOnboarding` | New organisation setup wizard |
| `/org/settings` | `OrgSettings` | Organisation settings, audit trail, data retention |
| `/org/new-role` | `NewRole` | Create new job role |
| `/org/role/:roleId` | `RoleDetails` | View role candidates, send invitations |
| `/org/role/:roleId/rubric` | `EditRoleRubric` | Customize scoring weights |
| `/org/interview/:interviewId` | `InterviewReport` | View interview results and transcript |

#### Candidate Routes
| Route | Component | Description |
|-------|-----------|-------------|
| `/candidate/portal` | `CandidatePortal` | Candidate dashboard |
| `/candidate/profile` | `CandidateProfile` | Edit profile, upload CV |
| `/candidate/practice` | `PracticeInterview` | Practice interview session |
| `/candidate/practice/complete` | `PracticeInterviewComplete` | Practice completion screen |
| `/candidate/:inviteId/lobby` | `InterviewLobby` | Device check before interview |
| `/candidate/:inviteId/live` | `LiveInterview` | Live AI interview session |
| `/candidate/:inviteId` | `CandidateInterview` | Interview landing page |
| `/candidate/complete` | `InterviewComplete` | Interview completion with scoring |

---

## 4. Page Components (src/pages/)

### 4.1 Index.tsx (Landing Page)
**Purpose:** Marketing landing page for the platform.

**Features:**
- Hero section with "AI-Powered Recruitment" messaging
- Two user entry points: Candidate vs Organisation buttons
- Features section highlighting async video interviews, AI scoring, resume parsing
- Animated gradient backgrounds
- Footer with company info

**Key Dependencies:** None (static page)

---

### 4.2 Auth.tsx (Authentication)
**Purpose:** User authentication for both candidates and organisations.

**Features:**
- User type selector (Candidate/Organisation toggle)
- Sign In and Sign Up tabs with form switching
- Zod schema validation for email/password
- Supabase Auth integration with `signInWithPassword` and `signUp`
- Auto-redirect based on user type:
  - Candidates → `/candidate/portal`
  - Org users → `/org` (or `/org/onboarding` if no org)

**Key Functions:**
```typescript
handleSignIn(values) // Signs in user, redirects based on type
handleSignUp(values) // Creates account, adds user_role, redirects
```

**Database Interactions:**
- `user_roles` table: Creates candidate role on signup
- `org_users` table: Checks org membership for org users

---

### 4.3 OrgDashboard.tsx (Organisation Dashboard)
**Purpose:** Main dashboard for organisation users showing overview stats and job roles.

**Features:**
- Stats cards: Active roles, Total candidates, Completed interviews, Avg score
- Job roles list with status badges (active, draft, paused, closed)
- Navigation to create roles, settings, individual role details
- Loading skeleton states

**Hooks Used:**
- `useCurrentOrg()` - Get current user's organisation
- `useJobRoles(orgId)` - Get all job roles
- `useOrgStats(orgId)` - Get aggregate statistics

**Database Queries:**
- `job_roles` table with org filter
- `applications` table for candidate counts
- `interviews` table for interview stats
- `interview_scores` table for avg scores

---

### 4.4 OrgOnboarding.tsx (Organisation Setup)
**Purpose:** Two-step wizard for new organisation creation.

**Step 1 - Basic Info:**
- Organisation name (required)
- Industry selection
- Website URL

**Step 2 - Additional Details:**
- Description
- Billing email

**Key Functions:**
```typescript
handleSubmit() // Calls create-organisation edge function
```

**Edge Function:** `create-organisation`
- Creates organisation record
- Adds current user as admin in `org_users`

---

### 4.5 OrgSettings.tsx (Organisation Settings)
**Purpose:** Organisation configuration and management.

**Tabs:**
1. **General** - Basic org info editing
2. **Data Retention** - Recording retention settings (`OrgDataRetentionSettings`)
3. **Audit Trail** - Action logs (`AuditTrailViewer`)
4. **Notifications** - Email preferences (placeholder)

**Components Used:**
- `OrgDataRetentionSettings` - Configure recording retention days
- `AuditTrailViewer` - Paginated audit log viewer

---

### 4.6 NewRole.tsx (Create Job Role)
**Purpose:** Job role creation with AI-powered requirements extraction.

**Form Fields:**
- Title, Department, Work type, Location
- Salary range (min/max)
- Employment type
- Job description (textarea)

**AI Feature - Requirements Extraction:**
```typescript
extractRequirements() // Calls extract-requirements edge function
```
Returns structured data:
- Skills (technical/soft)
- Experience requirements
- Qualifications
- Responsibilities
- Suggested interview questions

**Scoring Weights Configuration:**
- Technical Skills (default 25%)
- Culture Fit (default 20%)
- Motivation (default 20%)
- Communication (default 20%)
- Salary Alignment (default 15%)

**Database:** Saves to `job_roles` table with:
- `requirements` JSON field
- `scoring_rubric` JSON field
- `interview_structure` JSON field

---

### 4.7 RoleDetails.tsx (Role Candidate Management)
**Purpose:** View and manage candidates for a specific job role.

**Features:**
- Role info header with stats
- Candidate applications table with:
  - Name, Email, Match score, Status, Actions
- **AI Shortlist Generation** - `generate-shortlist` edge function
- **Candidate Comparison** - Side-by-side view (`CandidateComparison`)
- **Send Invitation** - Email interview invites (`SendInvitationDialog`)
- **PDF Report Download** - Generate interview reports
- Links to individual interview reports

**Hooks Used:**
- `useJobRole(roleId)` - Get role details
- `useRoleApplications(roleId)` - Get applications
- `useShortlist()` - Generate AI shortlist

**Components:**
- `ShortlistView` - Displays AI-ranked candidates
- `SendInvitationDialog` - Modal for sending invites
- `CandidateComparison` - Compare selected candidates

---

### 4.8 EditRoleRubric.tsx (Scoring Rubric Editor)
**Purpose:** Customize interview scoring weights for a role.

**Dimensions:**
| Dimension | Default Weight | Description |
|-----------|----------------|-------------|
| Technical Skills | 25% | Role-specific technical competencies |
| Culture Fit | 20% | Alignment with company values |
| Motivation | 20% | Interest and enthusiasm for role |
| Communication | 20% | Clarity and articulation |
| Salary Alignment | 15% | Expectations vs budget |

**Features:**
- Slider controls for each weight
- Real-time total calculation (must equal 100%)
- Save to `job_roles.scoring_rubric`

---

### 4.9 InterviewReport.tsx (Interview Results)
**Purpose:** Detailed view of a completed interview.

**Sections:**
1. **Header** - Candidate info, interview date, duration
2. **Overall Score** - Large score display with risk level
3. **Narrative Summary** - AI-generated interview summary
4. **Dimension Scores** - Breakdown by category with evidence
5. **Transcript** - Full interview transcript with timestamps
6. **Human Override** - Ability to adjust scores with reason

**Data Sources:**
- `interviews` table - Session metadata
- `interview_scores` table - Overall scores
- `score_dimensions` table - Individual dimensions
- `transcript_segments` table - Transcript

**Features:**
- Score override with reason (updates `human_override`, `human_override_by`, `human_override_reason`)
- Anti-cheat risk level display
- Expandable transcript sections

---

### 4.10 CandidatePortal.tsx (Candidate Dashboard)
**Purpose:** Main dashboard for candidates.

**Sections:**
1. **Profile Completion** - Progress indicator, link to profile
2. **Pending Invitations** - Interview invites to accept
3. **Applications** - List of job applications with status
4. **Practice Interviews** - Practice session history
5. **Interview Feedback** - Scores from completed interviews
6. **Privacy Settings** - Data retention preferences

**Hooks Used:**
- `useCandidateProfile()` - Profile data
- `useCandidateApplications()` - Applications list
- `useCandidateInvitations()` - Pending invites
- `useCandidateInterviewFeedback()` - Completed interview scores

**Components:**
- `DataRetentionSettings` - GDPR data preferences

---

### 4.11 CandidateProfile.tsx (Profile Editor)
**Purpose:** Complete profile management for candidates.

**Sections:**

**Personal Information:**
- First/Last name, Email, Phone
- Location (suburb, postcode, state, country)

**Work Preferences:**
- Work rights, Availability, Work mode (remote/hybrid/onsite)

**Employment History:**
- CRUD operations for work experience
- Fields: Company, Title, Start/End dates, Description, Current checkbox

**Education:**
- CRUD operations for education records
- Fields: Institution, Degree, Field of study, Start/End dates

**Skills:**
- Add/remove skills with type (hard/soft)
- Proficiency level

**CV Upload:**
```typescript
handleCVUpload(file) // Uploads to candidate-cvs bucket
parseCV() // Calls parse-resume edge function
```
- Uploads PDF to Supabase Storage
- AI parses CV and auto-fills profile sections

**Profile Visibility:**
- Toggle visibility for: name, email, phone, location, etc.
- `ProfileManagement` component

---

### 4.12 InterviewLobby.tsx (Pre-Interview Check)
**Purpose:** Device verification before starting interview.

**Checks:**
1. **Camera** - Request permission, show preview
2. **Microphone** - Request permission, show audio level
3. **Speaker** - Test audio output

**Additional Features:**
- Interview details display (role, company)
- Consent checkbox for recording
- Validates invitation token is still valid
- Start interview button (disabled until all checks pass)

**Navigation:**
- On start → `/candidate/:inviteId/live`

---

### 4.13 LiveInterview.tsx (AI Interview Session)
**Purpose:** Core interview experience with AI interviewer.

**Audio Modes:**
1. **Azure Speech SDK** (Primary) - High-quality STT/TTS
2. **Browser Web Speech API** (Fallback) - If Azure unavailable

**Key Components:**
- `AvatarRenderer` - Azure AI Avatar display
- `CallControls` - Mute/video controls
- `VideoRenderer` - ACS video tiles

**Hooks Used:**
- `useAzureSpeech()` - STT/TTS with Azure
- `useSpeechRecognition()` - Browser STT fallback
- `useSpeechSynthesis()` - Browser TTS fallback
- `useAzureAvatar()` - Avatar rendering
- `useAcsCall()` - Video call management
- `useInterviewPersistence()` - Save transcripts
- `useInterviewContext()` - Load CAG context

**AI Interviewer Flow:**
```typescript
sendToAI(transcript) // Calls ai-interviewer edge function
// Returns: AI response text, detected competencies
speakResponse(text) // TTS playback
saveTranscript(segment) // Persist to database
```

**Context-Augmented Generation (CAG):**
- Job requirements and description
- Company values framework
- Candidate background (from profile)
- Interview progress (questions asked)

**Anti-Cheat Signals:**
- Tab switch detection (`visibilitychange` event)
- Silence duration tracking
- Response latency monitoring
- Stored in `interviews.anti_cheat_signals`

**Interview Structure:**
- 10-15 minute duration
- ~5-7 questions
- Timer display
- Question progress indicator

**Completion:**
- Calls `completeInterview()` from persistence hook
- Navigates to `/candidate/complete`

---

### 4.14 InterviewComplete.tsx (Post-Interview)
**Purpose:** Shows scoring progress and final results.

**Flow:**
1. Trigger scoring via `score-interview` edge function
2. Poll for completion (score appears in `interview_scores`)
3. Display results when ready

**Displayed Data:**
- Overall score (0-100)
- Dimension breakdowns
- Narrative summary
- Personalized feedback

**Functions:**
```typescript
triggerInterviewScoring(interviewId) // From lib/scoring.ts
getInterviewScore(interviewId) // Poll for results
```

---

### 4.15 PracticeInterview.tsx
**Purpose:** Practice interview mode for candidates.

**Differences from Live Interview:**
- Uses `practice_interviews` table instead of `interviews`
- No invitation required
- Sample role types (e.g., "Software Engineer", "Product Manager")
- Less formal scoring

**Features:**
- Same speech recognition and synthesis
- Simplified feedback at end

---

### 4.16 PracticeInterviewComplete.tsx
**Purpose:** Practice session completion screen.

**Features:**
- Duration display
- Basic feedback from AI
- Link to try again or go to portal

---

### 4.17 InviteValidation.tsx
**Purpose:** Validates invitation tokens from email links.

**Flow:**
1. Extract token from URL params
2. Call `validateInvitation(token)` from `useInvitations`
3. Mark invitation as "opened" if first access
4. Redirect to interview lobby

**Error Handling:**
- Invalid token → Error message
- Expired token → Expiration message
- Already used → Already completed message

---

### 4.18 NotFound.tsx
**Purpose:** 404 page for invalid routes.

---

## 5. Components (src/components/)

### 5.1 Business Components

#### AuditTrailViewer.tsx
**Purpose:** Displays organisation audit logs with filtering.

**Features:**
- Date range filter
- Action type filter
- Entity type filter
- Paginated results
- Expandable rows for details

**Props:**
```typescript
interface Props {
  orgId: string;
}
```

---

#### AvatarRenderer.tsx
**Purpose:** Renders Azure AI Avatar for animated interviewer.

**Props:**
```typescript
interface Props {
  avatarRef: React.RefObject<HTMLVideoElement>;
  isAvatarReady: boolean;
}
```

**Behavior:**
- Shows video element when avatar is ready
- Placeholder/loading state when not ready

---

#### CallControls.tsx
**Purpose:** Audio/video controls for ACS calls.

**Props:**
```typescript
interface Props {
  isMuted: boolean;
  isVideoOn: boolean;
  onToggleMute: () => void;
  onToggleVideo: () => void;
  onEndCall: () => void;
}
```

---

#### CandidateComparison.tsx
**Purpose:** Side-by-side comparison of selected candidates.

**Props:**
```typescript
interface Props {
  candidates: Application[];
  roleId: string;
}
```

**Features:**
- Up to 3 candidates side-by-side
- Compare: scores, skills, experience, education
- Visual indicators for best in category

---

#### DataRetentionSettings.tsx
**Purpose:** Candidate-facing data retention preferences.

**Features:**
- Data deletion request
- Export my data
- Pause profile visibility
- Delete account option

**Uses:** `useDeletionRequests()` hook

---

#### NavLink.tsx
**Purpose:** Navigation link component with active state styling.

---

#### OrgDataRetentionSettings.tsx
**Purpose:** Organisation recording retention configuration.

**Props:**
```typescript
interface Props {
  orgId: string;
  currentDays: number;
}
```

**Features:**
- Slider for retention days (7-365)
- Save to `organisations.recording_retention_days`

---

#### ProfileManagement.tsx
**Purpose:** Toggle visibility for profile fields.

**Props:**
```typescript
interface Props {
  settings: VisibilitySettings;
  onUpdate: (settings: VisibilitySettings) => void;
}
```

**Toggles:** name, email, phone, location, linkedin, portfolio, employment, education, skills

---

#### SendInvitationDialog.tsx
**Purpose:** Modal dialog for sending interview invitations.

**Props:**
```typescript
interface Props {
  applicationId: string;
  candidateEmail: string;
  roleTitle: string;
  companyName: string;
  isOpen: boolean;
  onClose: () => void;
}
```

**Flow:**
1. Confirm details
2. Call `sendInvitation()` from `useInvitations`
3. Edge function sends email via Resend

---

#### ShortlistView.tsx
**Purpose:** Displays AI-generated candidate shortlist.

**Props:**
```typescript
interface Props {
  candidates: CandidateMatch[];
  isLoading: boolean;
}
```

**Features:**
- Ranked list with match scores
- Match reasons for each candidate
- Click to view candidate details

---

#### VideoRenderer.tsx
**Purpose:** Renders video tiles for ACS participants.

**Props:**
```typescript
interface Props {
  streams: VideoStreamRenderer[];
}
```

---

### 5.2 UI Components (src/components/ui/)

Complete shadcn/ui component library. Key components:

| Component | File | Purpose |
|-----------|------|---------|
| Button | button.tsx | Primary action buttons with variants |
| Card | card.tsx | Content containers |
| Dialog | dialog.tsx | Modal dialogs |
| Form | form.tsx | Form wrapper with react-hook-form |
| Input | input.tsx | Text inputs |
| Select | select.tsx | Dropdown selects |
| Table | table.tsx | Data tables |
| Tabs | tabs.tsx | Tab navigation |
| Toast | toast.tsx | Notification toasts |
| Tooltip | tooltip.tsx | Hover tooltips |

---

## 6. Custom Hooks (src/hooks/)

### 6.1 Data Fetching Hooks

#### useOrgData.ts
**Exports:**

```typescript
useCurrentOrg()
// Returns: { data: Organisation, isLoading, error }
// Fetches current user's organisation via org_users join

useJobRoles(orgId: string)
// Returns: { data: JobRole[], isLoading, error }
// Fetches all job roles for an organisation

useJobRole(roleId: string)
// Returns: { data: JobRole, isLoading, error }
// Fetches single job role with org details

useRoleApplications(roleId: string)
// Returns: { data: Application[], isLoading, error }
// Fetches applications with candidate profiles and interview data

useOrgStats(orgId: string)
// Returns: { activeRoles, totalCandidates, completedInterviews, avgScore }
// Aggregated statistics for dashboard
```

---

#### useCandidateData.ts
**Exports:**

```typescript
useCandidateProfile()
// Returns: { profile, skills, employment, education, isLoading }
// Complete candidate profile data

useCandidateApplications()
// Returns: { data: Application[], isLoading }
// Candidate's job applications with role details

useCandidateInvitations()
// Returns: { data: Invitation[], isLoading }
// Pending interview invitations

useCandidateInterviewFeedback()
// Returns: { data: InterviewFeedback[], isLoading }
// Completed interview scores and feedback
```

---

### 6.2 Interview Hooks

#### useInterviewPersistence.ts
**Purpose:** Manages interview lifecycle and data persistence.

**Exports:**
```typescript
interface TranscriptSegment {
  speaker: 'candidate' | 'ai';
  content: string;
  startTimeMs: number;
  endTimeMs?: number;
  confidence?: number;
}

interface AntiCheatSignal {
  type: 'tab_switch' | 'silence' | 'copy_paste';
  timestamp: number;
  duration?: number;
}

useInterviewPersistence()
// Returns:
{
  interviewId: string | null;
  isLoading: boolean;
  error: Error | null;
  createInterview: (applicationId: string) => Promise<string | null>;
  saveTranscriptSegment: (interviewId: string, segment: TranscriptSegment) => Promise<void>;
  updateAntiCheatSignals: (interviewId: string, signals: AntiCheatSignal[]) => Promise<void>;
  completeInterview: (interviewId: string, durationSeconds: number, signals: AntiCheatSignal[]) => Promise<boolean>;
  getOrCreateDemoApplication: () => Promise<string | null>;
}
```

**Database Operations:**
- Creates `interviews` record with status 'in_progress'
- Inserts `transcript_segments` records
- Updates `interviews.anti_cheat_signals`
- Sets status to 'completed' on finish
- Updates `applications.status` to 'interviewed'

---

#### useInterviewContext.ts
**Purpose:** Loads Context-Augmented Generation (CAG) context for AI interviewer.

**Returns:**
```typescript
interface CAGContext {
  jobRole: {
    title: string;
    department: string;
    description: string;
    requirements: Requirements;
  };
  organisation: {
    name: string;
    values: ValuesFramework;
  };
  candidate: {
    background: string;
    skills: Skill[];
  };
}
```

**Data Sources:**
- `job_roles` table
- `organisations` table
- `candidate_profiles` table
- `candidate_skills` table
- `employment_history` table

---

#### useInvitations.ts
**Purpose:** Invitation management for interview scheduling.

**Exports:**
```typescript
useInvitations()
// Returns:
{
  sendInvitation: (params: SendInvitationParams) => Promise<Result>;
  validateInvitation: (token: string) => Promise<ValidateInvitationResult>;
  markInvitationCompleted: (invitationId: string) => Promise<void>;
  isSending: boolean;
  isValidating: boolean;
}
```

**SendInvitationParams:**
```typescript
{
  applicationId: string;
  candidateEmail: string;
  roleTitle: string;
  companyName: string;
}
```

---

### 6.3 Speech/Communication Hooks

#### useAzureSpeech.ts
**Purpose:** Azure Speech SDK integration for STT/TTS.

**Features:**
- Token fetching from `azure-speech-token` edge function
- Token refresh before expiration
- Continuous speech recognition
- Speech synthesis with configurable voice

**Exports:**
```typescript
interface UseAzureSpeechOptions {
  onSpeechResult?: (text: string) => void;
  onSpeechEnd?: () => void;
  onSpeechStart?: () => void;
  onSpeechError?: (error: Error) => void;
  onTTSStart?: () => void;
  onTTSEnd?: () => void;
  voicePreference?: string;
}

useAzureSpeech(options: UseAzureSpeechOptions)
// Returns:
{
  isListening: boolean;
  isSpeaking: boolean;
  transcript: string;
  interimTranscript: string;
  isInitialized: boolean;
  error: Error | null;
  startListening: () => Promise<void>;
  stopListening: () => void;
  speak: (text: string) => Promise<void>;
  stopSpeaking: () => void;
  resetTranscript: () => void;
}
```

---

#### useSpeechRecognition.ts
**Purpose:** Browser Web Speech API fallback for STT.

**Uses:** `webkitSpeechRecognition` or `SpeechRecognition` API

**Exports:**
```typescript
useSpeechRecognition(onResult: (text: string) => void)
// Returns:
{
  isListening: boolean;
  transcript: string;
  startListening: () => void;
  stopListening: () => void;
  resetTranscript: () => void;
  isSupported: boolean;
}
```

---

#### useSpeechSynthesis.ts
**Purpose:** Browser TTS fallback.

**Exports:**
```typescript
useSpeechSynthesis()
// Returns:
{
  isSpeaking: boolean;
  speak: (text: string) => void;
  stop: () => void;
  isSupported: boolean;
}
```

---

#### useAzureAvatar.ts
**Purpose:** Azure AI Avatar for animated interviewer face.

**Exports:**
```typescript
useAzureAvatar(videoRef: RefObject<HTMLVideoElement>)
// Returns:
{
  isReady: boolean;
  isLoading: boolean;
  error: Error | null;
  speak: (text: string) => Promise<void>;
  stop: () => void;
}
```

---

#### useAcsToken.ts
**Purpose:** Fetch Azure Communication Services access tokens.

**Exports:**
```typescript
useAcsToken()
// Returns:
{
  token: string | null;
  userId: string | null;
  isLoading: boolean;
  error: Error | null;
  refreshToken: () => Promise<void>;
}
```

---

#### useAcsCall.ts
**Purpose:** ACS call management for video interviews.

**Exports:**
```typescript
useAcsCall(token: string, userId: string)
// Returns:
{
  call: Call | null;
  callState: string;
  isMuted: boolean;
  isVideoOn: boolean;
  localVideoStream: VideoStreamRenderer | null;
  remoteParticipants: RemoteParticipant[];
  startCall: (meetingLink: string) => Promise<void>;
  endCall: () => Promise<void>;
  toggleMute: () => Promise<void>;
  toggleVideo: () => Promise<void>;
}
```

---

### 6.4 Utility Hooks

#### useAuditLog.ts
**Purpose:** Fetch and format audit logs for organisation.

**Exports:**
```typescript
useAuditLog(orgId: string, filters?: AuditFilters)
// Returns:
{
  logs: AuditLogEntry[];
  isLoading: boolean;
  error: Error | null;
  totalCount: number;
  loadMore: () => void;
}
```

---

#### useShortlist.ts
**Purpose:** Generate AI-powered candidate shortlist.

**Exports:**
```typescript
useShortlist()
// Returns:
{
  generateShortlist: (roleId: string) => Promise<CandidateMatch[]>;
  isGenerating: boolean;
  error: Error | null;
}
```

---

#### useDeletionRequests.ts
**Purpose:** GDPR data deletion request management.

**Exports:**
```typescript
useDeletionRequests()
// Returns:
{
  requests: DeletionRequest[];
  createRequest: (type: 'full_deletion' | 'data_export', reason?: string) => Promise<void>;
  isLoading: boolean;
}
```

---

#### use-toast.ts
**Purpose:** Toast notification hook from shadcn/ui.

---

#### use-mobile.tsx
**Purpose:** Mobile device detection hook.

---

## 7. Utility Libraries (src/lib/)

### utils.ts
```typescript
cn(...inputs: ClassValue[]): string
// Merges Tailwind classes using clsx and tailwind-merge
```

---

### auditLog.ts
```typescript
logAction(params: AuditLogParams): Promise<void>
// Client-side helper to insert audit log entries
// Params: action, entityType, entityId, oldValues, newValues
```

---

### scoring.ts
```typescript
triggerInterviewScoring(interviewId: string): Promise<void>
// Calls score-interview edge function

getInterviewScore(interviewId: string): Promise<InterviewScore | null>
// Fetches score from interview_scores table
```

---

### generateInterviewReport.ts
```typescript
generateInterviewReport(interview: Interview, scores: InterviewScore): Promise<Blob>
// Generates PDF report using jsPDF
// Includes: candidate info, scores, transcript, recommendations
```

---

## 8. Edge Functions (supabase/functions/)

### 8.1 AI Functions

#### ai-interviewer/index.ts
**Purpose:** Generates AI interviewer responses using Context-Augmented Generation.

**Request:**
```typescript
{
  messages: { role: 'user' | 'assistant', content: string }[];
  context: CAGContext;
}
```

**Response:**
```typescript
{
  response: string;
  detectedCompetencies: string[];
}
```

**Features:**
- Rate limiting (10 requests/minute per IP, 100/minute per user)
- JWT authentication required
- System prompt with job context, company values, interview guidelines
- Competency detection from conversation
- Uses Lovable AI Gateway (Gemini 2.5 Flash)

---

#### score-interview/index.ts
**Purpose:** Scores completed interview transcripts.

**Request:**
```typescript
{
  transcript: TranscriptSegment[];
  rubric?: ScoringDimension[];
  jobContext?: string;
}
```

**Response:**
```typescript
{
  overallScore: number;
  dimensions: {
    dimension: string;
    score: number;
    evidence: string;
    citedQuotes: string[];
  }[];
  narrativeSummary: string;
  candidateFeedback: string;
  antiCheatRiskLevel: 'low' | 'medium' | 'high';
}
```

**Features:**
- Default dimensions if no custom rubric
- Evidence-based scoring with transcript quotes
- Anti-cheat signal analysis
- Rate limiting

---

#### extract-requirements/index.ts
**Purpose:** Extracts structured requirements from job descriptions.

**Request:**
```typescript
{
  jobDescription: string;
  jobTitle: string;
}
```

**Response:**
```typescript
{
  skills: { name: string; type: 'hard' | 'soft'; importance: 'required' | 'preferred' }[];
  experience: { years: number; description: string }[];
  qualifications: string[];
  responsibilities: string[];
  interviewQuestions: string[];
}
```

---

#### parse-resume/index.ts
**Purpose:** AI parsing of uploaded CV/resume PDFs.

**Request:**
```typescript
{
  filePath: string;
  userId: string;
}
```

**Response:**
```typescript
{
  personalInfo: { name, email, phone, location };
  employment: { company, title, dates, description }[];
  education: { institution, degree, field, dates }[];
  skills: string[];
  summary: string;
}
```

**Security:**
- Validates user owns the CV file
- Path traversal prevention
- JWT required

---

#### generate-shortlist/index.ts
**Purpose:** AI-powered candidate ranking for a job role.

**Request:**
```typescript
{
  roleId: string;
}
```

**Response:**
```typescript
{
  candidates: {
    applicationId: string;
    matchScore: number;
    matchReasons: string[];
    anonymizedProfile: object;
  }[];
}
```

**Features:**
- Fetches all applications for role
- Creates anonymized candidate summaries
- Semantic matching with AI
- Updates `applications.match_score`
- Authorization check for org membership

---

### 8.2 Business Logic Functions

#### create-organisation/index.ts
**Purpose:** Creates new organisation and adds user as admin.

**Request:**
```typescript
{
  name: string;
  industry?: string;
  website?: string;
  description?: string;
  billingEmail?: string;
}
```

**Operations:**
1. Create organisation record
2. Add user to org_users with role 'admin'
3. Create user_role 'org_admin' if not exists

---

#### send-invitation/index.ts
**Purpose:** Sends interview invitation emails.

**Request:**
```typescript
{
  applicationId: string;
  candidateEmail: string;
  roleTitle: string;
  companyName: string;
}
```

**Operations:**
1. Generate unique invitation token
2. Create invitation record
3. Send email via Resend
4. Update invitation status to 'sent'

**Email Content:**
- Interview link with token
- Role and company info
- Expiration date (7 days)

---

#### data-retention-cleanup/index.ts
**Purpose:** Scheduled cleanup of expired recordings.

**Trigger:** Scheduled (cron)

**Operations:**
1. Query interviews older than org's retention days
2. Delete recordings from storage
3. Update interview.recording_deleted_at
4. Log cleanup to audit_log

---

### 8.3 Integration Functions

#### azure-speech-token/index.ts
**Purpose:** Generates Azure Speech SDK authentication tokens.

**Response:**
```typescript
{
  token: string;
  region: string;
  expiresAt: number;
}
```

**Uses:** `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` secrets

---

#### acs-token-generator/index.ts
**Purpose:** Generates Azure Communication Services access tokens.

**Response:**
```typescript
{
  token: string;
  userId: string;
  expiresOn: string;
}
```

**Uses:** `ACS_CONNECTION_STRING` secret

---

#### acs-webhook-handler/index.ts
**Purpose:** Handles ACS call event webhooks.

**Events Handled:**
- Call started
- Call ended
- Recording available

**Uses:** `ACS_WEBHOOK_SECRET` for validation

---

## 9. Database Schema

### 9.1 Core Tables

#### organisations
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| name | text | Organisation name |
| industry | text | Industry category |
| website | text | Company website |
| logo_url | text | Logo image URL |
| description | text | About the company |
| values_framework | jsonb | Company values for AI context |
| recording_retention_days | integer | Days to keep recordings (default 60) |
| billing_email | text | Billing contact |
| billing_address | text | Billing address |
| created_at | timestamptz | Creation timestamp |
| updated_at | timestamptz | Last update timestamp |

**RLS Policies:**
- Org members can view their organisation
- Org admins can update their organisation
- Authenticated users can create organisations
- Candidates can view orgs they've applied to

---

#### org_users
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| user_id | uuid | Auth user ID |
| organisation_id | uuid | FK to organisations |
| role | text | 'admin', 'recruiter', 'hiring_manager' |
| created_at | timestamptz | Join date |

**RLS Policies:**
- Org members can view org users
- Org admins can manage org users

---

#### job_roles
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| organisation_id | uuid | FK to organisations |
| title | text | Job title |
| department | text | Department name |
| industry | text | Industry |
| work_type | text | 'remote', 'hybrid', 'onsite' |
| location | text | Office location |
| employment_type | text | 'full-time', 'part-time', 'contract' |
| description | text | Full job description |
| salary_range_min | integer | Minimum salary |
| salary_range_max | integer | Maximum salary |
| requirements | jsonb | AI-extracted requirements |
| interview_structure | jsonb | Interview configuration |
| scoring_rubric | jsonb | Dimension weights |
| status | enum | 'draft', 'active', 'paused', 'closed' |
| created_by | uuid | Creator user ID |
| created_at | timestamptz | Creation timestamp |
| updated_at | timestamptz | Last update |

**RLS Policies:**
- Authenticated users can view active roles
- Org members can view their roles
- Org recruiters/admins can create/update roles
- Org admins can delete roles

---

#### applications
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| candidate_id | uuid | Candidate user ID |
| job_role_id | uuid | FK to job_roles |
| status | text | 'applied', 'shortlisted', 'interviewed', 'offered', 'rejected' |
| match_score | numeric | AI-calculated match score |
| created_at | timestamptz | Application date |
| updated_at | timestamptz | Last update |

**RLS Policies:**
- Candidates can view/create their applications
- Org members can view/update applications for their roles

---

#### invitations
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| application_id | uuid | FK to applications |
| token | text | Unique invitation token |
| status | enum | 'pending', 'sent', 'delivered', 'opened', 'bounced', 'expired' |
| email_template | text | Email template used |
| sent_at | timestamptz | When email was sent |
| opened_at | timestamptz | When link was first clicked |
| expires_at | timestamptz | Expiration timestamp |
| created_at | timestamptz | Creation timestamp |

**RLS Policies:**
- Candidates can view/update their invitations
- Org members can create/view invitations for their roles

---

#### interviews
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| application_id | uuid | FK to applications |
| status | enum | 'invited', 'scheduled', 'in_progress', 'completed', 'cancelled', 'expired' |
| started_at | timestamptz | Interview start time |
| ended_at | timestamptz | Interview end time |
| duration_seconds | integer | Total duration |
| recording_url | text | Recording file URL |
| recording_deleted_at | timestamptz | When recording was deleted |
| anti_cheat_signals | jsonb | Array of anti-cheat events |
| metadata | jsonb | Additional metadata |
| created_at | timestamptz | Creation timestamp |
| updated_at | timestamptz | Last update |

**RLS Policies:**
- Candidates can view their interviews
- Candidates can create/update their interviews
- Org members can view interviews for their roles

---

#### interview_scores
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| interview_id | uuid | FK to interviews (unique) |
| overall_score | numeric | 0-100 score |
| narrative_summary | text | AI-generated summary |
| candidate_feedback | text | Feedback for candidate |
| anti_cheat_risk_level | text | 'low', 'medium', 'high' |
| scored_by | text | 'ai' or 'human' |
| model_version | text | AI model used |
| prompt_version | text | Prompt version |
| rubric_version | text | Rubric version |
| human_override | boolean | If manually overridden |
| human_override_by | uuid | Who overrode |
| human_override_reason | text | Override justification |
| created_at | timestamptz | Score timestamp |
| updated_at | timestamptz | Last update |

**RLS Policies:**
- Candidates can view their scores
- Org members can view/insert/update scores for their roles

---

#### score_dimensions
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| interview_id | uuid | FK to interviews |
| dimension | text | Dimension name |
| score | numeric | 0-100 score |
| weight | numeric | Dimension weight |
| evidence | text | Supporting evidence |
| cited_quotes | jsonb | Transcript quotes |
| created_at | timestamptz | Creation timestamp |

**RLS Policies:**
- Candidates can view their dimensions
- Org members can view/insert dimensions for their roles

---

#### transcript_segments
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| interview_id | uuid | FK to interviews |
| speaker | text | 'candidate' or 'ai' |
| content | text | Spoken text |
| start_time_ms | integer | Start timestamp (ms) |
| end_time_ms | integer | End timestamp (ms) |
| confidence | numeric | STT confidence score |
| created_at | timestamptz | Creation timestamp |

**RLS Policies:**
- Candidates can view/insert their transcripts
- Org members can view transcripts for their roles

---

### 9.2 Candidate Tables

#### candidate_profiles
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| user_id | uuid | Auth user ID |
| first_name | text | First name |
| last_name | text | Last name |
| email | text | Contact email |
| phone | text | Phone number |
| suburb | text | Suburb |
| postcode | text | Postal code |
| state | text | State/province |
| country | text | Country (default 'Australia') |
| work_rights | text | Work authorization |
| availability | text | Start date availability |
| work_mode | text | 'remote', 'hybrid', 'onsite' |
| portfolio_url | text | Portfolio link |
| linkedin_url | text | LinkedIn profile |
| cv_file_path | text | Path in storage |
| cv_uploaded_at | timestamptz | CV upload time |
| gpa_wam | numeric | Academic score |
| profile_visibility | text | 'visible', 'hidden', 'paused' |
| visibility_settings | jsonb | Field-level visibility |
| paused_at | timestamptz | When profile was paused |
| created_at | timestamptz | Creation timestamp |
| updated_at | timestamptz | Last update |

**RLS Policies:**
- Users can CRUD their own profile
- Org members can view applicant profiles

---

#### employment_history
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| user_id | uuid | Auth user ID |
| company_name | text | Company name |
| job_title | text | Position title |
| description | text | Role description |
| start_date | date | Start date |
| end_date | date | End date (null if current) |
| is_current | boolean | Currently employed |
| created_at | timestamptz | Creation timestamp |

**RLS Policies:**
- Users can CRUD their own history
- Org members can view applicant employment

---

#### education
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| user_id | uuid | Auth user ID |
| institution | text | School/university |
| degree | text | Degree type |
| field_of_study | text | Major/field |
| start_date | date | Start date |
| end_date | date | End date |
| is_current | boolean | Currently enrolled |
| created_at | timestamptz | Creation timestamp |

**RLS Policies:**
- Users can CRUD their own education
- Org members can view applicant education

---

#### candidate_skills
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| user_id | uuid | Auth user ID |
| skill_name | text | Skill name |
| skill_type | text | 'hard' or 'soft' |
| proficiency_level | text | Proficiency level |
| created_at | timestamptz | Creation timestamp |

**RLS Policies:**
- Users can CRUD their own skills
- Org members can view applicant skills

---

#### candidate_dei
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| user_id | uuid | Auth user ID |
| gender | text | Gender identity |
| ethnicity | text | Ethnicity |
| disability_status | text | Disability status |
| veteran_status | text | Veteran status |
| created_at | timestamptz | Creation timestamp |

**RLS Policies:**
- Users can CRUD their own DEI data
- Org admins can view aggregated DEI for reporting

---

#### practice_interviews
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| user_id | uuid | Auth user ID |
| sample_role_type | text | Practice role type |
| status | text | Session status |
| started_at | timestamptz | Start time |
| ended_at | timestamptz | End time |
| duration_seconds | integer | Duration |
| feedback | jsonb | AI feedback |
| created_at | timestamptz | Creation timestamp |

**RLS Policies:**
- Users can CRUD their own practice interviews

---

### 9.3 System Tables

#### user_roles
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| user_id | uuid | Auth user ID |
| role | enum | 'org_admin', 'org_recruiter', 'org_viewer', 'candidate' |
| created_at | timestamptz | Creation timestamp |

**RLS Policies:**
- Users can view their own roles

---

#### audit_log
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| user_id | uuid | Acting user ID |
| organisation_id | uuid | FK to organisations |
| action | text | Action performed |
| entity_type | text | Affected entity type |
| entity_id | uuid | Affected entity ID |
| old_values | jsonb | Previous values |
| new_values | jsonb | New values |
| ip_address | text | Client IP |
| created_at | timestamptz | Action timestamp |

**RLS Policies:**
- Org admins can view their audit logs
- Authenticated users can insert logs

---

#### data_deletion_requests
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| user_id | uuid | Requesting user ID |
| request_type | text | 'full_deletion', 'data_export' |
| status | text | 'pending', 'processing', 'completed', 'rejected' |
| reason | text | User's reason |
| notes | text | Admin notes |
| processed_by | text | Who processed |
| requested_at | timestamptz | Request timestamp |
| processed_at | timestamptz | Processing timestamp |

**RLS Policies:**
- Users can create/view their own requests

---

### 9.4 Database Functions

```sql
user_belongs_to_org(_user_id uuid, _org_id uuid) RETURNS boolean
-- Checks if user is a member of the organisation

user_org_role(_user_id uuid, _org_id uuid) RETURNS text
-- Returns user's role in the organisation ('admin', 'recruiter', etc.)

get_user_org_id(_user_id uuid) RETURNS uuid
-- Returns user's primary organisation ID

has_role(_user_id uuid, _role app_role) RETURNS boolean
-- Checks if user has a specific app-wide role

update_updated_at_column() RETURNS trigger
-- Trigger function to update updated_at on row changes
```

---

## 10. Storage Configuration

### Buckets

| Bucket | Purpose | Public | RLS |
|--------|---------|--------|-----|
| `candidate-cvs` | CV/resume uploads | No | Yes |

### Storage Policies
- Candidates can upload to their own folder (`{user_id}/*`)
- Candidates can view/delete their own files
- Org members can view CVs for their applicants

---

## 11. Environment Configuration

### Required Secrets (Supabase Edge Functions)

| Secret | Purpose | Required For |
|--------|---------|--------------|
| `LOVABLE_API_KEY` | Lovable AI Gateway access | All AI functions |
| `RESEND_API_KEY` | Email delivery via Resend | send-invitation |
| `AZURE_SPEECH_KEY` | Azure Speech SDK | azure-speech-token |
| `AZURE_SPEECH_REGION` | Azure region (e.g., 'australiaeast') | azure-speech-token |
| `ACS_CONNECTION_STRING` | Azure Communication Services | acs-token-generator |
| `ACS_WEBHOOK_SECRET` | Webhook validation | acs-webhook-handler |
| `SUPABASE_URL` | Auto-configured | All functions |
| `SUPABASE_ANON_KEY` | Auto-configured | All functions |
| `SUPABASE_SERVICE_ROLE_KEY` | Auto-configured | Admin operations |

### Frontend Environment Variables

| Variable | Purpose |
|----------|---------|
| `VITE_SUPABASE_URL` | Supabase project URL |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Supabase anon key |
| `VITE_SUPABASE_PROJECT_ID` | Project ID for references |

---

## 12. Security Features

### Row-Level Security (RLS)
- **All tables have RLS enabled**
- Candidates can only access their own data
- Org members can access their organisation's data
- Role-based access control (admin > recruiter > viewer)

### API Security
- JWT authentication on all edge functions
- Rate limiting:
  - Per IP: 10 requests/minute
  - Per user: 100 requests/minute
- Path traversal prevention on file operations
- Authorization checks for org membership

### Anti-Cheat Measures
- Tab switch detection during interviews
- Silence duration tracking
- Response latency monitoring
- Copy/paste detection
- Risk level assessment in scoring

### Data Protection
- Recording retention policies (configurable per org)
- GDPR deletion request workflow
- Profile visibility controls
- Sensitive field masking in views

---

## 13. Python ACS Service (Optional)

Located in `python-acs-service/`, this is an optional FastAPI microservice for advanced Azure Communication Services features.

### Structure
```
python-acs-service/
├── app/
│   ├── main.py              # FastAPI app entry
│   ├── config.py            # Configuration
│   ├── api/routes/
│   │   ├── calls.py         # Call management endpoints
│   │   ├── recordings.py    # Recording management
│   │   └── health.py        # Health check
│   ├── services/
│   │   ├── call_automation.py    # ACS Call Automation SDK
│   │   ├── recording.py          # Recording service
│   │   └── supabase_client.py    # Supabase integration
│   └── models/
│       ├── call.py          # Call data models
│       └── recording.py     # Recording models
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

### Features
- Call recording start/stop
- Recording download and management
- Call automation (future)
- Supabase sync for recording metadata

**Note:** This service is for future expansion and not currently integrated with the main app.

---

## 14. Key User Flows

### Organisation Flow
```
1. Sign Up (Auth.tsx)
   └── Select "Organisation" type
   └── Create account

2. Onboarding (OrgOnboarding.tsx)
   └── Enter org details
   └── create-organisation edge function
   └── Added as admin

3. Create Role (NewRole.tsx)
   └── Enter job details
   └── AI extracts requirements
   └── Configure scoring weights
   └── Save to job_roles

4. Manage Candidates (RoleDetails.tsx)
   └── View applications
   └── Generate AI shortlist
   └── Compare candidates
   └── Send invitations

5. Review Interviews (InterviewReport.tsx)
   └── View scores and transcript
   └── Override if needed
   └── Export reports
```

### Candidate Flow
```
1. Receive Invitation (Email)
   └── Click interview link

2. Validate Token (InviteValidation.tsx)
   └── Check expiration
   └── Mark as opened
   └── Redirect to lobby

3. Device Check (InterviewLobby.tsx)
   └── Camera permission
   └── Microphone permission
   └── Speaker test
   └── Accept terms

4. Live Interview (LiveInterview.tsx)
   └── 10-15 minute session
   └── AI asks questions
   └── Speech recognition captures answers
   └── Transcript saved in real-time
   └── Anti-cheat monitoring

5. Completion (InterviewComplete.tsx)
   └── Scoring triggered
   └── View results
   └── See feedback

6. Profile Management (CandidateProfile.tsx)
   └── Update profile
   └── Upload CV (AI parsed)
   └── Manage privacy settings
```

---

## 15. Deployment

### Frontend Deployment
- Deploy via Lovable's "Publish" button
- Automatic builds on code changes
- Preview available during development

### Edge Functions
- Deploy automatically on code changes
- No manual deployment required
- Logs available in Lovable Cloud

### Database Migrations
- Run automatically via migration tool
- Requires user approval for schema changes
- Rollback not supported (design carefully)

### Environment
- Secrets configured in Lovable Cloud
- No Supabase dashboard access needed
- All management via Lovable interface

---

## 16. Maintenance Notes

### Common Tasks

**Adding a new AI feature:**
1. Create edge function in `supabase/functions/`
2. Add rate limiting and auth
3. Use Lovable AI Gateway
4. Handle errors gracefully

**Adding a new database table:**
1. Use migration tool
2. Enable RLS
3. Create appropriate policies
4. Update types (auto-generated)

**Adding a new page:**
1. Create component in `src/pages/`
2. Add route in `App.tsx`
3. Create necessary hooks
4. Add navigation links

### Monitoring
- Check edge function logs for errors
- Monitor rate limit hits
- Review audit logs for security
- Track interview completion rates

---

## 17. Files Quick Reference

### Pages (19 files)
- `Auth.tsx` - Authentication
- `CandidateInterview.tsx` - Interview entry
- `CandidatePortal.tsx` - Candidate dashboard
- `CandidateProfile.tsx` - Profile editor
- `EditRoleRubric.tsx` - Scoring weights
- `Index.tsx` - Landing page
- `InterviewComplete.tsx` - Post-interview
- `InterviewLobby.tsx` - Device check
- `InterviewReport.tsx` - Results view
- `InviteValidation.tsx` - Token validation
- `LiveInterview.tsx` - AI interview
- `NewRole.tsx` - Create role
- `NotFound.tsx` - 404 page
- `OrgDashboard.tsx` - Org dashboard
- `OrgOnboarding.tsx` - Org setup
- `OrgSettings.tsx` - Org settings
- `PracticeInterview.tsx` - Practice mode
- `PracticeInterviewComplete.tsx` - Practice results
- `RoleDetails.tsx` - Role management

### Hooks (16 files)
- `use-mobile.tsx` - Mobile detection
- `use-toast.ts` - Toast notifications
- `useAcsCall.ts` - ACS calls
- `useAcsToken.ts` - ACS tokens
- `useAuditLog.ts` - Audit logs
- `useAzureAvatar.ts` - AI Avatar
- `useAzureSpeech.ts` - Azure Speech
- `useCandidateData.ts` - Candidate data
- `useDeletionRequests.ts` - GDPR requests
- `useInterviewContext.ts` - CAG context
- `useInterviewPersistence.ts` - Interview CRUD
- `useInvitations.ts` - Invitations
- `useOrgData.ts` - Org data
- `useShortlist.ts` - AI shortlist
- `useSpeechRecognition.ts` - Browser STT
- `useSpeechSynthesis.ts` - Browser TTS

### Edge Functions (11 functions)
- `acs-token-generator` - ACS tokens
- `acs-webhook-handler` - ACS events
- `ai-interviewer` - AI responses
- `azure-speech-token` - Speech tokens
- `create-organisation` - Org creation
- `data-retention-cleanup` - Recording cleanup
- `extract-requirements` - Job parsing
- `generate-shortlist` - Candidate ranking
- `parse-resume` - CV parsing
- `score-interview` - Interview scoring
- `send-invitation` - Email invites

### Libraries (4 files)
- `utils.ts` - Class merging
- `auditLog.ts` - Audit helper
- `scoring.ts` - Scoring triggers
- `generateInterviewReport.ts` - PDF generation

---

## 18. Contact & Support

This application was built using Lovable. For technical support:
- Lovable Documentation: https://docs.lovable.dev
- Edge Function Logs: Available in Lovable Cloud interface
- Database Management: Via Lovable Cloud backend panel

---

*Document generated: January 2026*
*Application Version: 1.0.0*
