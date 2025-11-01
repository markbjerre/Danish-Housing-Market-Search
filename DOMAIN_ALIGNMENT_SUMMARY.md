# Domain Alignment Update - Summary

**Date:** November 2, 2025  
**Commit:** 807b3c0  
**Production URL:** https://ai-vaerksted.cloud/housing

---

## Overview

All references to the Danish Housing Market Search application have been updated to align with the new production domain. The application is now deployment-ready for the VPS.

---

## Files Updated

### 1. Documentation Files

#### `docs/README.md` 
- ✅ Added production URL reference
- ✅ Clarified development vs production setup
- ✅ Documented both localhost and cloud URLs

#### `portable/README.md`
- ✅ Added development and production URL sections
- ✅ Differentiated between local and deployed access

#### `portable/README_PORTABLE.md`
- ✅ Added production URL guidance
- ✅ Included both local and cloud deployment instructions

#### `claude.md` (Main Project Documentation)
- ✅ Updated architecture diagram with URL references
- ✅ Added production URL comments
- ✅ Clarified deployment scenarios

### 2. New Files Created

#### `DEPLOYMENT_CONFIG.md` (NEW)
Complete production deployment guide including:
- **Dockerfile:** Multi-stage build with Python 3.11-slim, Gunicorn
- **docker-compose.yml:** Service configuration for Traefik routing
- **Deployment Instructions:** Step-by-step setup for VPS
- **Data Management:** Parquet file handling and updates
- **Monitoring:** Health checks, logging, troubleshooting
- **Performance:** Optimization recommendations
- **Security:** Best practices checklist
- **Backup Strategy:** Data recovery procedures

#### `child_repo_config.md` (Copied for reference)
Template configuration from parent project for deployment standards

### 3. Application Code Updates

#### `webapp/app_portable.py`
**New Features:**
- ✅ **Health Check Endpoint** (`/api/health`)
  - Returns JSON status: `{"status": "ok", "properties_count": 228594, ...}`
  - Includes environment detection (production/development)
  - Useful for Docker container monitoring

- ✅ **Environment-Aware Configuration**
  - Detects `FLASK_ENV=production` environment variable
  - Production: Runs on `0.0.0.0:8000` (all interfaces, suitable for Docker)
  - Development: Runs on `127.0.0.1:5000` (localhost only)
  - Debug mode disabled in production

- ✅ **Improved Startup Logging**
  ```
  ENVIRONMENT: PRODUCTION/DEVELOPMENT
  Properties: 228,594
  Active Listings: 3,683
  Data Export: full_export_20251101_232009
  Data from: /app/portable/data/backups/...
  Available Endpoints: (comprehensive list)
  ```

- ✅ **New API Endpoints**
  - `/api/health` - Health check for Traefik/monitoring
  - `POST /api/search` - Property search API
  - `GET /api/property/<id>` - Property details
  - `GET /api/stats` - Database statistics

---

## Production Deployment Setup

### Docker Configuration

**Dockerfile:**
```dockerfile
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
WORKDIR /app/webapp
EXPOSE 8000
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8000", "app_portable:app"]
```

**docker-compose.yml Entry:**
```yaml
ai-vaerksted-housing:
  build: /opt/ai-vaerksted/Danish-Housing-Market-Search
  container_name: ai-vaerksted-housing
  environment:
    - FLASK_ENV=production
  labels:
    - 'traefik.http.routers.housing.rule=Host(`ai-vaerksted.cloud`) && PathPrefix(`/housing`)'
    - traefik.http.routers.housing.middlewares=housing-strip
  volumes:
    - /opt/ai-vaerksted/Danish-Housing-Market-Search/portable/data:/app/portable/data
```

### Deployment Steps

1. **Build Image**
   ```bash
   docker build -t ai-vaerksted-housing:latest .
   ```

2. **Add to docker-compose.yml**
   - Add service configuration (see DEPLOYMENT_CONFIG.md)
   - Include Traefik labels for `/housing` path routing

3. **Deploy**
   ```bash
   docker-compose up -d ai-vaerksted-housing
   ```

4. **Verify**
   ```bash
   curl https://ai-vaerksted.cloud/housing/api/health
   ```

---

## URL Mapping

| Context | URL |
|---------|-----|
| **Local Development** | http://127.0.0.1:5000 |
| **Production (Web)** | https://ai-vaerksted.cloud/housing |
| **Health Check** | https://ai-vaerksted.cloud/housing/api/health |
| **Search API** | https://ai-vaerksted.cloud/housing/api/search |
| **Property Details** | https://ai-vaerksted.cloud/housing/api/property/{id} |

---

## API Endpoints Reference

### Public Endpoints

**GET `/`**
- Home page with search interface

**GET `/search`**
- Search interface page

**POST `/api/search`**
- Search properties with filters
- Query parameters: municipality, priceMin, priceMax, sizeMin, sizeMax, etc.

**GET `/api/property/<property_id>`**
- Get detailed property information
- Returns JSON with comprehensive property data

**GET `/api/health`** (NEW)
- Health check for deployment monitoring
- Returns: `{"status": "ok", "properties_count": 228594, ...}`

**GET `/api/stats`**
- Database statistics
- Returns counts and metadata

**GET `/data-info`**
- HTML page with data statistics

---

## Environment Variables

For Production Deployment:

```bash
FLASK_ENV=production          # Disables debug mode
PYTHONUNBUFFERED=1           # Real-time log output
# Optional:
DB_HOST=localhost            # For future PostgreSQL connection
DB_NAME=housing_db
```

---

## Data Management

### Current Data Setup
- **Format:** Parquet (Apache Arrow columnar compression)
- **Location:** `portable/data/backups/full_export_*`
- **Size:** ~87.6 MB (compressed)
- **Tables:** 13 (properties, cases, images, registrations, geographic, market data)

### Update Procedure
1. Export from local PostgreSQL using `backup_database.py`
2. Upload to VPS: `rsync -av portable/data/backups/ user@server:/opt/.../portable/data/backups/`
3. Restart container: `docker restart ai-vaerksted-housing`
4. App auto-detects latest export on startup

---

## Monitoring & Health Checks

### Health Endpoint
```bash
curl https://ai-vaerksted.cloud/housing/api/health
```

**Response:**
```json
{
  "status": "ok",
  "properties_count": 228594,
  "active_listings": 3683,
  "data_export": "full_export_20251101_232009",
  "environment": "production"
}
```

### View Logs
```bash
docker logs -f ai-vaerksted-housing
```

### Check Container Status
```bash
docker ps | grep housing
```

---

## Technical Specifications

| Component | Value |
|-----------|-------|
| **Base Image** | python:3.11-slim |
| **Flask Version** | 2.3.3 |
| **Gunicorn Workers** | 2 |
| **Internal Port** | 8000 |
| **External Domain** | ai-vaerksted.cloud/housing |
| **SSL/TLS** | Let's Encrypt (auto via Traefik) |
| **Data Format** | Parquet (columnar, compressed) |
| **Data Size** | ~87.6 MB |
| **Properties** | 228,594 |
| **Active Listings** | 3,683 |

---

## Quick Reference

### For VPS Setup
1. See `DEPLOYMENT_CONFIG.md` - Complete deployment guide
2. See `child_repo_config.md` - Standard template configuration
3. Add service to main `docker-compose.yml`
4. Run `docker-compose up -d ai-vaerksted-housing`

### For Local Development
1. Run: `cd webapp && python app_portable.py`
2. Visit: http://127.0.0.1:5000
3. App automatically loads latest Parquet export

### For Data Updates
1. Export: `python portable/backup_database.py --export`
2. Upload: `rsync -av portable/data/backups/ ...`
3. Restart: `docker restart ai-vaerksted-housing`

---

## Next Steps

✅ **Completed:**
- Domain alignment across all documentation
- Production deployment configuration
- Health monitoring endpoint
- Environment-aware application startup
- Docker/docker-compose configuration

📋 **Ready for:**
- VPS deployment with Traefik routing
- Docker container orchestration
- Production data updates
- Monitoring and alerting setup

---

## Related Documentation

- **DEPLOYMENT_CONFIG.md** - Complete deployment guide
- **claude.md** - Project overview and architecture
- **docs/README.md** - Quick start guide
- **portable/README.md** - Portable setup instructions
- **child_repo_config.md** - Deployment template reference

---

**Status:** ✅ Deployment Ready  
**Last Updated:** November 2, 2025  
**Commit:** 807b3c0
