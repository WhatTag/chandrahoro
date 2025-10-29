# Azure Deployment Setup - ChandraHoro V2.1

## Prerequisites

```bash
# Install Azure CLI
# macOS
brew install azure-cli

# Verify installation
az --version

# Login to Azure
az login

# Set default subscription
az account set --subscription "YOUR_SUBSCRIPTION_ID"
```

## Step 1: Create Resource Group

```bash
# Variables
RESOURCE_GROUP="chandrahoro-prod"
LOCATION="eastus"  # or your preferred region

# Create resource group
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION

# Verify
az group show --name $RESOURCE_GROUP
```

## Step 2: Create App Service Plan

```bash
# Variables
APP_SERVICE_PLAN="chandrahoro-plan"
SKU="B2"  # B2 = 1.75 GB RAM, 2 cores (~$50/month)

# Create App Service Plan (Linux)
az appservice plan create \
  --name $APP_SERVICE_PLAN \
  --resource-group $RESOURCE_GROUP \
  --sku $SKU \
  --is-linux

# Verify
az appservice plan show \
  --name $APP_SERVICE_PLAN \
  --resource-group $RESOURCE_GROUP
```

## Step 3: Create Azure Database for MySQL

```bash
# Variables
DB_SERVER="chandrahoro-mysql"
DB_ADMIN="azureuser"
DB_PASSWORD="YourSecurePassword123!"  # Change this!
DB_NAME="chandrahoro"

# Create MySQL server
az mysql server create \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER \
  --location $LOCATION \
  --admin-user $DB_ADMIN \
  --admin-password $DB_PASSWORD \
  --sku-name B_Gen5_1 \
  --storage-size 51200 \
  --version 8.0 \
  --ssl-enforcement ENABLED

# Create database
az mysql db create \
  --resource-group $RESOURCE_GROUP \
  --server-name $DB_SERVER \
  --name $DB_NAME

# Configure firewall (allow Azure services)
az mysql server firewall-rule create \
  --resource-group $RESOURCE_GROUP \
  --server-name $DB_SERVER \
  --name "AllowAzureServices" \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0

# Get connection string
CONNECTION_STRING="mysql://${DB_ADMIN}:${DB_PASSWORD}@${DB_SERVER}.mysql.database.azure.com:3306/${DB_NAME}?ssl=true"
echo "DATABASE_URL=$CONNECTION_STRING"
```

## Step 4: Create Storage Account

```bash
# Variables
STORAGE_ACCOUNT="chandrahorostorage"  # Must be globally unique

# Create storage account
az storage account create \
  --resource-group $RESOURCE_GROUP \
  --name $STORAGE_ACCOUNT \
  --location $LOCATION \
  --sku Standard_LRS \
  --kind StorageV2

# Get connection string
STORAGE_CONNECTION=$(az storage account show-connection-string \
  --resource-group $RESOURCE_GROUP \
  --name $STORAGE_ACCOUNT \
  --query connectionString -o tsv)

echo "STORAGE_CONNECTION_STRING=$STORAGE_CONNECTION"
```

## Step 5: Create Key Vault

```bash
# Variables
KEY_VAULT="chandrahoro-vault"

# Create Key Vault
az keyvault create \
  --resource-group $RESOURCE_GROUP \
  --name $KEY_VAULT \
  --location $LOCATION \
  --enable-soft-delete true \
  --purge-protection false

# Add secrets
az keyvault secret set \
  --vault-name $KEY_VAULT \
  --name "NEXTAUTH-SECRET" \
  --value "$(openssl rand -base64 32)"

az keyvault secret set \
  --vault-name $KEY_VAULT \
  --name "JWT-SECRET" \
  --value "$(openssl rand -base64 32)"

az keyvault secret set \
  --vault-name $KEY_VAULT \
  --name "ANTHROPIC-API-KEY" \
  --value "YOUR_ANTHROPIC_KEY"

az keyvault secret set \
  --vault-name $KEY_VAULT \
  --name "DATABASE-URL" \
  --value "$CONNECTION_STRING"
```

## Step 6: Create Frontend App Service

```bash
# Variables
FRONTEND_APP="chandrahoro-frontend"

# Create App Service
az webapp create \
  --resource-group $RESOURCE_GROUP \
  --plan $APP_SERVICE_PLAN \
  --name $FRONTEND_APP \
  --runtime "NODE|18-lts"

# Configure deployment from GitHub
az webapp deployment source config-zip \
  --resource-group $RESOURCE_GROUP \
  --name $FRONTEND_APP \
  --src frontend.zip

# Set environment variables
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $FRONTEND_APP \
  --settings \
    NEXT_PUBLIC_APP_URL="https://${FRONTEND_APP}.azurewebsites.net" \
    NEXT_PUBLIC_API_URL="https://${BACKEND_APP}.azurewebsites.net" \
    NODE_ENV="production" \
    NEXTAUTH_URL="https://${FRONTEND_APP}.azurewebsites.net"
```

## Step 7: Create Backend App Service

```bash
# Variables
BACKEND_APP="chandrahoro-backend"

# Create App Service
az webapp create \
  --resource-group $RESOURCE_GROUP \
  --plan $APP_SERVICE_PLAN \
  --name $BACKEND_APP \
  --runtime "PYTHON|3.11"

# Set environment variables
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_APP \
  --settings \
    DATABASE_URL="$CONNECTION_STRING" \
    ANTHROPIC_API_KEY="YOUR_KEY" \
    ENVIRONMENT="production"
```

## Step 8: Configure Custom Domain (Optional)

```bash
# Add custom domain
az webapp config hostname add \
  --resource-group $RESOURCE_GROUP \
  --webapp-name $FRONTEND_APP \
  --hostname "yourdomain.com"

# Create SSL certificate
az appservice certificate create \
  --resource-group $RESOURCE_GROUP \
  --name "chandrahoro-cert" \
  --host-name "yourdomain.com"
```

## Monitoring & Logging

```bash
# Enable Application Insights
az monitor app-insights component create \
  --app chandrahoro-insights \
  --location $LOCATION \
  --resource-group $RESOURCE_GROUP \
  --application-type web

# View logs
az webapp log tail \
  --resource-group $RESOURCE_GROUP \
  --name $FRONTEND_APP

# View metrics
az monitor metrics list \
  --resource $FRONTEND_APP \
  --resource-group $RESOURCE_GROUP
```

## Cleanup (if needed)

```bash
# Delete entire resource group
az group delete \
  --name $RESOURCE_GROUP \
  --yes --no-wait
```

## Next Steps

1. Update environment variables in Key Vault
2. Deploy frontend and backend code
3. Run database migrations
4. Configure custom domain and SSL
5. Set up monitoring and alerts

