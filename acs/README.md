# Talenti ACS Service

Python FastAPI service for Azure Communication Services (ACS) call automation and recording management.

## Features

- **Call Management**: Create, answer, and manage VoIP calls
- **Recording**: Start, pause, resume, and stop call recordings
- **Storage Integration**: Automatic upload to Azure Blob Storage
- **Supabase Sync**: Keep interview records updated

## Prerequisites

- Python 3.11+
- Azure Communication Services resource
- Azure Blob Storage account
- Supabase project

## Quick Start

### Local Development

1. **Clone and setup**:
   ```bash
   cd python-acs-service
   cp .env.example .env
   # Edit .env with your credentials
   ```

2. **Install dependencies**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Run the service**:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

4. **Access API docs**:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Docker

```bash
docker-compose up --build
```

## API Endpoints

### Health
- `GET /health` - Health check
- `GET /health/ready` - Readiness check
- `GET /health/live` - Liveness probe

### Calls
- `POST /api/calls/create` - Create outbound call
- `GET /api/calls/{call_connection_id}` - Get call info
- `POST /api/calls/{call_connection_id}/answer` - Answer call
- `POST /api/calls/{call_connection_id}/hangup` - End call
- `POST /api/calls/{call_connection_id}/play` - Play audio/TTS
- `POST /api/calls/{call_connection_id}/participants` - Add participant
- `DELETE /api/calls/{call_connection_id}/participants/{id}` - Remove participant

### Recordings
- `POST /api/recordings/start` - Start recording
- `POST /api/recordings/{recording_id}/pause` - Pause recording
- `POST /api/recordings/{recording_id}/resume` - Resume recording
- `POST /api/recordings/{recording_id}/stop` - Stop recording
- `GET /api/recordings/{recording_id}` - Get recording info
- `GET /api/recordings/{recording_id}/download` - Download recording
- `DELETE /api/recordings/{recording_id}` - Delete recording

## Azure Container Apps Deployment

1. **Build and push image**:
   ```bash
   az acr build --registry <your-acr> --image talenti-acs-service:latest .
   ```

2. **Deploy to Container Apps**:
   ```bash
   az containerapp create \
     --name talenti-acs-service \
     --resource-group <your-rg> \
     --environment <your-env> \
     --image <your-acr>.azurecr.io/talenti-acs-service:latest \
     --target-port 8000 \
     --ingress external \
     --min-replicas 1 \
     --max-replicas 10 \
     --secrets acs-conn-string=<your-acs-connection-string> \
     --env-vars ACS_CONNECTION_STRING=secretref:acs-conn-string
   ```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ACS_CONNECTION_STRING` | ACS connection string | Yes |
| `ACS_ENDPOINT` | ACS endpoint URL | Yes |
| `ACS_CALLBACK_URL` | Webhook callback URL | Yes |
| `AZURE_STORAGE_CONNECTION_STRING` | Blob storage connection | Yes |
| `SUPABASE_URL` | Supabase project URL | Yes |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | Yes |
| `LOG_LEVEL` | Logging level (INFO, DEBUG) | No |

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│  Lovable Edge   │────▶│  ACS Service     │────▶│  Azure ACS  │
│  Functions      │     │  (This Service)  │     │             │
└─────────────────┘     └──────────────────┘     └─────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │  Azure Blob      │
                        │  Storage         │
                        └──────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │  Supabase        │
                        │  (interviews)    │
                        └──────────────────┘
```

## License

Proprietary - Talenti
