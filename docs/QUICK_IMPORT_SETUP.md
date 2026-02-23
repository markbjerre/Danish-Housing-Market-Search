# Quick Start: Automated Housing Data Import

## TL;DR - Setup in 5 Minutes

### Prerequisites
- SSH access to VPS: `ssh root@72.61.179.126`
- Docker container `ai-vaerksted-housing` is running
- Database `housing-db` is healthy

### Step 1: Create Wrapper Script
```bash
ssh root@72.61.179.126
sudo cat > /usr/local/bin/run-housing-import.sh << 'EOF'
#!/bin/bash
set -e
LOG_DIR="/var/log/housing-import"
mkdir -p $LOG_DIR
LOG_FILE="$LOG_DIR/import_$(date +%Y%m%d_%H%M%S).log"
echo "[$(date)] Starting import..." | tee -a $LOG_FILE
docker exec ai-vaerksted-housing python /app/scripts/import_copenhagen_area.py \
  --workers=20 --batch_size=50 >> $LOG_FILE 2>&1 && \
echo "[$(date)] ✅ Completed" | tee -a $LOG_FILE || \
echo "[$(date)] ❌ Failed" | tee -a $LOG_FILE
find $LOG_DIR -name "import_*.log" -mtime +30 -delete
EOF
sudo chmod +x /usr/local/bin/run-housing-import.sh
```

### Step 2: Test It Works
```bash
/usr/local/bin/run-housing-import.sh
tail /var/log/housing-import/import_*.log
```

### Step 3: Schedule with Cron
```bash
sudo crontab -e
```
Add this line:
```cron
# Run daily at 2 AM
0 2 * * * /usr/local/bin/run-housing-import.sh

# Or run weekly on Monday at 2 AM
0 2 * * 1 /usr/local/bin/run-housing-import.sh
```

### Step 4: Verify
```bash
sudo crontab -l        # See your scheduled jobs
tail -f /var/log/housing-import/errors.log  # Watch for errors
```

---

## Common Commands

### Check Last Import Status
```bash
ssh root@72.61.179.126
ls -lth /var/log/housing-import/ | head -3
tail -50 /var/log/housing-import/import_$(date +%Y%m%d)*.log
```

### View Import Progress (Live)
```bash
docker compose logs -f ai-vaerksted-housing | grep -E "Zip Code|Found|properties"
```

### Check Database Row Count
```bash
docker exec housing-db psql -U housing -d housing -c \
  'SELECT COUNT(*) as total_properties FROM properties_new;'
```

### Manually Trigger Import (Don't Wait for Cron)
```bash
/usr/local/bin/run-housing-import.sh
```

### View All Cron Jobs
```bash
sudo crontab -l
```

### Disable Scheduled Import (Temporarily)
```bash
sudo crontab -e
# Add # before the line:
# 0 2 * * * /usr/local/bin/run-housing-import.sh
```

### Re-enable Scheduled Import
```bash
sudo crontab -e
# Remove the # before the line:
0 2 * * * /usr/local/bin/run-housing-import.sh
```

---

## Schedule Options

| Schedule | Cron | When to Use |
|----------|------|-----------|
| **Daily at 2 AM** | `0 2 * * *` | Keep data fresh daily |
| **Weekly Monday 2 AM** | `0 2 * * 1` | Reduce server load |
| **Every 6 hours** | `0 */6 * * *` | Keep data very fresh |
| **Daily at 3 AM** | `0 3 * * *` | Avoid conflicts |
| **Weekdays only** | `0 2 * * 1-5` | Save weekends |

---

## Local Machine Setup

If you want to run imports from your local machine first before setting up on VPS:

### 1. Install Requirements
```bash
cd "Danish Housing Market Search"
pip install -r requirements.txt
```

### 2. Configure .env
The local `.env` is already configured. For production pointing:
```
DB_HOST=72.61.179.126
DB_PORT=5432
DB_NAME=housing
DB_USER=housing
DB_PASSWORD=housing_secure_2024
```

⚠️ **Don't commit this to git!** The `.gitignore` protects `.env`

### 3. Run Import Once
```bash
python scripts/import_copenhagen_area.py --dry-run
# Remove --dry-run to actually save to database
python scripts/import_copenhagen_area.py --workers=20 --batch_size=50
```

### 4. Python Scheduler (Linux/Mac Only)
```bash
# Daily at 2 AM
python scripts/scheduler.py --frequency daily --time 02:00 &

# Weekly Monday at 2 AM
python scripts/scheduler.py --frequency weekly --day monday --time 02:00 &

# Once now
python scripts/scheduler.py --once
```

---

## Monitoring & Alerts

### Check Import Health Weekly
```bash
# SSH to server
ssh root@72.61.179.126

# Show last 3 imports
echo "=== LAST 3 IMPORTS ===" && \
ls -lth /var/log/housing-import/ | head -4

# Check for any errors
echo "=== ERRORS ===" && \
tail -20 /var/log/housing-import/errors.log

# Database stats
echo "=== DATABASE STATS ===" && \
docker exec housing-db psql -U housing -d housing -c \
  "SELECT COUNT(*) as properties, MAX(modified_date) as last_update FROM properties_new;"
```

### Auto-Check Script
Save as `/usr/local/bin/check-imports.sh`:
```bash
#!/bin/bash
LATEST=$(ls -t /var/log/housing-import/import_*.log 2>/dev/null | head -1)
if [ -z "$LATEST" ]; then
  echo "❌ No imports found!"
  exit 1
fi
HOURS=$(($(date +%s) - $(stat -c %Y "$LATEST")) / 3600))
if [ $HOURS -gt 48 ]; then
  echo "⚠️  No import for $HOURS hours"
  exit 1
fi
if tail -1 "$LATEST" | grep -q "Completed"; then
  echo "✅ Last import successful ($HOURS hours ago)"
  exit 0
else
  echo "❌ Last import failed or incomplete"
  exit 1
fi
```

Run weekly:
```cron
0 10 * * 1 /usr/local/bin/check-imports.sh || echo "Housing import issue" | mail root
```

---

## Troubleshooting Quick Ref

| Issue | Check | Fix |
|-------|-------|-----|
| Import never runs | `sudo crontab -l` | Check cron is scheduled |
| Logs not created | `ls /var/log/housing-import/` | Create dir: `sudo mkdir -p /var/log/housing-import` |
| Container crashes | `docker ps -a \| grep housing` | `docker compose logs ai-vaerksted-housing` |
| DB connection fails | `docker exec housing-db pg_isready` | Check DB is running |
| Disk full | `df -h` | Clean old logs: `rm /var/log/housing-import/*.log` |
| API timeouts | `curl https://api.boligsiden.dk` | Check internet connection |

---

## File Locations

| Item | Path |
|------|------|
| **Local project** | `c:\Users\Mark BJ\Desktop\Code Projects\Danish Housing Market Search` |
| **VPS code** | `/opt/ai-vaerksted/Danish-Housing-Market-Search` |
| **Import script** | `scripts/import_copenhagen_area.py` |
| **Import logs** | `/var/log/housing-import/` |
| **Scheduler script** | `scripts/scheduler.py` |
| **Setup docs** | `SCHEDULER_SETUP.md` |
| **Wrapper script** | `/usr/local/bin/run-housing-import.sh` |
| **Database** | `housing-db` container, `housing` database |

---

## Next: Advanced Topics

See `SCHEDULER_SETUP.md` for:
- Systemd timer setup (more robust)
- Docker container scheduling
- Database backups with imports
- Monitoring and alerting
- Error recovery procedures

