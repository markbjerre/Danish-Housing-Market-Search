# Danish Housing Market Search - Deployment Configuration

**Production deployment guide for https://ai-vaerksted.cloud/housing**

---

## Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set working directory to webapp (where Flask app.py is located)
WORKDIR /app/webapp

# Expose port
EXPOSE 8000

# Start with Gunicorn
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8000", "app_portable:app"]
```

**Note:** The app runs `app_portable.py` which uses file-based database (Parquet) instead of PostgreSQL, making it portable and suitable for containerized environments.

---

## requirements.txt

```
flask==2.3.3
werkzeug==2.3.7
gunicorn==21.2.0
pandas==2.1.1
pyarrow==13.0.0
numpy==1.24.3
requests==2.31.0
```

**Critical Points:**
- Must include gunicorn for production
- Flask/Werkzeug versions must be aligned
- Pandas and PyArrow for file-based database operations
- Keep versions locked for reproducibility

---

## docker-compose.yml Service Entry

Add this to `/root/docker-compose.yml` on VPS:

```yaml
ai-vaerksted-housing:
  build: /opt/ai-vaerksted/Danish-Housing-Market-Search
  container_name: ai-vaerksted-housing
  networks:
    - default
  environment:
    - FLASK_ENV=production
    - PYTHONUNBUFFERED=1
  labels:
    - traefik.enable=true
    - 'traefik.http.routers.housing.rule=Host(`ai-vaerksted.cloud`) && PathPrefix(`/housing`)'
    - traefik.http.routers.housing.entrypoints=websecure
    - traefik.http.routers.housing.tls.certresolver=mytlschallenge
    - 'traefik.http.middlewares.housing-strip.stripprefix.prefixes=/housing'
    - traefik.http.routers.housing.middlewares=housing-strip
    - traefik.http.services.housing.loadbalancer.server.port=8000
  volumes:
    - /opt/ai-vaerksted/Danish-Housing-Market-Search/portable/data:/app/portable/data
```

**Configuration Details:**
- Service name: `ai-vaerksted-housing`
- Build path: `/opt/ai-vaerksted/Danish-Housing-Market-Search`
- URL path: `/housing` (automatically stripped before routing to Flask)
- Port: 8000 (internal Gunicorn port)
- Volume: Persistent storage for Parquet data files

---

## Deployment Instructions

### 1. Initial Setup on VPS

```bash
# Navigate to deployment directory
cd /opt/ai-vaerksted

# Clone repository
git clone https://github.com/markbjerre/Danish-Housing-Market-Search.git
cd Danish-Housing-Market-Search

# Create data directory for Parquet files
mkdir -p portable/data/backups

# Ensure latest data is present
# (You can export from your local PostgreSQL and upload)
```

### 2. Build and Deploy

```bash
# Build Docker image
docker build -t ai-vaerksted-housing:latest .

# Add service to docker-compose.yml (see config above)
# Then deploy
cd /root
docker-compose up -d ai-vaerksted-housing
```

### 3. Verify Deployment

```bash
# Check service is running
curl https://ai-vaerksted.cloud/housing

# Check health endpoint
curl https://ai-vaerksted.cloud/housing/api/health

# View logs
docker logs ai-vaerksted-housing

# Check container status
docker ps | grep housing
```

### 4. Update Data (From Local Machine)

When you have fresh data locally:

```bash
# Export to Parquet
cd portable
python backup_database.py --export

# Upload to VPS
rsync -av portable/data/backups/ user@ai-vaerksted.cloud:/opt/ai-vaerksted/Danish-Housing-Market-Search/portable/data/backups/

# Restart container to load new data
docker restart ai-vaerksted-housing
```

---

## Application Configuration

### Flask App Settings (webapp/app_portable.py)

The app automatically:
- ✅ Loads latest Parquet export from `portable/data/backups/`
- ✅ Implements `/health` endpoint for monitoring
- ✅ Runs in production mode (no debug)
- ✅ Binds to `0.0.0.0:8000` (all interfaces)

### Traefik Routing

- **Domain:** `ai-vaerksted.cloud`
- **Path:** `/housing`
- **TLS:** Automatic via Let's Encrypt
- **Path Stripping:** Traefik removes `/housing` prefix before routing
  - User visits: `https://ai-vaerksted.cloud/housing`
  - Flask receives: `/` (not `/housing`)

**Important:** Flask routes should NOT include the `/housing` prefix.

---

## Environment Variables

```yaml
FLASK_ENV=production        # Disables debug mode
PYTHONUNBUFFERED=1         # Real-time log output
```

---

## Data Management

### Parquet File Structure

Location: `/app/portable/data/backups/full_export_*`

Contains 13 tables:
- `properties_new.parquet` - 228,594 properties
- `cases.parquet` - 3,683 active listings
- `case_images.parquet` - 27,348 property images
- `registrations.parquet` - 388,113 transaction history
- Plus geographic and market data tables

Total size: ~87.6 MB

### Automatic Data Detection

The Flask app automatically:
1. Scans `portable/data/backups/` for exports
2. Selects the most recent export by timestamp
3. Loads all Parquet files into memory on startup
4. Provides search/filter endpoints backed by in-memory Pandas DataFrames

### Update Procedure

To refresh data:

```bash
# On local machine
cd portable
python backup_database.py --export

# On VPS
docker restart ai-vaerksted-housing
```

No database service needed - all data is self-contained in Parquet files.

---

## Monitoring and Logs

### View Logs

```bash
# Real-time logs
docker logs -f ai-vaerksted-housing

# Last 100 lines
docker logs --tail 100 ai-vaerksted-housing
```

### Health Check

```bash
# Check app health
curl -s https://ai-vaerksted.cloud/housing/api/health | jq

# Expected response:
# {
#   "status": "ok",
#   "properties_count": 228594,
#   "active_listings": 3683,
#   "data_export": "full_export_20251101_232009"
# }
```

### Troubleshooting

**App won't start:**
- Check logs: `docker logs ai-vaerksted-housing`
- Verify data files exist: `ls portable/data/backups/`
- Verify Parquet files are readable

**Slow performance:**
- Check RAM: Parquet loads ~87.6 MB into memory (acceptable)
- Monitor CPU: 2 Gunicorn workers should be sufficient
- Check logs for errors

**Data outdated:**
- Re-export from local PostgreSQL
- Upload new Parquet files
- Restart container

---

## SSL/TLS

Handled automatically by Traefik with Let's Encrypt:
- Certificate auto-renewal: ✅ Enabled
- Domain: `ai-vaerksted.cloud`
- HTTP → HTTPS: ✅ Automatic redirect

---

## Backup Strategy

### Local Backup (on VPS)

```bash
# Backup Parquet data
tar -czf housing_backup_$(date +%Y%m%d).tar.gz \
  /opt/ai-vaerksted/Danish-Housing-Market-Search/portable/data/

# Keep backups
ls -lh housing_backup_*.tar.gz
```

### Data Restoration

```bash
# If data corrupted
cd /opt/ai-vaerksted/Danish-Housing-Market-Search/portable/data

# Restore from backup
tar -xzf ../housing_backup_20251102.tar.gz --strip-components=6

# Restart app
docker restart ai-vaerksted-housing
```

---

## Performance Optimization

### Memory Usage
- Parquet format: Compressed columnar storage (87.6 MB)
- In-memory: Pandas DataFrames (~200-300 MB loaded)
- Docker memory limit: 512 MB recommended minimum

### CPU Usage
- Gunicorn workers: 2 (suitable for moderate traffic)
- Request handling: <100ms typical for property search
- Parallelization: Already implemented in worker pool

### Disk Space
- Parquet files: ~87.6 MB
- Logs: Rotate with Docker's log driver
- Recommended: 500 MB free space minimum

---

## Updating to New Versions

### Update Source Code

```bash
cd /opt/ai-vaerksted/Danish-Housing-Market-Search
git pull origin main
docker build -t ai-vaerksted-housing:latest .
docker-compose up -d ai-vaerksted-housing
```

### Update Dependencies

1. Update `requirements.txt` locally
2. Test with portable setup
3. Rebuild Docker image
4. Restart container

---

## Security Considerations

✅ **Implemented:**
- Production Flask mode (debug=False)
- No hardcoded credentials
- Environment variables for config
- SSL/TLS via Let's Encrypt
- Path-based routing (Traefik)
- No exposed database ports

⚠️ **To Consider:**
- Rate limiting on API endpoints
- Input validation on search parameters
- CORS configuration if API used by external sites
- Regular security updates to dependencies

---

## Reference

- **Flask App:** `webapp/app_portable.py`
- **Database Layer:** `portable/file_database.py`
- **Data Format:** Parquet (Apache Arrow columnar format)
- **Deployment Template:** `child_repo_config.md`
- **Traefik Setup:** Handled by main docker-compose.yml in /root

---

## URLs

| Environment | URL |
|-------------|-----|
| **Local Development** | http://127.0.0.1:5000 |
| **Production** | https://ai-vaerksted.cloud/housing |
| **Health Check** | https://ai-vaerksted.cloud/housing/api/health |
| **Search API** | https://ai-vaerksted.cloud/housing/api/search |

---

**Last Updated:** November 2, 2025  
**Status:** Ready for Deployment
