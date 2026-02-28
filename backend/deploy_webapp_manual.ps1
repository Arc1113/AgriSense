$ErrorActionPreference = 'Stop'

$rg = 'agrisense-rg'
$app = 'agrisense-api-jytid2'
$plan = 'agrisense-plan'
$acr = 'agrisenseacrwxqtcm'
$acrServer = 'agrisenseacrwxqtcm.azurecr.io'
$image = "$acrServer/agrisense-rag:latest"
$storage = 'agrisensestw2i30z'
$share = 'vector-store'
$location = 'southeastasia'

az webapp create --resource-group $rg --plan $plan --name $app --deployment-container-image-name $image --output none

$acrUser = az acr credential show --name $acr --query username -o tsv
$acrPass = az acr credential show --name $acr --query passwords[0].value -o tsv

az webapp config container set `
  --resource-group $rg `
  --name $app `
  --container-image-name $image `
  --container-registry-url ("https://" + $acrServer) `
  --container-registry-user $acrUser `
  --container-registry-password $acrPass `
  --output none

$envFile = 'c:\AgriSense-clean\backend\.env'
if (!(Test-Path $envFile)) { throw '.env not found for GROQ_API_KEY' }

$line = Get-Content $envFile | Where-Object { $_ -match '^\s*GROQ_API_KEY\s*=' } | Select-Object -First 1
if (-not $line) { throw 'GROQ_API_KEY not found in backend/.env' }

$groq = ($line -split '=', 2)[1].Trim().Trim('"').Trim("'")
if ([string]::IsNullOrWhiteSpace($groq) -or $groq -eq 'your_groq_api_key_here') {
  throw 'GROQ_API_KEY in .env is empty/placeholder'
}

az webapp config appsettings set `
  --resource-group $rg `
  --name $app `
  --settings `
    WEBSITES_PORT=8000 `
    DEPLOY_MODE=rag_only `
    PYTHONUNBUFFERED=1 `
    RAG_ENABLE_RERANKING=false `
    RAG_EMBEDDINGS_PROVIDER=fastembed `
    RAG_FASTEMBED_MODEL=BAAI/bge-small-en-v1.5 `
    GROQ_API_KEY=$groq `
  --output none

az storage account create --name $storage --resource-group $rg --location $location --sku Standard_LRS --kind StorageV2 --output none
$storageKey = az storage account keys list --resource-group $rg --account-name $storage --query [0].value -o tsv
az storage share-rm create --resource-group $rg --storage-account $storage --name $share --quota 10 --enabled-protocols SMB --output none

az webapp config storage-account add `
  --resource-group $rg `
  --name $app `
  --custom-id vectorstore `
  --storage-type AzureFiles `
  --account-name $storage `
  --share-name $share `
  --access-key $storageKey `
  --mount-path /app/vector_store `
  --output none

az webapp restart --resource-group $rg --name $app --output none

Write-Output "DEPLOYED_URL=https://$app.azurewebsites.net"