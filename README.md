# Talenti AI Interview Platform

> **📚 [View Full Documentation Index →](DOCS.md)** — Find setup guides, API references, security docs, and more.

---

## Project Info

Talenti is a FastAPI + SQLite backend with a React (Vite) frontend and Azure Cognitive Services integrations.

## Target architecture

- FastAPI backend with SQLite.
- React frontend (JavaScript/JSX).
- Azure Cognitive Services integrations.

## How can I edit this code?

There are several ways of editing your application.

**Use your preferred IDE**

The only requirement is having Node.js & npm installed - [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating)

Follow these steps:

```sh
# Step 1: Clone the repository using the project's Git URL.
git clone <YOUR_GIT_URL>

# Step 2: Navigate to the project directory.
cd <YOUR_PROJECT_NAME>

# Step 3: Install the necessary dependencies.
npm i

# Step 4: Start the backend API (FastAPI + SQLite).
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
- React
- JavaScript (JSX)
- shadcn-ui
- Tailwind CSS
- FastAPI
- SQLite
- Azure Communication Services
- Azure Speech Services

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [DOCS.md](DOCS.md) | **Master index** — Start here to find all documentation |
| [HANDOVER.md](HANDOVER.md) | Technical handover with complete codebase overview |
| [ENV_SETUP.md](ENV_SETUP.md) | Environment setup and configuration guide |
| [FRONTEND_GUIDE.md](FRONTEND_GUIDE.md) | React architecture, components, and patterns |
| [API_REFERENCE.md](API_REFERENCE.md) | FastAPI API documentation |
| [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | Database tables, relationships, and ERD |
| [SECURITY.md](SECURITY.md) | Authentication, JWT guidance, and compliance |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines and code standards |
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | Deployment and release procedures |
| [MONITORING.md](MONITORING.md) | Logging, metrics, and observability |
| [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md) | Backup and incident response procedures |
| [USER_GUIDE.md](USER_GUIDE.md) | End-user documentation for the platform |
| [CHANGELOG.md](CHANGELOG.md) | Version history and release notes |
| [ARCHITECTURE_DECISIONS.md](ARCHITECTURE_DECISIONS.md) | Technical decision records (ADRs) |
| [TESTING_STRATEGY.md](TESTING_STRATEGY.md) | Testing approach and guidelines |
| [SQLITE_MIGRATION.md](SQLITE_MIGRATION.md) | Guide for migrating to SQLite |
| [PYTHON_REBUILD_GUIDE.md](PYTHON_REBUILD_GUIDE.md) | Legacy migration guide (superseded by current FastAPI stack) |
| [PYTHON_MIGRATION_CHECKLIST.md](PYTHON_MIGRATION_CHECKLIST.md) | Legacy migration checklist (no longer required) |

## How can I deploy this project?

Deploy the FastAPI service and Vite frontend using your preferred infrastructure (container platform, VM, or PaaS).
Ensure the backend has access to the SQLite database path and required Azure credentials.
