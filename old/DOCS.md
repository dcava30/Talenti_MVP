# Talenti Documentation Index

> **Quick Reference Guide** - Find the right documentation for your needs.

---

## - Documentation Overview

This project contains comprehensive documentation organized by audience and purpose. Use this guide to navigate to the right resource.

---

## - Quick Navigation

| I want to... | Go to |
|--------------|-------|
| Understand the project | [README.md](#project-overview) |
| Set up my development environment | [ENV_SETUP.md](#environment-setup) |
| Understand the codebase | [HANDOVER.md](#technical-handover) |
| Learn the frontend architecture | [FRONTEND_GUIDE.md](#frontend-guide) |
| Work with APIs | [API_REFERENCE.md](#api-reference) |
| Understand the database | [DATABASE_SCHEMA.md](#database-schema) |
| Review security practices | [SECURITY.md](#security) |
| Contribute code | [CONTRIBUTING.md](#contributing) |
| Deploy the application | [DEPLOYMENT_GUIDE.md](#deployment) |
| Monitor production | [MONITORING.md](#monitoring) |
| Handle incidents | [DISASTER_RECOVERY.md](#disaster-recovery) |
| Use the platform (end user) | [USER_GUIDE.md](#user-guide) |
| See what's changed | [CHANGELOG.md](#changelog) |
| Rebuild with Python/FastAPI | [PYTHON_REBUILD_GUIDE.md](#python-rebuild-guide) |
| Track Python migration progress | [PYTHON_MIGRATION_CHECKLIST.md](#python-migration-checklist) |
| Understand architecture decisions | [ARCHITECTURE_DECISIONS.md](#architecture-decisions) |

---

## - Documentation Details

### Project Overview
**File:** `README.md`

The main entry point for the project. Contains:
- Project description and purpose
- Technology stack overview
- Quick start instructions
- Links to other documentation

**Best for:** First-time visitors, stakeholders, quick overview

---

### Technical Handover
**File:** `HANDOVER.md`

Comprehensive technical deep-dive for developers taking over the project. Contains:
- Complete technology stack details
- Application structure (pages, components, hooks)
- Edge functions overview
- Database schema summary
- Security implementation details
- Environment configuration

**Best for:** New developers, technical leads, code reviewers

---

### Environment Setup
**File:** `ENV_SETUP.md`

Step-by-step guide to setting up a local development environment. Contains:
- Required environment variables
- Lovable Cloud configuration
- Azure service setup (Speech, Communication Services)
- AI Gateway configuration
- Troubleshooting common issues

**Best for:** New developers, DevOps engineers

---

### Frontend Guide
**File:** `FRONTEND_GUIDE.md`

Architecture and patterns for the React frontend. Contains:
- Component hierarchy and organization
- State management with React Query
- Routing structure and auth guards
- Form handling patterns
- Styling conventions (Tailwind + shadcn/ui)
- Custom hooks documentation

**Best for:** Frontend developers, UI/UX implementers

---

### API Reference
**File:** `API_REFERENCE.md`

Complete documentation for all backend Edge Functions. Contains:
- Endpoint specifications (12 functions)
- Request/response schemas
- Authentication requirements
- Error codes and handling
- Rate limiting information
- Code examples

**Best for:** Frontend developers, API integrators, QA engineers

---

### Database Schema
**File:** `DATABASE_SCHEMA.md`

Complete database documentation. Contains:
- Entity Relationship Diagram (ERD)
- Table descriptions (16 tables)
- Column-level documentation
- Enum definitions
- Foreign key relationships
- Index documentation

**Best for:** Backend developers, database administrators, data analysts

---

### Security
**File:** `SECURITY.md`

Security implementation and compliance documentation. Contains:
- Authentication flows
- Row Level Security (RLS) policies
- Data protection measures
- GDPR compliance procedures
- Secrets management
- Incident response procedures

**Best for:** Security engineers, compliance officers, architects

---

### Contributing
**File:** `CONTRIBUTING.md`

Guidelines for contributing to the project. Contains:
- Development workflow
- Code style guidelines
- Pull request process
- Testing requirements
- Documentation standards

**Best for:** All contributors, open source developers

---

### Deployment
**File:** `DEPLOYMENT_GUIDE.md`

Instructions for deploying the application. Contains:
- Lovable deployment process
- Environment configuration
- Edge function deployment
- Post-deployment verification
- Rollback procedures

**Best for:** DevOps engineers, release managers

---

### Monitoring
**File:** `MONITORING.md`

Production monitoring and observability guide. Contains:
- Log analysis techniques
- Key metrics to track
- Alerting configuration
- Performance monitoring
- Debugging procedures

**Best for:** DevOps engineers, SREs, on-call engineers

---

### Disaster Recovery
**File:** `DISASTER_RECOVERY.md`

Incident response and recovery procedures. Contains:
- Backup procedures
- Recovery Time Objectives (RTO/RPO)
- Failover procedures
- Incident response playbooks
- Business continuity planning

**Best for:** DevOps engineers, incident commanders, management

---

### User Guide
**File:** `USER_GUIDE.md`

End-user documentation for platform users. Contains:
- Organisation admin workflows
- Recruiter interview management
- Candidate interview experience
- FAQ and troubleshooting

**Best for:** End users, customer support, training

---

### Changelog
**File:** `CHANGELOG.md`

Version history and release notes. Contains:
- Feature additions
- Bug fixes
- Breaking changes
- Migration notes

**Best for:** All stakeholders, upgrade planning

---

### Architecture Decisions
**File:** `ARCHITECTURE_DECISIONS.md`

Records of significant technical decisions. Contains:
- Technology choices and rationale
- Trade-off analysis
- Alternative options considered
- Decision outcomes

**Best for:** Architects, technical leads, new team members

---

### Testing Strategy
**File:** `TESTING_STRATEGY.md`

Testing approach and guidelines. Contains:
- Testing philosophy
- Unit testing patterns
- Integration testing
- E2E testing approach
- Coverage requirements

**Best for:** QA engineers, developers

---

## - Specialized Documentation

### PostgreSQL Migration
**File:** `POSTGRESQL_MIGRATION.md`

Guide for migrating from Supabase/PostgreSQL to PostgreSQL. Contains:
- Type mappings
- Schema conversion
- RLS to application-layer security
- Data migration scripts

**Best for:** Teams moving to self-hosted/offline solutions

---

### Azure SDK Examples
**File:** `AZURE_SDK_EXAMPLES.md`

Code examples for Azure Communication Services. Contains:
- Call Automation examples
- Recording management
- Event handling patterns

**Best for:** Developers working with ACS integration

---

### Python Rebuild Guide
**File:** `PYTHON_REBUILD_GUIDE.md`

Complete guide for rebuilding the backend with Python and FastAPI. Contains:
- Edge Function to FastAPI endpoint mappings
- Full Python dependencies (requirements.txt)
- Authentication and rate limiting middleware
- AI gateway service integration
- Docker and Azure Container Apps deployment
- Testing patterns with pytest

**Best for:** Teams migrating to Python backend, Azure-first deployments

---

### Python Migration Checklist
**File:** `PYTHON_MIGRATION_CHECKLIST.md`

Progress tracking document for the Python migration. Contains:
- Phase-by-phase task checklists
- Endpoint migration status table
- Testing and deployment tasks
- Team assignment tracking
- Notes and decisions log

**Best for:** Project managers, migration leads, development teams

---

### Python ACS Service
**File:** `python-acs-service/README.md`

Documentation for the optional Python backend service. Contains:
- Service architecture
- API endpoints
- Deployment instructions

**Best for:** Teams requiring Python-based ACS handling

---

## - File Location Summary

```
/
- README.md                 # Project overview
- DOCS.md                   # This file - documentation index
- HANDOVER.md               # Technical handover
- ENV_SETUP.md              # Environment setup
- FRONTEND_GUIDE.md         # Frontend architecture
- API_REFERENCE.md          # API documentation
- DATABASE_SCHEMA.md        # Database documentation
- SECURITY.md               # Security documentation
- CONTRIBUTING.md           # Contribution guidelines
- DEPLOYMENT_GUIDE.md       # Deployment instructions
- MONITORING.md             # Monitoring guide
- DISASTER_RECOVERY.md      # DR procedures
- USER_GUIDE.md             # End-user documentation
- CHANGELOG.md              # Version history
- ARCHITECTURE_DECISIONS.md # ADRs
- TESTING_STRATEGY.md       # Testing approach
- POSTGRESQL_MIGRATION.md       # PostgreSQL migration guide
- AZURE_SDK_EXAMPLES.md     # Azure code examples
- PYTHON_REBUILD_GUIDE.md   # Python/FastAPI migration
- PYTHON_MIGRATION_CHECKLIST.md # Migration tracking
- python-acs-service/
    - README.md             # Python service docs
```

---

## - Getting Started Paths

### New Developer
1. `README.md` - Project overview
2. `ENV_SETUP.md` - Set up your environment
3. `HANDOVER.md` - Understand the codebase
4. `FRONTEND_GUIDE.md` - Learn the patterns
5. `CONTRIBUTING.md` - Start contributing

### DevOps Engineer
1. `DEPLOYMENT_GUIDE.md` - Deployment process
2. `ENV_SETUP.md` - Configuration
3. `MONITORING.md` - Observability
4. `DISASTER_RECOVERY.md` - Incident response

### Security Auditor
1. `SECURITY.md` - Security overview
2. `DATABASE_SCHEMA.md` - Data model & RLS
3. `API_REFERENCE.md` - Endpoint security

### Product Manager / Stakeholder
1. `README.md` - Project overview
2. `USER_GUIDE.md` - User experience
3. `CHANGELOG.md` - Feature history

---

## - Documentation Maintenance

- All documentation is in **Markdown** format
- Diagrams use **Mermaid** syntax (renders in GitHub/GitLab)
- Update relevant docs when making code changes
- Follow the templates established in each document
- Keep the CHANGELOG.md updated with releases

---

*Last updated: January 2025*



