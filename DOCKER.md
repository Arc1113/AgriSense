# AgriSense - AI Plant Disease Detection

Modern PWA for plant disease detection using deep learning.

## 🚀 Quick Start with Docker

### Prerequisites
- Docker Desktop installed
- Docker Compose installed

### Running Locally

1. **Build and start all services:**
   ```bash
   docker-compose up --build
   ```

2. **Access the application:**
   - Frontend: http://localhost
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

3. **Stop the services:**
   ```bash
   docker-compose down
   ```

## 📦 Docker Commands

### Build images
```bash
docker-compose build
```

### Start services
```bash
docker-compose up -d
```

### View logs
```bash
docker-compose logs -f
```

### Stop services
```bash
docker-compose stop
```

### Remove containers
```bash
docker-compose down -v
```

## ☁️ Azure Deployment

### Option 1: Azure Container Instances (ACI)

1. **Build and push images to Azure Container Registry:**
   ```bash
   # Login to Azure
   az login
   
   # Create resource group
   az group create --name agrisense-rg --location eastus
   
   # Create container registry
   az acr create --resource-group agrisense-rg --name agrisenseacr --sku Basic
   
   # Login to ACR
   az acr login --name agrisenseacr
   
   # Tag images
   docker tag agrisense-backend agrisenseacr.azurecr.io/agrisense-backend:latest
   docker tag agrisense-frontend agrisenseacr.azurecr.io/agrisense-frontend:latest
   
   # Push images
   docker push agrisenseacr.azurecr.io/agrisense-backend:latest
   docker push agrisenseacr.azurecr.io/agrisense-frontend:latest
   ```

2. **Deploy to ACI:**
   ```bash
   # Deploy backend
   az container create \
     --resource-group agrisense-rg \
     --name agrisense-backend \
     --image agrisenseacr.azurecr.io/agrisense-backend:latest \
     --registry-login-server agrisenseacr.azurecr.io \
     --registry-username <username> \
     --registry-password <password> \
     --dns-name-label agrisense-api \
     --ports 8000
   
   # Deploy frontend
   az container create \
     --resource-group agrisense-rg \
     --name agrisense-frontend \
     --image agrisenseacr.azurecr.io/agrisense-frontend:latest \
     --registry-login-server agrisenseacr.azurecr.io \
     --registry-username <username> \
     --registry-password <password> \
     --dns-name-label agrisense-app \
     --ports 80
   ```

### Option 2: Azure App Service (Recommended)

1. **Create App Service Plan:**
   ```bash
   az appservice plan create \
     --name agrisense-plan \
     --resource-group agrisense-rg \
     --is-linux \
     --sku B1
   ```

2. **Create Web Apps:**
   ```bash
   # Backend
   az webapp create \
     --resource-group agrisense-rg \
     --plan agrisense-plan \
     --name agrisense-api \
     --deployment-container-image-name agrisenseacr.azurecr.io/agrisense-backend:latest
   
   # Frontend
   az webapp create \
     --resource-group agrisense-rg \
     --plan agrisense-plan \
     --name agrisense-app \
     --deployment-container-image-name agrisenseacr.azurecr.io/agrisense-frontend:latest
   ```

### Option 3: Azure Kubernetes Service (AKS) - For Production Scale

1. **Create AKS cluster:**
   ```bash
   az aks create \
     --resource-group agrisense-rg \
     --name agrisense-cluster \
     --node-count 2 \
     --enable-addons monitoring \
     --generate-ssh-keys
   
   az aks get-credentials --resource-group agrisense-rg --name agrisense-cluster
   ```

2. **Deploy using kubectl:**
   ```bash
   kubectl apply -f kubernetes/
   ```

## 🏗️ Project Structure

```
AgriSense/
├── backend/
│   ├── Dockerfile
│   ├── main.py
│   ├── requirements.txt
│   └── models/
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   └── src/
└── docker-compose.yml
```

## 🔧 Environment Variables

### Backend
- `PORT`: API port (default: 8000)
- `PYTHONUNBUFFERED`: Python output buffering

### Frontend
- `VITE_API_URL`: Backend API URL for production

## 📊 Health Checks

- Frontend: `http://localhost/health`
- Backend: `http://localhost:8000/health`

## 🔒 Security Notes

For production deployment:
1. Enable HTTPS/SSL
2. Configure CORS properly
3. Use Azure Key Vault for secrets
4. Enable Azure AD authentication
5. Configure network security groups

## 📝 License

MIT License - see LICENSE file for details
