# Changelog

All notable changes to the Talenti AI Interview Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Data export functionality for GDPR portability
- Multi-language interview support
- Advanced analytics dashboard
- Webhook integrations for ATS systems

---

## [1.0.0] - 2026-01-13

### Initial Release

This is the first production release of the Talenti AI Interview Platform.

### Added

#### Authentication & Authorization
- Email/password authentication via Supabase Auth
- Role-based access control (org_admin, org_recruiter, org_viewer, candidate)
- Organisation-scoped data isolation via RLS policies
- Session management with JWT tokens

#### Organisation Management
- Organisation creation and onboarding flow
- Team member management
- Organisation settings and branding
- Recording retention policy configuration

#### Job Role Management
- Job role creation with rich descriptions
- AI-powered requirement extraction from job descriptions
- Custom scoring rubric configuration
- Interview structure customization
- Role status management (draft, active, paused, closed)

#### Candidate Experience
- Candidate portal with profile management
- CV/resume upload and AI parsing
- Skills and experience tracking
- Education and employment history
- Profile visibility controls
- Practice interview mode

#### Interview System
- AI-powered interviewer using Lovable AI (Gemini)
- Real-time speech-to-text transcription
- Text-to-speech AI responses
- Video calling via Azure Communication Services
- Interview recording and storage
- Competency-based question generation
- Context-aware follow-up questions

#### Scoring & Evaluation
- AI interview scoring with 8 default dimensions
- Custom scoring rubric support
- Evidence-based scoring with transcript citations
- Narrative summary generation
- Candidate feedback generation
- Anti-cheat risk assessment

#### Shortlisting
- AI-powered candidate matching
- Semantic skills matching
- Ranked candidate shortlists
- Match reasoning and scores
- Candidate comparison view

#### Invitations
- Email invitation system via Resend
- Secure token-based invite links
- Invitation tracking and expiry
- Branded email templates

#### Data Management
- GDPR-compliant data handling
- Data deletion request workflow
- Recording retention automation
- Audit logging for key actions
- Data anonymization option

#### Security
- Row Level Security on all tables
- Rate limiting on all endpoints
- Webhook signature verification
- Input validation and sanitization
- Path traversal protection

### Technical

#### Frontend
- React 18 with TypeScript
- Vite build system
- Tailwind CSS with shadcn/ui
- React Query for state management
- React Hook Form with Zod validation
- React Router v6

#### Backend
- Supabase (Lovable Cloud) backend
- 11 Edge Functions for business logic
- PostgreSQL database
- Supabase Storage for files
- Real-time subscriptions

#### Integrations
- Azure Communication Services (video calling)
- Azure Speech Services (STT/TTS)
- Lovable AI Gateway (Gemini models)
- Resend (email delivery)

---

## Version History Template

Use this template for future releases:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- New features

### Changed
- Changes to existing functionality

### Deprecated
- Features that will be removed in future versions

### Removed
- Features that have been removed

### Fixed
- Bug fixes

### Security
- Security-related changes
```

---

## Versioning Guidelines

### Major Version (X.0.0)
- Breaking API changes
- Database schema changes requiring migration
- Removal of deprecated features
- Major UI overhaul

### Minor Version (X.Y.0)
- New features (backward compatible)
- New Edge Functions
- New database tables
- UI enhancements

### Patch Version (X.Y.Z)
- Bug fixes
- Performance improvements
- Documentation updates
- Security patches

---

## Migration Notes

### Upgrading to 1.0.0

This is the initial release. No migration required.

### Future Migrations

Migration notes will be documented here for each version that requires database changes or configuration updates.

---

## Links

- [API Reference](./API_REFERENCE.md)
- [Security Documentation](./SECURITY.md)
- [Frontend Guide](./FRONTEND_GUIDE.md)
- [Environment Setup](./ENV_SETUP.md)
