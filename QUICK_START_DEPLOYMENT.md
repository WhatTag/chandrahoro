# ChandraHoro Deployment Guide - Multiple Options

## 🚀 Deployment Options

Choose your preferred deployment platform:

### Option 1: Azure (Recommended for Full Control) ⭐
- **Cost**: ~$90-105/month
- **Setup Time**: 2-3 hours
- **Best For**: Production, full control, enterprise
- **See**: `AZURE_DEPLOYMENT_SETUP.md`

### Option 2: Vercel + Railway (Recommended for Simplicity)
- **Cost**: Free tier available, $20-50/month for production
- **Setup Time**: 30 minutes
- **Best For**: Quick deployment, minimal configuration
- **See**: Section below

### Option 3: Docker + Any Cloud Provider
- **Cost**: Varies
- **Setup Time**: 1-2 hours
- **Best For**: Flexibility, multi-cloud
- **See**: `docker-compose.yml`

---

## 🚀 Option 1: Azure Deployment (Recommended)

### Prerequisites
- Azure subscription (active)
- Azure CLI installed (`brew install azure-cli`)
- GitHub account with chandrahoro repository
- API keys (Anthropic, Google Maps, etc.)

### Quick Start (5 minutes)

```bash
# 1. Login to Azure
az login

# 2. Create resource group
az group create --name chandrahoro-prod --location eastus

# 3. Create App Service Plan
az appservice plan create \
  --name chandrahoro-plan \
  --resource-group chandrahoro-prod \
  --sku B2 \
  --is-linux

# 4. Create MySQL database
az mysql server create \
  --resource-group chandrahoro-prod \
  --name chandrahoro-mysql \
  --location eastus \
  --admin-user azureuser \
  --admin-password YourSecurePassword123! \
  --sku-name B_Gen5_1 \
  --version 8.0

# 5. Create database
az mysql db create \
  --resource-group chandrahoro-prod \
  --server-name chandrahoro-mysql \
  --name chandrahoro

# 6. Create frontend app
az webapp create \
  --resource-group chandrahoro-prod \
  --plan chandrahoro-plan \
  --name chandrahoro-frontend \
  --runtime "NODE|18-lts"

# 7. Create backend app
az webapp create \
  --resource-group chandrahoro-prod \
  --plan chandrahoro-plan \
  --name chandrahoro-backend \
  --runtime "PYTHON|3.11"
```

**For detailed instructions, see**: `AZURE_DEPLOYMENT_SETUP.md`

---

## 🚀 Option 2: Vercel + Railway Deployment (Simplest)

### Prerequisites
- GitHub account with chandrahoro repository
- Vercel account (free at https://vercel.com)
- Railway account (free at https://railway.app)
- GeoNames username (free at https://www.geonames.org)

---

## Step 1: Deploy Backend to Railway (10 min)

### 1.1 Create Railway Project
```bash
# Go to https://railway.app
# Click "New Project" → "Deploy from GitHub"
# Select chandrahoro repository
```

### 1.2 Configure Backend Service
```bash
# In Railway dashboard:
# 1. Add Service → GitHub Repo → chandrahoro
# 2. Set root directory: backend
# 3. Railway auto-detects Python and requirements.txt
```

### 1.3 Add Environment Variables
```bash
# In Railway dashboard → Variables:
ENVIRONMENT=production
DEBUG=False
BACKEND_CORS_ORIGINS=["https://your-frontend-url.vercel.app"]
GEONAMES_USERNAME=your_geonames_username
```

### 1.4 Add PostgreSQL (Optional)
```bash
# In Railway dashboard:
# Click "Add Service" → "Database" → "PostgreSQL"
# Railway auto-sets DATABASE_URL
```

### 1.5 Get Backend URL
```bash
# In Railway dashboard → Settings → Domains
# Copy the generated URL (e.g., https://api.railway.app)
```

---

## Step 2: Deploy Frontend to Vercel (5 min)

### 2.1 Create Vercel Project
```bash
# Go to https://vercel.com
# Click "New Project" → "Import Git Repository"
# Select chandrahoro repository
```

### 2.2 Configure Frontend
```bash
# In Vercel dashboard:
# 1. Framework Preset: Next.js (auto-detected)
# 2. Root Directory: frontend
# 3. Build Command: npm run build
```

### 2.3 Add Environment Variables
```bash
# In Vercel dashboard → Settings → Environment Variables:
NEXT_PUBLIC_API_URL=https://your-railway-backend-url.railway.app
NEXT_PUBLIC_APP_NAME=Chandrahoro
NEXT_PUBLIC_ENABLE_AI_FEATURES=false
NEXT_PUBLIC_ENABLE_ANALYTICS=true
```

### 2.4 Deploy
```bash
# Click "Deploy"
# Vercel builds and deploys automatically
# Get frontend URL (e.g., https://chandrahoro.vercel.app)
```

---

## Step 3: Update CORS (2 min)

### 3.1 Update Backend CORS
```bash
# In Railway dashboard → Variables:
# Update BACKEND_CORS_ORIGINS with your Vercel URL:
BACKEND_CORS_ORIGINS=["https://chandrahoro.vercel.app"]
```

### 3.2 Redeploy Backend
```bash
# Push a commit to trigger redeployment:
git commit --allow-empty -m "Update CORS settings"
git push origin main
# Or manually trigger in Railway dashboard
```

---

## Step 4: Test Deployment (5 min)

### 4.1 Test Frontend
```bash
# Visit https://your-frontend-url.vercel.app
# Check that page loads without errors
```

### 4.2 Test Backend Health
```bash
curl https://your-backend-url.railway.app/api/v1/health
# Should return: {"status": "ok"}
```

### 4.3 Test Chart Generation
```bash
curl -X POST https://your-backend-url.railway.app/api/v1/chart/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "birth_details": {
      "name": "Test",
      "date": "1990-01-01",
      "time": "12:00:00",
      "latitude": 28.6139,
      "longitude": 77.2090,
      "timezone": "Asia/Kolkata",
      "location_name": "Delhi"
    }
  }'
```

### 4.4 Test Location Search
```bash
curl -X POST https://your-backend-url.railway.app/api/v1/location/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Mumbai"}'
```

---

## Step 5: Configure Custom Domain (Optional, 5 min)

### 5.1 Frontend Custom Domain
```bash
# In Vercel dashboard → Settings → Domains:
# 1. Add your domain (e.g., chandrahoro.com)
# 2. Update DNS records as instructed
# 3. SSL auto-provisioned
```

### 5.2 Backend Custom Domain
```bash
# In Railway dashboard → Settings → Domains:
# 1. Add your API domain (e.g., api.chandrahoro.com)
# 2. Update DNS records
# 3. SSL auto-provisioned
```

---

## 🔍 Troubleshooting

### Frontend shows "API connection error"
```bash
# Check NEXT_PUBLIC_API_URL in Vercel environment variables
# Verify backend URL is correct and accessible
# Check CORS settings in backend
```

### Backend returns CORS error
```bash
# Update BACKEND_CORS_ORIGINS in Railway environment variables
# Include the exact frontend URL (with https://)
# Redeploy backend
```

### Chart calculation fails
```bash
# Check backend logs in Railway dashboard
# Verify GeoNames username is set
# Test with curl command above
```

### Location search returns no results
```bash
# Verify GEONAMES_USERNAME is set in backend
# Check backend logs for API errors
# Test with different location names
```

---

## 📊 Monitoring

### Railway Dashboard
```bash
# Monitor backend:
# 1. Go to Railway dashboard
# 2. Click on backend service
# 3. View logs, metrics, and deployments
```

### Vercel Dashboard
```bash
# Monitor frontend:
# 1. Go to Vercel dashboard
# 2. Click on project
# 3. View deployments, analytics, and errors
```

---

## 🔄 Continuous Deployment

### Automatic Deployments
```bash
# Both Vercel and Railway auto-deploy on push to main:
git add .
git commit -m "Your changes"
git push origin main
# Deployments start automatically
```

### Manual Redeployment
```bash
# Railway: Click "Redeploy" in dashboard
# Vercel: Click "Redeploy" in dashboard
```

---

## 📝 Environment Variables Reference

### Frontend (.env.local)
```
NEXT_PUBLIC_API_URL=https://api.railway.app
NEXT_PUBLIC_APP_NAME=Chandrahoro
NEXT_PUBLIC_ENABLE_AI_FEATURES=false
NEXT_PUBLIC_ENABLE_ANALYTICS=true
```

### Backend (.env)
```
ENVIRONMENT=production
DEBUG=False
BACKEND_CORS_ORIGINS=["https://chandrahoro.vercel.app"]
GEONAMES_USERNAME=your_username
REDIS_HOST=redis_host
REDIS_PORT=6379
```

---

## ✅ Deployment Checklist

- [ ] Backend deployed to Railway
- [ ] Frontend deployed to Vercel
- [ ] Environment variables configured
- [ ] CORS settings updated
- [ ] Frontend loads without errors
- [ ] Backend health check passes
- [ ] Chart generation works
- [ ] Location search works
- [ ] Custom domain configured (optional)
- [ ] Monitoring enabled

---

## 🎉 You're Done!

Your Chandrahoro application is now live in production!

**Frontend**: https://your-frontend-url.vercel.app
**Backend**: https://your-backend-url.railway.app

For detailed information, see DEPLOYMENT_GUIDE.md

