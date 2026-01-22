# Python Rebuild Guide

> **Complete migration guide from Supabase Edge Functions to Python FastAPI**

This guide provides comprehensive mappings for rebuilding the Talenti AI Interview Platform backend using Python, FastAPI, and Azure services.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Technology Stack Comparison](#technology-stack-comparison)
3. [Complete Dependencies](#complete-dependencies)
4. [Project Structure](#project-structure)
5. [Shared Components](#shared-components)
6. [Edge Function Mappings](#edge-function-mappings)
7. [Database Integration](#database-integration)
8. [Deployment](#deployment)
9. [Testing](#testing)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        React Frontend                           │
│                   (Existing - Minimal Changes)                  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Python FastAPI Backend                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   AI Routes  │  │  ACS Routes  │  │  Organisation Routes │  │
│  │ /api/ai/*    │  │ /api/acs/*   │  │  /api/organisations  │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Invitations  │  │ Azure Speech │  │  Data Retention      │  │
│  │ /api/invite  │  │ /api/azure/* │  │  /api/admin/*        │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   PostgreSQL  │    │ Azure Blob    │    │  Azure ACS    │
│   (Supabase)  │    │   Storage     │    │  + Speech     │
└───────────────┘    └───────────────┘    └───────────────┘
```

---

## Technology Stack Comparison

| Component | Current (Edge Functions) | Python Rebuild |
|-----------|-------------------------|----------------|
| Runtime | Deno | Python 3.11+ |
| Framework | Deno HTTP | FastAPI |
| Type Safety | TypeScript | Pydantic |
| Auth | Supabase JWT | python-jose |
| Database | Supabase Client | supabase-py / SQLAlchemy |
| AI Gateway | Lovable AI | OpenAI SDK / httpx |
| Email | Resend (fetch) | resend-python |
| Azure SDK | REST API | azure-* packages |
| Rate Limiting | Custom | slowapi |
| Testing | Deno test | pytest-asyncio |

---

## Complete Dependencies

Create `requirements.txt` with all dependencies:

```txt
# =============================================================================
# PYTHON REBUILD - COMPLETE DEPENDENCIES
# Talenti AI Interview Platform
# =============================================================================

# -----------------------------------------------------------------------------
# Core Framework
# -----------------------------------------------------------------------------
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
pydantic-settings==2.1.0
python-multipart==0.0.6
starlette==0.35.1

# -----------------------------------------------------------------------------
# Authentication & Security
# -----------------------------------------------------------------------------
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
cryptography==41.0.7

# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------
# Option A: Supabase Python Client (recommended for migration)
supabase==2.3.0
postgrest-py==0.13.0

# Option B: SQLAlchemy (for full control)
# sqlalchemy[asyncio]==2.0.25
# asyncpg==0.29.0
# alembic==1.13.1

# -----------------------------------------------------------------------------
# Azure Communication Services
# -----------------------------------------------------------------------------
azure-communication-callautomation==1.1.0
azure-communication-identity==1.4.0
azure-communication-sms==1.0.1
azure-eventgrid==4.17.0

# -----------------------------------------------------------------------------
# Azure Cognitive Services (Speech)
# -----------------------------------------------------------------------------
azure-cognitiveservices-speech==1.34.1

# -----------------------------------------------------------------------------
# Azure Storage
# -----------------------------------------------------------------------------
azure-storage-blob==12.19.0

# -----------------------------------------------------------------------------
# Azure Service Bus (for async processing)
# -----------------------------------------------------------------------------
azure-servicebus==7.11.4

# -----------------------------------------------------------------------------
# AI Integration
# -----------------------------------------------------------------------------
# OpenAI SDK (for Lovable AI Gateway or direct OpenAI)
openai==1.12.0

# Alternative: Direct HTTP requests
httpx==0.26.0

# LangChain (optional, for advanced AI workflows)
# langchain==0.1.5
# langchain-openai==0.0.5

# -----------------------------------------------------------------------------
# PDF Processing
# -----------------------------------------------------------------------------
pypdf==4.0.1
pdfplumber==0.10.3
python-docx==1.1.0

# -----------------------------------------------------------------------------
# Email
# -----------------------------------------------------------------------------
resend==0.7.2

# -----------------------------------------------------------------------------
# Rate Limiting
# -----------------------------------------------------------------------------
slowapi==0.1.9

# -----------------------------------------------------------------------------
# Audio Processing
# -----------------------------------------------------------------------------
pydub==0.25.1

# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------
python-dotenv==1.0.0
aiofiles==23.2.1
orjson==3.9.12
tenacity==8.2.3

# -----------------------------------------------------------------------------
# Monitoring & Logging
# -----------------------------------------------------------------------------
structlog==24.1.0
sentry-sdk[fastapi]==1.39.2

# -----------------------------------------------------------------------------
# Testing
# -----------------------------------------------------------------------------
pytest==7.4.4
pytest-asyncio==0.23.3
pytest-cov==4.1.0
httpx==0.26.0
respx==0.20.2
factory-boy==3.3.0

# -----------------------------------------------------------------------------
# Development
# -----------------------------------------------------------------------------
black==24.1.1
ruff==0.1.14
mypy==1.8.0
pre-commit==3.6.0
```

---

## Project Structure

```
python-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry
│   ├── config.py                  # Settings and environment
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py                # Shared dependencies (auth, db)
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health.py          # Health checks
│   │       ├── ai.py              # AI endpoints (interviewer, score, parse)
│   │       ├── acs.py             # ACS token & webhook
│   │       ├── azure_speech.py    # Speech token
│   │       ├── invitations.py     # Send invitation
│   │       ├── organisations.py   # Create organisation
│   │       └── admin.py           # Data retention cleanup
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── ai.py                  # AI request/response models
│   │   ├── acs.py                 # ACS models
│   │   ├── invitation.py          # Invitation models
│   │   └── organisation.py        # Organisation models
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── supabase_client.py     # Database client
│   │   ├── ai_gateway.py          # Lovable AI / OpenAI client
│   │   ├── acs_service.py         # Azure Communication Services
│   │   ├── speech_service.py      # Azure Speech
│   │   ├── storage_service.py     # Azure Blob Storage
│   │   ├── email_service.py       # Resend email
│   │   └── pdf_service.py         # PDF parsing
│   │
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py                # JWT authentication
│   │   ├── rate_limit.py          # Rate limiting
│   │   └── cors.py                # CORS configuration
│   │
│   └── utils/
│       ├── __init__.py
│       ├── scoring.py             # Interview scoring logic
│       └── tokens.py              # Token generation
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Pytest fixtures
│   ├── test_ai.py
│   ├── test_acs.py
│   └── test_invitations.py
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## Shared Components

### Configuration (`app/config.py`)

```python
"""
Application configuration using pydantic-settings
"""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "Talenti API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    SUPABASE_JWT_SECRET: str
    
    # Azure Communication Services
    ACS_CONNECTION_STRING: str
    ACS_ENDPOINT: str
    ACS_CALLBACK_URL: str = ""
    
    # Azure Speech
    AZURE_SPEECH_KEY: str
    AZURE_SPEECH_REGION: str = "australiaeast"
    
    # Azure Storage
    AZURE_STORAGE_CONNECTION_STRING: str
    RECORDING_CONTAINER: str = "interview-recordings"
    
    # AI Gateway (Lovable AI or OpenAI)
    LOVABLE_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    AI_GATEWAY_URL: str = "https://ai.gateway.lovable.dev/v1/chat/completions"
    DEFAULT_AI_MODEL: str = "google/gemini-3-flash-preview"
    
    # Email (Resend)
    RESEND_API_KEY: str
    FROM_EMAIL: str = "noreply@talenti.app"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    AI_RATE_LIMIT_PER_MINUTE: int = 20
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
```

### Main Application (`app/main.py`)

```python
"""
Talenti API - FastAPI Application
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.config import settings
from app.api.routes import health, ai, acs, azure_speech, invitations, organisations, admin
from app.middleware.rate_limit import limiter

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("starting_application", version=settings.APP_VERSION)
    yield
    logger.info("shutting_down_application")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI Interview Platform API",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Add rate limiter state
app.state.limiter = limiter

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])
app.include_router(acs.router, prefix="/api/acs", tags=["Azure Communication Services"])
app.include_router(azure_speech.router, prefix="/api/azure", tags=["Azure Speech"])
app.include_router(invitations.router, prefix="/api/invitations", tags=["Invitations"])
app.include_router(organisations.router, prefix="/api/organisations", tags=["Organisations"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])


@app.get("/")
async def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }
```

### Authentication Middleware (`app/middleware/auth.py`)

```python
"""
JWT Authentication middleware
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel

from app.config import settings

security = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    """JWT token payload"""
    sub: str  # User ID
    email: Optional[str] = None
    role: Optional[str] = None
    aud: str = "authenticated"
    exp: int


class CurrentUser(BaseModel):
    """Authenticated user"""
    id: str
    email: Optional[str] = None
    role: Optional[str] = None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> CurrentUser:
    """
    Validate JWT token and return current user.
    Raises 401 if token is missing or invalid.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"
        )
        
        token_data = TokenPayload(**payload)
        
        return CurrentUser(
            id=token_data.sub,
            email=token_data.email,
            role=token_data.role
        )
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[CurrentUser]:
    """
    Optionally validate JWT token.
    Returns None if no token provided.
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def require_role(required_role: str):
    """
    Dependency that requires a specific role.
    Usage: Depends(require_role("org_admin"))
    """
    async def role_checker(user: CurrentUser = Depends(get_current_user)):
        if user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {required_role}"
            )
        return user
    return role_checker
```

### Rate Limiting (`app/middleware/rate_limit.py`)

```python
"""
Rate limiting middleware using slowapi
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

from app.config import settings


def get_user_identifier(request: Request) -> str:
    """
    Get rate limit identifier from user or IP.
    Authenticated users get their user ID, anonymous get IP.
    """
    # Try to get user ID from auth header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        # Use a hash of the token for rate limiting
        return f"user:{hash(auth_header)}"
    
    # Fall back to IP address
    return get_remote_address(request)


limiter = Limiter(key_func=get_user_identifier)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors"""
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "detail": str(exc.detail),
            "retry_after": exc.detail
        },
        headers={"Retry-After": str(60)}
    )


# Rate limit decorators for different endpoints
def ai_rate_limit():
    """Rate limit for AI endpoints (more restrictive)"""
    return limiter.limit(f"{settings.AI_RATE_LIMIT_PER_MINUTE}/minute")


def standard_rate_limit():
    """Standard rate limit"""
    return limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
```

### Supabase Client Service (`app/services/supabase_client.py`)

```python
"""
Supabase client service for database operations
"""
from typing import Any, Dict, List, Optional
from supabase import create_client, Client
import structlog

from app.config import settings

logger = structlog.get_logger()


class SupabaseService:
    """Service for Supabase database operations"""
    
    def __init__(self):
        self._client: Optional[Client] = None
    
    @property
    def client(self) -> Client:
        """Get or create Supabase client"""
        if self._client is None:
            self._client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_KEY
            )
        return self._client
    
    # -------------------------------------------------------------------------
    # Interviews
    # -------------------------------------------------------------------------
    
    async def get_interview(self, interview_id: str) -> Optional[Dict]:
        """Get interview by ID with related data"""
        response = self.client.table("interviews").select(
            "*, applications(*, job_roles(*, organisations(*)))"
        ).eq("id", interview_id).single().execute()
        return response.data
    
    async def update_interview_status(
        self, 
        interview_id: str, 
        status: str,
        **kwargs
    ) -> Dict:
        """Update interview status and optional fields"""
        data = {"status": status, **kwargs}
        response = self.client.table("interviews").update(data).eq(
            "id", interview_id
        ).execute()
        return response.data
    
    async def save_transcript_segment(
        self,
        interview_id: str,
        speaker: str,
        content: str,
        start_time_ms: int,
        end_time_ms: Optional[int] = None,
        confidence: Optional[float] = None
    ) -> Dict:
        """Save a transcript segment"""
        response = self.client.table("transcript_segments").insert({
            "interview_id": interview_id,
            "speaker": speaker,
            "content": content,
            "start_time_ms": start_time_ms,
            "end_time_ms": end_time_ms,
            "confidence": confidence
        }).execute()
        return response.data
    
    async def get_transcript(self, interview_id: str) -> List[Dict]:
        """Get full transcript for an interview"""
        response = self.client.table("transcript_segments").select("*").eq(
            "interview_id", interview_id
        ).order("start_time_ms").execute()
        return response.data
    
    # -------------------------------------------------------------------------
    # Scoring
    # -------------------------------------------------------------------------
    
    async def save_interview_score(
        self,
        interview_id: str,
        overall_score: float,
        narrative_summary: str,
        candidate_feedback: str,
        model_version: str,
        prompt_version: str,
        rubric_version: Optional[str] = None
    ) -> Dict:
        """Save interview score"""
        response = self.client.table("interview_scores").upsert({
            "interview_id": interview_id,
            "overall_score": overall_score,
            "narrative_summary": narrative_summary,
            "candidate_feedback": candidate_feedback,
            "model_version": model_version,
            "prompt_version": prompt_version,
            "rubric_version": rubric_version,
            "scored_by": "ai"
        }).execute()
        return response.data
    
    async def save_score_dimensions(
        self,
        interview_id: str,
        dimensions: List[Dict]
    ) -> List[Dict]:
        """Save score dimensions for an interview"""
        records = [
            {
                "interview_id": interview_id,
                "dimension": d["dimension"],
                "score": d["score"],
                "weight": d.get("weight", 1.0),
                "evidence": d.get("evidence"),
                "cited_quotes": d.get("cited_quotes", [])
            }
            for d in dimensions
        ]
        response = self.client.table("score_dimensions").insert(records).execute()
        return response.data
    
    # -------------------------------------------------------------------------
    # Job Roles
    # -------------------------------------------------------------------------
    
    async def get_job_role(self, role_id: str) -> Optional[Dict]:
        """Get job role with scoring rubric"""
        response = self.client.table("job_roles").select("*").eq(
            "id", role_id
        ).single().execute()
        return response.data
    
    # -------------------------------------------------------------------------
    # Invitations
    # -------------------------------------------------------------------------
    
    async def create_invitation(
        self,
        application_id: str,
        token: str,
        expires_at: str,
        email_template: Optional[str] = None
    ) -> Dict:
        """Create a new invitation"""
        response = self.client.table("invitations").insert({
            "application_id": application_id,
            "token": token,
            "expires_at": expires_at,
            "email_template": email_template,
            "status": "pending"
        }).execute()
        return response.data
    
    async def update_invitation_status(
        self,
        invitation_id: str,
        status: str,
        **kwargs
    ) -> Dict:
        """Update invitation status"""
        data = {"status": status, **kwargs}
        response = self.client.table("invitations").update(data).eq(
            "id", invitation_id
        ).execute()
        return response.data
    
    # -------------------------------------------------------------------------
    # Organisations
    # -------------------------------------------------------------------------
    
    async def create_organisation(self, name: str, **kwargs) -> Dict:
        """Create a new organisation"""
        response = self.client.table("organisations").insert({
            "name": name,
            **kwargs
        }).execute()
        return response.data[0]
    
    async def add_org_user(
        self,
        organisation_id: str,
        user_id: str,
        role: str = "org_admin"
    ) -> Dict:
        """Add user to organisation"""
        response = self.client.table("org_users").insert({
            "organisation_id": organisation_id,
            "user_id": user_id,
            "role": role
        }).execute()
        return response.data
    
    # -------------------------------------------------------------------------
    # Candidate Profiles
    # -------------------------------------------------------------------------
    
    async def get_candidate_profile(self, user_id: str) -> Optional[Dict]:
        """Get candidate profile by user ID"""
        response = self.client.table("candidate_profiles").select("*").eq(
            "user_id", user_id
        ).single().execute()
        return response.data
    
    async def upsert_candidate_profile(
        self,
        user_id: str,
        data: Dict
    ) -> Dict:
        """Create or update candidate profile"""
        response = self.client.table("candidate_profiles").upsert({
            "user_id": user_id,
            **data
        }).execute()
        return response.data
    
    # -------------------------------------------------------------------------
    # Data Retention
    # -------------------------------------------------------------------------
    
    async def get_expired_recordings(self, retention_days: int) -> List[Dict]:
        """Get interviews with recordings past retention period"""
        from datetime import datetime, timedelta
        cutoff = (datetime.utcnow() - timedelta(days=retention_days)).isoformat()
        
        response = self.client.table("interviews").select(
            "id, recording_url, applications(job_roles(organisations(recording_retention_days)))"
        ).not_.is_("recording_url", "null").is_(
            "recording_deleted_at", "null"
        ).lt("ended_at", cutoff).execute()
        
        return response.data
    
    async def mark_recording_deleted(self, interview_id: str) -> Dict:
        """Mark interview recording as deleted"""
        from datetime import datetime
        response = self.client.table("interviews").update({
            "recording_url": None,
            "recording_deleted_at": datetime.utcnow().isoformat()
        }).eq("id", interview_id).execute()
        return response.data


# Singleton instance
supabase_service = SupabaseService()
```

### AI Gateway Service (`app/services/ai_gateway.py`)

```python
"""
AI Gateway service for Lovable AI / OpenAI integration
"""
from typing import Any, AsyncIterator, Dict, List, Optional
import httpx
import orjson
import structlog
from openai import AsyncOpenAI

from app.config import settings

logger = structlog.get_logger()


class AIGatewayService:
    """Service for AI model interactions via Lovable AI Gateway"""
    
    def __init__(self):
        self._client: Optional[AsyncOpenAI] = None
    
    @property
    def client(self) -> AsyncOpenAI:
        """Get or create OpenAI-compatible client for Lovable AI Gateway"""
        if self._client is None:
            # Use Lovable AI Gateway
            if settings.LOVABLE_API_KEY:
                self._client = AsyncOpenAI(
                    api_key=settings.LOVABLE_API_KEY,
                    base_url="https://ai.gateway.lovable.dev/v1"
                )
            # Fallback to direct OpenAI
            elif settings.OPENAI_API_KEY:
                self._client = AsyncOpenAI(
                    api_key=settings.OPENAI_API_KEY
                )
            else:
                raise ValueError("No AI API key configured")
        return self._client
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Non-streaming chat completion.
        Returns the full response.
        """
        model = model or settings.DEFAULT_AI_MODEL
        
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice
        
        try:
            response = await self.client.chat.completions.create(**kwargs)
            return response.model_dump()
        except Exception as e:
            logger.error("ai_completion_error", error=str(e), model=model)
            raise
    
    async def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> AsyncIterator[str]:
        """
        Streaming chat completion.
        Yields content chunks as they arrive.
        """
        model = model or settings.DEFAULT_AI_MODEL
        
        try:
            stream = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error("ai_stream_error", error=str(e), model=model)
            raise
    
    async def extract_structured_output(
        self,
        messages: List[Dict[str, str]],
        tool_schema: Dict,
        tool_name: str,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract structured output using tool calling.
        Returns the parsed tool arguments.
        """
        tools = [{
            "type": "function",
            "function": {
                "name": tool_name,
                **tool_schema
            }
        }]
        
        response = await self.chat_completion(
            messages=messages,
            model=model,
            tools=tools,
            tool_choice={"type": "function", "function": {"name": tool_name}}
        )
        
        # Extract tool call arguments
        tool_calls = response.get("choices", [{}])[0].get("message", {}).get("tool_calls", [])
        if tool_calls:
            return orjson.loads(tool_calls[0]["function"]["arguments"])
        
        return {}


# Singleton instance
ai_service = AIGatewayService()
```

---

## Edge Function Mappings

### 1. AI Interviewer (`/api/ai/interviewer`)

**Original:** `supabase/functions/ai-interviewer/index.ts`

**Python Equivalent:**

```python
# app/api/routes/ai.py

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import structlog

from app.middleware.auth import get_current_user, CurrentUser
from app.middleware.rate_limit import ai_rate_limit, limiter
from app.services.ai_gateway import ai_service
from app.services.supabase_client import supabase_service

logger = structlog.get_logger()
router = APIRouter()


# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------

class Message(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str


class InterviewerRequest(BaseModel):
    interview_id: str
    messages: List[Message]
    job_context: Optional[dict] = None
    competencies: Optional[List[str]] = None


class InterviewerResponse(BaseModel):
    response: str
    suggested_followup: Optional[str] = None
    competencies_covered: List[str] = []


# -----------------------------------------------------------------------------
# System Prompts
# -----------------------------------------------------------------------------

def build_interviewer_system_prompt(
    job_context: Optional[dict] = None,
    competencies: Optional[List[str]] = None
) -> str:
    """Build the system prompt for the AI interviewer"""
    
    base_prompt = """You are an expert AI interviewer conducting a professional job interview.

Your responsibilities:
1. Ask clear, relevant questions to assess the candidate's qualifications
2. Listen carefully to responses and ask thoughtful follow-up questions
3. Maintain a professional, friendly, and encouraging tone
4. Cover the key competencies required for the role
5. Allow the candidate to showcase their experience and skills

Guidelines:
- Ask one question at a time
- Use the STAR method (Situation, Task, Action, Result) for behavioral questions
- Provide brief acknowledgments of good answers
- Redirect politely if the candidate goes off-topic
- Keep track of which competencies have been assessed"""

    if job_context:
        base_prompt += f"""

Job Context:
- Role: {job_context.get('title', 'Not specified')}
- Department: {job_context.get('department', 'Not specified')}
- Description: {job_context.get('description', 'Not specified')}"""

    if competencies:
        base_prompt += f"""

Key Competencies to Assess:
{chr(10).join(f'- {c}' for c in competencies)}"""

    return base_prompt


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------

@router.post("/interviewer", response_model=InterviewerResponse)
@limiter.limit("20/minute")
async def ai_interviewer(
    request: InterviewerRequest,
    user: CurrentUser = Depends(get_current_user)
):
    """
    AI interviewer endpoint for conducting interviews.
    Maintains conversation context and tracks competencies.
    """
    logger.info(
        "ai_interviewer_request",
        interview_id=request.interview_id,
        user_id=user.id,
        message_count=len(request.messages)
    )
    
    try:
        # Build system prompt
        system_prompt = build_interviewer_system_prompt(
            job_context=request.job_context,
            competencies=request.competencies
        )
        
        # Prepare messages for AI
        messages = [
            {"role": "system", "content": system_prompt},
            *[{"role": m.role, "content": m.content} for m in request.messages]
        ]
        
        # Get AI response
        response = await ai_service.chat_completion(
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        ai_message = response["choices"][0]["message"]["content"]
        
        # Save transcript segment
        if request.messages:
            last_user_message = next(
                (m for m in reversed(request.messages) if m.role == "user"),
                None
            )
            if last_user_message:
                await supabase_service.save_transcript_segment(
                    interview_id=request.interview_id,
                    speaker="candidate",
                    content=last_user_message.content,
                    start_time_ms=0  # Would be provided by frontend
                )
        
        # Save AI response as transcript
        await supabase_service.save_transcript_segment(
            interview_id=request.interview_id,
            speaker="interviewer",
            content=ai_message,
            start_time_ms=0
        )
        
        return InterviewerResponse(
            response=ai_message,
            competencies_covered=[]  # Would be tracked across conversation
        )
        
    except Exception as e:
        logger.error("ai_interviewer_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/interviewer/stream")
@limiter.limit("20/minute")
async def ai_interviewer_stream(
    request: InterviewerRequest,
    user: CurrentUser = Depends(get_current_user)
):
    """
    Streaming AI interviewer endpoint.
    Returns Server-Sent Events with token-by-token responses.
    """
    logger.info(
        "ai_interviewer_stream_request",
        interview_id=request.interview_id,
        user_id=user.id
    )
    
    async def generate():
        system_prompt = build_interviewer_system_prompt(
            job_context=request.job_context,
            competencies=request.competencies
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            *[{"role": m.role, "content": m.content} for m in request.messages]
        ]
        
        full_response = ""
        
        async for chunk in ai_service.chat_completion_stream(
            messages=messages,
            temperature=0.7,
            max_tokens=500
        ):
            full_response += chunk
            yield f"data: {orjson.dumps({'content': chunk}).decode()}\n\n"
        
        # Save complete response to transcript
        await supabase_service.save_transcript_segment(
            interview_id=request.interview_id,
            speaker="interviewer",
            content=full_response,
            start_time_ms=0
        )
        
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )
```

---

### 2. Score Interview (`/api/ai/score`)

**Original:** `supabase/functions/score-interview/index.ts`

**Python Equivalent:**

```python
# app/api/routes/ai.py (continued)

class ScoreRequest(BaseModel):
    interview_id: str
    rubric_id: Optional[str] = None


class DimensionScore(BaseModel):
    dimension: str
    score: float
    weight: float
    evidence: str
    cited_quotes: List[str]


class ScoreResponse(BaseModel):
    overall_score: float
    dimensions: List[DimensionScore]
    narrative_summary: str
    candidate_feedback: str
    anti_cheat_risk_level: str


# Default scoring dimensions
DEFAULT_DIMENSIONS = [
    {"name": "Technical Skills", "weight": 0.25, "description": "Technical knowledge and problem-solving ability"},
    {"name": "Communication", "weight": 0.20, "description": "Clarity, articulation, and listening skills"},
    {"name": "Problem Solving", "weight": 0.20, "description": "Analytical thinking and approach to challenges"},
    {"name": "Cultural Fit", "weight": 0.15, "description": "Alignment with company values and team dynamics"},
    {"name": "Experience Relevance", "weight": 0.20, "description": "Relevance of past experience to the role"}
]


def build_scoring_tool_schema(dimensions: List[dict]) -> dict:
    """Build the tool schema for structured scoring output"""
    return {
        "description": "Score an interview transcript across multiple dimensions",
        "parameters": {
            "type": "object",
            "properties": {
                "dimensions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "dimension": {"type": "string"},
                            "score": {"type": "number", "minimum": 0, "maximum": 100},
                            "evidence": {"type": "string"},
                            "cited_quotes": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["dimension", "score", "evidence", "cited_quotes"]
                    }
                },
                "narrative_summary": {
                    "type": "string",
                    "description": "2-3 paragraph summary of the candidate's performance"
                },
                "candidate_feedback": {
                    "type": "string",
                    "description": "Constructive feedback for the candidate"
                },
                "anti_cheat_risk_level": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Assessment of potential cheating indicators"
                }
            },
            "required": ["dimensions", "narrative_summary", "candidate_feedback", "anti_cheat_risk_level"]
        }
    }


@router.post("/score", response_model=ScoreResponse)
@limiter.limit("10/minute")
async def score_interview(
    request: ScoreRequest,
    user: CurrentUser = Depends(get_current_user)
):
    """
    Score an interview transcript using AI.
    Uses structured output via tool calling for reliable JSON.
    """
    logger.info(
        "score_interview_request",
        interview_id=request.interview_id,
        user_id=user.id
    )
    
    try:
        # Get interview and transcript
        interview = await supabase_service.get_interview(request.interview_id)
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")
        
        transcript = await supabase_service.get_transcript(request.interview_id)
        if not transcript:
            raise HTTPException(status_code=400, detail="No transcript available")
        
        # Get custom rubric or use defaults
        dimensions = DEFAULT_DIMENSIONS
        if request.rubric_id:
            job_role = await supabase_service.get_job_role(
                interview["applications"]["job_role_id"]
            )
            if job_role and job_role.get("scoring_rubric"):
                dimensions = job_role["scoring_rubric"].get("dimensions", DEFAULT_DIMENSIONS)
        
        # Format transcript
        transcript_text = "\n".join([
            f"[{seg['speaker'].upper()}]: {seg['content']}"
            for seg in transcript
        ])
        
        # Build scoring prompt
        system_prompt = f"""You are an expert interview evaluator. Analyze the following interview transcript and score the candidate.

Scoring Dimensions:
{chr(10).join(f"- {d['name']} (weight: {d['weight']}): {d['description']}" for d in dimensions)}

Guidelines:
- Score each dimension from 0-100
- Provide specific evidence with direct quotes from the transcript
- Be fair and objective in your assessment
- Consider both strengths and areas for improvement
- Assess for any potential cheating indicators (rehearsed answers, background assistance, etc.)"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Please score this interview transcript:\n\n{transcript_text}"}
        ]
        
        # Get structured output using tool calling
        tool_schema = build_scoring_tool_schema(dimensions)
        result = await ai_service.extract_structured_output(
            messages=messages,
            tool_schema=tool_schema,
            tool_name="score_interview",
            model="google/gemini-2.5-pro"  # Use more capable model for scoring
        )
        
        # Calculate overall score
        dimension_scores = result.get("dimensions", [])
        total_weight = sum(d["weight"] for d in dimensions)
        overall_score = sum(
            next((ds["score"] for ds in dimension_scores if ds["dimension"] == d["name"]), 0) * d["weight"]
            for d in dimensions
        ) / total_weight
        
        # Save scores to database
        await supabase_service.save_interview_score(
            interview_id=request.interview_id,
            overall_score=overall_score,
            narrative_summary=result.get("narrative_summary", ""),
            candidate_feedback=result.get("candidate_feedback", ""),
            model_version="google/gemini-2.5-pro",
            prompt_version="v1.0"
        )
        
        # Save dimension scores
        await supabase_service.save_score_dimensions(
            interview_id=request.interview_id,
            dimensions=[
                {
                    "dimension": ds["dimension"],
                    "score": ds["score"],
                    "weight": next((d["weight"] for d in dimensions if d["name"] == ds["dimension"]), 1.0),
                    "evidence": ds["evidence"],
                    "cited_quotes": ds["cited_quotes"]
                }
                for ds in dimension_scores
            ]
        )
        
        return ScoreResponse(
            overall_score=overall_score,
            dimensions=[
                DimensionScore(
                    dimension=ds["dimension"],
                    score=ds["score"],
                    weight=next((d["weight"] for d in dimensions if d["name"] == ds["dimension"]), 1.0),
                    evidence=ds["evidence"],
                    cited_quotes=ds["cited_quotes"]
                )
                for ds in dimension_scores
            ],
            narrative_summary=result.get("narrative_summary", ""),
            candidate_feedback=result.get("candidate_feedback", ""),
            anti_cheat_risk_level=result.get("anti_cheat_risk_level", "low")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("score_interview_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
```

---

### 3. Parse Resume (`/api/ai/parse-resume`)

**Original:** `supabase/functions/parse-resume/index.ts`

**Python Equivalent:**

```python
# app/api/routes/ai.py (continued)

from fastapi import File, UploadFile
import pdfplumber
import io


class ParsedResume(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    summary: Optional[str] = None
    skills: List[str] = []
    experience: List[dict] = []
    education: List[dict] = []
    certifications: List[str] = []


def build_resume_parser_schema() -> dict:
    """Build the tool schema for resume parsing"""
    return {
        "description": "Parse a resume and extract structured information",
        "parameters": {
            "type": "object",
            "properties": {
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string"},
                "linkedin_url": {"type": "string"},
                "portfolio_url": {"type": "string"},
                "summary": {"type": "string", "description": "Professional summary or objective"},
                "skills": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of skills and technologies"
                },
                "experience": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "job_title": {"type": "string"},
                            "company_name": {"type": "string"},
                            "start_date": {"type": "string"},
                            "end_date": {"type": "string"},
                            "is_current": {"type": "boolean"},
                            "description": {"type": "string"}
                        }
                    }
                },
                "education": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "degree": {"type": "string"},
                            "institution": {"type": "string"},
                            "field_of_study": {"type": "string"},
                            "start_date": {"type": "string"},
                            "end_date": {"type": "string"}
                        }
                    }
                },
                "certifications": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["skills", "experience", "education"]
        }
    }


@router.post("/parse-resume", response_model=ParsedResume)
@limiter.limit("10/minute")
async def parse_resume(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user)
):
    """
    Parse a resume PDF and extract structured information using AI.
    """
    logger.info(
        "parse_resume_request",
        user_id=user.id,
        filename=file.filename,
        content_type=file.content_type
    )
    
    # Validate file type
    if not file.content_type or "pdf" not in file.content_type.lower():
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Read PDF content
        content = await file.read()
        pdf_file = io.BytesIO(content)
        
        # Extract text from PDF
        text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")
        
        # Limit text length for API
        max_chars = 15000
        if len(text) > max_chars:
            text = text[:max_chars] + "...[truncated]"
        
        # Parse with AI
        system_prompt = """You are an expert resume parser. Extract structured information from the resume text.

Guidelines:
- Extract all relevant contact information
- Parse work experience with dates and descriptions
- Extract education details
- Identify skills and technologies mentioned
- If information is not found, omit the field"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Please parse this resume:\n\n{text}"}
        ]
        
        result = await ai_service.extract_structured_output(
            messages=messages,
            tool_schema=build_resume_parser_schema(),
            tool_name="parse_resume"
        )
        
        return ParsedResume(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("parse_resume_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
```

---

### 4. Extract Requirements (`/api/ai/extract-requirements`)

**Original:** `supabase/functions/extract-requirements/index.ts`

**Python Equivalent:**

```python
# app/api/routes/ai.py (continued)

class ExtractRequirementsRequest(BaseModel):
    job_description: str
    title: Optional[str] = None


class ExtractedRequirements(BaseModel):
    required_skills: List[str]
    preferred_skills: List[str]
    experience_years: Optional[int] = None
    education_requirements: List[str]
    certifications: List[str]
    responsibilities: List[str]
    key_competencies: List[str]


def build_requirements_schema() -> dict:
    """Build the tool schema for requirements extraction"""
    return {
        "description": "Extract job requirements from a job description",
        "parameters": {
            "type": "object",
            "properties": {
                "required_skills": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Must-have skills"
                },
                "preferred_skills": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Nice-to-have skills"
                },
                "experience_years": {
                    "type": "integer",
                    "description": "Minimum years of experience required"
                },
                "education_requirements": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "certifications": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "responsibilities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Key job responsibilities"
                },
                "key_competencies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Behavioral competencies to assess"
                }
            },
            "required": ["required_skills", "responsibilities", "key_competencies"]
        }
    }


@router.post("/extract-requirements", response_model=ExtractedRequirements)
@limiter.limit("20/minute")
async def extract_requirements(
    request: ExtractRequirementsRequest,
    user: CurrentUser = Depends(get_current_user)
):
    """
    Extract structured requirements from a job description.
    """
    logger.info(
        "extract_requirements_request",
        user_id=user.id,
        title=request.title
    )
    
    try:
        system_prompt = """You are an expert HR analyst. Extract structured job requirements from the job description.

Guidelines:
- Separate required vs preferred skills
- Identify minimum experience requirements
- Extract education and certification requirements
- List key responsibilities
- Identify competencies that should be assessed in an interview"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extract requirements from this job description:\n\n{request.job_description}"}
        ]
        
        result = await ai_service.extract_structured_output(
            messages=messages,
            tool_schema=build_requirements_schema(),
            tool_name="extract_requirements"
        )
        
        return ExtractedRequirements(**result)
        
    except Exception as e:
        logger.error("extract_requirements_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
```

---

### 5. Generate Shortlist (`/api/ai/generate-shortlist`)

**Original:** `supabase/functions/generate-shortlist/index.ts`

**Python Equivalent:**

```python
# app/api/routes/ai.py (continued)

class GenerateShortlistRequest(BaseModel):
    job_role_id: str
    max_candidates: int = 10
    min_score: float = 60.0


class ShortlistCandidate(BaseModel):
    application_id: str
    candidate_name: str
    match_score: float
    match_reasons: List[str]
    concerns: List[str]


class ShortlistResponse(BaseModel):
    candidates: List[ShortlistCandidate]
    total_evaluated: int


@router.post("/generate-shortlist", response_model=ShortlistResponse)
@limiter.limit("5/minute")
async def generate_shortlist(
    request: GenerateShortlistRequest,
    user: CurrentUser = Depends(get_current_user)
):
    """
    Generate a shortlist of candidates for a job role using AI matching.
    """
    logger.info(
        "generate_shortlist_request",
        user_id=user.id,
        job_role_id=request.job_role_id
    )
    
    try:
        # Get job role details
        job_role = await supabase_service.get_job_role(request.job_role_id)
        if not job_role:
            raise HTTPException(status_code=404, detail="Job role not found")
        
        # Get applications with completed interviews
        applications = await supabase_service.client.table("applications").select(
            "*, candidate_profiles(*), interviews(*, interview_scores(*))"
        ).eq("job_role_id", request.job_role_id).execute()
        
        candidates = []
        
        for app in applications.data:
            if not app.get("interviews"):
                continue
            
            # Get best interview score
            interviews = app["interviews"]
            best_interview = max(
                (i for i in interviews if i.get("interview_scores")),
                key=lambda x: x["interview_scores"].get("overall_score", 0) if x.get("interview_scores") else 0,
                default=None
            )
            
            if not best_interview or not best_interview.get("interview_scores"):
                continue
            
            score = best_interview["interview_scores"]["overall_score"]
            
            if score >= request.min_score:
                profile = app.get("candidate_profiles", {})
                candidates.append(ShortlistCandidate(
                    application_id=app["id"],
                    candidate_name=f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip() or "Unknown",
                    match_score=score,
                    match_reasons=["Completed interview", f"Score: {score:.1f}"],
                    concerns=[]
                ))
        
        # Sort by score and limit
        candidates.sort(key=lambda x: x.match_score, reverse=True)
        candidates = candidates[:request.max_candidates]
        
        return ShortlistResponse(
            candidates=candidates,
            total_evaluated=len(applications.data)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("generate_shortlist_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
```

---

### 6. Send Invitation (`/api/invitations/send`)

**Original:** `supabase/functions/send-invitation/index.ts`

**Python Equivalent:**

```python
# app/api/routes/invitations.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timedelta
import secrets
import structlog
import resend

from app.config import settings
from app.middleware.auth import get_current_user, CurrentUser
from app.middleware.rate_limit import limiter
from app.services.supabase_client import supabase_service

logger = structlog.get_logger()
router = APIRouter()

# Initialize Resend
resend.api_key = settings.RESEND_API_KEY


class SendInvitationRequest(BaseModel):
    application_id: str
    candidate_email: EmailStr
    candidate_name: str
    job_title: str
    organisation_name: str
    expires_in_days: int = 7
    custom_message: Optional[str] = None


class SendInvitationResponse(BaseModel):
    invitation_id: str
    token: str
    expires_at: str
    email_sent: bool


def generate_invitation_token() -> str:
    """Generate a secure invitation token"""
    return secrets.token_urlsafe(32)


def build_invitation_email(
    candidate_name: str,
    job_title: str,
    organisation_name: str,
    invitation_url: str,
    expires_at: datetime,
    custom_message: Optional[str] = None
) -> dict:
    """Build the invitation email content"""
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 8px 8px; }}
            .button {{ display: inline-block; background: #667eea; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
            .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Interview Invitation</h1>
            </div>
            <div class="content">
                <p>Hi {candidate_name},</p>
                
                <p>You've been invited to complete an AI-powered interview for the <strong>{job_title}</strong> position at <strong>{organisation_name}</strong>.</p>
                
                {f'<p><em>"{custom_message}"</em></p>' if custom_message else ''}
                
                <p>Click the button below to start your interview:</p>
                
                <p style="text-align: center;">
                    <a href="{invitation_url}" class="button">Start Interview</a>
                </p>
                
                <p><strong>Important:</strong></p>
                <ul>
                    <li>This invitation expires on {expires_at.strftime('%B %d, %Y at %I:%M %p')}</li>
                    <li>The interview typically takes 20-30 minutes</li>
                    <li>Find a quiet place with stable internet</li>
                    <li>Have your camera and microphone ready</li>
                </ul>
                
                <p>Good luck!</p>
            </div>
            <div class="footer">
                <p>Powered by Talenti AI Interview Platform</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return {
        "from": settings.FROM_EMAIL,
        "subject": f"Interview Invitation: {job_title} at {organisation_name}",
        "html": html_content
    }


@router.post("/send", response_model=SendInvitationResponse)
@limiter.limit("30/minute")
async def send_invitation(
    request: SendInvitationRequest,
    user: CurrentUser = Depends(get_current_user)
):
    """
    Send an interview invitation email to a candidate.
    """
    logger.info(
        "send_invitation_request",
        user_id=user.id,
        application_id=request.application_id,
        candidate_email=request.candidate_email
    )
    
    try:
        # Generate secure token
        token = generate_invitation_token()
        
        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)
        
        # Create invitation record
        invitation = await supabase_service.create_invitation(
            application_id=request.application_id,
            token=token,
            expires_at=expires_at.isoformat()
        )
        
        invitation_id = invitation[0]["id"]
        
        # Build invitation URL
        invitation_url = f"https://talenti.app/interview/{token}"
        
        # Build and send email
        email_content = build_invitation_email(
            candidate_name=request.candidate_name,
            job_title=request.job_title,
            organisation_name=request.organisation_name,
            invitation_url=invitation_url,
            expires_at=expires_at,
            custom_message=request.custom_message
        )
        
        email_sent = False
        try:
            resend.Emails.send({
                "from": email_content["from"],
                "to": request.candidate_email,
                "subject": email_content["subject"],
                "html": email_content["html"]
            })
            email_sent = True
            
            # Update invitation status
            await supabase_service.update_invitation_status(
                invitation_id=invitation_id,
                status="sent",
                sent_at=datetime.utcnow().isoformat()
            )
            
        except Exception as email_error:
            logger.error("email_send_error", error=str(email_error))
            # Invitation created but email failed
            await supabase_service.update_invitation_status(
                invitation_id=invitation_id,
                status="pending"
            )
        
        return SendInvitationResponse(
            invitation_id=invitation_id,
            token=token,
            expires_at=expires_at.isoformat(),
            email_sent=email_sent
        )
        
    except Exception as e:
        logger.error("send_invitation_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
```

---

### 7. ACS Token Generator (`/api/acs/token`)

**Original:** `supabase/functions/acs-token-generator/index.ts`

**Python Equivalent:**

```python
# app/api/routes/acs.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import structlog

from azure.communication.identity import CommunicationIdentityClient
from azure.communication.identity import CommunicationUserIdentifier

from app.config import settings
from app.middleware.auth import get_current_user, CurrentUser
from app.middleware.rate_limit import limiter

logger = structlog.get_logger()
router = APIRouter()


class TokenRequest(BaseModel):
    interview_id: Optional[str] = None
    scopes: list[str] = ["voip"]


class TokenResponse(BaseModel):
    token: str
    expires_on: str
    user_id: str


# Initialize ACS Identity Client
acs_identity_client = CommunicationIdentityClient.from_connection_string(
    settings.ACS_CONNECTION_STRING
)


@router.post("/token", response_model=TokenResponse)
@limiter.limit("60/minute")
async def generate_acs_token(
    request: TokenRequest,
    user: CurrentUser = Depends(get_current_user)
):
    """
    Generate an Azure Communication Services access token for video calling.
    """
    logger.info(
        "acs_token_request",
        user_id=user.id,
        interview_id=request.interview_id
    )
    
    try:
        # Create or get ACS user identity
        # In production, you might want to store and reuse identities
        acs_user = acs_identity_client.create_user()
        
        # Generate access token with specified scopes
        from azure.communication.identity import CommunicationTokenScope
        
        scope_mapping = {
            "voip": CommunicationTokenScope.VOIP,
            "chat": CommunicationTokenScope.CHAT
        }
        
        scopes = [scope_mapping.get(s, CommunicationTokenScope.VOIP) for s in request.scopes]
        
        token_response = acs_identity_client.get_token(acs_user, scopes)
        
        return TokenResponse(
            token=token_response.token,
            expires_on=token_response.expires_on.isoformat(),
            user_id=acs_user.properties["id"]
        )
        
    except Exception as e:
        logger.error("acs_token_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to generate ACS token: {str(e)}")
```

---

### 8. ACS Webhook Handler (`/api/acs/webhook`)

**Original:** `supabase/functions/acs-webhook-handler/index.ts`

**Python Equivalent:**

```python
# app/api/routes/acs.py (continued)

from fastapi import Request, BackgroundTasks
import hmac
import hashlib
import base64


class WebhookEvent(BaseModel):
    type: str
    data: dict


async def verify_event_grid_signature(request: Request) -> bool:
    """Verify Azure Event Grid webhook signature"""
    # Get signature from header
    signature = request.headers.get("aeg-signature")
    if not signature:
        return False
    
    # For validation events, return true (they use different validation)
    validation_code = request.headers.get("aeg-subscription-validation-code")
    if validation_code:
        return True
    
    # Verify HMAC signature
    # Note: In production, implement full Event Grid signature validation
    return True  # Simplified for example


async def process_call_started(event_data: dict):
    """Process call started event"""
    call_connection_id = event_data.get("callConnectionId")
    logger.info("call_started", call_connection_id=call_connection_id)
    
    # Update interview status if applicable
    interview_id = event_data.get("correlationId")
    if interview_id:
        await supabase_service.update_interview_status(
            interview_id=interview_id,
            status="in_progress",
            started_at=datetime.utcnow().isoformat()
        )


async def process_call_ended(event_data: dict):
    """Process call ended event"""
    call_connection_id = event_data.get("callConnectionId")
    logger.info("call_ended", call_connection_id=call_connection_id)
    
    interview_id = event_data.get("correlationId")
    if interview_id:
        await supabase_service.update_interview_status(
            interview_id=interview_id,
            status="completed",
            ended_at=datetime.utcnow().isoformat()
        )


async def process_recording_available(event_data: dict):
    """Process recording available event"""
    recording_url = event_data.get("recordingStorageInfo", {}).get("recordingChunks", [{}])[0].get("contentLocation")
    logger.info("recording_available", recording_url=recording_url)
    
    interview_id = event_data.get("correlationId")
    if interview_id and recording_url:
        await supabase_service.update_interview_status(
            interview_id=interview_id,
            recording_url=recording_url
        )


@router.post("/webhook")
async def acs_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Handle Azure Communication Services Event Grid webhooks.
    Processes call lifecycle and recording events.
    """
    # Verify signature
    if not await verify_event_grid_signature(request):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    body = await request.json()
    
    # Handle Event Grid validation
    if isinstance(body, list) and body:
        first_event = body[0]
        if first_event.get("eventType") == "Microsoft.EventGrid.SubscriptionValidationEvent":
            validation_code = first_event.get("data", {}).get("validationCode")
            return {"validationResponse": validation_code}
    
    # Process events
    events = body if isinstance(body, list) else [body]
    
    for event in events:
        event_type = event.get("eventType", "")
        event_data = event.get("data", {})
        
        logger.info("acs_webhook_event", event_type=event_type)
        
        if "CallStarted" in event_type:
            background_tasks.add_task(process_call_started, event_data)
        elif "CallEnded" in event_type:
            background_tasks.add_task(process_call_ended, event_data)
        elif "RecordingFileStatusUpdated" in event_type:
            if event_data.get("recordingStorageInfo"):
                background_tasks.add_task(process_recording_available, event_data)
    
    return {"status": "processed"}
```

---

### 9. Azure Speech Token (`/api/azure/speech-token`)

**Original:** `supabase/functions/azure-speech-token/index.ts`

**Python Equivalent:**

```python
# app/api/routes/azure_speech.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import httpx
import structlog

from app.config import settings
from app.middleware.auth import get_current_user, CurrentUser
from app.middleware.rate_limit import limiter

logger = structlog.get_logger()
router = APIRouter()


class SpeechTokenResponse(BaseModel):
    token: str
    region: str
    expires_in: int


@router.get("/speech-token", response_model=SpeechTokenResponse)
@limiter.limit("60/minute")
async def get_speech_token(
    user: CurrentUser = Depends(get_current_user)
):
    """
    Generate an Azure Speech Services authentication token.
    Used for browser-based speech-to-text and text-to-speech.
    """
    logger.info("speech_token_request", user_id=user.id)
    
    try:
        # Get token from Azure Speech Services
        token_url = f"https://{settings.AZURE_SPEECH_REGION}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                headers={
                    "Ocp-Apim-Subscription-Key": settings.AZURE_SPEECH_KEY,
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )
            
            if response.status_code != 200:
                logger.error(
                    "speech_token_error",
                    status=response.status_code,
                    body=response.text
                )
                raise HTTPException(
                    status_code=500,
                    detail="Failed to get speech token from Azure"
                )
            
            token = response.text
            
            return SpeechTokenResponse(
                token=token,
                region=settings.AZURE_SPEECH_REGION,
                expires_in=600  # Token valid for 10 minutes
            )
            
    except httpx.RequestError as e:
        logger.error("speech_token_request_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
```

---

### 10. Create Organisation (`/api/organisations`)

**Original:** `supabase/functions/create-organisation/index.ts`

**Python Equivalent:**

```python
# app/api/routes/organisations.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import structlog

from app.middleware.auth import get_current_user, CurrentUser
from app.middleware.rate_limit import limiter
from app.services.supabase_client import supabase_service

logger = structlog.get_logger()
router = APIRouter()


class CreateOrganisationRequest(BaseModel):
    name: str
    industry: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    billing_email: Optional[str] = None


class OrganisationResponse(BaseModel):
    id: str
    name: str
    industry: Optional[str]
    website: Optional[str]
    description: Optional[str]
    created_at: str


@router.post("/", response_model=OrganisationResponse)
@limiter.limit("10/minute")
async def create_organisation(
    request: CreateOrganisationRequest,
    user: CurrentUser = Depends(get_current_user)
):
    """
    Create a new organisation and assign the current user as admin.
    """
    logger.info(
        "create_organisation_request",
        user_id=user.id,
        org_name=request.name
    )
    
    try:
        # Create organisation
        org = await supabase_service.create_organisation(
            name=request.name,
            industry=request.industry,
            website=request.website,
            description=request.description,
            billing_email=request.billing_email
        )
        
        # Add user as org admin
        await supabase_service.add_org_user(
            organisation_id=org["id"],
            user_id=user.id,
            role="org_admin"
        )
        
        # Also add to user_roles table
        await supabase_service.client.table("user_roles").insert({
            "user_id": user.id,
            "role": "org_admin"
        }).execute()
        
        logger.info(
            "organisation_created",
            org_id=org["id"],
            admin_user_id=user.id
        )
        
        return OrganisationResponse(
            id=org["id"],
            name=org["name"],
            industry=org.get("industry"),
            website=org.get("website"),
            description=org.get("description"),
            created_at=org["created_at"]
        )
        
    except Exception as e:
        logger.error("create_organisation_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
```

---

### 11. Data Retention Cleanup (`/api/admin/data-cleanup`)

**Original:** `supabase/functions/data-retention-cleanup/index.ts`

**Python Equivalent:**

```python
# app/api/routes/admin.py

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import structlog

from azure.storage.blob import BlobServiceClient

from app.config import settings
from app.middleware.auth import require_role, CurrentUser
from app.middleware.rate_limit import limiter
from app.services.supabase_client import supabase_service

logger = structlog.get_logger()
router = APIRouter()


class CleanupResult(BaseModel):
    recordings_deleted: int
    interviews_updated: int
    errors: List[str]


class CleanupResponse(BaseModel):
    status: str
    result: Optional[CleanupResult] = None
    message: str


# Initialize Azure Blob Storage client
blob_service_client = BlobServiceClient.from_connection_string(
    settings.AZURE_STORAGE_CONNECTION_STRING
)


async def delete_recording_from_storage(recording_url: str) -> bool:
    """Delete a recording file from Azure Blob Storage"""
    try:
        # Parse blob URL to get container and blob name
        # URL format: https://<account>.blob.core.windows.net/<container>/<blob>
        from urllib.parse import urlparse
        parsed = urlparse(recording_url)
        path_parts = parsed.path.strip("/").split("/", 1)
        
        if len(path_parts) != 2:
            logger.warning("invalid_recording_url", url=recording_url)
            return False
        
        container_name, blob_name = path_parts
        
        container_client = blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        
        blob_client.delete_blob()
        logger.info("recording_deleted", blob_name=blob_name)
        return True
        
    except Exception as e:
        logger.error("recording_delete_error", url=recording_url, error=str(e))
        return False


async def run_cleanup(default_retention_days: int = 90) -> CleanupResult:
    """Run the data retention cleanup process"""
    recordings_deleted = 0
    interviews_updated = 0
    errors = []
    
    try:
        # Get expired recordings
        expired = await supabase_service.get_expired_recordings(default_retention_days)
        
        for interview in expired:
            recording_url = interview.get("recording_url")
            interview_id = interview.get("id")
            
            # Check org-specific retention setting
            org_retention = (
                interview.get("applications", {})
                .get("job_roles", {})
                .get("organisations", {})
                .get("recording_retention_days")
            )
            
            retention_days = org_retention or default_retention_days
            
            # Double-check if actually expired
            from datetime import timedelta
            ended_at = datetime.fromisoformat(interview.get("ended_at", "").replace("Z", "+00:00"))
            cutoff = datetime.now(ended_at.tzinfo) - timedelta(days=retention_days)
            
            if ended_at > cutoff:
                continue
            
            # Delete from storage
            if recording_url:
                if await delete_recording_from_storage(recording_url):
                    recordings_deleted += 1
                    
                    # Mark as deleted in database
                    await supabase_service.mark_recording_deleted(interview_id)
                    interviews_updated += 1
                else:
                    errors.append(f"Failed to delete recording for interview {interview_id}")
        
    except Exception as e:
        errors.append(str(e))
        logger.error("cleanup_error", error=str(e))
    
    return CleanupResult(
        recordings_deleted=recordings_deleted,
        interviews_updated=interviews_updated,
        errors=errors
    )


@router.post("/data-cleanup", response_model=CleanupResponse)
@limiter.limit("1/minute")
async def data_retention_cleanup(
    background_tasks: BackgroundTasks,
    run_async: bool = True,
    user: CurrentUser = Depends(require_role("org_admin"))
):
    """
    Run data retention cleanup to delete expired recordings.
    Respects organisation-specific retention settings.
    
    Can run synchronously or asynchronously (background task).
    """
    logger.info(
        "data_cleanup_request",
        user_id=user.id,
        run_async=run_async
    )
    
    if run_async:
        background_tasks.add_task(run_cleanup)
        return CleanupResponse(
            status="started",
            message="Cleanup job started in background"
        )
    
    # Run synchronously
    result = await run_cleanup()
    
    return CleanupResponse(
        status="completed",
        result=result,
        message=f"Deleted {result.recordings_deleted} recordings, updated {result.interviews_updated} interviews"
    )


@router.get("/data-cleanup/status")
async def cleanup_status(
    user: CurrentUser = Depends(require_role("org_admin"))
):
    """Get the status of data retention settings and pending cleanup."""
    
    # Get count of recordings pending cleanup
    expired = await supabase_service.get_expired_recordings(90)
    
    return {
        "pending_cleanup_count": len(expired),
        "default_retention_days": 90,
        "last_run": None  # Would be tracked in a separate table
    }
```

---

## Database Integration

### Option A: Supabase Python Client (Recommended for Migration)

The examples above use the Supabase Python client, which provides:
- Direct compatibility with existing Supabase database
- Row Level Security (RLS) support
- Real-time subscriptions (if needed)

### Option B: SQLAlchemy (For Full Control)

If you need more control or want to migrate away from Supabase:

```python
# app/services/database.py

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,  # postgresql+asyncpg://...
    echo=settings.DEBUG,
    pool_pre_ping=True
)

# Create session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()


async def get_db() -> AsyncSession:
    """Dependency for database sessions"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
```

---

## Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health/live')"

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
      # Load from .env file
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Azure Container Apps Deployment

```bash
# Create resource group
az group create --name talenti-rg --location australiaeast

# Create Container Apps environment
az containerapp env create \
  --name talenti-env \
  --resource-group talenti-rg \
  --location australiaeast

# Deploy container
az containerapp create \
  --name talenti-api \
  --resource-group talenti-rg \
  --environment talenti-env \
  --image your-registry.azurecr.io/talenti-api:latest \
  --target-port 8000 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 10 \
  --secrets \
    supabase-url=secretref:supabase-url \
    supabase-key=secretref:supabase-service-key \
  --env-vars \
    SUPABASE_URL=secretref:supabase-url \
    SUPABASE_SERVICE_KEY=secretref:supabase-key
```

---

## Testing

### Pytest Configuration (`tests/conftest.py`)

```python
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.middleware.auth import CurrentUser


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_user():
    return CurrentUser(
        id="test-user-123",
        email="test@example.com",
        role="org_admin"
    )


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def mock_supabase():
    with patch("app.services.supabase_client.supabase_service") as mock:
        mock.get_interview = AsyncMock(return_value={
            "id": "int-123",
            "status": "in_progress"
        })
        mock.get_transcript = AsyncMock(return_value=[
            {"speaker": "interviewer", "content": "Tell me about yourself"},
            {"speaker": "candidate", "content": "I am a software engineer..."}
        ])
        yield mock


@pytest.fixture
def mock_ai_service():
    with patch("app.services.ai_gateway.ai_service") as mock:
        mock.chat_completion = AsyncMock(return_value={
            "choices": [{"message": {"content": "Great answer!"}}]
        })
        yield mock
```

### Example Tests (`tests/test_ai.py`)

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ai_interviewer(
    client: AsyncClient,
    auth_headers: dict,
    mock_supabase,
    mock_ai_service
):
    response = await client.post(
        "/api/ai/interviewer",
        json={
            "interview_id": "int-123",
            "messages": [
                {"role": "user", "content": "I have 5 years of experience..."}
            ]
        },
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "response" in data


@pytest.mark.asyncio
async def test_score_interview(
    client: AsyncClient,
    auth_headers: dict,
    mock_supabase,
    mock_ai_service
):
    mock_ai_service.extract_structured_output = AsyncMock(return_value={
        "dimensions": [
            {"dimension": "Technical Skills", "score": 85, "evidence": "...", "cited_quotes": []}
        ],
        "narrative_summary": "Strong candidate",
        "candidate_feedback": "Good job!",
        "anti_cheat_risk_level": "low"
    })
    
    response = await client.post(
        "/api/ai/score",
        json={"interview_id": "int-123"},
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "overall_score" in data
    assert "dimensions" in data
```

---

## Environment Variables Template (`.env.example`)

```bash
# =============================================================================
# Talenti Python Backend - Environment Variables
# =============================================================================

# Application
APP_NAME=Talenti API
APP_VERSION=1.0.0
DEBUG=false
LOG_LEVEL=INFO
ENVIRONMENT=production

# CORS
ALLOWED_ORIGINS=https://talenti.app,http://localhost:3000

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key
SUPABASE_JWT_SECRET=your-jwt-secret

# Azure Communication Services
ACS_CONNECTION_STRING=endpoint=https://your-acs.communication.azure.com/;accesskey=...
ACS_ENDPOINT=https://your-acs.communication.azure.com
ACS_CALLBACK_URL=https://your-api.azurecontainerapps.io/api/acs/webhook

# Azure Speech
AZURE_SPEECH_KEY=your-speech-key
AZURE_SPEECH_REGION=australiaeast

# Azure Storage
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
RECORDING_CONTAINER=interview-recordings

# AI Gateway
LOVABLE_API_KEY=your-lovable-api-key
# OR
OPENAI_API_KEY=your-openai-key
AI_GATEWAY_URL=https://ai.gateway.lovable.dev/v1/chat/completions
DEFAULT_AI_MODEL=google/gemini-3-flash-preview

# Email (Resend)
RESEND_API_KEY=re_...
FROM_EMAIL=noreply@talenti.app

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
AI_RATE_LIMIT_PER_MINUTE=20
```

---

## Migration Checklist

Use this checklist to track progress:

- [ ] **Setup**
  - [ ] Create Python project structure
  - [ ] Install dependencies
  - [ ] Configure environment variables
  
- [ ] **Shared Components**
  - [ ] Configuration module
  - [ ] Authentication middleware
  - [ ] Rate limiting
  - [ ] Supabase client service
  - [ ] AI gateway service
  
- [ ] **Edge Functions Migration**
  - [ ] `/api/ai/interviewer` (ai-interviewer)
  - [ ] `/api/ai/score` (score-interview)
  - [ ] `/api/ai/parse-resume` (parse-resume)
  - [ ] `/api/ai/extract-requirements` (extract-requirements)
  - [ ] `/api/ai/generate-shortlist` (generate-shortlist)
  - [ ] `/api/invitations/send` (send-invitation)
  - [ ] `/api/acs/token` (acs-token-generator)
  - [ ] `/api/acs/webhook` (acs-webhook-handler)
  - [ ] `/api/azure/speech-token` (azure-speech-token)
  - [ ] `/api/organisations` (create-organisation)
  - [ ] `/api/admin/data-cleanup` (data-retention-cleanup)
  
- [ ] **Testing**
  - [ ] Unit tests for all endpoints
  - [ ] Integration tests
  - [ ] Load testing
  
- [ ] **Deployment**
  - [ ] Docker configuration
  - [ ] Azure Container Apps setup
  - [ ] CI/CD pipeline
  - [ ] Monitoring and logging

---

## Related Documentation

- [HANDOVER.md](HANDOVER.md) - Complete codebase overview
- [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) - Database structure
- [API_REFERENCE.md](API_REFERENCE.md) - Original Edge Functions API
- [AZURE_SDK_EXAMPLES.md](AZURE_SDK_EXAMPLES.md) - Azure SDK usage patterns
- [SECURITY.md](SECURITY.md) - Security implementation details
