import asyncio
import importlib
import sys

import pytest
from conftest import backend_root, clear_app_modules, prepare_test_environment


def _load_ml_module():
    backend_path = str(backend_root())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    prepare_test_environment()
    clear_app_modules()
    import app.services.ml_client as ml_client

    importlib.reload(ml_client)
    return ml_client


def test_build_model1_payload_includes_optional_fields() -> None:
    ml_module = _load_ml_module()
    client = ml_module.MLClient(model1_url="http://m1", model2_url="http://m2")
    payload = client._build_model1_payload(
        [{"speaker": "candidate", "content": "hello"}],
        candidate_id="cand-1",
        role_id="role-1",
        department_id="dep-1",
        interview_id="int-1",
        operating_environment={"control_vs_autonomy": "full_ownership"},
        taxonomy={"taxonomy_id": "tax-1"},
        trace=True,
    )

    assert payload["candidate_id"] == "cand-1"
    assert payload["role_id"] == "role-1"
    assert payload["department_id"] == "dep-1"
    assert payload["interview_id"] == "int-1"
    assert payload["operating_environment"]["control_vs_autonomy"] == "full_ownership"
    assert payload["taxonomy"]["taxonomy_id"] == "tax-1"
    assert payload["trace"] is True


def test_predict_model_validates_transcript_type() -> None:
    ml_module = _load_ml_module()
    client = ml_module.MLClient(model1_url="http://m1", model2_url="http://m2")

    with pytest.raises(AssertionError):
        asyncio.run(client.predict_model1("not-a-list"))  # type: ignore[arg-type]

    with pytest.raises(AssertionError):
        asyncio.run(client.predict_model2("not-a-list"))  # type: ignore[arg-type]


def test_make_request_returns_json_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    ml_module = _load_ml_module()
    client = ml_module.MLClient(model1_url="http://m1", model2_url="http://m2")

    class FakeResponse:
        status_code = 200
        text = "ok"

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {"scores": {"autonomy": {"score": 3}}}

    class FakeAsyncClient:
        def __init__(self, timeout: float):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *_args, **_kwargs):
            return FakeResponse()

    monkeypatch.setattr(ml_module.httpx, "AsyncClient", FakeAsyncClient)
    result = asyncio.run(client._make_request("http://m1", "/predict", {"x": 1}))
    assert result["scores"]["autonomy"]["score"] == 3


def test_make_request_rejects_non_dict_and_bad_json(monkeypatch: pytest.MonkeyPatch) -> None:
    ml_module = _load_ml_module()
    client = ml_module.MLClient(model1_url="http://m1", model2_url="http://m2")

    class NonDictResponse:
        status_code = 200
        text = "[]"

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return []

    class InvalidJsonResponse:
        status_code = 200
        text = "invalid"

        def raise_for_status(self) -> None:
            return None

        def json(self):
            raise ValueError("bad json")

    class FakeAsyncClient:
        def __init__(self, timeout: float):
            self.timeout = timeout
            self.calls = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *_args, **_kwargs):
            self.calls += 1
            return NonDictResponse() if self.calls == 1 else InvalidJsonResponse()

    fake_client = FakeAsyncClient(timeout=30.0)

    class FakeClientFactory:
        def __init__(self, timeout: float):
            self.timeout = timeout

        async def __aenter__(self):
            return fake_client

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(ml_module.httpx, "AsyncClient", FakeClientFactory)

    with pytest.raises(ml_module.MLServiceError, match="invalid response shape"):
        asyncio.run(client._make_request("http://m1", "/predict", {"x": 1}))

    with pytest.raises(ml_module.MLServiceError, match="invalid JSON"):
        asyncio.run(client._make_request("http://m1", "/predict", {"x": 1}))


def test_combined_predictions_fallback_and_health_check(monkeypatch: pytest.MonkeyPatch) -> None:
    ml_module = _load_ml_module()
    client = ml_module.MLClient(model1_url="http://m1", model2_url="http://m2")

    async def model1_fail(*_args, **_kwargs):
        raise RuntimeError("model1 down")

    async def model2_bad(*_args, **_kwargs):
        return "unexpected-shape"

    monkeypatch.setattr(client, "predict_model1", model1_fail)
    monkeypatch.setattr(client, "predict_model2", model2_bad)

    model1_result, model2_result = asyncio.run(
        client.get_combined_predictions([{"speaker": "candidate", "content": "hello"}])
    )
    assert model1_result["fallback"] is True
    assert "model1 down" in model1_result["error"]
    assert model2_result["fallback"] is True

    class HealthResponse:
        def __init__(self, status_code: int):
            self.status_code = status_code

    class HealthAsyncClient:
        def __init__(self, timeout: float):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url: str):
            if "http://m1/health" in url:
                return HealthResponse(200)
            raise RuntimeError("service unavailable")

    monkeypatch.setattr(ml_module.httpx, "AsyncClient", HealthAsyncClient)
    health = asyncio.run(client.health_check())
    assert health["model_service_1"] is True
    assert health["model_service_2"] is False
