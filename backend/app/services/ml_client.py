"""
ML Model Client Service
Handles communication with external ML model microservices.
"""
import asyncio
import logging
from typing import Any

import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class MLServiceError(Exception):
    """Raised when ML service communication fails."""
    pass


class MLClient:
    """
    Client for communicating with ML model microservices.
    Handles async requests, retries, and error handling.
    """

    def __init__(
        self,
        model1_url: str | None = None,
        model2_url: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        self.model1_url = model1_url or settings.model_service_1_url
        self.model2_url = model2_url or settings.model_service_2_url
        self.timeout = timeout
        self.max_retries = max_retries

    async def _make_request(
        self,
        url: str,
        endpoint: str,
        payload: dict[str, Any],
        retry_count: int = 0
    ) -> dict[str, Any]:
        """
        Make HTTP request to model service with retry logic.

        Args:
            url: Base URL of the model service
            endpoint: Specific endpoint to call
            payload: Request payload
            retry_count: Current retry attempt

        Returns:
            Response JSON

        Raises:
            MLServiceError: If request fails after retries
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{url}{endpoint}",
                    json=payload
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from {url}: {e.response.status_code} - {e.response.text}")
            if retry_count < self.max_retries:
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                return await self._make_request(url, endpoint, payload, retry_count + 1)
            raise MLServiceError(f"Model service returned error: {e.response.status_code}")

        except httpx.RequestError as e:
            logger.error(f"Request error to {url}: {str(e)}")
            if retry_count < self.max_retries:
                await asyncio.sleep(2 ** retry_count)
                return await self._make_request(url, endpoint, payload, retry_count + 1)
            raise MLServiceError(f"Failed to connect to model service: {str(e)}")

        except Exception as e:
            logger.error(f"Unexpected error calling {url}: {str(e)}")
            raise MLServiceError(f"Unexpected error: {str(e)}")

    async def predict_model1(self, transcript: list[dict[str, str]]) -> dict[str, Any]:
        """
        Call Model Service 1 for predictions.

        Args:
            transcript: List of transcript segments with speaker and content

        Returns:
            Model 1 prediction results
        """
        payload = {"transcript": transcript}
        return await self._make_request(
            self.model1_url,
            "/predict",
            payload
        )

    async def predict_model2(
        self,
        transcript: list[dict[str, str]],
        job_description: str = "",
        resume_text: str = "",
        role_title: str | None = None,
        seniority: str | None = None,
    ) -> dict[str, Any]:
        """
        Call Model Service 2 for predictions.

        Args:
            transcript: List of transcript segments with speaker and content

        Returns:
            Model 2 prediction results
        """
        payload: dict[str, Any] = {
            "job_description": job_description,
            "resume_text": resume_text,
            "transcript": transcript,
        }
        if role_title:
            payload["role_title"] = role_title
        if seniority:
            payload["seniority"] = seniority
        return await self._make_request(
            self.model2_url,
            "/predict/transcript",
            payload
        )

    async def get_combined_predictions(
        self,
        transcript: list[dict[str, str]],
        job_description: str = "",
        resume_text: str = "",
        role_title: str | None = None,
        seniority: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Get predictions from both models concurrently.

        Args:
            transcript: List of transcript segments

        Returns:
            Tuple of (model1_results, model2_results)
        """
        try:
            results = await asyncio.gather(
                self.predict_model1(transcript),
                self.predict_model2(
                    transcript,
                    job_description=job_description,
                    resume_text=resume_text,
                    role_title=role_title,
                    seniority=seniority,
                ),
                return_exceptions=True
            )

            model1_result = results[0]
            model2_result = results[1]

            # Handle individual model failures
            if isinstance(model1_result, Exception):
                logger.error(f"Model 1 failed: {str(model1_result)}")
                model1_result = {"error": str(model1_result), "fallback": True}

            if isinstance(model2_result, Exception):
                logger.error(f"Model 2 failed: {str(model2_result)}")
                model2_result = {"error": str(model2_result), "fallback": True}

            return model1_result, model2_result

        except Exception as e:
            logger.error(f"Failed to get combined predictions: {str(e)}")
            raise MLServiceError(f"Failed to get predictions: {str(e)}")

    async def health_check(self) -> dict[str, bool]:
        """
        Check health status of both model services.

        Returns:
            Dict with service names and their health status
        """
        async def check_service(url: str) -> bool:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{url}/health")
                    return response.status_code == 200
            except Exception:
                return False

        model1_healthy, model2_healthy = await asyncio.gather(
            check_service(self.model1_url),
            check_service(self.model2_url),
            return_exceptions=True
        )

        return {
            "model_service_1": model1_healthy if isinstance(model1_healthy, bool) else False,
            "model_service_2": model2_healthy if isinstance(model2_healthy, bool) else False,
        }


# Singleton instance
ml_client = MLClient()
