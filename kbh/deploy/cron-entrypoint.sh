#!/bin/sh
# Daily pipeline runner for the Copenhagen apartment monitor.
#
# Runs cron in the foreground so Docker can supervise it and restart it. The
# alternative, backgrounding cron and sleeping, hides a dead scheduler behind a
# healthy looking container.
set -eu

SCHEDULE="${KBH_CRON_SCHEDULE:-0 7 * * *}"

# cron starts with almost no environment, which is the single most common way a
# containerised cron job dies: it works by hand and fails on the schedule
# because the variables are gone. Everything the pipeline needs is written out
# for the job to source.
{
    echo "export KBH_DB_PATH='${KBH_DB_PATH:-/data/kbh.sqlite3}'"
    echo "export TELEGRAM_BOT_TOKEN='${TELEGRAM_BOT_TOKEN:-}'"
    echo "export TELEGRAM_CHAT_ID='${TELEGRAM_CHAT_ID:-}'"
    echo "export KBH_AI_ENABLED='${KBH_AI_ENABLED:-0}'"
    echo "export KBH_AI_MIN_SCORE='${KBH_AI_MIN_SCORE:-62}'"
    echo "export KBH_ALERT_THRESHOLD='${KBH_ALERT_THRESHOLD:-72}'"
    echo "export PATH='${PATH}'"
    echo "export TZ='${TZ:-Europe/Copenhagen}'"
} > /app/cron.env
chmod 600 /app/cron.env

cat > /etc/cron.d/kbh <<EOF
SHELL=/bin/sh
${SCHEDULE} cd /app && . /app/cron.env && python -m kbh.pipeline run >> /var/log/kbh-cron.log 2>&1
EOF
chmod 0644 /etc/cron.d/kbh
crontab /etc/cron.d/kbh

touch /var/log/kbh-cron.log

echo "kbh cron ready, schedule: ${SCHEDULE} (TZ ${TZ:-Europe/Copenhagen})"
echo "AI verdicts: ${KBH_AI_ENABLED:-0}"

# Tail the log to stdout so `docker logs` shows what the job did, and run cron
# in the foreground alongside it.
tail -F /var/log/kbh-cron.log &
exec cron -f
