# ML Model Microservices Integration Guide

## Overview

This guide walks you through integrating two separate ML model repositories into your Talenti interview platform as FastAPI microservices.

## Phase 1: Prepare Model Repositories

### Step 1: Setup Model Service 1

1. **Open Model Service 1 Repository in Claude Code**
   ```bash
   cd /path/to/model-service-1-repo
   code .  # or open in your IDE with Claude Code
   ```

2. **Copy and paste the entire contents of:**
   ```
   PROMPT_MODEL_SERVICE_1.txt
   ```

3. **Review the generated files:**
   - [ ] `app/main.py` - FastAPI application
   - [ ] `app/schemas.py` - Request/response models
   - [ ] `app/model.py` - Model wrapper with your actual model logic
   - [ ] `Dockerfile` - Container definition
   - [ ] `requirements.txt` - All dependencies
   - [ ] `README.md` - Documentation

4. **Test locally:**
   ```bash
   # Install dependencies
   pip install -r requirements.txt

   # Run the service
   uvicorn app.main:app --reload --port 8001

   # Test health check
   curl http://localhost:8001/health

   # Test prediction
   curl -X POST http://localhost:8001/predict \
     -H "Content-Type: application/json" \
     -d '{
       "transcript": [
         {"speaker": "interviewer", "content": "Tell me about yourself."},
         {"speaker": "candidate", "content": "I have 5 years of experience in software development..."}
       ]
     }'
   ```

5. **Test Docker build:**
   ```bash
   docker build -t model-service-1:latest .
   docker run -p 8001:8001 model-service-1:latest
   ```

6. **Commit and push:**
   ```bash
   git add .
   git commit -m "Add FastAPI microservice wrapper"
   git push origin main
   ```

### Step 2: Setup Model Service 2

Repeat the exact same process as Step 1, but:
- Use `PROMPT_MODEL_SERVICE_2.txt`
- Test on port 8002
- Tag Docker image as `model-service-2:latest`

---

## Phase 2: Integrate into Main Application

Once both model services are ready, return to the main Talenti application repository.

### Step 3: Add Model Services as Git Submodules

```bash
cd /path/to/Talenti_MVP

# Add model repositories as submodules
git submodule add <model-service-1-repo-url> model-service-1
git submodule add <model-service-2-repo-url> model-service-2

# Initialize and update submodules
git submodule update --init --recursive
```

**Alternative: Clone repositories separately** (if not using submodules)
```bash
cd /path/to/Talenti_MVP

# Clone into the project directory
git clone <model-service-1-repo-url> model-service-1
git clone <model-service-2-repo-url> model-service-2

# Add to .gitignore to avoid nested git repos
echo "model-service-1/" >> .gitignore
echo "model-service-2/" >> .gitignore
```

### Step 4: Update Backend Configuration

The following files have already been created/updated in your main repository:

1. **`docker-compose.yml`** ✅ - Orchestrates all services
2. **`backend/app/services/ml_client.py`** ✅ - ML service client
3. **`backend/app/core/config.py`** ✅ - Added model service URLs

### Step 5: Update Backend Scoring API

You need to update `backend/app/api/scoring.py` to use the ML client. Here's the pattern:

```python
from app.services.ml_client import ml_client

@router.post("/analyze", response_model=ScoringResponse)
async def score_interview(payload: ScoringRequest, ...):
    # Convert transcript to dict format
    transcript_data = [
        {"speaker": seg.speaker, "content": seg.content}
        for seg in payload.transcript
    ]

    # Get predictions from both models
    model1_results, model2_results = await ml_client.get_combined_predictions(
        transcript_data
    )

    # Combine results...
```

### Step 6: Update Environment Variables

Create or update `.env` file in the backend directory:

```env
# Existing variables
DATABASE_URL=sqlite:///./data/app.db
JWT_SECRET=your-secret-key

# Model service URLs (for local development)
MODEL_SERVICE_1_URL=http://localhost:8001
MODEL_SERVICE_2_URL=http://localhost:8002

# For Docker Compose (these are defaults in docker-compose.yml)
# MODEL_SERVICE_1_URL=http://model-service-1:8001
# MODEL_SERVICE_2_URL=http://model-service-2:8002
```

### Step 7: Install ML Client Dependencies

Add to `backend/requirements.txt`:
```txt
httpx==0.26.0  # For async HTTP requests
```

Then install:
```bash
cd backend
pip install -r requirements.txt
```

---

## Phase 3: Testing the Complete System

### Option A: Test with Docker Compose (Recommended)

```bash
# Build all services
docker-compose build

# Start all services
docker-compose up

# In another terminal, test the full pipeline
curl -X POST http://localhost:8000/api/v1/scoring/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "interview_id": "test-123",
    "transcript": [
      {"speaker": "interviewer", "content": "Tell me about your experience."},
      {"speaker": "candidate", "content": "I have 5 years in software development..."}
    ],
    "rubric": {
      "communication": 0.3,
      "technical": 0.4,
      "problem_solving": 0.3
    }
  }'
```

### Option B: Test Locally (Development)

**Terminal 1 - Model Service 1:**
```bash
cd model-service-1
uvicorn app.main:app --reload --port 8001
```

**Terminal 2 - Model Service 2:**
```bash
cd model-service-2
uvicorn app.main:app --reload --port 8002
```

**Terminal 3 - Backend:**
```bash
cd backend
export MODEL_SERVICE_1_URL=http://localhost:8001
export MODEL_SERVICE_2_URL=http://localhost:8002
uvicorn app.main:app --reload --port 8000
```

**Terminal 4 - Test:**
```bash
# Test model service 1
curl http://localhost:8001/health

# Test model service 2
curl http://localhost:8002/health

# Test backend scoring endpoint
curl -X POST http://localhost:8000/api/v1/scoring/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d @test_request.json
```

---

## Phase 4: Deployment

### Production Deployment Options

1. **Docker Compose on VM/Server**
   ```bash
   docker-compose -f docker-compose.yml up -d
   ```

2. **Kubernetes**
   - Convert docker-compose to k8s manifests
   - Deploy as separate services with HPA

3. **Cloud Container Services**
   - AWS ECS/Fargate
   - Azure Container Instances
   - Google Cloud Run

### Scaling Considerations

**Scale Model Services Independently:**
```bash
# Scale model-service-1 to 3 replicas
docker-compose up --scale model-service-1=3

# Or in docker-compose.yml:
services:
  model-service-1:
    deploy:
      replicas: 3
```

**Load Balancing:**
- Use nginx/traefik for load balancing
- Or rely on Docker Compose/K8s built-in load balancing

---

## Troubleshooting

### Model Service Won't Start

```bash
# Check logs
docker-compose logs model-service-1

# Common issues:
# 1. Model files missing - ensure models/ directory has weights
# 2. Out of memory - reduce workers or increase Docker memory
# 3. Port conflicts - check ports 8001, 8002 are available
```

### Backend Can't Connect to Model Services

```bash
# Check network connectivity
docker-compose exec backend ping model-service-1
docker-compose exec backend ping model-service-2

# Check service health
curl http://localhost:8001/health
curl http://localhost:8002/health

# Verify environment variables
docker-compose exec backend env | grep MODEL_SERVICE
```

### Slow Predictions

```bash
# Options:
# 1. Increase model service replicas
# 2. Add caching layer (Redis)
# 3. Implement batching in model services
# 4. Use GPU instances for model services
```

---

## Monitoring

### Health Checks

```bash
# Check all services
curl http://localhost:8000/api/v1/scoring/health

# Response shows status of both model services:
{
  "status": "healthy",
  "ml_services": {
    "model_service_1": true,
    "model_service_2": true
  },
  "all_services_healthy": true
}
```

### Logs

```bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f model-service-1

# View with timestamps
docker-compose logs -tf model-service-1
```

---

## Architecture Diagram

```
┌─────────────┐
│   Frontend  │
│   (React)   │
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────────────────────────┐
│   Backend (FastAPI)             │
│   - /api/v1/scoring/analyze     │
│   - ML Client Service           │
└──────┬──────────────────┬───────┘
       │                  │
       │ HTTP             │ HTTP
       ▼                  ▼
┌──────────────┐   ┌──────────────┐
│ Model Svc 1  │   │ Model Svc 2  │
│ Port: 8001   │   │ Port: 8002   │
│              │   │              │
│ - Soft skills│   │ - Technical  │
│ - Comms      │   │ - Problem    │
│ - Culture    │   │   Solving    │
└──────────────┘   └──────────────┘
```

---

## Next Steps

- [ ] Set up both model services using the prompts
- [ ] Test model services independently
- [ ] Add model repositories to main project
- [ ] Update backend scoring endpoint
- [ ] Test complete integration locally
- [ ] Deploy to staging environment
- [ ] Monitor and optimize performance
- [ ] Set up CI/CD pipelines for model updates

## Support

If you encounter issues:
1. Check the logs: `docker-compose logs [service-name]`
2. Verify health endpoints: `curl http://localhost:800X/health`
3. Test services individually before integration
4. Review the README.md in each model service repository
