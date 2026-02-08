#!/bin/bash
set -e
LOG_DIR="/var/log/housing-import"
mkdir -p $LOG_DIR
LOG_FILE="$LOG_DIR/import_$(date +%Y%m%d_%H%M%S).log"
ERROR_LOG="$LOG_DIR/errors.log"

echo "[$(date)] Starting housing property import..." | tee -a $LOG_FILE

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
