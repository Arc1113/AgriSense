param(
  [Parameter(Mandatory=$false)] [string]$SubscriptionId = "",
  [Parameter(Mandatory=$false)] [string]$ResourceGroup = "agrisense-rg",
  [Parameter(Mandatory=$false)] [string]$Location = "eastus",
  [Parameter(Mandatory=$false)] [string]$AcrName = "",
  [Parameter(Mandatory=$false)] [string]$AppServicePlan = "agrisense-plan",
  [Parameter(Mandatory=$false)] [string]$WebAppName = "",
  [Parameter(Mandatory=$false)] [string]$ImageName = "agrisense-rag",
  [Parameter(Mandatory=$false)] [string]$ImageTag = "latest",
  [Parameter(Mandatory=$false)] [string]$GroqApiKey = "",
  [Parameter(Mandatory=$false)] [string]$StorageAccountName = "",
  [Parameter(Mandatory=$false)] [string]$FileShareName = "vector-store",
  [Parameter(Mandatory=$false)] [switch]$SkipStorageMount
)

$ErrorActionPreference = 'Stop'

function Write-Step($msg) {
  Write-Host "`n==> $msg" -ForegroundColor Cyan
}

function Ensure-AzCli {
  if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw "Azure CLI ('az') not found. Install Azure CLI first: https://aka.ms/installazurecliwindows"
  }
}

function Ensure-LoggedIn {
  try {
    $null = az account show --output none
  } catch {
    Write-Step "Azure login required"
    az login | Out-Null
  }
}

function New-RandomSuffix {
  -join ((97..122) + (48..57) | Get-Random -Count 6 | ForEach-Object {[char]$_})
}

Ensure-AzCli
Ensure-LoggedIn

if ([string]::IsNullOrWhiteSpace($GroqApiKey)) {
  $GroqApiKey = $env:GROQ_API_KEY
}

if ([string]::IsNullOrWhiteSpace($GroqApiKey)) {
  $envFile = Join-Path $PSScriptRoot ".env"
  if (Test-Path $envFile) {
    $line = Get-Content $envFile | Where-Object { $_ -match '^\s*GROQ_API_KEY\s*=' } | Select-Object -First 1
    if ($line) {
      $GroqApiKey = ($line -split '=', 2)[1].Trim().Trim('"').Trim("'")
    }
  }
}

if ([string]::IsNullOrWhiteSpace($GroqApiKey) -or $GroqApiKey -eq "your_groq_api_key_here") {
  throw "GROQ_API_KEY is required. Pass -GroqApiKey, set env var GROQ_API_KEY, or define GROQ_API_KEY in backend/.env"
}

if ($SubscriptionId -ne "") {
  Write-Step "Setting subscription"
  az account set --subscription $SubscriptionId
}

$subId = az account show --query id -o tsv
if ([string]::IsNullOrWhiteSpace($subId)) {
  throw "Could not resolve Azure subscription ID."
}

if ([string]::IsNullOrWhiteSpace($AcrName)) {
  $AcrName = ("agrisenseacr" + (New-RandomSuffix)).ToLower()
}

if ([string]::IsNullOrWhiteSpace($WebAppName)) {
  $WebAppName = ("agrisense-api-" + (New-RandomSuffix)).ToLower()
}

if ([string]::IsNullOrWhiteSpace($StorageAccountName)) {
  $StorageAccountName = (("agrisensest" + (New-RandomSuffix)) -replace '[^a-z0-9]','').ToLower()
}
if ($StorageAccountName.Length -gt 24) {
  $StorageAccountName = $StorageAccountName.Substring(0,24)
}

Write-Step "Using values"
Write-Host "Subscription:      $subId"
Write-Host "Resource Group:    $ResourceGroup"
Write-Host "Location:          $Location"
Write-Host "ACR:               $AcrName"
Write-Host "App Service Plan:  $AppServicePlan"
Write-Host "Web App:           $WebAppName"
Write-Host "Image:             ${ImageName}:$ImageTag"
Write-Host "Storage Account:   $StorageAccountName"
Write-Host "File Share:        $FileShareName"

Write-Step "Creating resource group"
az group create --name $ResourceGroup --location $Location --output none

Write-Step "Creating Azure Container Registry"
az acr create --resource-group $ResourceGroup --name $AcrName --sku Basic --admin-enabled true --output none
$acrLoginServer = az acr show --name $AcrName --resource-group $ResourceGroup --query loginServer -o tsv

Write-Step "Building and pushing backend deploy image to ACR"
# Run from backend folder: context is current folder, Dockerfile.deploy is here
az acr build --registry $AcrName --image "${ImageName}:$ImageTag" --file Dockerfile.deploy .

Write-Step "Creating Linux App Service plan"
az appservice plan create --name $AppServicePlan --resource-group $ResourceGroup --is-linux --sku B2 --output none

Write-Step "Creating Web App"
az webapp create --resource-group $ResourceGroup --plan $AppServicePlan --name $WebAppName --deployment-container-image-name "$acrLoginServer/${ImageName}:$ImageTag" --output none

Write-Step "Configuring container registry credentials"
$acrUser = az acr credential show --name $AcrName --query username -o tsv
$acrPass = az acr credential show --name $AcrName --query passwords[0].value -o tsv
az webapp config container set `
  --resource-group $ResourceGroup `
  --name $WebAppName `
  --container-image-name "$acrLoginServer/${ImageName}:$ImageTag" `
  --container-registry-url "https://$acrLoginServer" `
  --container-registry-user $acrUser `
  --container-registry-password $acrPass `
  --output none

Write-Step "Applying required app settings"
az webapp config appsettings set `
  --resource-group $ResourceGroup `
  --name $WebAppName `
  --settings `
    WEBSITES_PORT=8000 `
    DEPLOY_MODE=rag_only `
    PYTHONUNBUFFERED=1 `
    RAG_ENABLE_RERANKING=false `
    RAG_EMBEDDINGS_PROVIDER=fastembed `
    RAG_FASTEMBED_MODEL=BAAI/bge-small-en-v1.5 `
    GROQ_API_KEY=$GroqApiKey `
  --output none

if (-not $SkipStorageMount) {
  Write-Step "Creating storage account and file share for persistent vector_store"
  az storage account create --name $StorageAccountName --resource-group $ResourceGroup --location $Location --sku Standard_LRS --kind StorageV2 --output none

  $storageKey = az storage account keys list --resource-group $ResourceGroup --account-name $StorageAccountName --query [0].value -o tsv

  az storage share-rm create --resource-group $ResourceGroup --storage-account $StorageAccountName --name $FileShareName --quota 10 --enabled-protocols SMB --output none

  Write-Step "Mounting Azure File share to /app/vector_store"
  az webapp config storage-account add `
    --resource-group $ResourceGroup `
    --name $WebAppName `
    --custom-id vectorstore `
    --storage-type AzureFiles `
    --account-name $StorageAccountName `
    --share-name $FileShareName `
    --access-key $storageKey `
    --mount-path /app/vector_store `
    --output none
}

Write-Step "Restarting web app"
az webapp restart --resource-group $ResourceGroup --name $WebAppName --output none

$appUrl = "https://$WebAppName.azurewebsites.net"

Write-Step "Deployment complete"
Write-Host "Backend URL: $appUrl" -ForegroundColor Green
Write-Host "Health URL:  $appUrl/health" -ForegroundColor Green
Write-Host "Docs URL:    $appUrl/docs" -ForegroundColor Green

Write-Host "`nNext: build Flutter with:" -ForegroundColor Yellow
Write-Host "flutter run --release --dart-define=API_BASE_URL=$appUrl --dart-define=ENABLE_ROBOTICS=false" -ForegroundColor Yellow
