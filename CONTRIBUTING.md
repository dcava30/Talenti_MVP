# Contributing to Talenti Python Backend

Welcome to the Talenti Python backend project! This guide will help you get started with development, understand our coding standards, and learn how to submit contributions.

## Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Project Architecture](#project-architecture)
3. [Coding Standards](#coding-standards)
4. [Git Workflow](#git-workflow)
5. [Pull Request Guidelines](#pull-request-guidelines)
6. [Code Review Process](#code-review-process)
7. [Testing Requirements](#testing-requirements)
8. [Documentation Standards](#documentation-standards)
9. [Security Guidelines](#security-guidelines)
10. [Getting Help](#getting-help)

---

## Development Environment Setup

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Runtime |
| Poetry | 1.5+ | Dependency management |
| Docker | 24.0+ | Containerization |
| Docker Compose | 2.20+ | Local services |
| Git | 2.40+ | Version control |
| VS Code | Latest | Recommended IDE |

### Initial Setup

#### 1. Clone the Repository

```bash
git clone https://github.com/your-org/talenti-backend.git
cd talenti-backend/python-acs-service
```

#### 2. Install Poetry

```bash
# macOS/Linux
curl -sSL https://install.python-poetry.org | python3 -

# Windows (PowerShell)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -

# Verify installation
poetry --version
```

#### 3. Create Virtual Environment

```bash
# Create and activate virtual environment
poetry install

# Activate the environment
poetry shell

# Or run commands directly
poetry run python -m pytest
```

#### 4. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit with your values
nano .env
```

Required environment variables:

```env
# Azure Communication Services
ACS_CONNECTION_STRING=endpoint=https://your-acs.communication.azure.com/;accesskey=...
ACS_PHONE_NUMBER=+1234567890

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4

# Azure Speech
AZURE_SPEECH_KEY=your-speech-key
AZURE_SPEECH_REGION=eastus

# Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
AZURE_STORAGE_CONTAINER=recordings

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key

# Application
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

#### 5. Start Local Services

```bash
# Start all services with Docker Compose
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f api
```

#### 6. Verify Setup

```bash
# Run health check
curl http://localhost:8000/health

# Run tests
poetry run pytest tests/unit -v

# Check code formatting
poetry run black --check .
poetry run ruff check .
```

### IDE Configuration

#### VS Code Settings

Create `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.formatting.provider": "none",
  "python.linting.enabled": true,
  "python.linting.mypyEnabled": true,
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit"
    },
    "editor.defaultFormatter": "ms-python.black-formatter"
  },
  
  "editor.rulers": [88, 120],
  "files.trimTrailingWhitespace": true,
  "files.insertFinalNewline": true
}
```

#### Recommended VS Code Extensions

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-python.black-formatter",
    "charliermarsh.ruff",
    "ms-python.mypy-type-checker",
    "njpwerner.autodocstring",
    "mtxr.sqltools",
    "ms-azuretools.vscode-docker"
  ]
}
```

#### PyCharm Configuration

1. Open Settings → Project → Python Interpreter
2. Add Poetry environment: `poetry env info --path`
3. Enable Black formatter: Settings → Tools → Black
4. Configure pytest: Settings → Tools → Python Integrated Tools

---

## Project Architecture

### Directory Structure

```
python-acs-service/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry
│   ├── config.py            # Configuration management
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py          # Dependency injection
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── calls.py     # Call management endpoints
│   │       ├── health.py    # Health check endpoints
│   │       ├── interview.py # Interview endpoints
│   │       └── recordings.py # Recording endpoints
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── exceptions.py    # Custom exceptions
│   │   ├── middleware.py    # Custom middleware
│   │   └── security.py      # Authentication/authorization
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── call.py          # Call-related models
│   │   ├── interview.py     # Interview models
│   │   └── recording.py     # Recording models
│   │
│   └── services/
│       ├── __init__.py
│       ├── azure_openai.py  # OpenAI integration
│       ├── call_automation.py # ACS call automation
│       ├── recording.py     # Recording management
│       ├── speech.py        # Speech services
│       └── supabase_client.py # Database client
│
├── tests/
│   ├── conftest.py          # Shared fixtures
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   └── e2e/                 # End-to-end tests
│
├── scripts/
│   ├── deploy.sh            # Deployment script
│   ├── migrate.py           # Database migrations
│   └── seed.py              # Test data seeding
│
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── README.md
```

### Layer Responsibilities

```
┌─────────────────────────────────────────┐
│              API Routes                  │
│  - Request validation                    │
│  - Response formatting                   │
│  - HTTP-specific concerns                │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│              Services                    │
│  - Business logic                        │
│  - External service integration          │
│  - Error handling & retries              │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│              Models                      │
│  - Data structures                       │
│  - Validation rules                      │
│  - Type definitions                      │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│           Core/Infrastructure            │
│  - Configuration                         │
│  - Middleware                            │
│  - Shared utilities                      │
└─────────────────────────────────────────┘
```

---

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with the following tools:

| Tool | Purpose | Config File |
|------|---------|-------------|
| Black | Code formatting | `pyproject.toml` |
| Ruff | Linting | `pyproject.toml` |
| isort | Import sorting | `pyproject.toml` |
| mypy | Type checking | `pyproject.toml` |

### Code Formatting Rules

```toml
# pyproject.toml
[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'

[tool.ruff]
line-length = 88
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # Pyflakes
    "I",   # isort
    "C",   # flake8-comprehensions
    "B",   # flake8-bugbear
    "UP",  # pyupgrade
    "S",   # bandit security
]
ignore = [
    "E501",  # line too long (handled by black)
    "B008",  # function call in default argument
]

[tool.isort]
profile = "black"
line_length = 88
known_first_party = ["app"]

[tool.mypy]
python_version = "3.11"
strict = true
ignore_missing_imports = true
```

### Naming Conventions

```python
# ✅ Good Examples

# Modules: lowercase with underscores
call_automation.py
azure_openai.py

# Classes: PascalCase
class InterviewService:
    pass

class AzureOpenAIClient:
    pass

# Functions and methods: lowercase with underscores
async def create_interview(interview_id: str) -> Interview:
    pass

def calculate_score(responses: list[str]) -> float:
    pass

# Constants: UPPERCASE with underscores
MAX_RETRY_ATTEMPTS = 3
DEFAULT_TIMEOUT_SECONDS = 30

# Variables: lowercase with underscores
interview_count = 0
user_response = ""

# Private attributes: single leading underscore
class Service:
    def __init__(self):
        self._client = None
        self._cache = {}

# Type aliases: PascalCase
InterviewId = str
ScoreResult = dict[str, float]
```

### Type Hints

Always use type hints for function signatures:

```python
from typing import Optional
from collections.abc import AsyncGenerator

# ✅ Good: Complete type hints
async def get_interview(
    interview_id: str,
    include_transcript: bool = False,
) -> Optional[Interview]:
    """Retrieve an interview by ID."""
    pass

async def stream_responses(
    messages: list[Message],
) -> AsyncGenerator[str, None]:
    """Stream AI responses."""
    pass

# ❌ Bad: Missing type hints
async def get_interview(interview_id, include_transcript=False):
    pass
```

### Docstrings

Use Google-style docstrings:

```python
async def score_interview(
    interview_id: str,
    rubric: ScoringRubric,
    *,
    model: str = "gpt-4",
) -> InterviewScore:
    """Score an interview using AI analysis.

    Analyzes the interview transcript against the provided rubric
    and generates dimension scores with evidence.

    Args:
        interview_id: Unique identifier for the interview.
        rubric: Scoring rubric with dimensions and criteria.
        model: OpenAI model to use for scoring. Defaults to "gpt-4".

    Returns:
        InterviewScore containing overall score, dimension scores,
        and narrative feedback.

    Raises:
        InterviewNotFoundError: If interview doesn't exist.
        TranscriptEmptyError: If interview has no transcript.
        ScoringError: If AI scoring fails after retries.

    Example:
        >>> rubric = ScoringRubric(dimensions=[...])
        >>> score = await score_interview("int_123", rubric)
        >>> print(f"Overall: {score.overall_score}/100")
    """
    pass
```

### Error Handling

```python
from app.core.exceptions import (
    InterviewNotFoundError,
    ServiceUnavailableError,
)

# ✅ Good: Specific exception handling
async def get_interview(interview_id: str) -> Interview:
    try:
        response = await self._client.get(f"/interviews/{interview_id}")
        return Interview.model_validate(response.json())
    except httpx.TimeoutException as e:
        logger.warning(f"Timeout fetching interview {interview_id}: {e}")
        raise ServiceUnavailableError("Database timeout") from e
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise InterviewNotFoundError(interview_id) from e
        raise

# ❌ Bad: Catching all exceptions
async def get_interview(interview_id: str) -> Interview:
    try:
        # ...
    except Exception:
        return None  # Silent failure
```

### Async Best Practices

```python
import asyncio
from typing import Any

# ✅ Good: Concurrent execution
async def fetch_interview_data(interview_id: str) -> dict[str, Any]:
    transcript, scores, metadata = await asyncio.gather(
        self._get_transcript(interview_id),
        self._get_scores(interview_id),
        self._get_metadata(interview_id),
    )
    return {
        "transcript": transcript,
        "scores": scores,
        "metadata": metadata,
    }

# ❌ Bad: Sequential execution
async def fetch_interview_data(interview_id: str) -> dict[str, Any]:
    transcript = await self._get_transcript(interview_id)
    scores = await self._get_scores(interview_id)
    metadata = await self._get_metadata(interview_id)
    return {...}
```

### Pydantic Models

```python
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

class InterviewCreate(BaseModel):
    """Request model for creating an interview."""

    application_id: str = Field(
        ...,
        description="Associated application ID",
        examples=["app_abc123"],
    )
    scheduled_at: datetime | None = Field(
        default=None,
        description="Scheduled interview time",
    )

    @field_validator("application_id")
    @classmethod
    def validate_application_id(cls, v: str) -> str:
        if not v.startswith("app_"):
            raise ValueError("Application ID must start with 'app_'")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "application_id": "app_abc123",
                    "scheduled_at": "2024-01-15T10:00:00Z",
                }
            ]
        }
    }
```

---

## Git Workflow

### Branch Naming

```
<type>/<ticket-id>-<short-description>

Examples:
  feature/TAL-123-add-recording-endpoint
  bugfix/TAL-456-fix-token-expiry
  hotfix/TAL-789-critical-auth-bug
  refactor/TAL-101-extract-speech-service
  docs/TAL-202-update-api-docs
```

### Branch Types

| Type | Purpose | Base Branch |
|------|---------|-------------|
| `feature/` | New features | `develop` |
| `bugfix/` | Bug fixes | `develop` |
| `hotfix/` | Critical production fixes | `main` |
| `refactor/` | Code refactoring | `develop` |
| `docs/` | Documentation updates | `develop` |
| `test/` | Test additions/fixes | `develop` |

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

[optional body]

[optional footer(s)]
```

#### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation |
| `style` | Formatting (no code change) |
| `refactor` | Code restructuring |
| `perf` | Performance improvement |
| `test` | Adding/fixing tests |
| `chore` | Maintenance tasks |
| `ci` | CI/CD changes |

#### Examples

```bash
# Feature
feat(interview): add streaming chat endpoint

Implements WebSocket-based streaming for interview chat
with real-time token counting and rate limiting.

Closes TAL-123

# Bug fix
fix(auth): handle expired JWT tokens gracefully

Previously, expired tokens caused a 500 error.
Now returns 401 with a clear message.

Fixes TAL-456

# Breaking change
feat(api)!: change recording endpoint response format

BREAKING CHANGE: Recording list endpoint now returns
paginated response instead of flat array.

Migration: Update clients to handle pagination wrapper.
```

### Workflow

```bash
# 1. Create feature branch
git checkout develop
git pull origin develop
git checkout -b feature/TAL-123-new-endpoint

# 2. Make changes with atomic commits
git add app/api/routes/new_endpoint.py
git commit -m "feat(api): add new endpoint skeleton"

git add tests/unit/test_new_endpoint.py
git commit -m "test(api): add unit tests for new endpoint"

# 3. Keep branch updated
git fetch origin
git rebase origin/develop

# 4. Push and create PR
git push origin feature/TAL-123-new-endpoint
```

---

## Pull Request Guidelines

### Before Creating a PR

```bash
# 1. Run all quality checks
poetry run black .
poetry run ruff check --fix .
poetry run mypy app/

# 2. Run tests
poetry run pytest tests/ -v --cov=app --cov-report=term-missing

# 3. Update documentation if needed
# - API docs in docstrings
# - README for new features
# - CHANGELOG.md entry

# 4. Self-review your changes
git diff develop...HEAD
```

### PR Template

```markdown
## Description
<!-- What does this PR do? Why is it needed? -->

## Related Issues
<!-- Link to related issues: Closes #123, Fixes #456 -->

## Type of Change
- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📚 Documentation update
- [ ] 🔧 Refactoring (no functional changes)
- [ ] ✅ Test update

## Changes Made
<!-- List the main changes -->
- 
- 
- 

## Testing
<!-- How was this tested? -->
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Screenshots
<!-- If applicable, add screenshots -->

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No new warnings introduced
- [ ] Tests pass locally
- [ ] Dependent changes merged
```

### PR Best Practices

1. **Keep PRs Small**
   - Aim for < 400 lines changed
   - Split large features into smaller PRs
   - One logical change per PR

2. **Write Clear Descriptions**
   - Explain the "why" not just the "what"
   - Include context for reviewers
   - Link to design docs if applicable

3. **Add Screenshots/Videos**
   - For UI changes
   - For API response changes
   - For error message updates

4. **Respond to Feedback**
   - Address all comments
   - Re-request review after changes
   - Use "Resolve conversation" appropriately

---

## Code Review Process

### For Authors

```markdown
## Preparing for Review

1. Self-review your code first
2. Ensure CI passes
3. Add reviewers (minimum 1, 2 for critical paths)
4. Mark PR as "Ready for Review"
5. Respond to feedback within 24 hours
```

### For Reviewers

```markdown
## Review Checklist

### Code Quality
- [ ] Code is readable and well-structured
- [ ] No obvious bugs or edge cases missed
- [ ] Error handling is appropriate
- [ ] No security vulnerabilities

### Architecture
- [ ] Follows project patterns
- [ ] No unnecessary complexity
- [ ] Appropriate abstraction level

### Testing
- [ ] Adequate test coverage
- [ ] Tests are meaningful, not just for coverage
- [ ] Edge cases tested

### Documentation
- [ ] Public APIs documented
- [ ] Complex logic explained
- [ ] README updated if needed
```

### Review Comments

Use prefixes for clarity:

| Prefix | Meaning |
|--------|---------|
| `blocking:` | Must be fixed before merge |
| `suggestion:` | Optional improvement |
| `question:` | Need clarification |
| `nitpick:` | Minor style issue |
| `praise:` | Something done well |

```markdown
# Examples

blocking: This could cause a race condition when multiple
requests arrive simultaneously. Consider using a lock.

suggestion: Consider extracting this into a separate method
for better testability.

question: Why did you choose this approach over X?

nitpick: Missing trailing comma.

praise: Great error handling here! Very thorough.
```

---

## Testing Requirements

### Coverage Requirements

| Component | Minimum Coverage |
|-----------|-----------------|
| Services | 90% |
| API Routes | 85% |
| Models | 80% |
| Core/Utils | 75% |
| Overall | 80% |

### Test Types Required

```python
# Every new feature needs:

# 1. Unit tests for business logic
def test_calculate_interview_score():
    """Test score calculation with various inputs."""
    pass

# 2. Integration tests for API endpoints
async def test_create_interview_endpoint():
    """Test the full request/response cycle."""
    pass

# 3. Edge case tests
def test_calculate_score_empty_transcript():
    """Test handling of empty transcript."""
    pass

def test_calculate_score_malformed_input():
    """Test handling of invalid input."""
    pass
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app --cov-report=html

# Run specific test file
poetry run pytest tests/unit/test_interview_service.py

# Run tests matching pattern
poetry run pytest -k "test_score"

# Run with verbose output
poetry run pytest -v

# Run only fast tests
poetry run pytest -m "not slow"

# Run in parallel
poetry run pytest -n auto
```

---

## Documentation Standards

### Code Documentation

```python
"""Module for Azure OpenAI integration.

This module provides a high-level interface for interacting with
Azure OpenAI services, including chat completions, embeddings,
and function calling.

Example:
    >>> service = AzureOpenAIService()
    >>> response = await service.chat("Hello!")
    >>> print(response.content)
"""

from typing import AsyncGenerator


class AzureOpenAIService:
    """Service for Azure OpenAI operations.

    Handles authentication, retries, rate limiting, and error
    handling for all OpenAI API calls.

    Attributes:
        model: The default model to use for completions.
        max_retries: Maximum number of retry attempts.

    Example:
        >>> async with AzureOpenAIService() as service:
        ...     response = await service.chat("Hello")
    """

    async def chat(
        self,
        message: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
    ) -> ChatResponse:
        """Send a chat message and get a response.

        Args:
            message: The user message to send.
            system_prompt: Optional system prompt to set context.
            temperature: Sampling temperature (0.0 to 2.0).

        Returns:
            ChatResponse with the assistant's reply.

        Raises:
            RateLimitError: If rate limit is exceeded.
            AuthenticationError: If API key is invalid.
        """
        pass
```

### API Documentation

API docs are auto-generated from code. Ensure:

1. All endpoints have docstrings
2. Request/response models have descriptions
3. Examples are provided

```python
@router.post(
    "/interviews",
    response_model=InterviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new interview",
    description="Creates a new interview session for a candidate application.",
    responses={
        201: {"description": "Interview created successfully"},
        400: {"description": "Invalid request data"},
        404: {"description": "Application not found"},
    },
)
async def create_interview(
    request: InterviewCreate,
    service: InterviewService = Depends(get_interview_service),
) -> InterviewResponse:
    """Create a new interview.

    Creates an interview session linked to the specified application.
    The interview will be initialized in 'pending' status.
    """
    pass
```

---

## Security Guidelines

### Secrets Management

```python
# ✅ Good: Use environment variables
from app.config import settings

api_key = settings.azure_openai_api_key

# ❌ Bad: Hardcoded secrets
api_key = "sk-1234567890abcdef"

# ❌ Bad: Secrets in code comments
# API key: sk-1234567890abcdef
```

### Input Validation

```python
from pydantic import BaseModel, Field, field_validator
import re

class UserInput(BaseModel):
    email: str = Field(..., max_length=255)
    name: str = Field(..., min_length=1, max_length=100)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        # Use proper email validation
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
            raise ValueError("Invalid email format")
        return v.lower()

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        # Prevent injection attacks
        if re.search(r"[<>\"']", v):
            raise ValueError("Invalid characters in name")
        return v.strip()
```

### SQL Injection Prevention

```python
# ✅ Good: Parameterized queries (Supabase handles this)
result = await supabase.table("interviews").select("*").eq("id", interview_id).execute()

# ❌ Bad: String interpolation
query = f"SELECT * FROM interviews WHERE id = '{interview_id}'"
```

### Authentication

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Validate JWT and return current user."""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=["HS256"],
        )
        return await get_user(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
```

---

## Getting Help

### Resources

| Resource | Link |
|----------|------|
| Project Documentation | `/docs` |
| API Documentation | `http://localhost:8000/docs` |
| Team Slack | `#talenti-backend` |
| Issue Tracker | GitHub Issues |

### Asking Questions

1. **Search First**: Check existing issues and documentation
2. **Be Specific**: Include error messages, logs, and steps to reproduce
3. **Provide Context**: What were you trying to do?

### Issue Template

```markdown
## Description
<!-- Clear description of the issue -->

## Steps to Reproduce
1. 
2. 
3. 

## Expected Behavior
<!-- What should happen? -->

## Actual Behavior
<!-- What actually happens? -->

## Environment
- Python version:
- OS:
- Branch:

## Logs/Screenshots
<!-- Include relevant logs or screenshots -->
```

### Contact

- **Tech Lead**: @tech-lead
- **Backend Team**: @backend-team
- **Security Issues**: security@example.com (do not post publicly)

---

## Appendix

### Useful Commands

```bash
# Development
poetry install           # Install dependencies
poetry add <package>     # Add dependency
poetry update           # Update dependencies
poetry shell            # Activate virtual environment

# Code Quality
poetry run black .      # Format code
poetry run ruff check . # Lint code
poetry run mypy app/    # Type check

# Testing
poetry run pytest                    # Run all tests
poetry run pytest -v                # Verbose
poetry run pytest --cov=app         # With coverage
poetry run pytest -x                # Stop on first failure

# Docker
docker-compose up -d    # Start services
docker-compose down     # Stop services
docker-compose logs -f  # View logs

# Database
poetry run python scripts/migrate.py  # Run migrations
poetry run python scripts/seed.py     # Seed test data
```

### Pre-commit Hooks

Install pre-commit hooks for automatic checks:

```bash
# Install pre-commit
poetry add --group dev pre-commit

# Install hooks
poetry run pre-commit install

# Run manually
poetry run pre-commit run --all-files
```

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 24.1.1
    hooks:
      - id: black

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.14
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic]
```

---

**Happy coding! 🚀**
