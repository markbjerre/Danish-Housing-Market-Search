# Automated Housing Data Import Scheduling

This document describes how to set up automated, periodic imports of Danish housing data on the production VPS.

## Overview

The housing database is populated via the Boligsiden API through `scripts/import_copenhagen_area.py`. To keep data fresh without manual intervention, we use one of these scheduling approaches:

1. **Cron jobs** (simplest - recommended)
2. **Systemd timer** (more robust)
3. **Docker container with scheduler** (works in containerized environment)

---

## Option 1: Cron Job (Recommended for Initial Setup)

### Setup on VPS

1. **SSH into the server:**
   ```bash
   ssh root@72.61.179.126
   ```

2. **Create a wrapper script** (`/usr/local/bin/run-housing-import.sh`):
   ```bash
   sudo cat > /usr/local/bin/run-housing-import.sh << 'EOF'
   #!/bin/bash
   
   # Automated Housing Property Import Script
   # Runs inside Docker container to import fresh data
   
   set -e  # Exit on error
   
   LOG_DIR="/var/log/housing-import"
   mkdir -p $LOG_DIR
   
   LOG_FILE="$LOG_DIR/import_$(date +%Y%m%d_%H%M%S).log"
   ERROR_LOG="$LOG_DIR/errors.log"
   
   echo "[$(date)] Starting housing property import..." | tee -a $LOG_FILE
   
   # Run import inside Docker container
   docker exec ai-vaerksted-housing python /app/scripts/import_copenhagen_area.py \
     --workers=20 \
     --batch_size=50 \
     >> $LOG_FILE 2>&1
   
   RESULT=$?
   
   if [ $RESULT -eq 0 ]; then
       echo "[$(date)] ✅ Import completed successfully" | tee -a $LOG_FILE
   else
       echo "[$(date)] ❌ Import failed with code $RESULT" | tee -a $LOG_FILE
       echo "[$(date)] Import failed with code $RESULT" >> $ERROR_LOG
   fi
   
   # Keep only last 30 days of logs
   find $LOG_DIR -name "import_*.log" -mtime +30 -delete
   
   exit $RESULT
   EOF
   
   sudo chmod +x /usr/local/bin/run-housing-import.sh
   ```

3. **Test the script manually:**
   ```bash
   /usr/local/bin/run-housing-import.sh
   ```
   Monitor the logs:
   ```bash
   tail -f /var/log/housing-import/import_*.log
   ```

4. **Add to crontab:**
   ```bash
   sudo crontab -e
   ```
   
   Add one of these lines:
   
   **Daily at 2 AM:**
   ```cron
   0 2 * * * /usr/local/bin/run-housing-import.sh
   ```
   
   **Weekly on Monday at 2 AM:**
   ```cron
   0 2 * * 1 /usr/local/bin/run-housing-import.sh
   ```
   
   **Every 6 hours:**
   ```cron
   0 */6 * * * /usr/local/bin/run-housing-import.sh
   ```

5. **Verify cron job is installed:**
   ```bash
   sudo crontab -l
   ```

### Managing Cron Jobs

**View logs:**
```bash
tail -50 /var/log/housing-import/import_*.log
tail -f /var/log/housing-import/errors.log
```

**Monitor last run:**
```bash
ls -lht /var/log/housing-import/ | head -5
```

**Disable temporarily:**
```bash
sudo crontab -e
# Comment out the line with #
```

**Disable permanently:**
```bash
sudo crontab -e
# Delete the line
```

---

## Option 2: Systemd Timer (More Robust)

Systemd timers are more reliable than cron and integrate better with Docker.

### Setup

1. **Create service file** (`/etc/systemd/system/housing-import.service`):
   ```bash
   sudo cat > /etc/systemd/system/housing-import.service << 'EOF'
   [Unit]
   Description=Import Housing Properties from Boligsiden API
   After=docker.service housing-db.service ai-vaerksted-housing.service
   Requires=docker.service
   
   [Service]
   Type=oneshot
   ExecStart=/usr/local/bin/run-housing-import.sh
   StandardOutput=journal
   StandardError=journal
   SyslogIdentifier=housing-import
   
   # Run as root (needed for docker exec)
   User=root
   Group=root
   EOF
   ```

2. **Create timer file** (`/etc/systemd/system/housing-import.timer`):
   ```bash
   sudo cat > /etc/systemd/system/housing-import.timer << 'EOF'
   [Unit]
   Description=Daily Housing Property Import Timer
   
   [Timer]
   # Run at 2 AM every day
   OnCalendar=*-*-* 02:00:00
   
   # Or use for weekly (Monday at 2 AM):
   # OnCalendar=Mon *-*-* 02:00:00
   
   # Or use for every 6 hours:
   # OnBootSec=5min
   # OnUnitActiveSec=6h
   
   Persistent=true
   
   [Install]
   WantedBy=timers.target
   EOF
   ```

3. **Enable and start the timer:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable housing-import.timer
   sudo systemctl start housing-import.timer
   ```

4. **Check timer status:**
   ```bash
   sudo systemctl status housing-import.timer
   sudo systemctl list-timers housing-import.timer
   ```

5. **View logs:**
   ```bash
   sudo journalctl -u housing-import.service -n 50
   sudo journalctl -u housing-import.service -f  # Follow
   ```

### Managing Systemd Timer

**Stop timer temporarily:**
```bash
sudo systemctl stop housing-import.timer
```

**Restart:**
```bash
sudo systemctl start housing-import.timer
```

**View next run time:**
```bash
sudo systemctl list-timers housing-import.timer
```

**Test the service manually:**
```bash
sudo systemctl start housing-import.service
sudo journalctl -u housing-import.service -f
```

---

## Option 3: Docker Container Scheduler (For Containerized Deployments)

If running the import inside Docker:

### Create a scheduled import service in docker-compose.yml

```yaml
housing-import-scheduler:
  image: ai-vaerksted-housing:latest
  container_name: housing-import-scheduler
  build: /opt/ai-vaerksted/Danish-Housing-Market-Search
  depends_on:
    housing-db:
      condition: service_healthy
  environment:
    - DB_PASSWORD=${DB_PASSWORD}
    - DB_USER=${DB_USER}
    - DB_NAME=${DB_NAME}
    - DB_HOST=housing-db
    - DB_PORT=5432
  volumes:
    - /var/log/housing-import:/app/logs
  entrypoint: >
    sh -c "
    python /app/scripts/scheduler.py 
      --frequency daily 
      --time 02:00 
      --workers 20 
      --batch_size 50
    "
  networks:
    - default
  restart: unless-stopped
```

Deploy with:
```bash
cd /root
docker compose up -d housing-import-scheduler
```

---

## Monitoring and Alerts

### Create a monitoring script (`/usr/local/bin/check-housing-import.sh`):

```bash
#!/bin/bash
# Check if housing import is running and sending alerts

LAST_LOG="/var/log/housing-import/import_*.log"
LATEST=$(ls -t $LAST_LOG 2>/dev/null | head -1)

if [ -z "$LATEST" ]; then
    echo "WARNING: No import logs found"
    exit 1
fi

LAST_RUN=$(stat -c %Y "$LATEST")
NOW=$(date +%s)
DIFF=$((NOW - LAST_RUN))

# Alert if no import in last 48 hours
if [ $DIFF -gt 172800 ]; then
    echo "ALERT: Housing import hasn't run in $((DIFF / 3600)) hours"
    exit 1
fi

# Check for errors in log
if grep -q "❌" "$LATEST"; then
    echo "ALERT: Import completed with errors"
    exit 1
fi

echo "OK: Import running normally (last run: $((DIFF / 3600)) hours ago)"
exit 0
```

Add to cron for monitoring:
```cron
0 */4 * * * /usr/local/bin/check-housing-import.sh || echo "Housing import check failed" | mail -s "Housing Import Alert" admin@example.com
```

---

## Database Automatic Backups

Pair imports with automated backups:

```bash
# In /usr/local/bin/backup-housing-db.sh (created during setup)
docker exec housing-db pg_dump -U housing housing | \
  gzip > /mnt/backups/housing_db_$(date +%Y%m%d).sql.gz

# Keep only last 30 days
find /mnt/backups -name "housing_db_*.sql.gz" -mtime +30 -delete
```

Schedule backups:
```cron
# Backup 1 hour after import (3 AM daily)
0 3 * * * /usr/local/bin/backup-housing-db.sh
```

---

## Troubleshooting

### Import hangs or times out
- Check Docker container status: `docker ps`
- Check API connectivity: `curl -I https://api.boligsiden.dk`
- Increase timeout: Modify wrapper script with `timeout 3600` command
- Check database connection: `docker exec housing-db psql -U housing -d housing -c "SELECT 1"`

### Container not running after scheduled import
- Check logs: `docker compose logs ai-vaerksted-housing`
- Restart container: `docker compose restart ai-vaerksted-housing`
- Check disk space: `df -h`
- Check memory: `free -h`

### Database locked during import
- Current imports may block web access
- Run imports during low-traffic hours (2-4 AM recommended)
- Consider read replicas for production (future enhancement)

### Logs not being written
- Check permissions: `ls -la /var/log/housing-import/`
- Check disk space: `df -h`
- Ensure log directory is writable: `chmod 777 /var/log/housing-import`

---

## Summary

| Approach | Setup Time | Reliability | Monitoring | Best For |
|----------|-----------|-------------|-----------|----------|
| **Cron** | 5 min | Good | Manual | Simple, immediate setup |
| **Systemd Timer** | 10 min | Excellent | Journal logs | Production deployments |
| **Docker Scheduler** | 15 min | Good | Docker logs | Containerized environments |

**Recommendation:** Start with **Cron** for quick setup, migrate to **Systemd Timer** for production robustness.

---

## Next Steps

1. ✅ Choose scheduling approach (Cron recommended to start)
2. ✅ Run test import manually
3. ✅ Set up logs directory with rotation
4. ✅ Schedule first automatic run
5. ✅ Monitor logs for first few runs
6. ✅ Set up backup scripts
7. ✅ Configure monitoring/alerts (optional)

