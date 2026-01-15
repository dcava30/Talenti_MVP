# Architecture Decision Records (ADRs)

> **Version:** 1.0.0  
> **Last Updated:** January 2026

This document captures the key architectural decisions made during the development of the Talenti AI Interview Platform, including context, rationale, and consequences.

---

## Table of Contents

1. [ADR-001: Use Lovable Cloud (Supabase) as Backend](#adr-001-use-lovable-cloud-supabase-as-backend)
2. [ADR-002: Edge Functions for Business Logic](#adr-002-edge-functions-for-business-logic)
3. [ADR-003: Azure Communication Services for Video](#adr-003-azure-communication-services-for-video)
4. [ADR-004: Lovable AI Gateway for AI Features](#adr-004-lovable-ai-gateway-for-ai-features)
5. [ADR-005: React Query for State Management](#adr-005-react-query-for-state-management)
6. [ADR-006: shadcn/ui for UI Components](#adr-006-shadcnui-for-ui-components)
7. [ADR-007: Row Level Security for Authorization](#adr-007-row-level-security-for-authorization)
8. [ADR-008: In-Memory Rate Limiting](#adr-008-in-memory-rate-limiting)
9. [ADR-009: JWT Validation in Code](#adr-009-jwt-validation-in-code)
10. [ADR-010: Multi-Dimension Scoring Model](#adr-010-multi-dimension-scoring-model)

---

## ADR-001: Use Lovable Cloud (Supabase) as Backend

### Status
Accepted

### Context
We needed a backend solution that provides:
- Database with real-time capabilities
- Authentication out of the box
- File storage
- Serverless functions
- Minimal DevOps overhead

### Decision
Use Lovable Cloud (powered by Supabase) as the complete backend solution.

### Rationale
1. **Integrated Experience**: Lovable Cloud provides seamless integration with the Lovable editor
2. **PostgreSQL**: Full-featured SQL database with JSON support
3. **Built-in Auth**: Supabase Auth handles user management
4. **Edge Functions**: Deno-based serverless functions for custom logic
5. **Storage**: Built-in file storage for CVs and recordings
6. **Real-time**: Native WebSocket support for live updates
7. **RLS**: Row Level Security for fine-grained access control

### Consequences
**Positive:**
- Faster development with integrated tooling
- No separate infrastructure to manage
- Automatic type generation from database schema
- Built-in security features

**Negative:**
- Vendor lock-in to Supabase/Lovable ecosystem
- Some PostgreSQL features not exposed
- Edge function cold starts can add latency

### Alternatives Considered
- Firebase: Less SQL-friendly, Firestore has different data model
- AWS Amplify: More complex setup, steeper learning curve
- Custom Node.js backend: More maintenance overhead

---

## ADR-002: Edge Functions for Business Logic

### Status
Accepted

### Context
The application requires server-side logic for:
- Secure API integrations (Azure, AI services)
- Data processing that shouldn't happen client-side
- Webhook handling
- Scheduled jobs

### Decision
Implement all backend business logic as Supabase Edge Functions using Deno.

### Rationale
1. **Security**: Secrets stay server-side
2. **Scalability**: Automatic scaling with serverless
3. **TypeScript**: Native TypeScript support in Deno
4. **Deployment**: Automatic deployment on code push
5. **Proximity**: Edge functions run close to Supabase database

### Consequences
**Positive:**
- Clean separation of frontend and backend
- No server management
- Pay-per-use pricing
- Fast iteration with auto-deploy

**Negative:**
- Cold start latency for infrequent functions
- Memory/time limits on function execution
- Deno ecosystem smaller than Node.js

### Implementation
Created 11 edge functions:
- `acs-token-generator` - Azure Communication Services tokens
- `acs-webhook-handler` - Call event webhooks
- `ai-interviewer` - Interview conversation AI
- `azure-speech-token` - Speech service tokens
- `create-organisation` - Org creation with admin setup
- `data-retention-cleanup` - GDPR compliance jobs
- `extract-requirements` - AI job requirement extraction
- `generate-shortlist` - AI candidate matching
- `parse-resume` - AI CV parsing
- `score-interview` - AI interview scoring
- `send-invitation` - Email invitations

---

## ADR-003: Azure Communication Services for Video

### Status
Accepted

### Context
The platform requires video calling capability for:
- Live AI interviews
- Recording interviews for review
- Future human interviewer support

### Decision
Use Azure Communication Services (ACS) for video/voice calling.

### Rationale
1. **Enterprise-grade**: Microsoft's communication platform
2. **Recording**: Built-in call recording
3. **SDK Quality**: Well-maintained JavaScript SDK
4. **Scalability**: Handles large-scale video at enterprise level
5. **Integration**: Works well with other Azure services (Speech)

### Consequences
**Positive:**
- Professional video quality
- Built-in recording infrastructure
- Strong documentation
- Compliance certifications

**Negative:**
- Azure lock-in for communication layer
- Cost per minute for calls
- Complex SDK for advanced features
- Webhook setup required

### Alternatives Considered
- Twilio Video: More expensive, better developer experience
- Daily.co: Simpler but less enterprise features
- Vonage: Similar capabilities, less Azure integration
- WebRTC direct: Too complex to implement correctly

---

## ADR-004: Lovable AI Gateway for AI Features

### Status
Accepted

### Context
The platform requires AI capabilities for:
- Interview conversation generation
- Resume/CV parsing
- Job requirement extraction
- Interview scoring
- Candidate matching

### Decision
Use Lovable AI Gateway with Gemini models for all AI features.

### Rationale
1. **No API Key Required**: Lovable provides AI access built-in
2. **Cost Efficiency**: Bundled with Lovable subscription
3. **Gemini Quality**: Google's Gemini models are high quality
4. **Simplicity**: Single integration point for all AI
5. **Tool Calling**: Native function calling support

### Consequences
**Positive:**
- No separate AI vendor management
- Automatic model updates
- Consistent API across features
- Built-in rate limiting

**Negative:**
- Limited to available models
- Can't fine-tune models
- Dependent on Lovable's AI allocation

### Model Selection
- `google/gemini-2.5-flash`: Primary model for all features
  - Good balance of speed and quality
  - Supports multimodal (text + images for CV parsing)
  - Cost-effective for high-volume use

### Alternatives Considered
- OpenAI API: Higher cost, requires separate API key
- Claude API: Better reasoning, requires separate key
- Self-hosted LLMs: Too complex for this scale

---

## ADR-005: React Query for State Management

### Status
Accepted

### Context
Need to manage:
- Server state (database data)
- Cache invalidation
- Loading/error states
- Optimistic updates

### Decision
Use TanStack Query (React Query) for all server state management.

### Rationale
1. **Cache Management**: Automatic caching and invalidation
2. **Loading States**: Built-in isLoading, isError, etc.
3. **Refetching**: Background refetch on window focus
4. **Mutations**: Clean mutation API with callbacks
5. **DevTools**: Excellent debugging tools

### Consequences
**Positive:**
- Eliminates manual cache management
- Consistent data fetching patterns
- Reduces boilerplate significantly
- Excellent TypeScript support

**Negative:**
- Learning curve for query key patterns
- Can be overkill for simple data
- Bundle size increase

### Patterns Used
```typescript
// Queries for reads
useQuery({ queryKey: ['interviews', roleId], queryFn: ... })

// Mutations for writes
useMutation({ mutationFn: ..., onSuccess: invalidate })

// Query invalidation
queryClient.invalidateQueries({ queryKey: ['interviews'] })
```

### Alternatives Considered
- Redux + RTK Query: More complex, heavier
- SWR: Similar but less features
- Apollo Client: GraphQL-focused, not needed
- Plain useState: Too much boilerplate

---

## ADR-006: shadcn/ui for UI Components

### Status
Accepted

### Context
Need a component library that:
- Looks professional
- Is highly customizable
- Works with Tailwind CSS
- Provides accessibility

### Decision
Use shadcn/ui as the UI component foundation.

### Rationale
1. **Ownership**: Components copied into project, not dependency
2. **Customization**: Full control over component code
3. **Tailwind Native**: Built for Tailwind CSS
4. **Radix Primitives**: Accessible by default
5. **Design System**: CSS variables for theming

### Consequences
**Positive:**
- Complete control over styling
- No version conflicts
- Consistent accessibility
- Easy to extend

**Negative:**
- Must maintain copied components
- Larger initial file count
- Updates require manual merge

### Theming Approach
```css
/* Design tokens in index.css */
:root {
  --primary: 37 92% 50%;  /* Orange */
  --background: 60 4% 95%;
  /* ... */
}
```

### Alternatives Considered
- Material UI: Too opinionated, heavy
- Chakra UI: Different styling approach
- Ant Design: Enterprise-focused, large bundle
- Headless UI: Less complete

---

## ADR-007: Row Level Security for Authorization

### Status
Accepted

### Context
Need to enforce data access rules:
- Candidates see only their data
- Org members see their org's data
- Public roles are visible to all

### Decision
Implement authorization primarily through PostgreSQL Row Level Security (RLS).

### Rationale
1. **Database-level**: Rules enforced at data layer
2. **Cannot Bypass**: Even with service role, policies apply
3. **Declarative**: SQL-based rules are clear
4. **Performance**: Optimized by PostgreSQL
5. **Composable**: Policies combine with AND logic

### Consequences
**Positive:**
- Security cannot be bypassed by frontend bugs
- Single source of truth for access rules
- Works with all query methods
- Easy to audit

**Negative:**
- Complex policies can be hard to debug
- Performance impact on complex joins
- Must understand auth.uid() context

### Key Policies
```sql
-- Candidates see own profile
CREATE POLICY "own_profile" ON candidate_profiles
  FOR ALL USING (user_id = auth.uid());

-- Org members see org data
CREATE POLICY "org_data" ON job_roles
  FOR SELECT USING (
    organisation_id IN (
      SELECT organisation_id FROM org_users 
      WHERE user_id = auth.uid()
    )
  );
```

### Alternatives Considered
- Application-level checks only: Error-prone, can be bypassed
- Middleware validation: Adds latency
- API gateway rules: Less flexible

---

## ADR-008: In-Memory Rate Limiting

### Status
Accepted

### Context
Need to prevent abuse of:
- AI endpoints (expensive)
- Token generation
- File processing

### Decision
Implement rate limiting using in-memory Map in each edge function.

### Rationale
1. **Simplicity**: No external service needed
2. **Speed**: No network latency for checks
3. **Sufficient**: Edge functions scale per-instance anyway
4. **Per-function**: Different limits per endpoint

### Consequences
**Positive:**
- Zero external dependencies
- Very fast checks
- Easy to implement and tune
- No additional costs

**Negative:**
- Not shared across function instances
- Resets on function cold start
- Less accurate at high scale

### Implementation
```typescript
const rateLimitStore = new Map<string, { count: number; resetAt: number }>();
const RATE_LIMIT = { windowMs: 60000, maxRequests: 10 };

function checkRateLimit(identifier: string) {
  // Check and update store
}
```

### Alternatives Considered
- Redis: More accurate, adds complexity/cost
- Upstash: Good but adds dependency
- Supabase table: Too slow for rate limiting

---

## ADR-009: JWT Validation in Code

### Status
Accepted

### Context
Edge functions need to verify caller identity.

### Decision
Use `getClaims()` for JWT validation instead of relying on `verify_jwt` config.

### Rationale
1. **Signing Keys**: New Supabase signing-keys system requires in-code validation
2. **Flexibility**: Can have public endpoints in same function
3. **Error Handling**: Better control over auth error responses
4. **Claims Access**: Direct access to JWT claims

### Consequences
**Positive:**
- Works with signing-keys rotation
- Consistent auth pattern across functions
- Clear error messages
- Access to full claims object

**Negative:**
- More boilerplate per function
- Must remember to validate

### Implementation
```typescript
const token = authHeader.replace('Bearer ', '');
const { data: claimsData, error } = await supabase.auth.getClaims(token);

if (error || !claimsData?.claims) {
  return new Response('Unauthorized', { status: 401 });
}

const userId = claimsData.claims.sub;
```

### Config
```toml
# supabase/config.toml
[functions.my-function]
verify_jwt = false  # Validate in code instead
```

---

## ADR-010: Multi-Dimension Scoring Model

### Status
Accepted

### Context
Need to evaluate candidates fairly and comprehensively during AI interviews.

### Decision
Implement 8-dimension scoring with configurable weights per organisation.

### Rationale
1. **Comprehensive**: Covers technical and soft skills
2. **Fair**: Multiple dimensions reduce bias
3. **Customizable**: Orgs can adjust weights
4. **Evidence-based**: Requires citations from transcript
5. **Transparent**: Clear breakdown of scores

### Dimensions
| Dimension | Default Weight | Measures |
|-----------|----------------|----------|
| vocabulary | 10% | Communication quality |
| domain_knowledge | 15% | Industry understanding |
| technical_skills | 20% | Hard skills |
| experience_depth | 10% | Past work depth |
| communication | 15% | Articulation |
| culture_fit | 10% | Values alignment |
| motivation | 10% | Drive and interest |
| confidence | 10% | Poise and delivery |

### Consequences
**Positive:**
- Reduces single-factor bias
- Orgs can emphasize what matters
- Clear scoring rationale
- Evidence-based decisions

**Negative:**
- More complex scoring logic
- AI must evaluate 8 dimensions
- Can be gamed if dimensions known

### Customization
```json
{
  "scoring_rubric": {
    "technical_skills": { "weight": 0.4, "label": "Technical" },
    "communication": { "weight": 0.3, "label": "Communication" },
    "culture_fit": { "weight": 0.3, "label": "Culture Fit" }
  }
}
```

---

## ADR Template

Use this template for future decisions:

```markdown
## ADR-XXX: [Title]

### Status
[Proposed | Accepted | Deprecated | Superseded by ADR-XXX]

### Context
[What is the issue that we're seeing that is motivating this decision?]

### Decision
[What is the change that we're proposing and/or doing?]

### Rationale
[Why is this decision the best option?]

### Consequences
**Positive:**
- [List positive outcomes]

**Negative:**
- [List negative outcomes or tradeoffs]

### Alternatives Considered
- [What other options were evaluated?]
```

---

## Decision Log

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| 001 | Lovable Cloud Backend | Accepted | 2026-01 |
| 002 | Edge Functions | Accepted | 2026-01 |
| 003 | Azure Communication Services | Accepted | 2026-01 |
| 004 | Lovable AI Gateway | Accepted | 2026-01 |
| 005 | React Query | Accepted | 2026-01 |
| 006 | shadcn/ui | Accepted | 2026-01 |
| 007 | Row Level Security | Accepted | 2026-01 |
| 008 | In-Memory Rate Limiting | Accepted | 2026-01 |
| 009 | JWT Validation in Code | Accepted | 2026-01 |
| 010 | Multi-Dimension Scoring | Accepted | 2026-01 |
