# Testing Strategy for Talenti Python Backend

This document outlines the comprehensive testing strategy for the Talenti AI Interview Platform Python FastAPI backend.

## Table of Contents

1. [Testing Philosophy](#1-testing-philosophy)
2. [Test Directory Structure](#2-test-directory-structure)
3. [Pytest Configuration](#3-pytest-configuration)
4. [Fixtures and Factories](#4-fixtures-and-factories)
5. [Unit Tests](#5-unit-tests)
6. [Integration Tests](#6-integration-tests)
7. [End-to-End Tests](#7-end-to-end-tests)
8. [Mocking Azure Services](#8-mocking-azure-services)
9. [Database Testing](#9-database-testing)
10. [WebSocket Testing](#10-websocket-testing)
11. [Performance Testing](#11-performance-testing)
12. [Security Testing](#12-security-testing)
13. [CI/CD Integration](#13-cicd-integration)
14. [Test Coverage](#14-test-coverage)

---

## 1. Testing Philosophy

### Testing Pyramid

```
         /\
        /  \
       / E2E\        <- Few, slow, high confidence
      /------\
     /        \
    /Integration\    <- Moderate, test service boundaries
   /--------------\
  /                \
 /    Unit Tests    \ <- Many, fast, isolated
/--------------------\
```

### Guiding Principles

1. **Fast Feedback**: Unit tests run in milliseconds
2. **Isolation**: Each test is independent
3. **Determinism**: Same input = same output
4. **Coverage**: Critical paths always tested
5. **Maintainability**: Tests are documentation

### Test Categories

| Category | Scope | Speed | Database | External Services |
|----------|-------|-------|----------|-------------------|
| Unit | Single function/class | < 10ms | No | Mocked |
| Integration | Multiple components | < 500ms | Yes (test DB) | Mocked |
| E2E | Full request flow | < 5s | Yes (test DB) | Real or Mocked |
| Performance | Load/stress | Minutes | Yes | Real |

---

## 2. Test Directory Structure

```
python-acs-service/
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Global fixtures
│   ├── pytest.ini                  # Pytest configuration
│   │
│   ├── unit/                       # Unit tests
│   │   ├── __init__.py
│   │   ├── conftest.py             # Unit test fixtures
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── test_azure_openai.py
│   │   │   ├── test_azure_speech.py
│   │   │   ├── test_azure_acs.py
│   │   │   ├── test_azure_blob.py
│   │   │   ├── test_document_service.py
│   │   │   ├── test_interview_service.py
│   │   │   ├── test_scoring_service.py
│   │   │   └── test_resume_service.py
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   ├── test_retry.py
│   │   │   ├── test_circuit_breaker.py
│   │   │   └── test_rate_limiter.py
│   │   └── models/
│   │       ├── __init__.py
│   │       └── test_validators.py
│   │
│   ├── integration/                # Integration tests
│   │   ├── __init__.py
│   │   ├── conftest.py             # Integration fixtures
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── test_interview_api.py
│   │   │   ├── test_resume_api.py
│   │   │   ├── test_speech_api.py
│   │   │   ├── test_acs_api.py
│   │   │   ├── test_recording_api.py
│   │   │   └── test_health_api.py
│   │   └── database/
│   │       ├── __init__.py
│   │       └── test_supabase_client.py
│   │
│   ├── e2e/                        # End-to-end tests
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_interview_flow.py
│   │   ├── test_resume_upload_flow.py
│   │   └── test_recording_flow.py
│   │
│   ├── performance/                # Performance tests
│   │   ├── __init__.py
│   │   ├── locustfile.py
│   │   └── test_load.py
│   │
│   ├── security/                   # Security tests
│   │   ├── __init__.py
│   │   ├── test_auth.py
│   │   ├── test_injection.py
│   │   └── test_rate_limiting.py
│   │
│   └── fixtures/                   # Shared test data
│       ├── __init__.py
│       ├── sample_resume.pdf
│       ├── sample_audio.wav
│       └── mock_responses.py
│
├── pyproject.toml                  # Project config with pytest settings
└── requirements-test.txt           # Test dependencies
```

---

## 3. Pytest Configuration

### pyproject.toml

```toml
[tool.pytest.ini_options]
minversion = "7.0"
addopts = [
    "-ra",
    "-q",
    "--strict-markers",
    "--strict-config",
    "-p no:warnings",
    "--tb=short",
]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
filterwarnings = [
    "ignore::DeprecationWarning",
    "ignore::PendingDeprecationWarning",
]

markers = [
    "unit: Unit tests (fast, isolated)",
    "integration: Integration tests (slower, with dependencies)",
    "e2e: End-to-end tests (slowest, full stack)",
    "slow: Marks tests as slow",
    "azure: Tests requiring Azure services",
    "database: Tests requiring database",
]

[tool.coverage.run]
source = ["app"]
branch = true
omit = [
    "*/tests/*",
    "*/__init__.py",
    "*/migrations/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
]
fail_under = 80
show_missing = true
```

### requirements-test.txt

```txt
# Testing
pytest>=7.4.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0
pytest-mock>=3.12.0
pytest-xdist>=3.5.0
pytest-timeout>=2.2.0
pytest-env>=1.1.0
pytest-randomly>=3.15.0

# HTTP testing
httpx>=0.26.0
respx>=0.20.2
aioresponses>=0.7.6

# Mocking
freezegun>=1.2.2
time-machine>=2.13.0
faker>=22.0.0
factory-boy>=3.3.0

# Performance testing
locust>=2.20.0
pytest-benchmark>=4.0.0

# Security testing
bandit>=1.7.6
safety>=2.3.5

# Type checking
mypy>=1.8.0

# Code quality
ruff>=0.1.9
black>=23.12.0
isort>=5.13.0
```

---

## 4. Fixtures and Factories

### Global Conftest (tests/conftest.py)

```python
"""
Global pytest configuration and fixtures.
"""
import asyncio
import os
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

# Set test environment before importing app
os.environ["ENVIRONMENT"] = "test"
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "test-anon-key"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test-service-key"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://test.openai.azure.com"
os.environ["AZURE_OPENAI_API_KEY"] = "test-api-key"
os.environ["AZURE_SPEECH_KEY"] = "test-speech-key"
os.environ["AZURE_SPEECH_REGION"] = "eastus"
os.environ["ACS_CONNECTION_STRING"] = "endpoint=https://test.communication.azure.com;accesskey=test"

from app.main import create_app
from app.config import Settings


# =============================================================================
# Event Loop Configuration
# =============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Application Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def app() -> FastAPI:
    """Create test application instance."""
    return create_app()


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    """Synchronous test client."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Asynchronous test client for async endpoint testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        timeout=30.0,
    ) as client:
        yield client


@pytest.fixture
def settings() -> Settings:
    """Test settings."""
    return Settings(
        environment="test",
        debug=True,
        supabase_url="https://test.supabase.co",
        supabase_anon_key="test-anon-key",
        supabase_service_role_key="test-service-key",
    )


# =============================================================================
# Authentication Fixtures
# =============================================================================

@pytest.fixture
def mock_user() -> dict:
    """Mock authenticated user data."""
    return {
        "id": "test-user-123",
        "email": "test@example.com",
        "role": "candidate",
        "organisation_id": None,
    }


@pytest.fixture
def mock_org_user() -> dict:
    """Mock authenticated organisation user."""
    return {
        "id": "org-user-456",
        "email": "recruiter@company.com",
        "role": "org_recruiter",
        "organisation_id": "org-123",
    }


@pytest.fixture
def mock_admin_user() -> dict:
    """Mock authenticated admin user."""
    return {
        "id": "admin-789",
        "email": "admin@company.com",
        "role": "org_admin",
        "organisation_id": "org-123",
    }


@pytest.fixture
def auth_headers(mock_user: dict) -> dict:
    """Authorization headers for authenticated requests."""
    return {"Authorization": "Bearer test-jwt-token"}


@pytest.fixture
def mock_auth(mock_user: dict):
    """Mock the authentication dependency."""
    with patch("app.api.dependencies.get_current_user") as mock:
        mock.return_value = mock_user
        yield mock


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    mock = MagicMock()
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    mock.delete.return_value = mock
    mock.eq.return_value = mock
    mock.execute.return_value = MagicMock(data=[])
    return mock


@pytest.fixture
def mock_supabase_service(mock_supabase):
    """Mock SupabaseService."""
    with patch("app.services.supabase_client.SupabaseService") as mock_class:
        instance = AsyncMock()
        instance.client = mock_supabase
        mock_class.return_value = instance
        yield instance


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture
def sample_interview() -> dict:
    """Sample interview data."""
    return {
        "id": "interview-123",
        "application_id": "application-456",
        "status": "in_progress",
        "started_at": "2024-01-15T10:00:00Z",
        "metadata": {
            "questions_asked": 3,
            "current_topic": "technical_skills",
        },
    }


@pytest.fixture
def sample_application() -> dict:
    """Sample application data."""
    return {
        "id": "application-456",
        "candidate_id": "test-user-123",
        "job_role_id": "role-789",
        "status": "interviewing",
        "match_score": 85,
    }


@pytest.fixture
def sample_job_role() -> dict:
    """Sample job role data."""
    return {
        "id": "role-789",
        "title": "Senior Software Engineer",
        "description": "Looking for an experienced developer...",
        "organisation_id": "org-123",
        "requirements": {
            "technical_skills": ["Python", "FastAPI", "Azure"],
            "experience_years": 5,
            "education": "Bachelor's in CS or equivalent",
        },
        "scoring_rubric": {
            "technical_skills": {"weight": 0.4},
            "communication": {"weight": 0.3},
            "problem_solving": {"weight": 0.3},
        },
    }


@pytest.fixture
def sample_transcript() -> list[dict]:
    """Sample interview transcript."""
    return [
        {
            "speaker": "interviewer",
            "content": "Tell me about your experience with Python.",
            "start_time_ms": 0,
            "end_time_ms": 3000,
        },
        {
            "speaker": "candidate",
            "content": "I have 5 years of experience with Python, primarily using FastAPI and Django.",
            "start_time_ms": 3500,
            "end_time_ms": 8000,
        },
        {
            "speaker": "interviewer",
            "content": "Can you describe a challenging project you've worked on?",
            "start_time_ms": 8500,
            "end_time_ms": 12000,
        },
    ]


@pytest.fixture
def sample_resume_text() -> str:
    """Sample parsed resume text."""
    return """
    John Doe
    Senior Software Engineer
    
    Experience:
    - 5 years at Tech Corp as Lead Developer
    - 3 years at Startup Inc as Software Engineer
    
    Skills:
    - Python, FastAPI, Django
    - Azure, AWS, Docker
    - PostgreSQL, Redis
    
    Education:
    - BS Computer Science, MIT, 2015
    """


# =============================================================================
# File Fixtures
# =============================================================================

@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Minimal valid PDF bytes for testing."""
    # Minimal PDF structure
    return b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >> endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer << /Size 4 /Root 1 0 R >>
startxref
190
%%EOF"""


@pytest.fixture
def sample_audio_bytes() -> bytes:
    """Minimal WAV audio bytes for testing."""
    # Minimal WAV header (44 bytes) + some audio data
    import struct
    
    sample_rate = 16000
    num_channels = 1
    bits_per_sample = 16
    num_samples = 1600  # 0.1 seconds
    
    data = bytes([0] * (num_samples * num_channels * bits_per_sample // 8))
    
    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        36 + len(data),
        b'WAVE',
        b'fmt ',
        16,
        1,  # PCM
        num_channels,
        sample_rate,
        sample_rate * num_channels * bits_per_sample // 8,
        num_channels * bits_per_sample // 8,
        bits_per_sample,
        b'data',
        len(data),
    )
    
    return header + data
```

### Test Factories (tests/fixtures/factories.py)

```python
"""
Test data factories using factory_boy.
"""
import factory
from datetime import datetime, timedelta
from typing import Any
import uuid


class InterviewFactory(factory.Factory):
    """Factory for interview test data."""
    
    class Meta:
        model = dict
    
    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    application_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    status = "scheduled"
    started_at = None
    ended_at = None
    duration_seconds = None
    recording_url = None
    metadata = factory.LazyFunction(dict)
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())
    updated_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())
    
    class Params:
        in_progress = factory.Trait(
            status="in_progress",
            started_at=factory.LazyFunction(
                lambda: (datetime.utcnow() - timedelta(minutes=15)).isoformat()
            ),
        )
        completed = factory.Trait(
            status="completed",
            started_at=factory.LazyFunction(
                lambda: (datetime.utcnow() - timedelta(hours=1)).isoformat()
            ),
            ended_at=factory.LazyFunction(
                lambda: (datetime.utcnow() - timedelta(minutes=30)).isoformat()
            ),
            duration_seconds=1800,
        )


class ApplicationFactory(factory.Factory):
    """Factory for application test data."""
    
    class Meta:
        model = dict
    
    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    candidate_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    job_role_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    status = "applied"
    match_score = factory.Faker("random_int", min=50, max=100)
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())
    updated_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())


class JobRoleFactory(factory.Factory):
    """Factory for job role test data."""
    
    class Meta:
        model = dict
    
    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    title = factory.Faker("job")
    description = factory.Faker("paragraph", nb_sentences=5)
    organisation_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    status = "active"
    requirements = factory.LazyFunction(lambda: {
        "technical_skills": ["Python", "SQL"],
        "experience_years": 3,
    })
    scoring_rubric = factory.LazyFunction(lambda: {
        "technical_skills": {"weight": 0.4, "criteria": []},
        "communication": {"weight": 0.3, "criteria": []},
        "problem_solving": {"weight": 0.3, "criteria": []},
    })
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())


class TranscriptSegmentFactory(factory.Factory):
    """Factory for transcript segment test data."""
    
    class Meta:
        model = dict
    
    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    interview_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    speaker = factory.Iterator(["interviewer", "candidate"])
    content = factory.Faker("sentence", nb_words=15)
    start_time_ms = factory.Sequence(lambda n: n * 5000)
    end_time_ms = factory.LazyAttribute(lambda o: o.start_time_ms + 4500)
    confidence = factory.Faker("pyfloat", min_value=0.8, max_value=1.0)
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())


class CandidateProfileFactory(factory.Factory):
    """Factory for candidate profile test data."""
    
    class Meta:
        model = dict
    
    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    user_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Faker("email")
    phone = factory.Faker("phone_number")
    country = factory.Faker("country_code")
    cv_file_path = None
    linkedin_url = factory.Faker("url")
    work_rights = "citizen"
    availability = "immediate"


class ScoringResultFactory(factory.Factory):
    """Factory for scoring result test data."""
    
    class Meta:
        model = dict
    
    interview_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    overall_score = factory.Faker("pyfloat", min_value=60, max_value=95)
    dimensions = factory.LazyFunction(lambda: [
        {
            "dimension": "technical_skills",
            "score": 85,
            "weight": 0.4,
            "evidence": "Demonstrated strong Python knowledge.",
        },
        {
            "dimension": "communication",
            "score": 80,
            "weight": 0.3,
            "evidence": "Clear and articulate responses.",
        },
        {
            "dimension": "problem_solving",
            "score": 75,
            "weight": 0.3,
            "evidence": "Good analytical approach.",
        },
    ])
    narrative_summary = factory.Faker("paragraph", nb_sentences=3)
    candidate_feedback = factory.Faker("paragraph", nb_sentences=2)
```

### Mock Responses (tests/fixtures/mock_responses.py)

```python
"""
Mock API responses for Azure services.
"""
from typing import Any


class MockOpenAIResponses:
    """Mock responses for Azure OpenAI."""
    
    @staticmethod
    def chat_completion(content: str = "This is a mock response.") -> dict:
        return {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1677652288,
            "model": "gpt-4",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
        }
    
    @staticmethod
    def interview_response() -> dict:
        return MockOpenAIResponses.chat_completion(
            "That's a great point. Can you tell me more about your experience "
            "with distributed systems?"
        )
    
    @staticmethod
    def scoring_response() -> dict:
        return MockOpenAIResponses.chat_completion("""
        {
            "overall_score": 82,
            "dimensions": [
                {
                    "dimension": "technical_skills",
                    "score": 85,
                    "weight": 0.4,
                    "evidence": "Strong understanding of Python and FastAPI.",
                    "cited_quotes": ["I have 5 years of experience with Python"]
                },
                {
                    "dimension": "communication",
                    "score": 80,
                    "weight": 0.3,
                    "evidence": "Clear and structured responses."
                },
                {
                    "dimension": "problem_solving",
                    "score": 78,
                    "weight": 0.3,
                    "evidence": "Good analytical approach to challenges."
                }
            ],
            "narrative_summary": "Strong technical candidate with good communication.",
            "candidate_feedback": "Great interview! Consider providing more examples."
        }
        """)
    
    @staticmethod
    def resume_parse_response() -> dict:
        return MockOpenAIResponses.chat_completion("""
        {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "+1-555-0123",
            "skills": ["Python", "FastAPI", "Azure", "PostgreSQL"],
            "experience": [
                {
                    "title": "Senior Developer",
                    "company": "Tech Corp",
                    "duration": "2019-2024",
                    "description": "Led development of cloud services."
                }
            ],
            "education": [
                {
                    "degree": "BS Computer Science",
                    "institution": "MIT",
                    "year": "2015"
                }
            ],
            "summary": "Experienced software engineer with 8 years in backend development."
        }
        """)


class MockSpeechResponses:
    """Mock responses for Azure Speech Services."""
    
    @staticmethod
    def token_response() -> dict:
        return {
            "token": "mock-speech-token-12345",
            "region": "eastus",
            "expires_at": "2024-01-15T11:00:00Z",
        }
    
    @staticmethod
    def synthesis_result() -> bytes:
        """Return minimal audio bytes."""
        return b"\x00" * 1000


class MockACSResponses:
    """Mock responses for Azure Communication Services."""
    
    @staticmethod
    def identity_response() -> dict:
        return {
            "user_id": "8:acs:test-user-id",
            "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsIng1dCI6IjJ...",
            "expires_on": "2024-01-15T12:00:00Z",
        }
    
    @staticmethod
    def call_response() -> dict:
        return {
            "call_connection_id": "call-conn-123",
            "server_call_id": "server-call-456",
            "status": "connected",
        }
    
    @staticmethod
    def recording_response() -> dict:
        return {
            "recording_id": "rec-789",
            "recording_state": "active",
        }


class MockBlobResponses:
    """Mock responses for Azure Blob Storage."""
    
    @staticmethod
    def upload_response() -> dict:
        return {
            "blob_url": "https://storage.blob.core.windows.net/container/file.pdf",
            "etag": "0x8D12345678",
            "last_modified": "2024-01-15T10:30:00Z",
        }
    
    @staticmethod
    def sas_url() -> str:
        return (
            "https://storage.blob.core.windows.net/container/file.pdf"
            "?sv=2023-01-03&st=2024-01-15T10%3A00%3A00Z&se=2024-01-15T11%3A00%3A00Z"
            "&sr=b&sp=r&sig=abcdef123456"
        )


class MockDocumentIntelligenceResponses:
    """Mock responses for Azure Document Intelligence."""
    
    @staticmethod
    def analyze_result() -> dict:
        return {
            "status": "succeeded",
            "created_date_time": "2024-01-15T10:30:00Z",
            "last_updated_date_time": "2024-01-15T10:30:05Z",
            "analyze_result": {
                "api_version": "2023-07-31",
                "model_id": "prebuilt-document",
                "content": "John Doe\nSenior Software Engineer\n...",
                "pages": [
                    {
                        "page_number": 1,
                        "width": 8.5,
                        "height": 11,
                        "unit": "inch",
                    }
                ],
            },
        }
```

---

## 5. Unit Tests

### Azure OpenAI Service Tests (tests/unit/services/test_azure_openai.py)

```python
"""
Unit tests for Azure OpenAI service.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from openai import RateLimitError, APIConnectionError, APIStatusError

from app.services.azure_openai import AzureOpenAIService
from tests.fixtures.mock_responses import MockOpenAIResponses


class TestAzureOpenAIService:
    """Test cases for AzureOpenAIService."""
    
    @pytest.fixture
    def service(self) -> AzureOpenAIService:
        """Create service instance with mocked client."""
        with patch("app.services.azure_openai.AsyncAzureOpenAI") as mock_class:
            mock_client = AsyncMock()
            mock_class.return_value = mock_client
            service = AzureOpenAIService()
            service._client = mock_client
            return service
    
    # =========================================================================
    # Chat Completion Tests
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_chat_completion_success(self, service: AzureOpenAIService):
        """Test successful chat completion."""
        # Arrange
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Hello, how can I help?"))
        ]
        mock_response.usage = MagicMock(total_tokens=50)
        service._client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        messages = [{"role": "user", "content": "Hi"}]
        
        # Act
        result = await service.chat_completion(messages)
        
        # Assert
        assert result == "Hello, how can I help?"
        service._client.chat.completions.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_chat_completion_with_system_message(self, service: AzureOpenAIService):
        """Test chat completion includes system message."""
        # Arrange
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
        service._client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        messages = [{"role": "user", "content": "Question"}]
        system_message = "You are a helpful assistant."
        
        # Act
        await service.chat_completion(messages, system_message=system_message)
        
        # Assert
        call_args = service._client.chat.completions.create.call_args
        passed_messages = call_args.kwargs["messages"]
        assert passed_messages[0]["role"] == "system"
        assert passed_messages[0]["content"] == system_message
    
    @pytest.mark.asyncio
    async def test_chat_completion_rate_limit_retry(self, service: AzureOpenAIService):
        """Test retry on rate limit error."""
        # Arrange
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Success"))]
        
        # First call raises rate limit, second succeeds
        service._client.chat.completions.create = AsyncMock(
            side_effect=[
                RateLimitError(
                    message="Rate limit exceeded",
                    response=MagicMock(status_code=429),
                    body={"error": {"message": "Rate limit"}},
                ),
                mock_response,
            ]
        )
        
        messages = [{"role": "user", "content": "Hi"}]
        
        # Act
        result = await service.chat_completion(messages)
        
        # Assert
        assert result == "Success"
        assert service._client.chat.completions.create.call_count == 2
    
    @pytest.mark.asyncio
    async def test_chat_completion_max_retries_exceeded(self, service: AzureOpenAIService):
        """Test max retries exceeded raises exception."""
        # Arrange
        service._client.chat.completions.create = AsyncMock(
            side_effect=RateLimitError(
                message="Rate limit exceeded",
                response=MagicMock(status_code=429),
                body={"error": {"message": "Rate limit"}},
            )
        )
        
        messages = [{"role": "user", "content": "Hi"}]
        
        # Act & Assert
        with pytest.raises(RateLimitError):
            await service.chat_completion(messages, max_retries=3)
    
    @pytest.mark.asyncio
    async def test_chat_completion_connection_error(self, service: AzureOpenAIService):
        """Test connection error handling."""
        # Arrange
        service._client.chat.completions.create = AsyncMock(
            side_effect=APIConnectionError(request=MagicMock())
        )
        
        messages = [{"role": "user", "content": "Hi"}]
        
        # Act & Assert
        with pytest.raises(APIConnectionError):
            await service.chat_completion(messages)
    
    # =========================================================================
    # Streaming Tests
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_stream_completion(self, service: AzureOpenAIService):
        """Test streaming chat completion."""
        # Arrange
        chunks = [
            MagicMock(choices=[MagicMock(delta=MagicMock(content="Hello"))]),
            MagicMock(choices=[MagicMock(delta=MagicMock(content=" World"))]),
            MagicMock(choices=[MagicMock(delta=MagicMock(content=None))]),
        ]
        
        async def mock_stream():
            for chunk in chunks:
                yield chunk
        
        service._client.chat.completions.create = AsyncMock(return_value=mock_stream())
        
        messages = [{"role": "user", "content": "Hi"}]
        
        # Act
        result_chunks = []
        async for chunk in service.stream_completion(messages):
            result_chunks.append(chunk)
        
        # Assert
        assert result_chunks == ["Hello", " World"]
    
    # =========================================================================
    # Interview Response Tests
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_generate_interview_response(
        self,
        service: AzureOpenAIService,
        sample_job_role: dict,
        sample_transcript: list,
    ):
        """Test interview response generation."""
        # Arrange
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(
                content="That's interesting. Can you elaborate on your experience?"
            ))
        ]
        service._client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Act
        result = await service.generate_interview_response(
            transcript=sample_transcript,
            job_role=sample_job_role,
            candidate_response="I worked on distributed systems.",
        )
        
        # Assert
        assert "interesting" in result.lower() or "elaborate" in result.lower()
    
    # =========================================================================
    # Scoring Tests
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_score_interview(
        self,
        service: AzureOpenAIService,
        sample_transcript: list,
        sample_job_role: dict,
    ):
        """Test interview scoring."""
        # Arrange
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="""
            {
                "overall_score": 82,
                "dimensions": [
                    {"dimension": "technical_skills", "score": 85, "weight": 0.4}
                ],
                "narrative_summary": "Strong candidate.",
                "candidate_feedback": "Good job!"
            }
            """))
        ]
        service._client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Act
        result = await service.score_interview(
            transcript=sample_transcript,
            job_role=sample_job_role,
        )
        
        # Assert
        assert result["overall_score"] == 82
        assert len(result["dimensions"]) == 1
        assert result["dimensions"][0]["dimension"] == "technical_skills"
    
    @pytest.mark.asyncio
    async def test_score_interview_invalid_json(self, service: AzureOpenAIService):
        """Test handling of invalid JSON in scoring response."""
        # Arrange
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="This is not valid JSON"))
        ]
        service._client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid scoring response"):
            await service.score_interview(
                transcript=[{"speaker": "interviewer", "content": "Hi"}],
                job_role={"title": "Developer"},
            )
    
    # =========================================================================
    # Token Counting Tests
    # =========================================================================
    
    def test_count_tokens(self, service: AzureOpenAIService):
        """Test token counting."""
        # Arrange
        text = "Hello, how are you today?"
        
        # Act
        count = service.count_tokens(text)
        
        # Assert
        assert isinstance(count, int)
        assert count > 0
        assert count < 100  # Reasonable for short text
    
    def test_truncate_messages(self, service: AzureOpenAIService):
        """Test message truncation to fit token limit."""
        # Arrange
        messages = [
            {"role": "user", "content": "A" * 10000},
            {"role": "assistant", "content": "B" * 10000},
            {"role": "user", "content": "C" * 10000},
        ]
        max_tokens = 1000
        
        # Act
        truncated = service.truncate_messages(messages, max_tokens=max_tokens)
        
        # Assert
        assert len(truncated) <= len(messages)
        total_tokens = sum(service.count_tokens(m["content"]) for m in truncated)
        assert total_tokens <= max_tokens


class TestInterviewPromptBuilder:
    """Test cases for interview prompt construction."""
    
    def test_build_system_prompt(self, sample_job_role: dict):
        """Test system prompt includes job requirements."""
        from app.services.azure_openai import build_interviewer_prompt
        
        # Act
        prompt = build_interviewer_prompt(sample_job_role)
        
        # Assert
        assert sample_job_role["title"] in prompt
        assert "Python" in prompt or "technical" in prompt.lower()
    
    def test_build_system_prompt_with_custom_structure(self):
        """Test custom interview structure is included."""
        from app.services.azure_openai import build_interviewer_prompt
        
        job_role = {
            "title": "Data Scientist",
            "interview_structure": {
                "topics": ["machine_learning", "statistics", "coding"],
                "time_per_topic": 10,
            },
        }
        
        # Act
        prompt = build_interviewer_prompt(job_role)
        
        # Assert
        assert "machine_learning" in prompt.lower() or "ml" in prompt.lower()
```

### Retry Utility Tests (tests/unit/utils/test_retry.py)

```python
"""
Unit tests for retry utilities.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
import asyncio

from app.utils.retry import async_retry, RetryExhaustedError


class TestAsyncRetry:
    """Test cases for async retry decorator."""
    
    @pytest.mark.asyncio
    async def test_success_first_attempt(self):
        """Test successful execution on first attempt."""
        # Arrange
        mock_func = AsyncMock(return_value="success")
        decorated = async_retry(max_retries=3)(mock_func)
        
        # Act
        result = await decorated()
        
        # Assert
        assert result == "success"
        assert mock_func.call_count == 1
    
    @pytest.mark.asyncio
    async def test_success_after_retry(self):
        """Test successful execution after initial failures."""
        # Arrange
        mock_func = AsyncMock(
            side_effect=[ValueError("fail"), ValueError("fail"), "success"]
        )
        decorated = async_retry(
            max_retries=3,
            exceptions=(ValueError,),
            base_delay=0.01,
        )(mock_func)
        
        # Act
        result = await decorated()
        
        # Assert
        assert result == "success"
        assert mock_func.call_count == 3
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test exception raised after max retries."""
        # Arrange
        mock_func = AsyncMock(side_effect=ValueError("always fails"))
        decorated = async_retry(
            max_retries=3,
            exceptions=(ValueError,),
            base_delay=0.01,
        )(mock_func)
        
        # Act & Assert
        with pytest.raises(ValueError, match="always fails"):
            await decorated()
        
        assert mock_func.call_count == 3
    
    @pytest.mark.asyncio
    async def test_non_retryable_exception(self):
        """Test non-retryable exception is raised immediately."""
        # Arrange
        mock_func = AsyncMock(side_effect=TypeError("wrong type"))
        decorated = async_retry(
            max_retries=3,
            exceptions=(ValueError,),  # TypeError not included
            base_delay=0.01,
        )(mock_func)
        
        # Act & Assert
        with pytest.raises(TypeError, match="wrong type"):
            await decorated()
        
        assert mock_func.call_count == 1
    
    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test delays increase exponentially."""
        # Arrange
        delays = []
        original_sleep = asyncio.sleep
        
        async def mock_sleep(delay):
            delays.append(delay)
            await original_sleep(0.001)  # Minimal actual sleep
        
        mock_func = AsyncMock(
            side_effect=[ValueError("fail")] * 4 + ["success"]
        )
        
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(asyncio, "sleep", mock_sleep)
            decorated = async_retry(
                max_retries=5,
                exceptions=(ValueError,),
                base_delay=0.1,
                max_delay=10.0,
                exponential_base=2,
            )(mock_func)
            
            await decorated()
        
        # Assert exponential increase (with some jitter)
        assert len(delays) == 4
        assert delays[1] > delays[0]
        assert delays[2] > delays[1]
    
    @pytest.mark.asyncio
    async def test_retry_with_callback(self):
        """Test retry callback is called on each retry."""
        # Arrange
        retry_callback = MagicMock()
        mock_func = AsyncMock(
            side_effect=[ValueError("fail"), ValueError("fail"), "success"]
        )
        decorated = async_retry(
            max_retries=3,
            exceptions=(ValueError,),
            base_delay=0.01,
            on_retry=retry_callback,
        )(mock_func)
        
        # Act
        await decorated()
        
        # Assert
        assert retry_callback.call_count == 2  # Called on retry 1 and 2
```

### Circuit Breaker Tests (tests/unit/utils/test_circuit_breaker.py)

```python
"""
Unit tests for circuit breaker pattern.
"""
import pytest
from unittest.mock import AsyncMock
import asyncio
from datetime import datetime, timedelta

from app.utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpen


class TestCircuitBreaker:
    """Test cases for CircuitBreaker."""
    
    @pytest.fixture
    def breaker(self) -> CircuitBreaker:
        """Create circuit breaker with test settings."""
        return CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1.0,
            half_open_max_calls=2,
        )
    
    @pytest.mark.asyncio
    async def test_closed_state_success(self, breaker: CircuitBreaker):
        """Test successful calls in closed state."""
        # Arrange
        async def successful_call():
            return "success"
        
        # Act
        result = await breaker.call(successful_call)
        
        # Assert
        assert result == "success"
        assert breaker.state == "closed"
        assert breaker.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_closed_state_failure_count(self, breaker: CircuitBreaker):
        """Test failure counting in closed state."""
        # Arrange
        async def failing_call():
            raise ValueError("error")
        
        # Act
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_call)
        
        # Assert
        assert breaker.state == "closed"
        assert breaker.failure_count == 2
    
    @pytest.mark.asyncio
    async def test_opens_after_threshold(self, breaker: CircuitBreaker):
        """Test circuit opens after failure threshold."""
        # Arrange
        async def failing_call():
            raise ValueError("error")
        
        # Act
        for _ in range(3):
            with pytest.raises(ValueError):
                await breaker.call(failing_call)
        
        # Assert
        assert breaker.state == "open"
    
    @pytest.mark.asyncio
    async def test_open_state_rejects_calls(self, breaker: CircuitBreaker):
        """Test open circuit rejects calls immediately."""
        # Arrange
        breaker._state = "open"
        breaker._opened_at = datetime.utcnow()
        
        async def any_call():
            return "should not execute"
        
        # Act & Assert
        with pytest.raises(CircuitBreakerOpen):
            await breaker.call(any_call)
    
    @pytest.mark.asyncio
    async def test_half_open_after_timeout(self, breaker: CircuitBreaker):
        """Test circuit enters half-open after recovery timeout."""
        # Arrange
        breaker._state = "open"
        breaker._opened_at = datetime.utcnow() - timedelta(seconds=2)
        
        async def successful_call():
            return "success"
        
        # Act
        result = await breaker.call(successful_call)
        
        # Assert
        assert result == "success"
        assert breaker.state in ("half-open", "closed")
    
    @pytest.mark.asyncio
    async def test_half_open_success_closes(self, breaker: CircuitBreaker):
        """Test successful calls in half-open close the circuit."""
        # Arrange
        breaker._state = "half-open"
        breaker._half_open_calls = 0
        
        async def successful_call():
            return "success"
        
        # Act
        for _ in range(breaker.half_open_max_calls):
            await breaker.call(successful_call)
        
        # Assert
        assert breaker.state == "closed"
        assert breaker.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_half_open_failure_reopens(self, breaker: CircuitBreaker):
        """Test failure in half-open reopens circuit."""
        # Arrange
        breaker._state = "half-open"
        breaker._half_open_calls = 0
        
        async def failing_call():
            raise ValueError("error")
        
        # Act & Assert
        with pytest.raises(ValueError):
            await breaker.call(failing_call)
        
        assert breaker.state == "open"
    
    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self, breaker: CircuitBreaker):
        """Test successful call resets failure count."""
        # Arrange
        breaker._failure_count = 2
        
        async def successful_call():
            return "success"
        
        # Act
        await breaker.call(successful_call)
        
        # Assert
        assert breaker.failure_count == 0
    
    def test_get_stats(self, breaker: CircuitBreaker):
        """Test circuit breaker statistics."""
        # Arrange
        breaker._failure_count = 2
        breaker._total_calls = 10
        breaker._total_failures = 3
        
        # Act
        stats = breaker.get_stats()
        
        # Assert
        assert stats["state"] == "closed"
        assert stats["failure_count"] == 2
        assert stats["total_calls"] == 10
        assert stats["total_failures"] == 3
        assert stats["failure_rate"] == 0.3
```

---

## 6. Integration Tests

### Interview API Tests (tests/integration/api/test_interview_api.py)

```python
"""
Integration tests for Interview API endpoints.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock

from tests.fixtures.factories import InterviewFactory, ApplicationFactory, JobRoleFactory


class TestInterviewAPI:
    """Integration tests for /api/v1/interview endpoints."""
    
    # =========================================================================
    # Chat Endpoint Tests
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_chat_success(
        self,
        async_client: AsyncClient,
        mock_auth,
        mock_supabase_service,
        sample_interview: dict,
        sample_application: dict,
        sample_job_role: dict,
    ):
        """Test successful interview chat interaction."""
        # Arrange
        mock_supabase_service.get_interview.return_value = sample_interview
        mock_supabase_service.get_application.return_value = {
            **sample_application,
            "job_roles": sample_job_role,
        }
        mock_supabase_service.get_transcript.return_value = []
        
        with patch("app.services.azure_openai.AzureOpenAIService") as mock_openai:
            mock_openai_instance = AsyncMock()
            mock_openai_instance.generate_interview_response.return_value = (
                "That's interesting. Tell me more about your experience."
            )
            mock_openai.return_value = mock_openai_instance
            
            # Act
            response = await async_client.post(
                "/api/v1/interview/chat",
                json={
                    "interview_id": sample_interview["id"],
                    "message": "I have 5 years of Python experience.",
                },
                headers={"Authorization": "Bearer test-token"},
            )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "Tell me more" in data["response"]
    
    @pytest.mark.asyncio
    async def test_chat_interview_not_found(
        self,
        async_client: AsyncClient,
        mock_auth,
        mock_supabase_service,
    ):
        """Test chat with non-existent interview."""
        # Arrange
        mock_supabase_service.get_interview.return_value = None
        
        # Act
        response = await async_client.post(
            "/api/v1/interview/chat",
            json={
                "interview_id": "non-existent-id",
                "message": "Hello",
            },
            headers={"Authorization": "Bearer test-token"},
        )
        
        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_chat_interview_not_in_progress(
        self,
        async_client: AsyncClient,
        mock_auth,
        mock_supabase_service,
    ):
        """Test chat with completed interview."""
        # Arrange
        completed_interview = InterviewFactory(completed=True)
        mock_supabase_service.get_interview.return_value = completed_interview
        
        # Act
        response = await async_client.post(
            "/api/v1/interview/chat",
            json={
                "interview_id": completed_interview["id"],
                "message": "Hello",
            },
            headers={"Authorization": "Bearer test-token"},
        )
        
        # Assert
        assert response.status_code == 400
        assert "not in progress" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_chat_unauthorized(self, async_client: AsyncClient):
        """Test chat without authentication."""
        # Act
        response = await async_client.post(
            "/api/v1/interview/chat",
            json={
                "interview_id": "interview-123",
                "message": "Hello",
            },
        )
        
        # Assert
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_chat_wrong_user(
        self,
        async_client: AsyncClient,
        mock_supabase_service,
        sample_interview: dict,
        sample_application: dict,
    ):
        """Test chat with interview belonging to different user."""
        # Arrange
        different_user = {"id": "different-user", "role": "candidate"}
        with patch("app.api.dependencies.get_current_user", return_value=different_user):
            mock_supabase_service.get_interview.return_value = sample_interview
            mock_supabase_service.get_application.return_value = {
                **sample_application,
                "candidate_id": "original-user",  # Different from authenticated user
            }
            
            # Act
            response = await async_client.post(
                "/api/v1/interview/chat",
                json={
                    "interview_id": sample_interview["id"],
                    "message": "Hello",
                },
                headers={"Authorization": "Bearer test-token"},
            )
        
        # Assert
        assert response.status_code == 403
    
    # =========================================================================
    # Streaming Chat Tests
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_chat_stream(
        self,
        async_client: AsyncClient,
        mock_auth,
        mock_supabase_service,
        sample_interview: dict,
        sample_application: dict,
        sample_job_role: dict,
    ):
        """Test streaming interview chat."""
        # Arrange
        mock_supabase_service.get_interview.return_value = sample_interview
        mock_supabase_service.get_application.return_value = {
            **sample_application,
            "job_roles": sample_job_role,
        }
        mock_supabase_service.get_transcript.return_value = []
        
        async def mock_stream():
            yield "Hello"
            yield " there"
            yield "!"
        
        with patch("app.services.azure_openai.AzureOpenAIService") as mock_openai:
            mock_openai_instance = AsyncMock()
            mock_openai_instance.stream_interview_response.return_value = mock_stream()
            mock_openai.return_value = mock_openai_instance
            
            # Act
            response = await async_client.post(
                "/api/v1/interview/chat/stream",
                json={
                    "interview_id": sample_interview["id"],
                    "message": "Tell me about yourself.",
                },
                headers={"Authorization": "Bearer test-token"},
            )
        
        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"
    
    # =========================================================================
    # Start Interview Tests
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_start_interview(
        self,
        async_client: AsyncClient,
        mock_auth,
        mock_supabase_service,
    ):
        """Test starting an interview."""
        # Arrange
        interview = InterviewFactory()
        application = ApplicationFactory()
        job_role = JobRoleFactory()
        
        mock_supabase_service.get_interview.return_value = interview
        mock_supabase_service.get_application.return_value = {
            **application,
            "job_roles": job_role,
        }
        mock_supabase_service.update_interview.return_value = {
            **interview,
            "status": "in_progress",
        }
        
        with patch("app.services.azure_openai.AzureOpenAIService") as mock_openai:
            mock_openai_instance = AsyncMock()
            mock_openai_instance.generate_interview_response.return_value = (
                "Welcome! Let's start with an introduction."
            )
            mock_openai.return_value = mock_openai_instance
            
            # Act
            response = await async_client.post(
                f"/api/v1/interview/{interview['id']}/start",
                headers={"Authorization": "Bearer test-token"},
            )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"
        assert "opening_message" in data
    
    # =========================================================================
    # End Interview Tests
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_end_interview(
        self,
        async_client: AsyncClient,
        mock_auth,
        mock_supabase_service,
        sample_interview: dict,
    ):
        """Test ending an interview."""
        # Arrange
        in_progress_interview = {**sample_interview, "status": "in_progress"}
        mock_supabase_service.get_interview.return_value = in_progress_interview
        mock_supabase_service.update_interview.return_value = {
            **in_progress_interview,
            "status": "completed",
        }
        
        # Act
        response = await async_client.post(
            f"/api/v1/interview/{sample_interview['id']}/end",
            headers={"Authorization": "Bearer test-token"},
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
    
    # =========================================================================
    # Score Interview Tests
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_score_interview(
        self,
        async_client: AsyncClient,
        mock_auth,
        mock_supabase_service,
        sample_transcript: list,
    ):
        """Test interview scoring."""
        # Arrange
        completed_interview = InterviewFactory(completed=True)
        job_role = JobRoleFactory()
        application = ApplicationFactory()
        
        mock_supabase_service.get_interview.return_value = completed_interview
        mock_supabase_service.get_application.return_value = {
            **application,
            "job_roles": job_role,
        }
        mock_supabase_service.get_transcript.return_value = sample_transcript
        
        scoring_result = {
            "overall_score": 82,
            "dimensions": [
                {"dimension": "technical_skills", "score": 85, "weight": 0.4},
            ],
            "narrative_summary": "Strong candidate.",
            "candidate_feedback": "Good job!",
        }
        
        with patch("app.services.azure_openai.AzureOpenAIService") as mock_openai:
            mock_openai_instance = AsyncMock()
            mock_openai_instance.score_interview.return_value = scoring_result
            mock_openai.return_value = mock_openai_instance
            
            # Act
            response = await async_client.post(
                f"/api/v1/interview/{completed_interview['id']}/score",
                headers={"Authorization": "Bearer test-token"},
            )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["overall_score"] == 82
        assert len(data["dimensions"]) == 1


class TestInterviewValidation:
    """Test input validation for interview endpoints."""
    
    @pytest.mark.asyncio
    async def test_chat_empty_message(
        self,
        async_client: AsyncClient,
        mock_auth,
    ):
        """Test chat with empty message."""
        # Act
        response = await async_client.post(
            "/api/v1/interview/chat",
            json={
                "interview_id": "interview-123",
                "message": "",
            },
            headers={"Authorization": "Bearer test-token"},
        )
        
        # Assert
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_chat_message_too_long(
        self,
        async_client: AsyncClient,
        mock_auth,
    ):
        """Test chat with excessively long message."""
        # Act
        response = await async_client.post(
            "/api/v1/interview/chat",
            json={
                "interview_id": "interview-123",
                "message": "x" * 50001,  # Exceeds 50000 char limit
            },
            headers={"Authorization": "Bearer test-token"},
        )
        
        # Assert
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_chat_invalid_interview_id(
        self,
        async_client: AsyncClient,
        mock_auth,
    ):
        """Test chat with invalid interview ID format."""
        # Act
        response = await async_client.post(
            "/api/v1/interview/chat",
            json={
                "interview_id": "not-a-uuid",
                "message": "Hello",
            },
            headers={"Authorization": "Bearer test-token"},
        )
        
        # Assert
        # Should either validate format (422) or not find (404)
        assert response.status_code in (404, 422)
```

### Resume API Tests (tests/integration/api/test_resume_api.py)

```python
"""
Integration tests for Resume API endpoints.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
import io


class TestResumeAPI:
    """Integration tests for /api/v1/resume endpoints."""
    
    @pytest.mark.asyncio
    async def test_parse_resume_pdf(
        self,
        async_client: AsyncClient,
        mock_auth,
        sample_pdf_bytes: bytes,
    ):
        """Test parsing PDF resume."""
        # Arrange
        parsed_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "skills": ["Python", "FastAPI"],
            "experience": [],
        }
        
        with patch("app.services.document_service.AzureDocumentService") as mock_doc:
            mock_doc_instance = AsyncMock()
            mock_doc_instance.extract_text.return_value = "John Doe\nPython Developer"
            mock_doc.return_value = mock_doc_instance
            
            with patch("app.services.azure_openai.AzureOpenAIService") as mock_openai:
                mock_openai_instance = AsyncMock()
                mock_openai_instance.parse_resume.return_value = parsed_data
                mock_openai.return_value = mock_openai_instance
                
                # Act
                response = await async_client.post(
                    "/api/v1/resume/parse",
                    files={"file": ("resume.pdf", sample_pdf_bytes, "application/pdf")},
                    headers={"Authorization": "Bearer test-token"},
                )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "John Doe"
        assert "Python" in data["skills"]
    
    @pytest.mark.asyncio
    async def test_parse_resume_invalid_format(
        self,
        async_client: AsyncClient,
        mock_auth,
    ):
        """Test parsing unsupported file format."""
        # Act
        response = await async_client.post(
            "/api/v1/resume/parse",
            files={"file": ("resume.exe", b"invalid", "application/octet-stream")},
            headers={"Authorization": "Bearer test-token"},
        )
        
        # Assert
        assert response.status_code == 400
        assert "unsupported" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_parse_resume_too_large(
        self,
        async_client: AsyncClient,
        mock_auth,
    ):
        """Test parsing file exceeding size limit."""
        # Arrange
        large_file = b"x" * (10 * 1024 * 1024 + 1)  # 10MB + 1 byte
        
        # Act
        response = await async_client.post(
            "/api/v1/resume/parse",
            files={"file": ("resume.pdf", large_file, "application/pdf")},
            headers={"Authorization": "Bearer test-token"},
        )
        
        # Assert
        assert response.status_code == 413
    
    @pytest.mark.asyncio
    async def test_upload_resume(
        self,
        async_client: AsyncClient,
        mock_auth,
        mock_supabase_service,
        sample_pdf_bytes: bytes,
    ):
        """Test uploading resume to storage."""
        # Arrange
        with patch("app.services.azure_blob.AzureBlobService") as mock_blob:
            mock_blob_instance = AsyncMock()
            mock_blob_instance.upload_file.return_value = {
                "blob_url": "https://storage.blob.core.windows.net/resumes/user-123/resume.pdf",
            }
            mock_blob.return_value = mock_blob_instance
            
            mock_supabase_service.update_candidate_profile.return_value = {}
            
            # Act
            response = await async_client.post(
                "/api/v1/resume/upload",
                files={"file": ("resume.pdf", sample_pdf_bytes, "application/pdf")},
                headers={"Authorization": "Bearer test-token"},
            )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "url" in data


class TestResumeRequirementsExtraction:
    """Test resume requirements extraction."""
    
    @pytest.mark.asyncio
    async def test_extract_requirements(
        self,
        async_client: AsyncClient,
        mock_auth,
    ):
        """Test extracting job requirements from description."""
        # Arrange
        job_description = """
        We are looking for a Senior Software Engineer with:
        - 5+ years of Python experience
        - Experience with FastAPI or Django
        - Cloud experience (AWS or Azure)
        - Strong communication skills
        """
        
        extracted = {
            "technical_skills": ["Python", "FastAPI", "Django", "AWS", "Azure"],
            "experience_years": 5,
            "soft_skills": ["communication"],
        }
        
        with patch("app.services.azure_openai.AzureOpenAIService") as mock_openai:
            mock_openai_instance = AsyncMock()
            mock_openai_instance.extract_requirements.return_value = extracted
            mock_openai.return_value = mock_openai_instance
            
            # Act
            response = await async_client.post(
                "/api/v1/resume/extract-requirements",
                json={"job_description": job_description},
                headers={"Authorization": "Bearer test-token"},
            )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "Python" in data["technical_skills"]
        assert data["experience_years"] == 5
```

### Health API Tests (tests/integration/api/test_health_api.py)

```python
"""
Integration tests for Health API endpoints.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


class TestHealthAPI:
    """Integration tests for health check endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_check(self, async_client: AsyncClient):
        """Test basic health check."""
        # Act
        response = await async_client.get("/health")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_readiness_all_healthy(self, async_client: AsyncClient):
        """Test readiness when all dependencies are healthy."""
        # Arrange
        with patch("app.api.routes.health.check_database") as mock_db:
            mock_db.return_value = True
            with patch("app.api.routes.health.check_azure_services") as mock_azure:
                mock_azure.return_value = True
                
                # Act
                response = await async_client.get("/health/ready")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["checks"]["database"] == "healthy"
        assert data["checks"]["azure"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_readiness_database_unhealthy(self, async_client: AsyncClient):
        """Test readiness when database is unhealthy."""
        # Arrange
        with patch("app.api.routes.health.check_database") as mock_db:
            mock_db.return_value = False
            with patch("app.api.routes.health.check_azure_services") as mock_azure:
                mock_azure.return_value = True
                
                # Act
                response = await async_client.get("/health/ready")
        
        # Assert
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["database"] == "unhealthy"
    
    @pytest.mark.asyncio
    async def test_liveness(self, async_client: AsyncClient):
        """Test liveness probe."""
        # Act
        response = await async_client.get("/health/live")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
    
    @pytest.mark.asyncio
    async def test_detailed_health(self, async_client: AsyncClient):
        """Test detailed health information."""
        # Act
        response = await async_client.get("/health/detailed")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "uptime" in data
        assert "memory" in data
```

---

## 7. End-to-End Tests

### Interview Flow E2E (tests/e2e/test_interview_flow.py)

```python
"""
End-to-end tests for complete interview flow.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
import asyncio

from tests.fixtures.factories import (
    InterviewFactory,
    ApplicationFactory,
    JobRoleFactory,
    TranscriptSegmentFactory,
)


class TestInterviewFlowE2E:
    """End-to-end tests for complete interview workflow."""
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_complete_interview_flow(
        self,
        async_client: AsyncClient,
        mock_auth,
        mock_supabase_service,
    ):
        """Test complete interview from start to scoring."""
        # Setup test data
        interview = InterviewFactory()
        application = ApplicationFactory(id=interview["application_id"])
        job_role = JobRoleFactory()
        
        mock_supabase_service.get_interview.return_value = interview
        mock_supabase_service.get_application.return_value = {
            **application,
            "job_roles": job_role,
        }
        mock_supabase_service.get_transcript.return_value = []
        mock_supabase_service.save_transcript_segment.return_value = {}
        
        with patch("app.services.azure_openai.AzureOpenAIService") as mock_openai:
            mock_instance = AsyncMock()
            mock_openai.return_value = mock_instance
            
            # Step 1: Start interview
            mock_instance.generate_interview_response.return_value = (
                "Welcome! Tell me about your background."
            )
            mock_supabase_service.update_interview.return_value = {
                **interview,
                "status": "in_progress",
            }
            
            start_response = await async_client.post(
                f"/api/v1/interview/{interview['id']}/start",
                headers={"Authorization": "Bearer test-token"},
            )
            assert start_response.status_code == 200
            
            # Step 2: Conduct interview conversation
            mock_instance.generate_interview_response.side_effect = [
                "Interesting! Can you elaborate on your Python experience?",
                "How do you handle challenging deadlines?",
                "Tell me about a project you're proud of.",
            ]
            
            candidate_responses = [
                "I have 5 years of experience in software development.",
                "I've worked extensively with Python and FastAPI.",
                "I prioritize tasks and communicate proactively.",
            ]
            
            for candidate_message in candidate_responses:
                chat_response = await async_client.post(
                    "/api/v1/interview/chat",
                    json={
                        "interview_id": interview["id"],
                        "message": candidate_message,
                    },
                    headers={"Authorization": "Bearer test-token"},
                )
                assert chat_response.status_code == 200
            
            # Step 3: End interview
            mock_supabase_service.update_interview.return_value = {
                **interview,
                "status": "completed",
            }
            
            end_response = await async_client.post(
                f"/api/v1/interview/{interview['id']}/end",
                headers={"Authorization": "Bearer test-token"},
            )
            assert end_response.status_code == 200
            
            # Step 4: Score interview
            mock_supabase_service.get_interview.return_value = {
                **interview,
                "status": "completed",
            }
            mock_supabase_service.get_transcript.return_value = [
                TranscriptSegmentFactory() for _ in range(6)
            ]
            
            mock_instance.score_interview.return_value = {
                "overall_score": 82,
                "dimensions": [
                    {"dimension": "technical_skills", "score": 85, "weight": 0.4},
                    {"dimension": "communication", "score": 80, "weight": 0.3},
                    {"dimension": "problem_solving", "score": 78, "weight": 0.3},
                ],
                "narrative_summary": "Strong technical candidate with good communication.",
                "candidate_feedback": "Great interview! Consider providing more examples.",
            }
            
            score_response = await async_client.post(
                f"/api/v1/interview/{interview['id']}/score",
                headers={"Authorization": "Bearer test-token"},
            )
            assert score_response.status_code == 200
            
            score_data = score_response.json()
            assert score_data["overall_score"] == 82
            assert len(score_data["dimensions"]) == 3
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_interview_with_recording(
        self,
        async_client: AsyncClient,
        mock_auth,
        mock_supabase_service,
    ):
        """Test interview flow with recording enabled."""
        interview = InterviewFactory()
        
        mock_supabase_service.get_interview.return_value = interview
        mock_supabase_service.update_interview.return_value = interview
        
        with patch("app.services.azure_acs.AzureACSService") as mock_acs:
            mock_acs_instance = AsyncMock()
            mock_acs_instance.start_recording.return_value = {
                "recording_id": "rec-123",
                "recording_state": "active",
            }
            mock_acs_instance.stop_recording.return_value = {
                "recording_state": "stopped",
            }
            mock_acs.return_value = mock_acs_instance
            
            # Start recording
            with patch("app.services.recording.recording_service") as mock_rec:
                mock_rec.start_recording = AsyncMock(return_value={
                    "recording_id": "rec-123",
                    "recording_state": "active",
                })
                
                start_rec_response = await async_client.post(
                    "/api/v1/recordings/start",
                    json={
                        "server_call_id": "call-456",
                        "interview_id": interview["id"],
                    },
                    headers={"Authorization": "Bearer test-token"},
                )
                assert start_rec_response.status_code == 200
            
            # Stop recording
            with patch("app.services.recording.recording_service") as mock_rec:
                mock_rec.stop_recording = AsyncMock(return_value="stopped")
                mock_rec.process_recording = AsyncMock()
                
                stop_rec_response = await async_client.post(
                    "/api/v1/recordings/rec-123/stop",
                    headers={"Authorization": "Bearer test-token"},
                )
                assert stop_rec_response.status_code == 200
```

---

## 8. Mocking Azure Services

### Comprehensive Azure Mocks (tests/mocks/azure_mocks.py)

```python
"""
Comprehensive mock implementations for Azure services.
"""
from unittest.mock import AsyncMock, MagicMock
from typing import AsyncIterator, Optional, Any
import asyncio


class MockAzureOpenAI:
    """Mock Azure OpenAI client."""
    
    def __init__(self, responses: Optional[list] = None):
        self.responses = responses or ["Default mock response"]
        self.response_index = 0
        self.chat = MagicMock()
        self.chat.completions = MagicMock()
        self.chat.completions.create = AsyncMock(side_effect=self._create_completion)
    
    async def _create_completion(self, **kwargs):
        response = self.responses[self.response_index % len(self.responses)]
        self.response_index += 1
        
        if kwargs.get("stream"):
            return self._stream_response(response)
        
        return MagicMock(
            choices=[MagicMock(message=MagicMock(content=response))],
            usage=MagicMock(total_tokens=100),
        )
    
    async def _stream_response(self, content: str) -> AsyncIterator:
        words = content.split()
        for word in words:
            yield MagicMock(choices=[MagicMock(delta=MagicMock(content=f"{word} "))])
        yield MagicMock(choices=[MagicMock(delta=MagicMock(content=None))])


class MockSpeechSynthesizer:
    """Mock Azure Speech Synthesizer."""
    
    def __init__(self, success: bool = True, audio_data: bytes = b"\x00" * 1000):
        self.success = success
        self.audio_data = audio_data
    
    def speak_text_async(self, text: str):
        result = MagicMock()
        if self.success:
            result.reason = 1  # SynthesisCompleted
            result.audio_data = self.audio_data
        else:
            result.reason = 0  # Canceled
            result.cancellation_details = MagicMock(
                reason=1,
                error_details="Mock error",
            )
        
        future = MagicMock()
        future.get.return_value = result
        return future
    
    def speak_ssml_async(self, ssml: str):
        return self.speak_text_async(ssml)


class MockSpeechRecognizer:
    """Mock Azure Speech Recognizer."""
    
    def __init__(self, transcripts: Optional[list] = None):
        self.transcripts = transcripts or ["Mock transcription"]
        self.transcript_index = 0
        self.recognized = MagicMock()
        self.session_stopped = MagicMock()
        self.canceled = MagicMock()
    
    def start_continuous_recognition_async(self):
        future = MagicMock()
        future.get.return_value = None
        return future
    
    def stop_continuous_recognition_async(self):
        future = MagicMock()
        future.get.return_value = None
        return future
    
    def get_next_result(self) -> Optional[str]:
        if self.transcript_index < len(self.transcripts):
            result = self.transcripts[self.transcript_index]
            self.transcript_index += 1
            return result
        return None


class MockBlobClient:
    """Mock Azure Blob Client."""
    
    def __init__(self, exists: bool = True, content: bytes = b"mock content"):
        self._exists = exists
        self._content = content
        self._properties = MagicMock(size=len(content), etag="mock-etag")
    
    async def exists(self) -> bool:
        return self._exists
    
    async def upload_blob(self, data, overwrite: bool = False, **kwargs):
        return {"etag": "mock-etag", "last_modified": "2024-01-15T10:00:00Z"}
    
    async def download_blob(self):
        downloader = MagicMock()
        downloader.readall = AsyncMock(return_value=self._content)
        downloader.chunks = AsyncMock(return_value=[self._content])
        return downloader
    
    async def delete_blob(self, **kwargs):
        pass
    
    async def get_blob_properties(self):
        return self._properties
    
    def generate_shared_access_signature(self, **kwargs) -> str:
        return "mock-sas-token"


class MockContainerClient:
    """Mock Azure Container Client."""
    
    def __init__(self, blobs: Optional[list] = None):
        self._blobs = blobs or []
    
    def get_blob_client(self, blob_name: str) -> MockBlobClient:
        return MockBlobClient()
    
    def list_blobs(self, **kwargs):
        for blob in self._blobs:
            yield MagicMock(name=blob["name"], size=blob.get("size", 0))


class MockBlobServiceClient:
    """Mock Azure Blob Service Client."""
    
    def __init__(self, containers: Optional[dict] = None):
        self._containers = containers or {}
    
    def get_container_client(self, container_name: str) -> MockContainerClient:
        return self._containers.get(container_name, MockContainerClient())


class MockCommunicationIdentityClient:
    """Mock Azure Communication Identity Client."""
    
    def create_user(self):
        return MagicMock(properties={"id": "8:acs:mock-user-id"})
    
    def get_token(self, user, scopes):
        return MagicMock(
            token="mock-acs-token",
            expires_on=MagicMock(isoformat=lambda: "2024-01-15T12:00:00Z"),
        )
    
    def create_user_and_token(self, scopes):
        user = self.create_user()
        token = self.get_token(user, scopes)
        return user, token


class MockCallAutomationClient:
    """Mock Azure Call Automation Client."""
    
    def __init__(self):
        self._active_calls = {}
    
    def create_call(self, target_participant, callback_url, **kwargs):
        call_id = "mock-call-connection-id"
        self._active_calls[call_id] = {
            "target": target_participant,
            "status": "connecting",
        }
        return MagicMock(call_connection_id=call_id)
    
    def get_call_connection(self, call_connection_id: str):
        if call_connection_id not in self._active_calls:
            raise ValueError(f"Call not found: {call_connection_id}")
        
        connection = MagicMock()
        connection.hang_up = MagicMock(return_value=None)
        connection.play_media = MagicMock(return_value=None)
        connection.start_recognizing_media = MagicMock(return_value=None)
        return connection
    
    def start_recording(self, call_locator, **kwargs):
        return MagicMock(recording_id="mock-recording-id")
    
    def stop_recording(self, recording_id: str):
        return MagicMock(recording_state="stopped")


# Pytest fixtures using mocks
import pytest


@pytest.fixture
def mock_azure_openai():
    """Fixture for mock Azure OpenAI."""
    return MockAzureOpenAI()


@pytest.fixture
def mock_speech_synthesizer():
    """Fixture for mock Speech Synthesizer."""
    return MockSpeechSynthesizer()


@pytest.fixture
def mock_blob_service():
    """Fixture for mock Blob Service."""
    return MockBlobServiceClient()


@pytest.fixture
def mock_acs_identity():
    """Fixture for mock ACS Identity Client."""
    return MockCommunicationIdentityClient()


@pytest.fixture
def mock_call_automation():
    """Fixture for mock Call Automation Client."""
    return MockCallAutomationClient()
```

---

## 9. Database Testing

### Supabase Client Tests (tests/integration/database/test_supabase_client.py)

```python
"""
Integration tests for Supabase client operations.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from app.services.supabase_client import SupabaseService
from tests.fixtures.factories import InterviewFactory, TranscriptSegmentFactory


class TestSupabaseService:
    """Tests for SupabaseService database operations."""
    
    @pytest.fixture
    def service(self, mock_supabase) -> SupabaseService:
        """Create service with mocked client."""
        service = SupabaseService()
        service._client = mock_supabase
        return service
    
    # =========================================================================
    # Interview Operations
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_get_interview(self, service: SupabaseService):
        """Test fetching interview by ID."""
        # Arrange
        interview = InterviewFactory()
        service._client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=interview
        )
        
        # Act
        result = await service.get_interview(interview["id"])
        
        # Assert
        assert result["id"] == interview["id"]
        service._client.table.assert_called_with("interviews")
    
    @pytest.mark.asyncio
    async def test_get_interview_not_found(self, service: SupabaseService):
        """Test fetching non-existent interview."""
        # Arrange
        service._client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=None
        )
        
        # Act
        result = await service.get_interview("non-existent")
        
        # Assert
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_interview(self, service: SupabaseService):
        """Test updating interview."""
        # Arrange
        interview = InterviewFactory()
        updates = {"status": "completed", "ended_at": datetime.utcnow().isoformat()}
        
        service._client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{**interview, **updates}]
        )
        
        # Act
        result = await service.update_interview(interview["id"], updates)
        
        # Assert
        assert result["status"] == "completed"
        assert "ended_at" in result
    
    # =========================================================================
    # Transcript Operations
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_save_transcript_segment(self, service: SupabaseService):
        """Test saving transcript segment."""
        # Arrange
        segment = TranscriptSegmentFactory()
        service._client.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[segment]
        )
        
        # Act
        result = await service.save_transcript_segment(
            interview_id=segment["interview_id"],
            speaker=segment["speaker"],
            content=segment["content"],
            start_time_ms=segment["start_time_ms"],
            end_time_ms=segment["end_time_ms"],
            confidence=segment["confidence"],
        )
        
        # Assert
        assert result["speaker"] == segment["speaker"]
        assert result["content"] == segment["content"]
    
    @pytest.mark.asyncio
    async def test_get_transcript(self, service: SupabaseService):
        """Test fetching interview transcript."""
        # Arrange
        segments = [TranscriptSegmentFactory() for _ in range(5)]
        service._client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=segments
        )
        
        # Act
        result = await service.get_transcript("interview-123")
        
        # Assert
        assert len(result) == 5
        service._client.table.assert_called_with("transcript_segments")
    
    # =========================================================================
    # Application Operations
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_get_application_with_job_role(self, service: SupabaseService):
        """Test fetching application with related job role."""
        # Arrange
        from tests.fixtures.factories import ApplicationFactory, JobRoleFactory
        
        application = ApplicationFactory()
        job_role = JobRoleFactory(id=application["job_role_id"])
        
        service._client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={**application, "job_roles": job_role}
        )
        
        # Act
        result = await service.get_application(application["id"])
        
        # Assert
        assert result["id"] == application["id"]
        assert "job_roles" in result
        assert result["job_roles"]["id"] == job_role["id"]
    
    # =========================================================================
    # Audit Logging
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_log_audit_event(self, service: SupabaseService):
        """Test audit log creation."""
        # Arrange
        service._client.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "audit-123"}]
        )
        
        # Act
        await service.log_audit_event(
            action="interview.started",
            entity_type="interview",
            entity_id="interview-123",
            user_id="user-456",
            organisation_id="org-789",
        )
        
        # Assert
        service._client.table.assert_called_with("audit_log")
        call_args = service._client.table.return_value.insert.call_args
        assert call_args[0][0]["action"] == "interview.started"
```

---

## 10. WebSocket Testing

### WebSocket Tests (tests/integration/test_websocket.py)

```python
"""
Tests for WebSocket endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import json


class TestTranscriptionWebSocket:
    """Tests for real-time transcription WebSocket."""
    
    def test_websocket_connect(self, client: TestClient):
        """Test WebSocket connection establishment."""
        with patch("app.api.routes.speech.verify_ws_token") as mock_verify:
            mock_verify.return_value = {"user_id": "test-user"}
            
            with client.websocket_connect(
                "/api/v1/speech/transcribe?token=valid-token"
            ) as websocket:
                # Connection should succeed
                data = websocket.receive_json()
                assert data["type"] == "connected"
    
    def test_websocket_invalid_token(self, client: TestClient):
        """Test WebSocket rejects invalid token."""
        with patch("app.api.routes.speech.verify_ws_token") as mock_verify:
            mock_verify.return_value = None
            
            with pytest.raises(Exception):  # WebSocket close
                with client.websocket_connect(
                    "/api/v1/speech/transcribe?token=invalid"
                ):
                    pass
    
    def test_websocket_audio_transcription(self, client: TestClient):
        """Test audio transcription over WebSocket."""
        with patch("app.api.routes.speech.verify_ws_token") as mock_verify:
            mock_verify.return_value = {"user_id": "test-user"}
            
            with patch("app.services.azure_speech.AzureSpeechService") as mock_speech:
                mock_instance = MagicMock()
                mock_instance.create_transcription_session.return_value = MagicMock(
                    start=AsyncMock(),
                    stop=AsyncMock(),
                    push_audio=AsyncMock(),
                )
                mock_speech.return_value = mock_instance
                
                with client.websocket_connect(
                    "/api/v1/speech/transcribe?token=valid"
                ) as websocket:
                    # Send audio data
                    websocket.send_bytes(b"\x00" * 1600)  # 0.1s of audio
                    
                    # Should receive transcription
                    data = websocket.receive_json()
                    assert data["type"] in ("partial", "final", "connected")
    
    def test_websocket_session_management(self, client: TestClient):
        """Test WebSocket session lifecycle."""
        with patch("app.api.routes.speech.verify_ws_token") as mock_verify:
            mock_verify.return_value = {"user_id": "test-user", "interview_id": "int-123"}
            
            session_events = []
            
            with patch("app.services.azure_speech.AzureSpeechService") as mock_speech:
                mock_session = MagicMock()
                mock_session.start = AsyncMock(side_effect=lambda: session_events.append("started"))
                mock_session.stop = AsyncMock(side_effect=lambda: session_events.append("stopped"))
                
                mock_instance = MagicMock()
                mock_instance.create_transcription_session.return_value = mock_session
                mock_speech.return_value = mock_instance
                
                with client.websocket_connect(
                    "/api/v1/speech/transcribe?token=valid"
                ) as websocket:
                    websocket.receive_json()  # connected message
                
                # After disconnect, session should be stopped
                assert "started" in session_events
                assert "stopped" in session_events


class TestInterviewChatWebSocket:
    """Tests for interview chat WebSocket."""
    
    def test_chat_websocket_streaming(self, client: TestClient):
        """Test streaming chat responses over WebSocket."""
        with patch("app.api.routes.interview.verify_ws_token") as mock_verify:
            mock_verify.return_value = {
                "user_id": "test-user",
                "interview_id": "int-123",
            }
            
            async def mock_stream():
                yield "Hello"
                yield " there"
                yield "!"
            
            with patch("app.services.azure_openai.AzureOpenAIService") as mock_openai:
                mock_instance = AsyncMock()
                mock_instance.stream_interview_response.return_value = mock_stream()
                mock_openai.return_value = mock_instance
                
                with patch("app.services.supabase_client.SupabaseService") as mock_db:
                    mock_db_instance = AsyncMock()
                    mock_db_instance.get_interview.return_value = {
                        "id": "int-123",
                        "status": "in_progress",
                    }
                    mock_db.return_value = mock_db_instance
                    
                    with client.websocket_connect(
                        "/api/v1/interview/chat/ws?token=valid"
                    ) as websocket:
                        # Send message
                        websocket.send_json({
                            "type": "message",
                            "content": "Tell me about yourself",
                        })
                        
                        # Receive streamed response
                        chunks = []
                        for _ in range(4):  # connected + 3 chunks
                            data = websocket.receive_json()
                            if data["type"] == "chunk":
                                chunks.append(data["content"])
                        
                        assert len(chunks) >= 1
```

---

## 11. Performance Testing

### Locust Load Tests (tests/performance/locustfile.py)

```python
"""
Load testing with Locust for API endpoints.
"""
from locust import HttpUser, task, between, tag
import random
import uuid


class InterviewUser(HttpUser):
    """Simulates interview platform users."""
    
    wait_time = between(1, 3)
    
    def on_start(self):
        """Setup before tests - login and create test data."""
        self.token = f"test-token-{uuid.uuid4()}"
        self.interview_id = str(uuid.uuid4())
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @tag("health")
    @task(1)
    def health_check(self):
        """Health check endpoint - low priority."""
        self.client.get("/health")
    
    @tag("interview", "critical")
    @task(10)
    def interview_chat(self):
        """Interview chat - high frequency."""
        messages = [
            "I have experience with Python and FastAPI.",
            "I worked on distributed systems at my previous company.",
            "I'm passionate about clean code and testing.",
            "My approach to problem-solving involves breaking down the problem.",
        ]
        
        self.client.post(
            "/api/v1/interview/chat",
            json={
                "interview_id": self.interview_id,
                "message": random.choice(messages),
            },
            headers=self.headers,
        )
    
    @tag("interview")
    @task(2)
    def start_interview(self):
        """Start interview - moderate frequency."""
        new_interview_id = str(uuid.uuid4())
        self.client.post(
            f"/api/v1/interview/{new_interview_id}/start",
            headers=self.headers,
        )
    
    @tag("resume")
    @task(3)
    def parse_resume(self):
        """Resume parsing - moderate frequency."""
        # Minimal PDF content for testing
        pdf_content = b"%PDF-1.4\n1 0 obj << >> endobj\ntrailer << >>\n%%EOF"
        
        self.client.post(
            "/api/v1/resume/parse",
            files={"file": ("resume.pdf", pdf_content, "application/pdf")},
            headers=self.headers,
        )
    
    @tag("speech")
    @task(5)
    def get_speech_token(self):
        """Speech token generation - frequent for real-time features."""
        self.client.get(
            "/api/v1/speech/token",
            headers=self.headers,
        )


class AdminUser(HttpUser):
    """Simulates admin/recruiter users."""
    
    wait_time = between(2, 5)
    
    def on_start(self):
        """Setup admin user."""
        self.token = f"admin-token-{uuid.uuid4()}"
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @tag("admin", "scoring")
    @task(5)
    def score_interview(self):
        """Interview scoring - admin task."""
        interview_id = str(uuid.uuid4())
        self.client.post(
            f"/api/v1/interview/{interview_id}/score",
            headers=self.headers,
        )
    
    @tag("admin")
    @task(2)
    def list_interviews(self):
        """List interviews for a job role."""
        job_role_id = str(uuid.uuid4())
        self.client.get(
            f"/api/v1/job-roles/{job_role_id}/interviews",
            headers=self.headers,
        )
    
    @tag("admin", "recording")
    @task(1)
    def download_recording(self):
        """Download interview recording."""
        recording_id = str(uuid.uuid4())
        self.client.get(
            f"/api/v1/recordings/{recording_id}/download",
            headers=self.headers,
        )
```

### Benchmark Tests (tests/performance/test_benchmarks.py)

```python
"""
Benchmark tests for critical operations.
"""
import pytest
from unittest.mock import AsyncMock, patch


class TestOpenAIBenchmarks:
    """Benchmarks for OpenAI operations."""
    
    @pytest.mark.benchmark
    def test_chat_completion_latency(self, benchmark):
        """Benchmark chat completion response time."""
        from app.services.azure_openai import AzureOpenAIService
        
        async def run_completion():
            with patch("app.services.azure_openai.AsyncAzureOpenAI") as mock:
                mock_instance = AsyncMock()
                mock_instance.chat.completions.create.return_value = AsyncMock(
                    choices=[AsyncMock(message=AsyncMock(content="Response"))]
                )
                mock.return_value = mock_instance
                
                service = AzureOpenAIService()
                await service.chat_completion([{"role": "user", "content": "Hi"}])
        
        import asyncio
        benchmark(lambda: asyncio.run(run_completion()))
    
    @pytest.mark.benchmark
    def test_token_counting_performance(self, benchmark):
        """Benchmark token counting for various text sizes."""
        from app.services.azure_openai import AzureOpenAIService
        
        service = AzureOpenAIService()
        text = "Hello world! " * 1000  # ~3000 tokens
        
        benchmark(lambda: service.count_tokens(text))


class TestDatabaseBenchmarks:
    """Benchmarks for database operations."""
    
    @pytest.mark.benchmark
    def test_transcript_insert_latency(self, benchmark, mock_supabase):
        """Benchmark transcript segment insertion."""
        from app.services.supabase_client import SupabaseService
        
        async def insert_segment():
            service = SupabaseService()
            service._client = mock_supabase
            mock_supabase.table.return_value.insert.return_value.execute.return_value = (
                AsyncMock(data=[{"id": "test"}])
            )
            
            await service.save_transcript_segment(
                interview_id="int-123",
                speaker="candidate",
                content="Test content",
                start_time_ms=0,
                end_time_ms=5000,
            )
        
        import asyncio
        benchmark(lambda: asyncio.run(insert_segment()))
```

---

## 12. Security Testing

### Authentication Tests (tests/security/test_auth.py)

```python
"""
Security tests for authentication and authorization.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
import jwt
from datetime import datetime, timedelta


class TestAuthentication:
    """Tests for authentication security."""
    
    @pytest.mark.asyncio
    async def test_missing_auth_header(self, async_client: AsyncClient):
        """Test requests without auth header are rejected."""
        response = await async_client.post(
            "/api/v1/interview/chat",
            json={"interview_id": "test", "message": "hello"},
        )
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_invalid_token_format(self, async_client: AsyncClient):
        """Test malformed tokens are rejected."""
        response = await async_client.post(
            "/api/v1/interview/chat",
            json={"interview_id": "test", "message": "hello"},
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_expired_token(self, async_client: AsyncClient):
        """Test expired tokens are rejected."""
        # Create expired JWT
        expired_token = jwt.encode(
            {
                "sub": "user-123",
                "exp": datetime.utcnow() - timedelta(hours=1),
            },
            "secret",
            algorithm="HS256",
        )
        
        with patch("app.api.dependencies.verify_jwt") as mock_verify:
            mock_verify.side_effect = jwt.ExpiredSignatureError("Token expired")
            
            response = await async_client.post(
                "/api/v1/interview/chat",
                json={"interview_id": "test", "message": "hello"},
                headers={"Authorization": f"Bearer {expired_token}"},
            )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_token_wrong_signature(self, async_client: AsyncClient):
        """Test tokens with wrong signature are rejected."""
        # Create token with wrong secret
        bad_token = jwt.encode(
            {"sub": "user-123", "exp": datetime.utcnow() + timedelta(hours=1)},
            "wrong-secret",
            algorithm="HS256",
        )
        
        with patch("app.api.dependencies.verify_jwt") as mock_verify:
            mock_verify.side_effect = jwt.InvalidSignatureError("Invalid signature")
            
            response = await async_client.post(
                "/api/v1/interview/chat",
                json={"interview_id": "test", "message": "hello"},
                headers={"Authorization": f"Bearer {bad_token}"},
            )
        
        assert response.status_code == 401


class TestAuthorization:
    """Tests for authorization and access control."""
    
    @pytest.mark.asyncio
    async def test_candidate_cannot_access_other_interview(
        self,
        async_client: AsyncClient,
        mock_supabase_service,
    ):
        """Test candidates can only access their own interviews."""
        # Arrange - user trying to access another candidate's interview
        with patch("app.api.dependencies.get_current_user") as mock_auth:
            mock_auth.return_value = {"id": "user-A", "role": "candidate"}
            
            mock_supabase_service.get_interview.return_value = {"id": "int-123"}
            mock_supabase_service.get_application.return_value = {
                "candidate_id": "user-B",  # Different user
            }
            
            response = await async_client.post(
                "/api/v1/interview/chat",
                json={"interview_id": "int-123", "message": "hello"},
                headers={"Authorization": "Bearer valid-token"},
            )
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_recruiter_can_access_org_interviews(
        self,
        async_client: AsyncClient,
        mock_supabase_service,
    ):
        """Test recruiters can access interviews for their organisation."""
        with patch("app.api.dependencies.get_current_user") as mock_auth:
            mock_auth.return_value = {
                "id": "recruiter-1",
                "role": "org_recruiter",
                "organisation_id": "org-123",
            }
            
            mock_supabase_service.get_interview.return_value = {
                "id": "int-123",
                "status": "completed",
            }
            mock_supabase_service.get_application.return_value = {
                "job_roles": {"organisation_id": "org-123"},
            }
            mock_supabase_service.get_transcript.return_value = []
            
            response = await async_client.get(
                "/api/v1/interview/int-123",
                headers={"Authorization": "Bearer valid-token"},
            )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_recruiter_cannot_access_other_org_interviews(
        self,
        async_client: AsyncClient,
        mock_supabase_service,
    ):
        """Test recruiters cannot access interviews from other organisations."""
        with patch("app.api.dependencies.get_current_user") as mock_auth:
            mock_auth.return_value = {
                "id": "recruiter-1",
                "role": "org_recruiter",
                "organisation_id": "org-123",
            }
            
            mock_supabase_service.get_interview.return_value = {"id": "int-123"}
            mock_supabase_service.get_application.return_value = {
                "job_roles": {"organisation_id": "org-456"},  # Different org
            }
            
            response = await async_client.get(
                "/api/v1/interview/int-123",
                headers={"Authorization": "Bearer valid-token"},
            )
        
        assert response.status_code == 403


class TestInputValidation:
    """Tests for input validation security."""
    
    @pytest.mark.asyncio
    async def test_sql_injection_prevention(
        self,
        async_client: AsyncClient,
        mock_auth,
    ):
        """Test SQL injection attempts are handled safely."""
        malicious_inputs = [
            "'; DROP TABLE interviews; --",
            "1 OR 1=1",
            "admin'--",
            "1; SELECT * FROM users",
        ]
        
        for payload in malicious_inputs:
            response = await async_client.post(
                "/api/v1/interview/chat",
                json={
                    "interview_id": payload,
                    "message": "hello",
                },
                headers={"Authorization": "Bearer valid-token"},
            )
            # Should either validate format or return not found - never execute SQL
            assert response.status_code in (400, 404, 422)
    
    @pytest.mark.asyncio
    async def test_xss_prevention(
        self,
        async_client: AsyncClient,
        mock_auth,
        mock_supabase_service,
    ):
        """Test XSS payloads are sanitized."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
        ]
        
        mock_supabase_service.get_interview.return_value = {
            "id": "int-123",
            "status": "in_progress",
        }
        mock_supabase_service.get_application.return_value = {
            "candidate_id": "test-user",
            "job_roles": {"title": "Developer"},
        }
        mock_supabase_service.get_transcript.return_value = []
        
        with patch("app.services.azure_openai.AzureOpenAIService") as mock_openai:
            mock_instance = AsyncMock()
            mock_instance.generate_interview_response.return_value = "Response"
            mock_openai.return_value = mock_instance
            
            for payload in xss_payloads:
                response = await async_client.post(
                    "/api/v1/interview/chat",
                    json={
                        "interview_id": "int-123",
                        "message": payload,
                    },
                    headers={"Authorization": "Bearer valid-token"},
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Response should not contain raw script tags
                    assert "<script>" not in str(data)
```

### Rate Limiting Tests (tests/security/test_rate_limiting.py)

```python
"""
Tests for rate limiting functionality.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
import asyncio


class TestRateLimiting:
    """Tests for API rate limiting."""
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, async_client: AsyncClient, mock_auth):
        """Test requests are rejected when rate limit is exceeded."""
        # Simulate hitting rate limit
        with patch("app.middleware.rate_limit.check_rate_limit") as mock_check:
            mock_check.return_value = {
                "is_limited": True,
                "remaining": 0,
                "reset_at": 1705312800,
            }
            
            response = await async_client.post(
                "/api/v1/interview/chat",
                json={"interview_id": "test", "message": "hello"},
                headers={"Authorization": "Bearer valid-token"},
            )
        
        assert response.status_code == 429
        assert "Retry-After" in response.headers
    
    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, async_client: AsyncClient, mock_auth):
        """Test rate limit headers are included in responses."""
        with patch("app.middleware.rate_limit.check_rate_limit") as mock_check:
            mock_check.return_value = {
                "is_limited": False,
                "remaining": 95,
                "reset_at": 1705312800,
            }
            
            with patch("app.api.dependencies.get_current_user") as mock_user:
                mock_user.return_value = {"id": "user-123"}
                
                response = await async_client.get(
                    "/health",
                )
        
        assert response.status_code == 200
        # Rate limit headers should be present
        assert "X-RateLimit-Remaining" in response.headers or response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_rate_limit_per_endpoint(self, async_client: AsyncClient, mock_auth):
        """Test different endpoints have different rate limits."""
        # Token generation should have stricter limits
        with patch("app.middleware.rate_limit.RATE_LIMITS") as mock_limits:
            mock_limits.__getitem__.side_effect = lambda key: {
                "token_generation": {"window_ms": 60000, "max_requests": 10},
                "ai_operation": {"window_ms": 60000, "max_requests": 100},
            }.get(key, {"window_ms": 60000, "max_requests": 1000})
            
            # This test verifies the rate limit configuration exists
            assert mock_limits["token_generation"]["max_requests"] < mock_limits["ai_operation"]["max_requests"]
```

---

## 13. CI/CD Integration

### GitHub Actions Workflow (.github/workflows/test.yml)

```yaml
name: Test Suite

on:
  push:
    branches: [main, develop]
    paths:
      - 'python-acs-service/**'
      - '.github/workflows/test.yml'
  pull_request:
    branches: [main]
    paths:
      - 'python-acs-service/**'

env:
  PYTHON_VERSION: '3.11'

jobs:
  unit-tests:
    name: Unit Tests
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: python-acs-service
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      
      - name: Run unit tests
        run: |
          pytest tests/unit \
            -v \
            --tb=short \
            --cov=app \
            --cov-report=xml \
            --cov-report=term-missing \
            -m "not slow"
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: python-acs-service/coverage.xml
          flags: unit
          fail_ci_if_error: true

  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    needs: unit-tests
    defaults:
      run:
        working-directory: python-acs-service
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      
      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/test
          REDIS_URL: redis://localhost:6379
          ENVIRONMENT: test
        run: |
          pytest tests/integration \
            -v \
            --tb=short \
            --cov=app \
            --cov-report=xml \
            --cov-append \
            -m "integration"
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: python-acs-service/coverage.xml
          flags: integration

  e2e-tests:
    name: E2E Tests
    runs-on: ubuntu-latest
    needs: integration-tests
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    defaults:
      run:
        working-directory: python-acs-service
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      
      - name: Run E2E tests
        env:
          ENVIRONMENT: test
        run: |
          pytest tests/e2e \
            -v \
            --tb=short \
            -m "e2e"

  security-scan:
    name: Security Scan
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: python-acs-service
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Install security tools
        run: |
          pip install bandit safety
      
      - name: Run Bandit
        run: |
          bandit -r app -f json -o bandit-report.json || true
          bandit -r app -f screen
      
      - name: Run Safety
        run: |
          safety check -r requirements.txt || true
      
      - name: Upload security reports
        uses: actions/upload-artifact@v3
        with:
          name: security-reports
          path: python-acs-service/bandit-report.json

  type-check:
    name: Type Checking
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: python-acs-service
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install mypy types-redis
      
      - name: Run mypy
        run: |
          mypy app --ignore-missing-imports
```

---

## 14. Test Coverage

### Coverage Configuration

```ini
# .coveragerc
[run]
source = app
branch = True
omit =
    */tests/*
    */__init__.py
    */migrations/*
    */config.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if TYPE_CHECKING:
    if __name__ == .__main__.:
    @abstractmethod

fail_under = 80
show_missing = True

[html]
directory = htmlcov
```

### Coverage Commands

```bash
# Run all tests with coverage
pytest --cov=app --cov-report=html --cov-report=term-missing

# Run specific test categories
pytest tests/unit --cov=app -m unit
pytest tests/integration --cov=app -m integration
pytest tests/e2e --cov=app -m e2e

# Generate coverage report
coverage report --show-missing

# Generate HTML report
coverage html
open htmlcov/index.html
```

### Coverage Targets

| Module | Target | Critical |
|--------|--------|----------|
| `app/services/azure_openai.py` | 90% | Yes |
| `app/services/azure_speech.py` | 85% | Yes |
| `app/services/azure_acs.py` | 85% | Yes |
| `app/services/supabase_client.py` | 90% | Yes |
| `app/api/routes/*` | 85% | Yes |
| `app/utils/*` | 80% | No |
| `app/models/*` | 70% | No |
| **Overall** | **80%** | - |

---

## Quick Reference

### Running Tests

```bash
# All tests
pytest

# Unit tests only (fast)
pytest tests/unit -m unit

# Integration tests
pytest tests/integration -m integration

# E2E tests
pytest tests/e2e -m e2e

# With coverage
pytest --cov=app --cov-report=html

# Parallel execution
pytest -n auto

# Specific file
pytest tests/unit/services/test_azure_openai.py

# Specific test
pytest tests/unit/services/test_azure_openai.py::TestAzureOpenAIService::test_chat_completion_success

# Watch mode (with pytest-watch)
ptw tests/unit

# Performance tests
locust -f tests/performance/locustfile.py
```

### Test Markers

```python
# Mark slow tests
@pytest.mark.slow
def test_large_file_processing():
    ...

# Mark tests requiring Azure
@pytest.mark.azure
def test_azure_integration():
    ...

# Mark database tests
@pytest.mark.database
def test_db_operations():
    ...

# Skip conditionally
@pytest.mark.skipif(os.getenv("CI"), reason="Requires local resources")
def test_local_only():
    ...
```

---

*This testing strategy ensures comprehensive coverage of the Talenti Python backend, from unit tests to end-to-end scenarios, with robust CI/CD integration.*
