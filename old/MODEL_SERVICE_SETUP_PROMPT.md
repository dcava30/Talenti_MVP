# Setup Prompt for Model Service Repository

Copy and paste this prompt into Claude Code when setting up each model service repository:

---

## PROMPT START

I need to convert this ML model repository into a FastAPI microservice that can be deployed as part of a Docker Compose orchestration. The service will receive interview transcript data and return scoring predictions.

### Requirements:

**Service Configuration:**
- Service Name: [model-service-1 OR model-service-2]
- Port: [8001 for model-1, 8002 for model-2]
- Framework: FastAPI with Uvicorn
- Python Version: 3.11

### Create the following structure:

```
repository-root/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── model.py             # ML model wrapper class
│   ├── schemas.py           # Pydantic request/response models
│   └── utils.py             # Helper functions (if needed)
├── models/                   # For model weights/checkpoints
│   └── .gitkeep
├── tests/
│   └── test_api.py          # Basic API tests
├── Dockerfile
├── .dockerignore
├── requirements.txt
└── README.md
```

### 1. app/main.py

Create a FastAPI application with:
- Lifespan context manager that loads the model on startup
- CORS middleware enabled
- Three endpoints:
  - `GET /` - Root info endpoint
  - `GET /health` - Health check (returns 503 if model not loaded)
  - `POST /predict` - Main prediction endpoint
- Proper error handling and logging
- Global model instance that persists across requests

The predict endpoint should:
- Accept a request body with: `{"transcript": [{"speaker": str, "content": str}, ...]}`
- Return: `{"scores": {dimension: {score, confidence, rationale}}, "summary": str, "metadata": {}, "model_version": str}`

### 2. app/schemas.py

Create Pydantic models for:
- `TranscriptSegment` - with speaker and content fields
- `PredictRequest` - with list of TranscriptSegment
- `DimensionScore` - with score (0-100), confidence (0-1), and rationale
- `PredictResponse` - with scores dict, summary, metadata, model_version
- `HealthResponse` - with status, model_loaded, version

### 3. app/model.py

Create a `ModelPredictor` class with:
- `__init__(model_path: str)` - Initialize with model path
- `load_model()` - Load model weights and any tokenizers/preprocessors
- `is_loaded() -> bool` - Check if model is ready
- `predict(transcript: list[dict]) -> dict` - Main inference method
- `get_version() -> str` - Return model version
- `cleanup()` - Resource cleanup

**Important:** The predict method should:
- Extract candidate responses from transcript
- Run inference using the actual ML model
- Return scores for relevant dimensions like: communication, technical, problem_solving, cultural_fit
- Include confidence scores and rationales for each dimension
- Generate an overall summary

### 4. Dockerfile

Create a production-ready Dockerfile:
- Base image: `python:3.11-slim`
- Install system dependencies if needed (especially for PyTorch/TensorFlow)
- Copy and install requirements.txt
- Copy app code and model files
- Expose the appropriate port (8001 or 8002)
- Include HEALTHCHECK command
- Run with: `uvicorn app.main:app --host 0.0.0.0 --port [PORT] --workers 1`

### 5. requirements.txt

Include all dependencies:
```txt
# FastAPI stack
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.0
httpx==0.26.0
python-multipart==0.0.6

# Add existing ML dependencies (torch, transformers, sklearn, etc.)
# Keep all current model dependencies here
```

### 6. .dockerignore

Standard Python Docker ignore patterns to reduce image size.

### 7. README.md

Include:
- Service description
- Local development setup instructions
- How to run locally and with Docker
- API endpoint documentation with curl examples
- Model information (type, framework, input/output format)

### 8. tests/test_api.py

Basic pytest tests for:
- Health endpoint returns 200 when model loaded
- Predict endpoint accepts valid input
- Predict endpoint returns correct response schema

---

### Important Notes:

1. **Preserve existing model code** - Don't remove or modify the actual ML model inference logic, just wrap it in the ModelPredictor class
2. **Keep all existing dependencies** - Add FastAPI requirements alongside existing ones
3. **Model loading** - Ensure models are loaded during application startup (lifespan context)
4. **Error handling** - Wrap predictions in try-except and return 500 errors gracefully
5. **Logging** - Add structured logging throughout for debugging
6. **Port configuration** - Make sure to use the correct port (8001 for service-1, 8002 for service-2)

### Expected Response Format:

The `/predict` endpoint must return this structure:
```json
{
  "scores": {
    "communication": {
      "score": 75.0,
      "confidence": 0.85,
      "rationale": "Clear articulation and professional demeanor."
    },
    "technical": {
      "score": 82.0,
      "confidence": 0.90,
      "rationale": "Strong technical knowledge demonstrated."
    },
    "problem_solving": {
      "score": 70.0,
      "confidence": 0.78,
      "rationale": "Logical approach to problem decomposition."
    }
  },
  "summary": "Candidate demonstrates strong technical abilities with effective communication skills.",
  "metadata": {
    "num_segments": 24,
    "candidate_word_count": 1247,
    "processing_time_ms": 150
  },
  "model_version": "1.0.0"
}
```

### After Setup:

Once created, verify the service works by:
1. Building the Docker image: `docker build -t model-service-X:latest .`
2. Running locally: `docker run -p 800X:800X model-service-X:latest`
3. Testing health: `curl http://localhost:800X/health`
4. Testing prediction with sample data

Please implement this structure while preserving all existing model logic and dependencies. Create all files and provide clear instructions for any manual steps needed.

## PROMPT END

---

## Usage Instructions:

1. **For Model Service 1:**
   - Open the model-1 repository in Claude Code
   - Replace `[model-service-1 OR model-service-2]` with `model-service-1`
   - Replace `[8001 for model-1, 8002 for model-2]` with `8001`
   - Replace `[PORT]` with `8001`
   - Paste the prompt

2. **For Model Service 2:**
   - Open the model-2 repository in Claude Code
   - Replace `[model-service-1 OR model-service-2]` with `model-service-2`
   - Replace `[8001 for model-1, 8002 for model-2]` with `8002`
   - Replace `[PORT]` with `8002`
   - Paste the prompt

3. **Follow up with:**
   - Review the generated code
   - Test the service locally
   - Commit changes to the model repository
   - Return to this repository to integrate with docker-compose
