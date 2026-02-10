# Azure SDK Examples - Error Handling, Retries & Edge Cases

> Comprehensive Python code samples for Azure services integration with production-ready error handling patterns.

---

## Table of Contents

1. [Common Patterns & Utilities](#1-common-patterns--utilities)
2. [Azure OpenAI](#2-azure-openai)
3. [Azure Speech Services](#3-azure-speech-services)
4. [Azure Communication Services](#4-azure-communication-services)
5. [Azure Blob Storage](#5-azure-blob-storage)
6. [Azure Document Intelligence](#6-azure-document-intelligence)
7. [Azure Key Vault](#7-azure-key-vault)
8. [Testing Patterns](#8-testing-patterns)

---

## 1. Common Patterns & Utilities

### 1.1 Retry Decorator with Exponential Backoff

```python
import asyncio
import functools
import logging
from typing import Type, Tuple, Callable, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class RetryableError(Exception):
    """Base class for errors that should trigger a retry."""
    pass

class NonRetryableError(Exception):
    """Base class for errors that should NOT be retried."""
    pass

def async_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    non_retryable_exceptions: Tuple[Type[Exception], ...] = (),
    on_retry: Callable[[Exception, int], None] | None = None
):
    """
    Async retry decorator with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff calculation
        retryable_exceptions: Tuple of exceptions that trigger retry
        non_retryable_exceptions: Tuple of exceptions that should NOT be retried
        on_retry: Optional callback called before each retry
    
    Example:
        @async_retry(max_attempts=3, retryable_exceptions=(httpx.TimeoutException,))
        async def call_api():
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                    
                except non_retryable_exceptions as e:
                    logger.error(f"{func.__name__} failed with non-retryable error: {e}")
                    raise
                    
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    # Calculate delay with exponential backoff and jitter
                    delay = min(
                        base_delay * (exponential_base ** (attempt - 1)),
                        max_delay
                    )
                    # Add jitter (±25%)
                    import random
                    delay = delay * (0.75 + random.random() * 0.5)
                    
                    logger.warning(
                        f"{func.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    
                    if on_retry:
                        on_retry(e, attempt)
                    
                    await asyncio.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator
```

### 1.2 Circuit Breaker Pattern

```python
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Any
import logging

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered

@dataclass
class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.
    
    Usage:
        breaker = CircuitBreaker(name="azure_openai", failure_threshold=5)
        
        async def call_openai():
            async with breaker:
                return await openai_client.chat(...)
    """
    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 30.0  # seconds
    half_open_max_calls: int = 3
    
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: datetime | None = field(default=None, init=False)
    _half_open_calls: int = field(default=0, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
    
    @property
    def state(self) -> CircuitState:
        return self._state
    
    async def __aenter__(self):
        async with self._lock:
            await self._check_state()
            
            if self._state == CircuitState.OPEN:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is open. "
                    f"Service unavailable until {self._recovery_time}"
                )
            
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        async with self._lock:
            if exc_type is None:
                # Success
                await self._on_success()
            else:
                # Failure
                await self._on_failure(exc_val)
        
        return False  # Don't suppress the exception
    
    async def _check_state(self):
        if self._state == CircuitState.OPEN:
            if datetime.now() >= self._recovery_time:
                logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN")
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
    
    async def _on_success(self):
        if self._state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.half_open_max_calls:
                logger.info(f"Circuit breaker '{self.name}' recovered, transitioning to CLOSED")
                self._state = CircuitState.CLOSED
                self._failure_count = 0
        elif self._state == CircuitState.CLOSED:
            self._failure_count = 0
    
    async def _on_failure(self, error: Exception):
        self._failure_count += 1
        self._last_failure_time = datetime.now()
        
        if self._state == CircuitState.HALF_OPEN:
            logger.warning(f"Circuit breaker '{self.name}' failed in HALF_OPEN, returning to OPEN")
            self._state = CircuitState.OPEN
        elif self._failure_count >= self.failure_threshold:
            logger.error(
                f"Circuit breaker '{self.name}' threshold reached ({self._failure_count} failures), "
                f"transitioning to OPEN"
            )
            self._state = CircuitState.OPEN
    
    @property
    def _recovery_time(self) -> datetime:
        if self._last_failure_time is None:
            return datetime.now()
        return self._last_failure_time + timedelta(seconds=self.recovery_timeout)

class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass
```

### 1.3 Structured Logging Middleware

```python
import logging
import json
import time
from contextvars import ContextVar
from typing import Any
from uuid import uuid4

# Context variable for request correlation
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")

class StructuredLogger:
    """
    Structured JSON logger for Azure service calls.
    
    Usage:
        logger = StructuredLogger("azure.openai")
        logger.info("API call started", model="gpt-4o", tokens=1500)
    """
    
    def __init__(self, name: str):
        self._logger = logging.getLogger(name)
    
    def _format(self, level: str, message: str, **kwargs) -> dict:
        return {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "level": level,
            "logger": self._logger.name,
            "correlation_id": correlation_id_var.get(),
            "message": message,
            **kwargs
        }
    
    def info(self, message: str, **kwargs):
        self._logger.info(json.dumps(self._format("INFO", message, **kwargs)))
    
    def warning(self, message: str, **kwargs):
        self._logger.warning(json.dumps(self._format("WARNING", message, **kwargs)))
    
    def error(self, message: str, exception: Exception | None = None, **kwargs):
        extra = kwargs.copy()
        if exception:
            extra["exception_type"] = type(exception).__name__
            extra["exception_message"] = str(exception)
        self._logger.error(json.dumps(self._format("ERROR", message, **extra)))
    
    def debug(self, message: str, **kwargs):
        self._logger.debug(json.dumps(self._format("DEBUG", message, **kwargs)))

# FastAPI middleware for correlation ID
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))
        correlation_id_var.set(correlation_id)
        
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response
```

### 1.4 Health Check Pattern

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List
from enum import Enum
import asyncio

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

@dataclass
class ServiceHealth:
    name: str
    status: HealthStatus
    latency_ms: float | None = None
    last_check: datetime = None
    error: str | None = None

class HealthChecker:
    """
    Aggregate health checker for all Azure services.
    
    Usage:
        checker = HealthChecker()
        checker.register("azure_openai", check_openai_health)
        checker.register("azure_speech", check_speech_health)
        
        health = await checker.check_all()
    """
    
    def __init__(self):
        self._checks: Dict[str, callable] = {}
    
    def register(self, name: str, check_func: callable):
        self._checks[name] = check_func
    
    async def check_all(self, timeout: float = 5.0) -> Dict[str, ServiceHealth]:
        results = {}
        
        async def run_check(name: str, check_func: callable):
            start = datetime.now()
            try:
                await asyncio.wait_for(check_func(), timeout=timeout)
                latency = (datetime.now() - start).total_seconds() * 1000
                return ServiceHealth(
                    name=name,
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency,
                    last_check=datetime.now()
                )
            except asyncio.TimeoutError:
                return ServiceHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    last_check=datetime.now(),
                    error="Health check timed out"
                )
            except Exception as e:
                return ServiceHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    last_check=datetime.now(),
                    error=str(e)
                )
        
        tasks = [run_check(name, func) for name, func in self._checks.items()]
        health_results = await asyncio.gather(*tasks)
        
        return {h.name: h for h in health_results}
    
    def aggregate_status(self, results: Dict[str, ServiceHealth]) -> HealthStatus:
        statuses = [h.status for h in results.values()]
        
        if all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        else:
            return HealthStatus.DEGRADED
```

---

## 2. Azure OpenAI

### 2.1 Client Configuration with Retry

```python
import httpx
from openai import AsyncAzureOpenAI, APIError, APIConnectionError, RateLimitError
from pydantic import BaseModel
from typing import AsyncGenerator, List, Optional
import tiktoken

from app.common.retry import async_retry
from app.common.circuit_breaker import CircuitBreaker
from app.common.logging import StructuredLogger

logger = StructuredLogger("azure.openai")

class OpenAIConfig(BaseModel):
    endpoint: str
    api_key: str
    api_version: str = "2024-02-15-preview"
    deployment_name: str = "gpt-4o"
    max_tokens: int = 4096
    timeout: float = 60.0
    max_retries: int = 3

class AzureOpenAIClient:
    """
    Production-ready Azure OpenAI client with comprehensive error handling.
    """
    
    # Retryable errors
    RETRYABLE_ERRORS = (
        APIConnectionError,
        httpx.TimeoutException,
        httpx.ConnectError,
    )
    
    # Rate limit handling
    RATE_LIMIT_ERRORS = (RateLimitError,)
    
    def __init__(self, config: OpenAIConfig):
        self.config = config
        self._client = AsyncAzureOpenAI(
            azure_endpoint=config.endpoint,
            api_key=config.api_key,
            api_version=config.api_version,
            timeout=config.timeout,
            max_retries=0  # We handle retries ourselves
        )
        self._circuit_breaker = CircuitBreaker(
            name="azure_openai",
            failure_threshold=5,
            recovery_timeout=30.0
        )
        self._tokenizer = tiktoken.encoding_for_model("gpt-4o")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text for context management."""
        return len(self._tokenizer.encode(text))
    
    def count_messages_tokens(self, messages: List[dict]) -> int:
        """Count total tokens in message array."""
        total = 0
        for msg in messages:
            # Add message overhead (role, separators)
            total += 4
            total += self.count_tokens(msg.get("content", ""))
        total += 2  # Priming tokens
        return total
    
    @async_retry(
        max_attempts=3,
        base_delay=1.0,
        retryable_exceptions=RETRYABLE_ERRORS
    )
    async def chat_completion(
        self,
        messages: List[dict],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[dict]] = None,
        tool_choice: Optional[str | dict] = None
    ) -> dict:
        """
        Non-streaming chat completion with error handling.
        
        Raises:
            RateLimitError: When rate limited (not retried automatically)
            APIError: For non-retryable API errors
            CircuitBreakerOpenError: When circuit breaker is open
        """
        async with self._circuit_breaker:
            try:
                # Check token limits
                input_tokens = self.count_messages_tokens(messages)
                effective_max_tokens = max_tokens or self.config.max_tokens
                
                if input_tokens + effective_max_tokens > 128000:  # GPT-4o limit
                    logger.warning(
                        "Token limit approaching",
                        input_tokens=input_tokens,
                        max_tokens=effective_max_tokens
                    )
                    # Truncate max_tokens to fit
                    effective_max_tokens = min(
                        effective_max_tokens,
                        128000 - input_tokens - 100  # Safety margin
                    )
                
                logger.info(
                    "Chat completion request",
                    deployment=self.config.deployment_name,
                    input_tokens=input_tokens,
                    max_tokens=effective_max_tokens
                )
                
                kwargs = {
                    "model": self.config.deployment_name,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": effective_max_tokens,
                }
                
                if tools:
                    kwargs["tools"] = tools
                if tool_choice:
                    kwargs["tool_choice"] = tool_choice
                
                response = await self._client.chat.completions.create(**kwargs)
                
                logger.info(
                    "Chat completion success",
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens
                )
                
                return response.model_dump()
                
            except RateLimitError as e:
                # Extract retry-after header if available
                retry_after = getattr(e, "retry_after", 60)
                logger.warning(
                    "Rate limited by Azure OpenAI",
                    retry_after=retry_after,
                    exception=e
                )
                raise  # Don't retry rate limits, let caller handle
                
            except APIError as e:
                logger.error(
                    "Azure OpenAI API error",
                    exception=e,
                    status_code=getattr(e, "status_code", None),
                    error_code=getattr(e, "code", None)
                )
                raise
    
    async def stream_chat_completion(
        self,
        messages: List[dict],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """
        Streaming chat completion with error handling.
        
        Yields:
            Content chunks as they arrive
            
        Raises:
            Various Azure OpenAI errors
        """
        async with self._circuit_breaker:
            try:
                logger.info(
                    "Streaming chat request",
                    deployment=self.config.deployment_name,
                    message_count=len(messages)
                )
                
                stream = await self._client.chat.completions.create(
                    model=self.config.deployment_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens or self.config.max_tokens,
                    stream=True
                )
                
                chunk_count = 0
                total_content = ""
                
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        total_content += content
                        chunk_count += 1
                        yield content
                
                logger.info(
                    "Streaming complete",
                    chunks=chunk_count,
                    total_length=len(total_content)
                )
                
            except httpx.ReadTimeout:
                logger.error("Stream read timeout")
                raise
                
            except Exception as e:
                logger.error("Streaming error", exception=e)
                raise
    
    async def health_check(self) -> bool:
        """Check if Azure OpenAI is reachable."""
        try:
            await self._client.chat.completions.create(
                model=self.config.deployment_name,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1
            )
            return True
        except Exception:
            return False
```

### 2.2 Handling Rate Limits with Backoff

```python
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field
import random

@dataclass
class RateLimitState:
    """Track rate limit state for adaptive throttling."""
    requests_this_minute: int = 0
    tokens_this_minute: int = 0
    minute_start: datetime = field(default_factory=datetime.now)
    retry_after: Optional[datetime] = None
    consecutive_rate_limits: int = 0
    
    # Azure OpenAI limits (adjust based on your tier)
    MAX_REQUESTS_PER_MINUTE: int = 60
    MAX_TOKENS_PER_MINUTE: int = 90000
    
    def reset_if_needed(self):
        """Reset counters if minute has passed."""
        now = datetime.now()
        if (now - self.minute_start).seconds >= 60:
            self.requests_this_minute = 0
            self.tokens_this_minute = 0
            self.minute_start = now
    
    def can_make_request(self, estimated_tokens: int = 0) -> bool:
        """Check if we can make a request without hitting limits."""
        self.reset_if_needed()
        
        # Check if we're in retry-after period
        if self.retry_after and datetime.now() < self.retry_after:
            return False
        
        # Check request limit
        if self.requests_this_minute >= self.MAX_REQUESTS_PER_MINUTE:
            return False
        
        # Check token limit
        if self.tokens_this_minute + estimated_tokens >= self.MAX_TOKENS_PER_MINUTE:
            return False
        
        return True
    
    def record_request(self, tokens_used: int):
        """Record a successful request."""
        self.reset_if_needed()
        self.requests_this_minute += 1
        self.tokens_this_minute += tokens_used
        self.consecutive_rate_limits = 0
    
    def record_rate_limit(self, retry_after_seconds: int = 60):
        """Record a rate limit response."""
        self.consecutive_rate_limits += 1
        
        # Exponential backoff for consecutive rate limits
        backoff = retry_after_seconds * (2 ** (self.consecutive_rate_limits - 1))
        backoff = min(backoff, 300)  # Max 5 minutes
        
        self.retry_after = datetime.now() + timedelta(seconds=backoff)
    
    async def wait_if_needed(self, estimated_tokens: int = 0):
        """Wait if we need to respect rate limits."""
        while not self.can_make_request(estimated_tokens):
            # Calculate wait time
            if self.retry_after:
                wait_seconds = (self.retry_after - datetime.now()).total_seconds()
            else:
                # Wait until next minute
                wait_seconds = 60 - (datetime.now() - self.minute_start).seconds
            
            wait_seconds = max(wait_seconds, 1)
            wait_seconds += random.uniform(0, 1)  # Add jitter
            
            await asyncio.sleep(wait_seconds)
            self.reset_if_needed()

class RateLimitedOpenAIClient(AzureOpenAIClient):
    """
    Azure OpenAI client with built-in rate limiting.
    """
    
    def __init__(self, config: OpenAIConfig):
        super().__init__(config)
        self._rate_limit_state = RateLimitState()
    
    async def chat_completion(self, messages: List[dict], **kwargs) -> dict:
        # Estimate tokens
        estimated_tokens = self.count_messages_tokens(messages) + (
            kwargs.get("max_tokens", self.config.max_tokens)
        )
        
        # Wait if needed
        await self._rate_limit_state.wait_if_needed(estimated_tokens)
        
        try:
            response = await super().chat_completion(messages, **kwargs)
            
            # Record successful request
            self._rate_limit_state.record_request(
                response.get("usage", {}).get("total_tokens", estimated_tokens)
            )
            
            return response
            
        except RateLimitError as e:
            retry_after = getattr(e, "retry_after", 60)
            self._rate_limit_state.record_rate_limit(retry_after)
            raise
```

### 2.3 Handling Streaming Errors

```python
from typing import AsyncGenerator, Optional
from dataclasses import dataclass

@dataclass
class StreamChunk:
    """Represents a chunk from the stream."""
    content: Optional[str] = None
    finish_reason: Optional[str] = None
    is_error: bool = False
    error_message: Optional[str] = None

async def robust_stream_handler(
    client: AzureOpenAIClient,
    messages: List[dict],
    on_chunk: callable,
    on_complete: callable,
    on_error: callable,
    max_retries: int = 2
) -> str:
    """
    Robust streaming handler with automatic retry on failure.
    
    If streaming fails mid-way, it will:
    1. Record what was received
    2. Retry with updated context
    3. Continue from where it left off
    """
    full_content = ""
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            # If retrying, add context about what was already generated
            effective_messages = messages.copy()
            if full_content and retry_count > 0:
                # Add partial response as assistant message
                effective_messages.append({
                    "role": "assistant",
                    "content": full_content
                })
                # Ask to continue
                effective_messages.append({
                    "role": "user",
                    "content": "Please continue from where you left off."
                })
            
            async for chunk in client.stream_chat_completion(effective_messages):
                full_content += chunk
                await on_chunk(StreamChunk(content=chunk))
            
            # Success
            await on_complete(full_content)
            return full_content
            
        except httpx.ReadTimeout:
            retry_count += 1
            if retry_count > max_retries:
                await on_error(StreamChunk(
                    is_error=True,
                    error_message="Stream timed out after multiple retries"
                ))
                raise
            
            # Brief pause before retry
            await asyncio.sleep(1)
            
        except Exception as e:
            await on_error(StreamChunk(
                is_error=True,
                error_message=str(e)
            ))
            raise
    
    return full_content
```

### 2.4 Function Calling with Validation

```python
import json
from pydantic import BaseModel, ValidationError
from typing import Type, TypeVar, Optional

T = TypeVar('T', bound=BaseModel)

class FunctionCallError(Exception):
    """Error during function call processing."""
    pass

async def call_with_function(
    client: AzureOpenAIClient,
    messages: List[dict],
    response_model: Type[T],
    function_name: str,
    function_description: str,
    max_retries: int = 2
) -> T:
    """
    Call Azure OpenAI with function calling and validate response.
    
    Args:
        client: Azure OpenAI client
        messages: Chat messages
        response_model: Pydantic model for response validation
        function_name: Name of the function to call
        function_description: Description for the model
        max_retries: Number of retries on validation failure
    
    Returns:
        Validated Pydantic model instance
        
    Raises:
        FunctionCallError: If response cannot be parsed/validated
    """
    # Build tool definition from Pydantic model
    tool = {
        "type": "function",
        "function": {
            "name": function_name,
            "description": function_description,
            "parameters": response_model.model_json_schema()
        }
    }
    
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            response = await client.chat_completion(
                messages=messages,
                tools=[tool],
                tool_choice={"type": "function", "function": {"name": function_name}}
            )
            
            # Extract function call arguments
            choice = response["choices"][0]
            
            if choice.get("finish_reason") == "tool_calls":
                tool_calls = choice["message"].get("tool_calls", [])
                
                if not tool_calls:
                    raise FunctionCallError("No tool calls in response")
                
                # Parse arguments
                arguments_str = tool_calls[0]["function"]["arguments"]
                arguments = json.loads(arguments_str)
                
                # Validate with Pydantic
                return response_model.model_validate(arguments)
            
            elif choice.get("finish_reason") == "stop":
                # Model didn't use function calling - try to parse content
                content = choice["message"].get("content", "")
                
                # Try to extract JSON from content
                try:
                    # Look for JSON in code blocks
                    if "```json" in content:
                        json_str = content.split("```json")[1].split("```")[0]
                    elif "```" in content:
                        json_str = content.split("```")[1].split("```")[0]
                    else:
                        json_str = content
                    
                    data = json.loads(json_str.strip())
                    return response_model.model_validate(data)
                    
                except (json.JSONDecodeError, IndexError):
                    raise FunctionCallError(
                        f"Model did not use function calling and content is not valid JSON"
                    )
            
            else:
                raise FunctionCallError(
                    f"Unexpected finish_reason: {choice.get('finish_reason')}"
                )
                
        except ValidationError as e:
            last_error = e
            
            if attempt < max_retries:
                # Add error feedback and retry
                messages = messages + [
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": response["choices"][0]["message"].get("tool_calls", [])
                    },
                    {
                        "role": "tool",
                        "tool_call_id": response["choices"][0]["message"]["tool_calls"][0]["id"],
                        "content": f"Validation error: {e}. Please fix and try again."
                    }
                ]
                continue
            
            raise FunctionCallError(f"Response validation failed: {e}")
        
        except json.JSONDecodeError as e:
            last_error = e
            raise FunctionCallError(f"Invalid JSON in function arguments: {e}")
    
    raise FunctionCallError(f"Failed after {max_retries + 1} attempts: {last_error}")

# Usage example
class InterviewScore(BaseModel):
    overall_score: float
    dimensions: List[dict]
    narrative: str
    recommendations: List[str]

async def score_interview(transcript: str) -> InterviewScore:
    return await call_with_function(
        client=openai_client,
        messages=[
            {"role": "system", "content": "Score this interview transcript..."},
            {"role": "user", "content": transcript}
        ],
        response_model=InterviewScore,
        function_name="submit_score",
        function_description="Submit the interview score with dimensions and narrative"
    )
```

---

## 3. Azure Speech Services

### 3.1 Speech Configuration with Error Handling

```python
import azure.cognitiveservices.speech as speechsdk
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable
import asyncio

from app.common.logging import StructuredLogger

logger = StructuredLogger("azure.speech")

@dataclass
class SpeechConfig:
    subscription_key: str
    region: str
    language: str = "en-AU"
    voice_name: str = "en-AU-NatashaNeural"
    
class SpeechServiceError(Exception):
    """Base error for speech service."""
    pass

class SpeechRecognitionError(SpeechServiceError):
    """Error during speech recognition."""
    pass

class SpeechSynthesisError(SpeechServiceError):
    """Error during speech synthesis."""
    pass

class AzureSpeechService:
    """
    Production-ready Azure Speech Service client.
    """
    
    def __init__(self, config: SpeechConfig):
        self.config = config
        self._speech_config = speechsdk.SpeechConfig(
            subscription=config.subscription_key,
            region=config.region
        )
        self._speech_config.speech_recognition_language = config.language
        self._speech_config.speech_synthesis_voice_name = config.voice_name
        
        # Enable detailed logging for debugging
        self._speech_config.set_property(
            speechsdk.PropertyId.Speech_LogFilename,
            "/tmp/azure_speech.log"
        )
    
    async def synthesize_speech(
        self,
        text: str,
        output_format: speechsdk.SpeechSynthesisOutputFormat = 
            speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
    ) -> bytes:
        """
        Convert text to speech audio.
        
        Args:
            text: Text to synthesize
            output_format: Audio format
            
        Returns:
            Audio bytes
            
        Raises:
            SpeechSynthesisError: On synthesis failure
        """
        self._speech_config.set_speech_synthesis_output_format(output_format)
        
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self._speech_config,
            audio_config=None  # Output to memory
        )
        
        try:
            logger.info("Starting speech synthesis", text_length=len(text))
            
            # Run synthesis in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                synthesizer.speak_text,
                text
            )
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                logger.info(
                    "Speech synthesis complete",
                    audio_length=len(result.audio_data)
                )
                return result.audio_data
                
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation = result.cancellation_details
                
                error_message = f"Synthesis canceled: {cancellation.reason}"
                
                if cancellation.reason == speechsdk.CancellationReason.Error:
                    error_message = (
                        f"Synthesis error: {cancellation.error_code} - "
                        f"{cancellation.error_details}"
                    )
                    
                    # Check for specific error codes
                    if "401" in str(cancellation.error_details):
                        raise SpeechSynthesisError("Invalid Azure Speech credentials")
                    elif "quota" in str(cancellation.error_details).lower():
                        raise SpeechSynthesisError("Azure Speech quota exceeded")
                
                logger.error("Speech synthesis failed", error=error_message)
                raise SpeechSynthesisError(error_message)
            
            else:
                raise SpeechSynthesisError(f"Unexpected result: {result.reason}")
                
        finally:
            del synthesizer  # Clean up
    
    async def synthesize_ssml(self, ssml: str) -> bytes:
        """
        Synthesize speech from SSML for advanced control.
        
        Args:
            ssml: SSML markup
            
        Returns:
            Audio bytes
        """
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self._speech_config,
            audio_config=None
        )
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                synthesizer.speak_ssml,
                ssml
            )
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                return result.audio_data
            else:
                cancellation = result.cancellation_details
                raise SpeechSynthesisError(
                    f"SSML synthesis failed: {cancellation.error_details}"
                )
                
        finally:
            del synthesizer
    
    def create_push_stream_recognizer(
        self,
        on_recognized: Callable[[str, float], Awaitable[None]],
        on_session_stopped: Callable[[], Awaitable[None]],
        on_error: Callable[[str], Awaitable[None]]
    ) -> tuple[speechsdk.SpeechRecognizer, speechsdk.audio.PushAudioInputStream]:
        """
        Create a recognizer with push audio stream for real-time transcription.
        
        Returns:
            Tuple of (recognizer, push_stream)
        """
        # Create push stream
        push_stream = speechsdk.audio.PushAudioInputStream()
        audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
        
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=self._speech_config,
            audio_config=audio_config
        )
        
        # Set up event handlers
        def handle_recognized(evt):
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                asyncio.create_task(on_recognized(
                    evt.result.text,
                    evt.result.offset / 10_000_000  # Convert to seconds
                ))
        
        def handle_canceled(evt):
            if evt.cancellation_details.reason == speechsdk.CancellationReason.Error:
                asyncio.create_task(on_error(
                    evt.cancellation_details.error_details
                ))
        
        def handle_session_stopped(evt):
            asyncio.create_task(on_session_stopped())
        
        recognizer.recognized.connect(handle_recognized)
        recognizer.canceled.connect(handle_canceled)
        recognizer.session_stopped.connect(handle_session_stopped)
        
        return recognizer, push_stream
    
    async def health_check(self) -> bool:
        """Verify speech service connectivity."""
        try:
            # Minimal synthesis to verify credentials
            result = await self.synthesize_speech("test")
            return len(result) > 0
        except Exception:
            return False
```

### 3.2 WebSocket Real-Time Transcription

```python
from fastapi import WebSocket, WebSocketDisconnect
import azure.cognitiveservices.speech as speechsdk
import asyncio
from typing import Optional
import json

class TranscriptionSession:
    """
    Manages a real-time transcription session over WebSocket.
    """
    
    def __init__(
        self,
        websocket: WebSocket,
        speech_service: AzureSpeechService,
        interview_id: str
    ):
        self.websocket = websocket
        self.speech_service = speech_service
        self.interview_id = interview_id
        self.recognizer: Optional[speechsdk.SpeechRecognizer] = None
        self.push_stream: Optional[speechsdk.audio.PushAudioInputStream] = None
        self._is_running = False
        self._segments: List[dict] = []
    
    async def start(self):
        """Start the transcription session."""
        logger.info("Starting transcription session", interview_id=self.interview_id)
        
        # Create recognizer with callbacks
        self.recognizer, self.push_stream = self.speech_service.create_push_stream_recognizer(
            on_recognized=self._on_recognized,
            on_session_stopped=self._on_session_stopped,
            on_error=self._on_error
        )
        
        # Start continuous recognition
        self.recognizer.start_continuous_recognition()
        self._is_running = True
        
        # Send ready message
        await self.websocket.send_json({
            "type": "session_started",
            "interview_id": self.interview_id
        })
    
    async def process_audio(self, audio_data: bytes):
        """Process incoming audio data."""
        if not self._is_running or not self.push_stream:
            return
        
        try:
            self.push_stream.write(audio_data)
        except Exception as e:
            logger.error("Error writing audio to stream", exception=e)
            await self._send_error(f"Audio processing error: {e}")
    
    async def stop(self):
        """Stop the transcription session."""
        logger.info("Stopping transcription session", interview_id=self.interview_id)
        
        self._is_running = False
        
        if self.push_stream:
            self.push_stream.close()
        
        if self.recognizer:
            self.recognizer.stop_continuous_recognition()
        
        # Send final summary
        await self.websocket.send_json({
            "type": "session_ended",
            "total_segments": len(self._segments)
        })
    
    async def _on_recognized(self, text: str, offset_seconds: float):
        """Handle recognized speech."""
        if not text.strip():
            return
        
        segment = {
            "text": text,
            "offset": offset_seconds,
            "speaker": "candidate"  # Would need speaker diarization for multiple speakers
        }
        self._segments.append(segment)
        
        await self.websocket.send_json({
            "type": "transcript_segment",
            "segment": segment
        })
    
    async def _on_session_stopped(self):
        """Handle session stop event."""
        logger.info("Recognition session stopped")
    
    async def _on_error(self, error_message: str):
        """Handle recognition error."""
        logger.error("Recognition error", error=error_message)
        await self._send_error(error_message)
    
    async def _send_error(self, message: str):
        """Send error message to client."""
        try:
            await self.websocket.send_json({
                "type": "error",
                "message": message
            })
        except Exception:
            pass  # WebSocket may be closed

# FastAPI WebSocket endpoint
@router.websocket("/transcribe/{interview_id}")
async def transcribe_websocket(
    websocket: WebSocket,
    interview_id: str,
    speech_service: AzureSpeechService = Depends(get_speech_service),
    current_user: User = Depends(get_ws_current_user)
):
    await websocket.accept()
    
    session = TranscriptionSession(
        websocket=websocket,
        speech_service=speech_service,
        interview_id=interview_id
    )
    
    try:
        await session.start()
        
        while True:
            try:
                # Receive audio data (binary) or control message (text)
                message = await asyncio.wait_for(
                    websocket.receive(),
                    timeout=30.0  # Heartbeat timeout
                )
                
                if "bytes" in message:
                    await session.process_audio(message["bytes"])
                    
                elif "text" in message:
                    data = json.loads(message["text"])
                    
                    if data.get("type") == "stop":
                        break
                    elif data.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                        
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_json({"type": "ping"})
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", interview_id=interview_id)
        
    except Exception as e:
        logger.error("WebSocket error", interview_id=interview_id, exception=e)
        
    finally:
        await session.stop()
```

### 3.3 Token Generation with Caching

```python
from datetime import datetime, timedelta
from typing import Optional
import aiohttp
import asyncio

@dataclass
class SpeechToken:
    token: str
    region: str
    expires_at: datetime

class SpeechTokenService:
    """
    Service for generating and caching Azure Speech tokens.
    """
    
    TOKEN_VALIDITY_MINUTES = 9  # Tokens valid for 10 mins, refresh at 9
    
    def __init__(self, subscription_key: str, region: str):
        self.subscription_key = subscription_key
        self.region = region
        self._cached_token: Optional[SpeechToken] = None
        self._lock = asyncio.Lock()
    
    async def get_token(self) -> SpeechToken:
        """
        Get a valid speech token, refreshing if necessary.
        """
        async with self._lock:
            # Check if cached token is still valid
            if self._cached_token:
                if datetime.now() < self._cached_token.expires_at:
                    return self._cached_token
            
            # Fetch new token
            self._cached_token = await self._fetch_token()
            return self._cached_token
    
    @async_retry(max_attempts=3, retryable_exceptions=(aiohttp.ClientError,))
    async def _fetch_token(self) -> SpeechToken:
        """Fetch a new token from Azure."""
        token_url = (
            f"https://{self.region}.api.cognitive.microsoft.com/"
            f"sts/v1.0/issueToken"
        )
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                token_url,
                headers={
                    "Ocp-Apim-Subscription-Key": self.subscription_key,
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            ) as response:
                if response.status == 401:
                    raise SpeechServiceError("Invalid Azure Speech subscription key")
                    
                if response.status == 403:
                    raise SpeechServiceError("Azure Speech subscription quota exceeded")
                    
                response.raise_for_status()
                
                token = await response.text()
                
                return SpeechToken(
                    token=token,
                    region=self.region,
                    expires_at=datetime.now() + timedelta(minutes=self.TOKEN_VALIDITY_MINUTES)
                )
```

---

## 4. Azure Communication Services

### 4.1 Identity and Token Management

```python
from azure.communication.identity import (
    CommunicationIdentityClient,
    CommunicationUserIdentifier
)
from azure.communication.identity._shared.models import CommunicationTokenScope
from azure.core.exceptions import (
    HttpResponseError,
    ClientAuthenticationError,
    ServiceRequestError
)
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from app.common.logging import StructuredLogger
from app.common.retry import async_retry

logger = StructuredLogger("azure.acs")

@dataclass
class AcsUser:
    communication_user_id: str
    
@dataclass
class AcsToken:
    token: str
    expires_on: datetime
    user: AcsUser

class AcsServiceError(Exception):
    """Base error for ACS operations."""
    pass

class AcsAuthenticationError(AcsServiceError):
    """Authentication failed."""
    pass

class AcsIdentityService:
    """
    Azure Communication Services identity and token management.
    """
    
    RETRYABLE_ERRORS = (ServiceRequestError,)
    
    def __init__(self, connection_string: str):
        self._client = CommunicationIdentityClient.from_connection_string(
            connection_string
        )
    
    @async_retry(max_attempts=3, retryable_exceptions=RETRYABLE_ERRORS)
    async def create_user_with_token(
        self,
        scopes: Optional[List[str]] = None
    ) -> AcsToken:
        """
        Create a new ACS user and generate an access token.
        
        Args:
            scopes: Token scopes (default: voip)
            
        Returns:
            AcsToken with user and token
        """
        if scopes is None:
            scopes = [CommunicationTokenScope.VOIP]
        
        try:
            logger.info("Creating ACS user with token", scopes=scopes)
            
            # Run in thread pool (SDK is sync)
            loop = asyncio.get_event_loop()
            user, token_response = await loop.run_in_executor(
                None,
                lambda: self._client.create_user_and_token(scopes=scopes)
            )
            
            logger.info(
                "ACS user created",
                user_id=user.properties["id"],
                expires_on=token_response.expires_on.isoformat()
            )
            
            return AcsToken(
                token=token_response.token,
                expires_on=token_response.expires_on,
                user=AcsUser(communication_user_id=user.properties["id"])
            )
            
        except ClientAuthenticationError as e:
            logger.error("ACS authentication failed", exception=e)
            raise AcsAuthenticationError("Invalid ACS connection string")
            
        except HttpResponseError as e:
            logger.error("ACS HTTP error", status_code=e.status_code, exception=e)
            
            if e.status_code == 429:
                raise AcsServiceError("ACS rate limit exceeded")
            elif e.status_code >= 500:
                raise  # Retry server errors
            else:
                raise AcsServiceError(f"ACS error: {e.message}")
    
    @async_retry(max_attempts=3, retryable_exceptions=RETRYABLE_ERRORS)
    async def refresh_token(
        self,
        user_id: str,
        scopes: Optional[List[str]] = None
    ) -> AcsToken:
        """
        Refresh token for an existing user.
        """
        if scopes is None:
            scopes = [CommunicationTokenScope.VOIP]
        
        try:
            user = CommunicationUserIdentifier(user_id)
            
            loop = asyncio.get_event_loop()
            token_response = await loop.run_in_executor(
                None,
                lambda: self._client.get_token(user, scopes=scopes)
            )
            
            return AcsToken(
                token=token_response.token,
                expires_on=token_response.expires_on,
                user=AcsUser(communication_user_id=user_id)
            )
            
        except HttpResponseError as e:
            if e.status_code == 404:
                raise AcsServiceError(f"User {user_id} not found")
            raise
    
    async def revoke_tokens(self, user_id: str) -> None:
        """Revoke all tokens for a user."""
        try:
            user = CommunicationUserIdentifier(user_id)
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._client.revoke_tokens(user)
            )
            
            logger.info("Tokens revoked", user_id=user_id)
            
        except HttpResponseError as e:
            logger.error("Failed to revoke tokens", user_id=user_id, exception=e)
            raise
    
    async def delete_user(self, user_id: str) -> None:
        """Delete an ACS user and all associated data."""
        try:
            user = CommunicationUserIdentifier(user_id)
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._client.delete_user(user)
            )
            
            logger.info("User deleted", user_id=user_id)
            
        except HttpResponseError as e:
            if e.status_code != 404:  # Ignore if already deleted
                raise
    
    async def health_check(self) -> bool:
        """Verify ACS connectivity."""
        try:
            await self.create_user_with_token()
            return True
        except Exception:
            return False
```

### 4.2 Call Automation with Error Recovery

```python
from azure.communication.callautomation import (
    CallAutomationClient,
    CallInvite,
    CommunicationUserIdentifier as CallUserIdentifier,
    PhoneNumberIdentifier,
    TextSource,
    FileSource
)
from azure.communication.callautomation.aio import CallAutomationClient as AsyncCallAutomationClient
from typing import Optional, Union
from dataclasses import dataclass

@dataclass
class CallInfo:
    call_connection_id: str
    server_call_id: str
    correlation_id: str

class AcsCallAutomationService:
    """
    Azure Communication Services Call Automation.
    """
    
    def __init__(self, connection_string: str, callback_url: str):
        self._client = AsyncCallAutomationClient.from_connection_string(
            connection_string
        )
        self.callback_url = callback_url
    
    async def create_call(
        self,
        target_id: str,
        source_caller_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> CallInfo:
        """
        Create an outbound call.
        
        Args:
            target_id: ACS user ID or phone number
            source_caller_id: Caller ID (phone number)
            correlation_id: For tracking
            
        Returns:
            CallInfo with connection details
        """
        try:
            # Determine target type
            if target_id.startswith("+"):
                target = PhoneNumberIdentifier(target_id)
            else:
                target = CallUserIdentifier(target_id)
            
            call_invite = CallInvite(target=target)
            
            # Set caller ID for PSTN calls
            if source_caller_id:
                call_invite.source_caller_id_number = PhoneNumberIdentifier(source_caller_id)
            
            logger.info(
                "Creating call",
                target=target_id,
                correlation_id=correlation_id
            )
            
            result = await self._client.create_call(
                target_participant=call_invite,
                callback_url=f"{self.callback_url}/api/v1/webhooks/acs",
                operation_context=correlation_id
            )
            
            call_connection = result.call_connection
            call_properties = await call_connection.get_call_properties()
            
            return CallInfo(
                call_connection_id=call_properties.call_connection_id,
                server_call_id=call_properties.server_call_id,
                correlation_id=correlation_id or call_properties.correlation_id
            )
            
        except HttpResponseError as e:
            logger.error("Create call failed", exception=e)
            
            if "InvalidPhoneNumber" in str(e):
                raise AcsServiceError(f"Invalid phone number: {target_id}")
            elif e.status_code == 403:
                raise AcsServiceError("Not authorized to make calls")
            else:
                raise AcsServiceError(f"Call creation failed: {e.message}")
    
    async def play_text(
        self,
        call_connection_id: str,
        text: str,
        voice_name: str = "en-AU-NatashaNeural",
        loop: bool = False
    ) -> None:
        """
        Play text-to-speech in a call.
        """
        try:
            call_connection = self._client.get_call_connection(call_connection_id)
            
            text_source = TextSource(
                text=text,
                voice_name=voice_name
            )
            
            await call_connection.play_media(
                play_source=text_source,
                loop=loop
            )
            
            logger.info("Playing text in call", call_id=call_connection_id)
            
        except HttpResponseError as e:
            if e.status_code == 404:
                raise AcsServiceError(f"Call {call_connection_id} not found or ended")
            raise
    
    async def play_audio(
        self,
        call_connection_id: str,
        audio_url: str,
        loop: bool = False
    ) -> None:
        """
        Play audio file in a call.
        """
        try:
            call_connection = self._client.get_call_connection(call_connection_id)
            
            file_source = FileSource(url=audio_url)
            
            await call_connection.play_media(
                play_source=file_source,
                loop=loop
            )
            
        except HttpResponseError as e:
            if e.status_code == 404:
                raise AcsServiceError(f"Call {call_connection_id} not found")
            elif "InvalidFileFormat" in str(e):
                raise AcsServiceError(f"Invalid audio format: {audio_url}")
            raise
    
    async def hangup(
        self,
        call_connection_id: str,
        for_everyone: bool = True
    ) -> None:
        """
        End a call.
        """
        try:
            call_connection = self._client.get_call_connection(call_connection_id)
            
            if for_everyone:
                await call_connection.hang_up(is_for_everyone=True)
            else:
                await call_connection.hang_up(is_for_everyone=False)
            
            logger.info("Call ended", call_id=call_connection_id)
            
        except HttpResponseError as e:
            if e.status_code == 404:
                # Call already ended
                logger.info("Call already ended", call_id=call_connection_id)
            else:
                raise
    
    async def start_recording(
        self,
        server_call_id: str,
        recording_content_type: str = "audio",
        recording_channel_type: str = "mixed"
    ) -> str:
        """
        Start recording a call.
        
        Returns:
            Recording ID
        """
        try:
            result = await self._client.start_recording(
                call_locator=server_call_id,
                recording_content_type=recording_content_type,
                recording_channel_type=recording_channel_type
            )
            
            logger.info(
                "Recording started",
                recording_id=result.recording_id,
                server_call_id=server_call_id
            )
            
            return result.recording_id
            
        except HttpResponseError as e:
            logger.error("Start recording failed", exception=e)
            raise AcsServiceError(f"Failed to start recording: {e.message}")
```

### 4.3 Webhook Handler with Validation

```python
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Any
import hashlib
import hmac
import json

router = APIRouter()

class AcsEvent(BaseModel):
    id: str
    topic: str
    subject: str
    eventType: str
    eventTime: str
    data: dict
    dataVersion: str

class AcsWebhookHandler:
    """
    Handler for Azure Communication Services webhook events.
    """
    
    # Event Grid subscription validation
    VALIDATION_EVENT = "Microsoft.EventGrid.SubscriptionValidationEvent"
    
    # Call events
    CALL_CONNECTED = "Microsoft.Communication.CallConnected"
    CALL_DISCONNECTED = "Microsoft.Communication.CallDisconnected"
    PARTICIPANTS_UPDATED = "Microsoft.Communication.ParticipantsUpdated"
    
    # Recording events
    RECORDING_STATE_CHANGED = "Microsoft.Communication.RecordingStateChanged"
    RECORDING_FILE_STATUS = "Microsoft.Communication.RecordingFileStatusUpdated"
    
    # Media events
    PLAY_COMPLETED = "Microsoft.Communication.PlayCompleted"
    PLAY_FAILED = "Microsoft.Communication.PlayFailed"
    RECOGNIZE_COMPLETED = "Microsoft.Communication.RecognizeCompleted"
    RECOGNIZE_FAILED = "Microsoft.Communication.RecognizeFailed"
    
    def __init__(
        self,
        supabase_client,
        recording_service: Optional['AcsRecordingService'] = None
    ):
        self.supabase = supabase_client
        self.recording_service = recording_service
    
    async def handle_events(
        self,
        events: List[AcsEvent],
        background_tasks: BackgroundTasks
    ) -> dict:
        """
        Process incoming ACS webhook events.
        """
        results = []
        
        for event in events:
            try:
                result = await self._route_event(event, background_tasks)
                results.append({"event_id": event.id, "status": "processed", **result})
                
            except Exception as e:
                logger.error(
                    "Event processing failed",
                    event_id=event.id,
                    event_type=event.eventType,
                    exception=e
                )
                results.append({
                    "event_id": event.id,
                    "status": "error",
                    "error": str(e)
                })
        
        return {"results": results}
    
    async def _route_event(
        self,
        event: AcsEvent,
        background_tasks: BackgroundTasks
    ) -> dict:
        """Route event to appropriate handler."""
        
        event_type = event.eventType
        data = event.data
        
        # Subscription validation
        if event_type == self.VALIDATION_EVENT:
            return {"validationResponse": data.get("validationCode")}
        
        # Call events
        if event_type == self.CALL_CONNECTED:
            await self._handle_call_connected(data)
            return {"action": "call_started"}
            
        if event_type == self.CALL_DISCONNECTED:
            await self._handle_call_disconnected(data)
            return {"action": "call_ended"}
        
        # Recording events
        if event_type == self.RECORDING_FILE_STATUS:
            # Process recording in background
            background_tasks.add_task(
                self._handle_recording_ready,
                data
            )
            return {"action": "recording_queued"}
        
        # Media events
        if event_type == self.PLAY_COMPLETED:
            logger.info("Play completed", context=data.get("operationContext"))
            return {"action": "play_completed"}
            
        if event_type == self.PLAY_FAILED:
            logger.error("Play failed", 
                reason=data.get("resultInformation", {}).get("message"))
            return {"action": "play_failed"}
        
        # Unknown event
        logger.warning("Unhandled event type", event_type=event_type)
        return {"action": "ignored"}
    
    async def _handle_call_connected(self, data: dict):
        """Handle call connected event."""
        call_connection_id = data.get("callConnectionId")
        correlation_id = data.get("correlationId")
        
        logger.info(
            "Call connected",
            call_connection_id=call_connection_id,
            correlation_id=correlation_id
        )
        
        # Update interview status
        if correlation_id:
            await self._update_interview(correlation_id, {
                "status": "in_progress",
                "started_at": datetime.utcnow().isoformat()
            })
    
    async def _handle_call_disconnected(self, data: dict):
        """Handle call disconnected event."""
        call_connection_id = data.get("callConnectionId")
        correlation_id = data.get("correlationId")
        
        logger.info(
            "Call disconnected",
            call_connection_id=call_connection_id,
            correlation_id=correlation_id
        )
        
        # Update interview status
        if correlation_id:
            await self._update_interview(correlation_id, {
                "status": "completed",
                "ended_at": datetime.utcnow().isoformat()
            })
    
    async def _handle_recording_ready(self, data: dict):
        """Handle recording file ready event."""
        recording_id = data.get("recordingId")
        content_location = data.get("recordingStorageInfo", {}).get("recordingChunks", [])
        
        if not content_location:
            logger.error("No recording chunks in event", recording_id=recording_id)
            return
        
        # Download and store recording
        if self.recording_service:
            try:
                await self.recording_service.process_recording(
                    recording_id=recording_id,
                    content_location=content_location[0].get("contentLocation")
                )
            except Exception as e:
                logger.error("Recording processing failed", 
                    recording_id=recording_id, exception=e)
    
    async def _update_interview(self, correlation_id: str, updates: dict):
        """Update interview record in database."""
        try:
            # Find interview by correlation ID in metadata
            result = await self.supabase.table("interviews") \
                .select("id, metadata") \
                .contains("metadata", {"correlation_id": correlation_id}) \
                .single() \
                .execute()
            
            if result.data:
                interview_id = result.data["id"]
                await self.supabase.table("interviews") \
                    .update(updates) \
                    .eq("id", interview_id) \
                    .execute()
                    
        except Exception as e:
            logger.error(
                "Failed to update interview",
                correlation_id=correlation_id,
                exception=e
            )

# FastAPI endpoint
@router.post("/acs")
async def handle_acs_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    handler: AcsWebhookHandler = Depends(get_webhook_handler)
):
    """
    Endpoint for Azure Communication Services webhooks.
    """
    try:
        body = await request.json()
        
        # Handle both single event and array of events
        if isinstance(body, list):
            events = [AcsEvent(**e) for e in body]
        else:
            events = [AcsEvent(**body)]
        
        return await handler.handle_events(events, background_tasks)
        
    except Exception as e:
        logger.error("Webhook processing failed", exception=e)
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 5. Azure Blob Storage

### 5.1 Upload with Retry and Progress

```python
from azure.storage.blob.aio import BlobServiceClient, ContainerClient
from azure.core.exceptions import (
    ResourceExistsError,
    ResourceNotFoundError,
    AzureError
)
from typing import AsyncGenerator, Optional, Callable
from dataclasses import dataclass
import hashlib
import mimetypes

@dataclass
class UploadResult:
    blob_url: str
    blob_name: str
    content_md5: str
    size_bytes: int

class AzureBlobService:
    """
    Azure Blob Storage service with comprehensive error handling.
    """
    
    def __init__(self, connection_string: str, container_name: str):
        self._client = BlobServiceClient.from_connection_string(connection_string)
        self.container_name = container_name
        self._container_client: Optional[ContainerClient] = None
    
    async def _get_container(self) -> ContainerClient:
        """Get or create container."""
        if self._container_client is None:
            self._container_client = self._client.get_container_client(
                self.container_name
            )
            
            # Create if not exists
            try:
                await self._container_client.create_container()
            except ResourceExistsError:
                pass  # Container already exists
        
        return self._container_client
    
    @async_retry(max_attempts=3, retryable_exceptions=(AzureError,))
    async def upload_file(
        self,
        file_content: bytes,
        blob_name: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> UploadResult:
        """
        Upload a file to blob storage.
        
        Args:
            file_content: File bytes
            blob_name: Name/path in container
            content_type: MIME type
            metadata: Custom metadata
            on_progress: Progress callback (bytes_uploaded, total_bytes)
            
        Returns:
            UploadResult with blob details
        """
        container = await self._get_container()
        blob_client = container.get_blob_client(blob_name)
        
        # Calculate MD5 for integrity
        content_md5 = hashlib.md5(file_content).hexdigest()
        
        # Guess content type if not provided
        if content_type is None:
            content_type, _ = mimetypes.guess_type(blob_name)
            content_type = content_type or "application/octet-stream"
        
        try:
            logger.info(
                "Uploading blob",
                blob_name=blob_name,
                size_bytes=len(file_content),
                content_type=content_type
            )
            
            # Upload with progress tracking
            await blob_client.upload_blob(
                file_content,
                overwrite=True,
                content_settings={"content_type": content_type},
                metadata=metadata,
                max_concurrency=4
            )
            
            # Get blob URL
            blob_url = blob_client.url
            
            logger.info("Blob uploaded", blob_url=blob_url)
            
            return UploadResult(
                blob_url=blob_url,
                blob_name=blob_name,
                content_md5=content_md5,
                size_bytes=len(file_content)
            )
            
        except ResourceExistsError:
            # Shouldn't happen with overwrite=True, but handle anyway
            raise AzureStorageError(f"Blob {blob_name} already exists")
            
        except AzureError as e:
            logger.error("Blob upload failed", blob_name=blob_name, exception=e)
            raise
    
    async def upload_stream(
        self,
        stream: AsyncGenerator[bytes, None],
        blob_name: str,
        content_type: str,
        estimated_size: Optional[int] = None
    ) -> UploadResult:
        """
        Upload a stream to blob storage.
        
        Useful for large files or when content comes from another source.
        """
        container = await self._get_container()
        blob_client = container.get_blob_client(blob_name)
        
        # Collect chunks for upload
        chunks = []
        total_size = 0
        
        async for chunk in stream:
            chunks.append(chunk)
            total_size += len(chunk)
        
        content = b"".join(chunks)
        
        return await self.upload_file(
            content,
            blob_name,
            content_type=content_type
        )
    
    @async_retry(max_attempts=3, retryable_exceptions=(AzureError,))
    async def download_file(self, blob_name: str) -> bytes:
        """
        Download a blob to memory.
        """
        container = await self._get_container()
        blob_client = container.get_blob_client(blob_name)
        
        try:
            stream = await blob_client.download_blob()
            content = await stream.readall()
            
            logger.info("Blob downloaded", blob_name=blob_name, size=len(content))
            
            return content
            
        except ResourceNotFoundError:
            raise AzureStorageError(f"Blob {blob_name} not found")
    
    async def download_stream(
        self,
        blob_name: str,
        chunk_size: int = 4 * 1024 * 1024  # 4MB chunks
    ) -> AsyncGenerator[bytes, None]:
        """
        Download a blob as a stream.
        
        Useful for large files to avoid loading entirely into memory.
        """
        container = await self._get_container()
        blob_client = container.get_blob_client(blob_name)
        
        try:
            stream = await blob_client.download_blob()
            
            async for chunk in stream.chunks():
                yield chunk
                
        except ResourceNotFoundError:
            raise AzureStorageError(f"Blob {blob_name} not found")
    
    async def generate_sas_url(
        self,
        blob_name: str,
        expiry_hours: int = 1,
        permissions: str = "r"  # r=read, w=write, d=delete
    ) -> str:
        """
        Generate a SAS URL for temporary blob access.
        """
        from azure.storage.blob import generate_blob_sas, BlobSasPermissions
        from datetime import datetime, timedelta
        
        container = await self._get_container()
        blob_client = container.get_blob_client(blob_name)
        
        # Check blob exists
        try:
            await blob_client.get_blob_properties()
        except ResourceNotFoundError:
            raise AzureStorageError(f"Blob {blob_name} not found")
        
        # Generate SAS token
        sas_token = generate_blob_sas(
            account_name=self._client.account_name,
            container_name=self.container_name,
            blob_name=blob_name,
            account_key=self._client.credential.account_key,
            permission=BlobSasPermissions(
                read="r" in permissions,
                write="w" in permissions,
                delete="d" in permissions
            ),
            expiry=datetime.utcnow() + timedelta(hours=expiry_hours)
        )
        
        return f"{blob_client.url}?{sas_token}"
    
    async def delete_blob(self, blob_name: str) -> bool:
        """
        Delete a blob.
        
        Returns:
            True if deleted, False if not found
        """
        container = await self._get_container()
        blob_client = container.get_blob_client(blob_name)
        
        try:
            await blob_client.delete_blob()
            logger.info("Blob deleted", blob_name=blob_name)
            return True
            
        except ResourceNotFoundError:
            logger.info("Blob not found for deletion", blob_name=blob_name)
            return False
    
    async def list_blobs(
        self,
        prefix: Optional[str] = None,
        max_results: int = 100
    ) -> List[dict]:
        """
        List blobs in container.
        """
        container = await self._get_container()
        
        blobs = []
        async for blob in container.list_blobs(name_starts_with=prefix):
            blobs.append({
                "name": blob.name,
                "size": blob.size,
                "last_modified": blob.last_modified.isoformat(),
                "content_type": blob.content_settings.content_type
            })
            
            if len(blobs) >= max_results:
                break
        
        return blobs
    
    async def health_check(self) -> bool:
        """Check storage connectivity."""
        try:
            container = await self._get_container()
            # List with limit 1 to verify access
            async for _ in container.list_blobs(max_results=1):
                pass
            return True
        except Exception:
            return False

class AzureStorageError(Exception):
    """Azure Storage error."""
    pass
```

---

## 6. Azure Document Intelligence

### 6.1 Document Analysis with Polling

```python
from azure.ai.documentintelligence.aio import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import (
    AnalyzeDocumentRequest,
    AnalyzeResult
)
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from typing import Optional
import asyncio

class DocumentAnalysisError(Exception):
    """Document analysis error."""
    pass

class AzureDocumentService:
    """
    Azure Document Intelligence service for document analysis.
    """
    
    # Supported document types
    SUPPORTED_TYPES = {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/tiff",
        "image/bmp"
    }
    
    def __init__(self, endpoint: str, api_key: str):
        self._client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(api_key)
        )
    
    async def analyze_document(
        self,
        document_content: bytes,
        model_id: str = "prebuilt-document",
        timeout_seconds: int = 120
    ) -> AnalyzeResult:
        """
        Analyze a document using Azure Document Intelligence.
        
        Args:
            document_content: Document bytes
            model_id: Model to use (prebuilt-document, prebuilt-layout, etc.)
            timeout_seconds: Maximum time to wait for analysis
            
        Returns:
            AnalyzeResult with extracted content
        """
        try:
            logger.info(
                "Starting document analysis",
                model=model_id,
                size_bytes=len(document_content)
            )
            
            # Start async analysis
            poller = await self._client.begin_analyze_document(
                model_id,
                AnalyzeDocumentRequest(bytes_source=document_content)
            )
            
            # Poll for completion with timeout
            start_time = asyncio.get_event_loop().time()
            
            while not poller.done():
                elapsed = asyncio.get_event_loop().time() - start_time
                
                if elapsed > timeout_seconds:
                    raise DocumentAnalysisError(
                        f"Document analysis timed out after {timeout_seconds}s"
                    )
                
                await asyncio.sleep(1)
                
                # Log progress
                status = poller.status()
                logger.debug("Analysis status", status=status)
            
            result = await poller.result()
            
            logger.info(
                "Document analysis complete",
                pages=len(result.pages) if result.pages else 0,
                tables=len(result.tables) if result.tables else 0
            )
            
            return result
            
        except HttpResponseError as e:
            if e.status_code == 400:
                raise DocumentAnalysisError(
                    f"Invalid document format or corrupted file"
                )
            elif e.status_code == 413:
                raise DocumentAnalysisError(
                    f"Document too large (max 500MB)"
                )
            else:
                raise DocumentAnalysisError(f"Analysis failed: {e.message}")
    
    async def extract_text(self, document_content: bytes) -> str:
        """
        Extract plain text from a document.
        """
        result = await self.analyze_document(
            document_content,
            model_id="prebuilt-read"  # Optimized for text extraction
        )
        
        # Combine all page content
        text_parts = []
        
        if result.content:
            return result.content
        
        # Fallback: combine paragraphs
        if result.paragraphs:
            for para in result.paragraphs:
                text_parts.append(para.content)
        
        return "\n\n".join(text_parts)
    
    async def extract_tables(self, document_content: bytes) -> List[dict]:
        """
        Extract tables from a document.
        """
        result = await self.analyze_document(
            document_content,
            model_id="prebuilt-layout"  # Best for tables
        )
        
        tables = []
        
        if result.tables:
            for table in result.tables:
                table_data = {
                    "row_count": table.row_count,
                    "column_count": table.column_count,
                    "cells": []
                }
                
                for cell in table.cells:
                    table_data["cells"].append({
                        "row": cell.row_index,
                        "column": cell.column_index,
                        "content": cell.content,
                        "is_header": cell.kind == "columnHeader"
                    })
                
                tables.append(table_data)
        
        return tables
    
    async def analyze_resume(self, resume_content: bytes) -> dict:
        """
        Extract structured data from a resume.
        
        Uses Document Intelligence + Azure OpenAI for best results.
        """
        # First extract text
        text = await self.extract_text(resume_content)
        
        # Then use Azure OpenAI for structured extraction
        # (This would call the OpenAI service)
        
        return {
            "raw_text": text,
            "needs_ai_extraction": True
        }
    
    async def health_check(self) -> bool:
        """Verify Document Intelligence connectivity."""
        try:
            # Use a minimal PDF for health check
            minimal_pdf = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\nxref\n0 3\n0000000000 65535 f\n0000000009 00000 n\n0000000052 00000 n\ntrailer<</Size 3/Root 1 0 R>>\nstartxref\n101\n%%EOF"
            
            await self.analyze_document(minimal_pdf, timeout_seconds=30)
            return True
        except Exception:
            return False
```

---

## 7. Azure Key Vault

### 7.1 Secret Management with Caching

```python
from azure.keyvault.secrets.aio import SecretClient
from azure.identity.aio import DefaultAzureCredential, ManagedIdentityCredential
from azure.core.exceptions import ResourceNotFoundError, HttpResponseError
from typing import Optional, Dict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio

@dataclass
class CachedSecret:
    value: str
    fetched_at: datetime
    expires_at: Optional[datetime] = None

class AzureKeyVaultService:
    """
    Azure Key Vault service with local caching.
    """
    
    # Cache secrets for 5 minutes by default
    DEFAULT_CACHE_TTL = timedelta(minutes=5)
    
    def __init__(
        self,
        vault_url: str,
        use_managed_identity: bool = True,
        cache_ttl: timedelta = DEFAULT_CACHE_TTL
    ):
        if use_managed_identity:
            credential = ManagedIdentityCredential()
        else:
            credential = DefaultAzureCredential()
        
        self._client = SecretClient(
            vault_url=vault_url,
            credential=credential
        )
        self._cache: Dict[str, CachedSecret] = {}
        self._cache_ttl = cache_ttl
        self._lock = asyncio.Lock()
    
    async def get_secret(
        self,
        name: str,
        use_cache: bool = True
    ) -> str:
        """
        Get a secret value.
        
        Args:
            name: Secret name
            use_cache: Whether to use cached value if available
            
        Returns:
            Secret value
            
        Raises:
            KeyVaultError: If secret not found or access denied
        """
        async with self._lock:
            # Check cache
            if use_cache and name in self._cache:
                cached = self._cache[name]
                if datetime.now() < cached.fetched_at + self._cache_ttl:
                    return cached.value
            
            # Fetch from Key Vault
            try:
                secret = await self._client.get_secret(name)
                
                # Cache the value
                self._cache[name] = CachedSecret(
                    value=secret.value,
                    fetched_at=datetime.now(),
                    expires_at=secret.properties.expires_on
                )
                
                return secret.value
                
            except ResourceNotFoundError:
                raise KeyVaultError(f"Secret '{name}' not found")
                
            except HttpResponseError as e:
                if e.status_code == 403:
                    raise KeyVaultError(f"Access denied to secret '{name}'")
                raise KeyVaultError(f"Failed to get secret: {e.message}")
    
    async def set_secret(
        self,
        name: str,
        value: str,
        expires_on: Optional[datetime] = None
    ) -> None:
        """
        Set a secret value.
        """
        try:
            await self._client.set_secret(
                name,
                value,
                expires_on=expires_on
            )
            
            # Update cache
            async with self._lock:
                self._cache[name] = CachedSecret(
                    value=value,
                    fetched_at=datetime.now(),
                    expires_at=expires_on
                )
            
            logger.info("Secret set", name=name)
            
        except HttpResponseError as e:
            if e.status_code == 403:
                raise KeyVaultError(f"Not authorized to set secret '{name}'")
            raise
    
    async def delete_secret(self, name: str) -> None:
        """
        Delete a secret.
        """
        try:
            poller = await self._client.begin_delete_secret(name)
            await poller.wait()
            
            # Remove from cache
            async with self._lock:
                self._cache.pop(name, None)
            
            logger.info("Secret deleted", name=name)
            
        except ResourceNotFoundError:
            pass  # Already deleted
    
    async def list_secrets(self) -> List[str]:
        """
        List all secret names (not values).
        """
        names = []
        async for secret_properties in self._client.list_properties_of_secrets():
            names.append(secret_properties.name)
        return names
    
    def clear_cache(self):
        """Clear the local secret cache."""
        self._cache.clear()
    
    async def health_check(self) -> bool:
        """Verify Key Vault connectivity."""
        try:
            # List secrets to verify access
            async for _ in self._client.list_properties_of_secrets():
                break
            return True
        except Exception:
            return False

class KeyVaultError(Exception):
    """Key Vault error."""
    pass
```

---

## 8. Testing Patterns

### 8.1 Mock Azure Services

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

# Mock Azure OpenAI
class MockAzureOpenAI:
    """Mock Azure OpenAI client for testing."""
    
    def __init__(self, responses: List[str] = None):
        self.responses = responses or ["Mock response"]
        self._call_count = 0
        self.calls: List[Dict[str, Any]] = []
    
    async def chat_completion(self, messages: List[dict], **kwargs) -> dict:
        self.calls.append({"messages": messages, **kwargs})
        
        response = self.responses[self._call_count % len(self.responses)]
        self._call_count += 1
        
        return {
            "choices": [{
                "message": {"content": response},
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }
    
    async def stream_chat_completion(self, messages: List[dict], **kwargs):
        self.calls.append({"messages": messages, "stream": True, **kwargs})
        
        response = self.responses[self._call_count % len(self.responses)]
        self._call_count += 1
        
        # Yield chunks
        for word in response.split():
            yield word + " "

# Mock Azure Speech
class MockAzureSpeech:
    """Mock Azure Speech service for testing."""
    
    def __init__(self, fail_on_call: int = -1):
        self._call_count = 0
        self._fail_on_call = fail_on_call
    
    async def synthesize_speech(self, text: str) -> bytes:
        self._call_count += 1
        
        if self._call_count == self._fail_on_call:
            raise SpeechSynthesisError("Mock failure")
        
        # Return fake audio data
        return b"RIFF" + b"\x00" * 100
    
    async def get_token(self) -> dict:
        return {
            "token": "mock-token",
            "region": "australiaeast",
            "expires_at": (datetime.now() + timedelta(minutes=10)).isoformat()
        }

# Pytest fixtures
@pytest.fixture
def mock_openai():
    return MockAzureOpenAI(responses=[
        "This is a mock interview response.",
        "Here's a follow-up question."
    ])

@pytest.fixture
def mock_speech():
    return MockAzureSpeech()

@pytest.fixture
def mock_blob_storage():
    """Mock blob storage with in-memory storage."""
    storage = {}
    
    async def upload(content: bytes, name: str, **kwargs):
        storage[name] = content
        return UploadResult(
            blob_url=f"https://mock.blob.core.windows.net/test/{name}",
            blob_name=name,
            content_md5="mock-md5",
            size_bytes=len(content)
        )
    
    async def download(name: str) -> bytes:
        if name not in storage:
            raise AzureStorageError(f"Blob {name} not found")
        return storage[name]
    
    mock = AsyncMock()
    mock.upload_file = upload
    mock.download_file = download
    mock.storage = storage
    
    return mock

# Test examples
@pytest.mark.asyncio
async def test_interview_chat(mock_openai):
    """Test interview chat with mock OpenAI."""
    service = InterviewService(openai_client=mock_openai)
    
    response = await service.process_turn(
        messages=[{"role": "user", "content": "Hello"}],
        context={"job_title": "Software Engineer"}
    )
    
    assert "mock interview response" in response.lower()
    assert len(mock_openai.calls) == 1

@pytest.mark.asyncio
async def test_retry_on_failure():
    """Test retry mechanism on transient failures."""
    call_count = 0
    
    @async_retry(max_attempts=3, retryable_exceptions=(ValueError,))
    async def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Transient error")
        return "success"
    
    result = await flaky_function()
    
    assert result == "success"
    assert call_count == 3

@pytest.mark.asyncio
async def test_circuit_breaker():
    """Test circuit breaker opens after failures."""
    breaker = CircuitBreaker(name="test", failure_threshold=2)
    
    async def failing_call():
        async with breaker:
            raise ValueError("Always fails")
    
    # First two calls should fail but circuit stays closed
    for _ in range(2):
        with pytest.raises(ValueError):
            await failing_call()
    
    # Third call should be blocked by open circuit
    with pytest.raises(CircuitBreakerOpenError):
        await failing_call()
    
    assert breaker.state == CircuitState.OPEN
```

### 8.2 Integration Test Utilities

```python
import pytest
from httpx import AsyncClient
from app.main import app
from app.dependencies import get_openai_client, get_supabase

# Override dependencies for testing
async def get_test_openai():
    return MockAzureOpenAI()

async def get_test_supabase():
    # Return mock Supabase client
    return MockSupabase()

@pytest.fixture
def test_app():
    """Create test app with mocked dependencies."""
    app.dependency_overrides[get_openai_client] = get_test_openai
    app.dependency_overrides[get_supabase] = get_test_supabase
    yield app
    app.dependency_overrides.clear()

@pytest.fixture
async def test_client(test_app):
    """Create async test client."""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        yield client

# Integration tests
@pytest.mark.asyncio
async def test_health_endpoint(test_client):
    """Test health check endpoint."""
    response = await test_client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded", "unhealthy"]

@pytest.mark.asyncio
async def test_interview_chat_endpoint(test_client):
    """Test interview chat endpoint."""
    response = await test_client.post(
        "/api/v1/interview/chat",
        json={
            "messages": [{"role": "user", "content": "Hello"}],
            "context": {"job_title": "Engineer"}
        },
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data

@pytest.mark.asyncio
async def test_rate_limiting(test_client):
    """Test rate limiting enforcement."""
    # Make many requests quickly
    for i in range(15):
        response = await test_client.get("/api/v1/speech/token")
        
        if response.status_code == 429:
            # Rate limited as expected
            assert "retry-after" in response.headers
            return
    
    pytest.fail("Rate limiting not enforced")
```

---

## Appendix: Error Code Reference

### Azure OpenAI Error Codes

| Code | Description | Retry? |
|------|-------------|--------|
| 400 | Invalid request | No |
| 401 | Invalid API key | No |
| 403 | Access denied | No |
| 404 | Model not found | No |
| 429 | Rate limited | Yes (with backoff) |
| 500 | Server error | Yes |
| 503 | Service unavailable | Yes |

### Azure Speech Error Codes

| Code | Description | Retry? |
|------|-------------|--------|
| AuthenticationFailure | Invalid key | No |
| BadRequest | Invalid audio format | No |
| TooManyRequests | Rate limited | Yes |
| ServiceTimeout | Recognition timeout | Yes |
| ServiceUnavailable | Service down | Yes |

### ACS Error Codes

| Code | Description | Retry? |
|------|-------------|--------|
| 400 | Invalid request | No |
| 401 | Invalid connection string | No |
| 403 | Operation not allowed | No |
| 404 | Resource not found | No |
| 409 | Conflict (duplicate) | No |
| 429 | Rate limited | Yes |
| 500+ | Server errors | Yes |

---

## Appendix: Performance Tuning

### Connection Pooling

```python
import httpx

# Create shared HTTP client with connection pooling
http_client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20,
        keepalive_expiry=30.0
    ),
    timeout=httpx.Timeout(
        connect=5.0,
        read=30.0,
        write=10.0,
        pool=5.0
    )
)
```

### Concurrent Request Management

```python
import asyncio
from asyncio import Semaphore

class ConcurrencyLimiter:
    """Limit concurrent Azure API calls."""
    
    def __init__(self, max_concurrent: int = 10):
        self._semaphore = Semaphore(max_concurrent)
    
    async def __aenter__(self):
        await self._semaphore.acquire()
        return self
    
    async def __aexit__(self, *args):
        self._semaphore.release()

# Usage
limiter = ConcurrencyLimiter(max_concurrent=5)

async def make_api_call():
    async with limiter:
        return await azure_client.call()

# Run many calls with controlled concurrency
results = await asyncio.gather(*[make_api_call() for _ in range(100)])
```

---

*Document Version: 1.0*
*Last Updated: 2025-01-07*
*Compatible with: Python 3.11+, Azure SDK 2024*
