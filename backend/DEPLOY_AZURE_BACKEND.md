# Deploy Backend to Azure App Service (Container)

This deploys the RAG-only backend container and gives you an HTTPS URL for the Flutter app.

## Prerequisites
- Azure CLI installed (`az`)
- Logged in: `az login`
- PowerShell
- A valid `GROQ_API_KEY`

## One-command deploy
Run from `backend/`:

```powershell
./deploy_azure_backend.ps1 -GroqApiKey "<YOUR_GROQ_API_KEY>"
```

Optional flags:

```powershell
./deploy_azure_backend.ps1 \
  -SubscriptionId "<sub-id>" \
  -ResourceGroup "agrisense-rg" \
  -Location "eastus" \
  -AcrName "agrisenseacr123" \
  -WebAppName "agrisense-api-123" \
  -GroqApiKey "<YOUR_GROQ_API_KEY>"
```

## What the script configures
- Resource Group
- Azure Container Registry (ACR)
- ACR build of `Dockerfile.deploy`
- Linux App Service Plan + Web App
- Container image binding to ACR
- App settings:
  - `WEBSITES_PORT=8000`
  - `DEPLOY_MODE=rag_only`
  - `PYTHONUNBUFFERED=1`
  - `RAG_ENABLE_RERANKING=false`
  - `RAG_EMBEDDINGS_PROVIDER=fastembed`
  - `RAG_FASTEMBED_MODEL=BAAI/bge-small-en-v1.5`
  - `GROQ_API_KEY=...`
- Azure Files mount to `/app/vector_store` for persistence

## Verify backend
After deploy:

- `https://<webapp-name>.azurewebsites.net/health`
- `https://<webapp-name>.azurewebsites.net/docs`

## Connect Flutter mobile app
Use the deployed backend URL at build/run time:

```bash
flutter run --release \
  --dart-define=API_BASE_URL=https://<webapp-name>.azurewebsites.net \
  --dart-define=ENABLE_ROBOTICS=false
```

Or for Android app bundle:

```bash
flutter build appbundle \
  --dart-define=API_BASE_URL=https://<webapp-name>.azurewebsites.net \
  --dart-define=ENABLE_ROBOTICS=false
```

## API contract reminder
Your mobile app sends disease + confidence to:
- `POST /predict`
- `GET /health`

## Troubleshooting
- If app is slow on first start: model/runtime caches warm up on first requests.
- If `/health` fails after deploy: check App Service logs and verify `GROQ_API_KEY` is set.
- If vector retrieval is empty after restart: ensure storage mount exists at `/app/vector_store`.

## GitHub Actions (RAG-Agent-Only)

This repo includes automated deployment for the **RAG-only backend** (small image) via:

- [.github/workflows/rag-agent-deploy.yml](../.github/workflows/rag-agent-deploy.yml)

### Scope

- Builds only `backend/Dockerfile.deploy`
- Deploys only the existing Azure Web App container for RAG agent
- Does **not** deploy full ML/robotics backend stack

### Required GitHub Secrets (Environment: `production`)

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `GROQ_API_KEY`

### Required GitHub Variables (Environment: `production`)

- `AZURE_RESOURCE_GROUP` (e.g., `agrisense-rg`)
- `AZURE_WEBAPP_NAME` (e.g., `agrisense-api-jytid2`)
- `AZURE_ACR_NAME` (e.g., `agrisenseacrwxqtcm`)
- `IMAGE_NAME` (e.g., `agrisense-rag`)

### Trigger behavior

- Auto deploy on push to `main` when RAG-backend files change
- Manual deploy/rollback via `workflow_dispatch`
- Image tags: `${{ github.sha }}` and `latest`
