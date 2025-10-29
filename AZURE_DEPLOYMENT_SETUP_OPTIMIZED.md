# Azure Deployment Setup - Optimized for Existing Resources

**Date**: 2025-10-29  
**Status**: Ready to Execute  
**Reusing**: Container Registry + Log Analytics Workspace

---

## 🎯 Deployment Overview

This guide uses your existing Azure resources to minimize costs and setup time:

- ✅ **Reuse**: pmactivitiesacr (Container Registry)
- ✅ **Reuse**: activity-tracker-env-law (Log Analytics Workspace)
- 🆕 **Create**: New resources for ChandraHoro in `chandrahoro-prod` resource group

**Estimated Cost**: $85-90/month  
**Setup Time**: ~1.5 hours

---

## 📋 Prerequisites

```bash
# Install Azure CLI
# macOS: brew install azure-cli
# Windows: https://aka.ms/installazurecliwindows
# Linux: curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Verify installation
az --version

# Login to Azure
az login

# Set default subscription
az account set --subscription "YOUR_SUBSCRIPTION_ID"

# Verify login
az account show
```

---

## 🚀 Phase 1: Preparation (5 minutes)

### 1.1 Set Variables

```bash
# Set these variables for all commands
export RESOURCE_GROUP="chandrahoro-prod"
export LOCATION="eastus"
export APP_SERVICE_PLAN="chandrahoro-plan"
export FRONTEND_APP="chandrahoro-frontend"
export BACKEND_APP="chandrahoro-backend"
export MYSQL_SERVER="chandrahoro-mysql"
export MYSQL_DB="chandrahoro"
export STORAGE_ACCOUNT="chandraborostorage"
export KEY_VAULT="chandrahoro-kv"
export CONTAINER_REGISTRY="pmactivitiesacr"  # REUSE existing
export LOG_ANALYTICS="activity-tracker-env-law"  # REUSE existing

# Verify variables
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
```

### 1.2 Create Resource Group

```bash
# Create new resource group for ChandraHoro
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION

# Verify creation
az group show --name $RESOURCE_GROUP
```

---

## 🚀 Phase 2: Create App Service Plan (5 minutes)

```bash
# Create App Service Plan (Linux, B2 tier)
az appservice plan create \
  --name $APP_SERVICE_PLAN \
  --resource-group $RESOURCE_GROUP \
  --sku B2 \
  --is-linux

# Verify creation
az appservice plan show \
  --name $APP_SERVICE_PLAN \
  --resource-group $RESOURCE_GROUP
```

---

## 🚀 Phase 3: Create MySQL Database (10 minutes)

```bash
# Generate secure password
MYSQL_PASSWORD=$(openssl rand -base64 32)
echo "MySQL Password: $MYSQL_PASSWORD"
echo "Save this password securely!"

# Create MySQL Server
az mysql flexible-server create \
  --resource-group $RESOURCE_GROUP \
  --name $MYSQL_SERVER \
  --location $LOCATION \
  --admin-user azureuser \
  --admin-password $MYSQL_PASSWORD \
  --sku-name Standard_B1s \
  --tier Burstable \
  --storage-size 20 \
  --version 8.0 \
  --high-availability Disabled \
  --backup-retention 7

# Create database
az mysql flexible-server db create \
  --resource-group $RESOURCE_GROUP \
  --server-name $MYSQL_SERVER \
  --database-name $MYSQL_DB

# Configure firewall to allow Azure services
az mysql flexible-server firewall-rule create \
  --resource-group $RESOURCE_GROUP \
  --name $MYSQL_SERVER \
  --rule-name "AllowAzureServices" \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0

# Get connection string
MYSQL_CONNECTION_STRING=$(az mysql flexible-server show-connection-string \
  --server-name $MYSQL_SERVER \
  --admin-user azureuser \
  --admin-password $MYSQL_PASSWORD \
  --database-name $MYSQL_DB \
  --query connectionStrings.mysql_cmd_line \
  --output tsv)

echo "MySQL Connection String: $MYSQL_CONNECTION_STRING"
```

---

## 🚀 Phase 4: Create Storage Account (5 minutes)

```bash
# Create Storage Account
az storage account create \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS \
  --kind StorageV2

# Get storage account key
STORAGE_KEY=$(az storage account keys list \
  --account-name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --query "[0].value" \
  --output tsv)

echo "Storage Account Key: $STORAGE_KEY"
```

---

## 🚀 Phase 5: Create Key Vault (5 minutes)

```bash
# Create Key Vault
az keyvault create \
  --name $KEY_VAULT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --enable-soft-delete true \
  --purge-protection false

# Add secrets to Key Vault
az keyvault secret set \
  --vault-name $KEY_VAULT \
  --name "DATABASE-URL" \
  --value "mysql://azureuser:$MYSQL_PASSWORD@$MYSQL_SERVER.mysql.database.azure.com:3306/$MYSQL_DB?ssl=true"

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
  --value "sk-ant-YOUR_ACTUAL_KEY_HERE"

# Verify secrets
az keyvault secret list --vault-name $KEY_VAULT
```

---

## 🚀 Phase 6: Create Frontend App Service (10 minutes)

```bash
# Create Frontend App Service
az webapp create \
  --name $FRONTEND_APP \
  --resource-group $RESOURCE_GROUP \
  --plan $APP_SERVICE_PLAN \
  --runtime "NODE|18-lts"

# Configure environment variables
az webapp config appsettings set \
  --name $FRONTEND_APP \
  --resource-group $RESOURCE_GROUP \
  --settings \
    NEXT_PUBLIC_APP_URL="https://$FRONTEND_APP.azurewebsites.net" \
    NEXT_PUBLIC_API_URL="https://$BACKEND_APP.azurewebsites.net" \
    NEXTAUTH_URL="https://$FRONTEND_APP.azurewebsites.net" \
    NODE_ENV="production"

# Enable continuous deployment from container registry
az webapp deployment container config \
  --name $FRONTEND_APP \
  --resource-group $RESOURCE_GROUP \
  --enable-cd true

# Set container image
az webapp config container set \
  --name $FRONTEND_APP \
  --resource-group $RESOURCE_GROUP \
  --docker-custom-image-name "$CONTAINER_REGISTRY.azurecr.io/chandrahoro-frontend:latest" \
  --docker-registry-server-url "https://$CONTAINER_REGISTRY.azurecr.io" \
  --docker-registry-server-user "YOUR_REGISTRY_USERNAME" \
  --docker-registry-server-password "YOUR_REGISTRY_PASSWORD"
```

---

## 🚀 Phase 7: Create Backend App Service (10 minutes)

```bash
# Create Backend App Service
az webapp create \
  --name $BACKEND_APP \
  --resource-group $RESOURCE_GROUP \
  --plan $APP_SERVICE_PLAN \
  --runtime "PYTHON|3.11"

# Configure environment variables
az webapp config appsettings set \
  --name $BACKEND_APP \
  --resource-group $RESOURCE_GROUP \
  --settings \
    ENVIRONMENT="production" \
    DATABASE_URL="mysql://azureuser:$MYSQL_PASSWORD@$MYSQL_SERVER.mysql.database.azure.com:3306/$MYSQL_DB?ssl=true" \
    NEXTAUTH_URL="https://$FRONTEND_APP.azurewebsites.net" \
    ANTHROPIC_API_KEY="sk-ant-YOUR_ACTUAL_KEY_HERE" \
    CORS_ORIGINS="https://$FRONTEND_APP.azurewebsites.net"

# Enable continuous deployment
az webapp deployment container config \
  --name $BACKEND_APP \
  --resource-group $RESOURCE_GROUP \
  --enable-cd true

# Set container image
az webapp config container set \
  --name $BACKEND_APP \
  --resource-group $RESOURCE_GROUP \
  --docker-custom-image-name "$CONTAINER_REGISTRY.azurecr.io/chandrahoro-backend:latest" \
  --docker-registry-server-url "https://$CONTAINER_REGISTRY.azurecr.io" \
  --docker-registry-server-user "YOUR_REGISTRY_USERNAME" \
  --docker-registry-server-password "YOUR_REGISTRY_PASSWORD"
```

---

## 🚀 Phase 8: Configure Application Insights (5 minutes)

```bash
# Get Log Analytics Workspace ID
LOG_ANALYTICS_ID=$(az monitor log-analytics workspace show \
  --resource-group activity-tracker-rg \
  --workspace-name activity-tracker-env-law \
  --query id \
  --output tsv)

# Create Application Insights (linked to existing Log Analytics)
az monitor app-insights component create \
  --app chandrahoro-insights \
  --location $LOCATION \
  --resource-group $RESOURCE_GROUP \
  --application-type web \
  --workspace $LOG_ANALYTICS_ID

# Get instrumentation key
INSTRUMENTATION_KEY=$(az monitor app-insights component show \
  --app chandrahoro-insights \
  --resource-group $RESOURCE_GROUP \
  --query instrumentationKey \
  --output tsv)

echo "Instrumentation Key: $INSTRUMENTATION_KEY"

# Add to App Services
az webapp config appsettings set \
  --name $FRONTEND_APP \
  --resource-group $RESOURCE_GROUP \
  --settings APPINSIGHTS_INSTRUMENTATIONKEY=$INSTRUMENTATION_KEY

az webapp config appsettings set \
  --name $BACKEND_APP \
  --resource-group $RESOURCE_GROUP \
  --settings APPINSIGHTS_INSTRUMENTATIONKEY=$INSTRUMENTATION_KEY
```

---

## ✅ Verification Checklist

```bash
# Verify all resources created
echo "=== Resource Group ==="
az group show --name $RESOURCE_GROUP

echo "=== App Service Plan ==="
az appservice plan show --name $APP_SERVICE_PLAN --resource-group $RESOURCE_GROUP

echo "=== MySQL Server ==="
az mysql flexible-server show --name $MYSQL_SERVER --resource-group $RESOURCE_GROUP

echo "=== Frontend App Service ==="
az webapp show --name $FRONTEND_APP --resource-group $RESOURCE_GROUP

echo "=== Backend App Service ==="
az webapp show --name $BACKEND_APP --resource-group $RESOURCE_GROUP

echo "=== Storage Account ==="
az storage account show --name $STORAGE_ACCOUNT --resource-group $RESOURCE_GROUP

echo "=== Key Vault ==="
az keyvault show --name $KEY_VAULT --resource-group $RESOURCE_GROUP

echo "=== Application Insights ==="
az monitor app-insights component show --app chandrahoro-insights --resource-group $RESOURCE_GROUP
```

---

## 🎉 Next Steps

1. ✅ **GitHub Setup** (GITHUB_SETUP_GUIDE.md)
2. ✅ **Azure Resources Created** (this guide)
3. ⏳ **Push Docker Images** (see DEPLOYMENT_CHECKLIST.md)
4. ⏳ **Run Database Migrations** (see DEPLOYMENT_CHECKLIST.md)
5. ⏳ **Test Deployment** (see DEPLOYMENT_CHECKLIST.md)

---

**Status**: ✅ Ready to Execute  
**Estimated Time**: 1.5 hours  
**Cost**: $85-90/month

