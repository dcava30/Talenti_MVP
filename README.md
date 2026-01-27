# Talenti AI Interview Platform

> **📚 [View Full Documentation Index →](DOCS.md)** — Find setup guides, API references, security docs, and more.

---

## Project Info

**URL**: https://lovable.dev/projects/823a9c71-397c-4a49-9190-91f5f3f8cbaf

## Target architecture

- Supabase is legacy and will be removed.
- Backend will be FastAPI + SQLite.
- Frontend will move to JS/JSX (no TypeScript).

## How can I edit this code?

There are several ways of editing your application.

**Use Lovable**

Simply visit the [Lovable Project](https://lovable.dev/projects/823a9c71-397c-4a49-9190-91f5f3f8cbaf) and start prompting.

Changes made via Lovable will be committed automatically to this repo.

**Use your preferred IDE**

If you want to work locally using your own IDE, you can clone this repo and push changes. Pushed changes will also be reflected in Lovable.

The only requirement is having Node.js & npm installed - [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating)

Follow these steps:

```sh
# Step 1: Clone the repository using the project's Git URL.
git clone <YOUR_GIT_URL>

# Step 2: Navigate to the project directory.
cd <YOUR_PROJECT_NAME>

# Step 3: Install the necessary dependencies.
npm i

# Step 4: Start the backend API (FastAPI).
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Step 5: Start the frontend development server with auto-reloading and an instant preview.
cd ..
export VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

**Edit a file directly in GitHub**

- Navigate to the desired file(s).
- Click the "Edit" button (pencil icon) at the top right of the file view.
- Make your changes and commit the changes.

**Use GitHub Codespaces**

- Navigate to the main page of your repository.
- Click on the "Code" button (green button) near the top right.
- Select the "Codespaces" tab.
- Click on "New codespace" to launch a new Codespace environment.
- Edit files directly within the Codespace and commit and push your changes once you're done.

## What technologies are used for this project?

This project is built with:

- Vite
- TypeScript
- React
- shadcn-ui
- Tailwind CSS
- Lovable Cloud (Supabase)
- Azure Communication Services
- Azure Speech Services

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [DOCS.md](DOCS.md) | **Master index** — Start here to find all documentation |
| [HANDOVER.md](HANDOVER.md) | Technical handover with complete codebase overview |
| [ENV_SETUP.md](ENV_SETUP.md) | Environment setup and configuration guide |
| [FRONTEND_GUIDE.md](FRONTEND_GUIDE.md) | React architecture, components, and patterns |
| [API_REFERENCE.md](API_REFERENCE.md) | Edge Functions API documentation |
| [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | Database tables, relationships, and ERD |
| [SECURITY.md](SECURITY.md) | Authentication, RLS policies, and compliance |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines and code standards |
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | Deployment and release procedures |
| [MONITORING.md](MONITORING.md) | Logging, metrics, and observability |
| [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md) | Backup and incident response procedures |
| [USER_GUIDE.md](USER_GUIDE.md) | End-user documentation for the platform |
| [CHANGELOG.md](CHANGELOG.md) | Version history and release notes |
| [ARCHITECTURE_DECISIONS.md](ARCHITECTURE_DECISIONS.md) | Technical decision records (ADRs) |
| [TESTING_STRATEGY.md](TESTING_STRATEGY.md) | Testing approach and guidelines |
| [SQLITE_MIGRATION.md](SQLITE_MIGRATION.md) | Guide for migrating to SQLite |
| [PYTHON_REBUILD_GUIDE.md](PYTHON_REBUILD_GUIDE.md) | Python/FastAPI backend migration guide |
| [PYTHON_MIGRATION_CHECKLIST.md](PYTHON_MIGRATION_CHECKLIST.md) | Migration progress tracking checklist |

## How can I deploy this project?

Simply open [Lovable](https://lovable.dev/projects/823a9c71-397c-4a49-9190-91f5f3f8cbaf) and click on Share -> Publish.

## Can I connect a custom domain to my Lovable project?

Yes, you can!

To connect a domain, navigate to Project > Settings > Domains and click Connect Domain.

Read more here: [Setting up a custom domain](https://docs.lovable.dev/features/custom-domain#custom-domain)
