#!/usr/bin/env bash
# Install the Copenhagen apartment monitor on the ai-vaerksted.cloud VPS.
#
# Run as root on the server:
#   bash /opt/ai-vaerksted/Danish-Housing-Market-Search/kbh/deploy/vps_install.sh
#
# Safe to run more than once. It reports what it would change, changes only
# what is missing, and validates the compose configuration before applying
# anything.
#
# WHY AN OVERRIDE FILE RATHER THAN EDITING docker-compose.yml
#
# /root/docker-compose.yml runs the live site. Text-munging YAML into the
# middle of it with sed is how a working server becomes a broken one at half
# past eleven at night. Docker Compose merges docker-compose.override.yml
# automatically with no extra flags, so the new services go there and the file
# everything else depends on is never touched.
#
# If an override file already exists this script stops rather than clobbering
# it, and says what to do.

set -euo pipefail

COMPOSE_DIR=/root
MAIN_COMPOSE="${COMPOSE_DIR}/docker-compose.yml"
OVERRIDE="${COMPOSE_DIR}/docker-compose.override.yml"
ENV_FILE="${COMPOSE_DIR}/.env"
REPO_DIR=/opt/ai-vaerksted/Danish-Housing-Market-Search
REPO_URL=https://github.com/markbjerre/Danish-Housing-Market-Search.git
BRANCH=kbh-apartment-monitor
STAMP="$(date +%Y%m%d-%H%M%S)"

say() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[33m    %s\033[0m\n' "$*"; }
die() { printf '\033[31mFAILED: %s\033[0m\n' "$*" >&2; exit 1; }

# --------------------------------------------------------------------------
say "Checking the ground"
# --------------------------------------------------------------------------

command -v docker >/dev/null || die "docker is not installed"
docker compose version >/dev/null 2>&1 || die "docker compose v2 is not available"
[ -f "$MAIN_COMPOSE" ] || die "no $MAIN_COMPOSE, this is not the machine I expected"

say "Recording the current state, so there is something to go back to"
cp -a "$MAIN_COMPOSE" "${MAIN_COMPOSE}.bak-${STAMP}"
[ -f "$ENV_FILE" ] && cp -a "$ENV_FILE" "${ENV_FILE}.bak-${STAMP}"
docker compose -f "$MAIN_COMPOSE" ps --format '{{.Name}} {{.Status}}' > "/root/services-before-${STAMP}.txt" 2>/dev/null || true
echo "    backup: ${MAIN_COMPOSE}.bak-${STAMP}"
echo "    running services recorded in /root/services-before-${STAMP}.txt"

# --------------------------------------------------------------------------
say "Fetching the code"
# --------------------------------------------------------------------------

mkdir -p /opt/ai-vaerksted
if [ -d "${REPO_DIR}/.git" ]; then
    git -C "$REPO_DIR" fetch --quiet origin "$BRANCH"
    git -C "$REPO_DIR" checkout --quiet "$BRANCH"
    git -C "$REPO_DIR" reset --hard --quiet "origin/${BRANCH}"
    echo "    updated to $(git -C "$REPO_DIR" rev-parse --short HEAD)"
else
    git clone --quiet --branch "$BRANCH" "$REPO_URL" "$REPO_DIR"
    echo "    cloned at $(git -C "$REPO_DIR" rev-parse --short HEAD)"
fi

# --------------------------------------------------------------------------
say "Credentials"
# --------------------------------------------------------------------------

touch "$ENV_FILE"

if grep -q '^KBH_BASIC_AUTH=' "$ENV_FILE"; then
    echo "    KBH_BASIC_AUTH already set, leaving it alone"
else
    # htpasswd is not usually installed, but Docker is, so borrow it from the
    # httpd image rather than apt-getting apache2-utils onto the host.
    MARK_PW="${KBH_PW_MARK:-$(openssl rand -base64 12 | tr -d '/+=' | cut -c1-16)}"
    ELLA_PW="${KBH_PW_ELLABELLA:-$(openssl rand -base64 12 | tr -d '/+=' | cut -c1-16)}"
    MARK_HASH="$(docker run --rm httpd:alpine htpasswd -nbB mark "$MARK_PW")"
    ELLA_HASH="$(docker run --rm httpd:alpine htpasswd -nbB ellabella "$ELLA_PW")"
    # Compose eats single dollar signs, so every one has to be doubled here.
    COMBINED="$(printf '%s,%s' "$MARK_HASH" "$ELLA_HASH" | tr -d '\n' | sed -e 's/\$/\$\$/g')"
    {
        echo ""
        echo "# Copenhagen apartment monitor, added ${STAMP}."
        echo "# The username is also the key each person's ratings are stored"
        echo "# under, so do not rename one without migrating the ratings."
        echo "KBH_BASIC_AUTH=${COMBINED}"
    } >> "$ENV_FILE"
    say "WRITE THESE DOWN, they are not recoverable from the hash"
    echo "    https://ai-vaerksted.cloud/boligjagt/"
    echo "    mark      / ${MARK_PW}"
    echo "    ellabella / ${ELLA_PW}"
fi

if ! grep -q '^TELEGRAM_BOT_TOKEN=' "$ENV_FILE"; then
    {
        echo "# Alerts and the morning digest are disabled until these are set."
        echo "# Get them from @BotFather, then rerun: docker compose up -d"
        echo "# TELEGRAM_BOT_TOKEN="
        echo "# TELEGRAM_CHAT_ID="
    } >> "$ENV_FILE"
    warn "No Telegram token. The daily run will refresh data and notify nobody."
fi

# --------------------------------------------------------------------------
say "Adding the services"
# --------------------------------------------------------------------------

if [ -f "$OVERRIDE" ] && ! grep -q 'ai-vaerksted-kbh' "$OVERRIDE"; then
    die "$OVERRIDE already exists and is not ours. Merge by hand rather than
     have this script overwrite something the live site may depend on."
fi

cp "${REPO_DIR}/kbh/docker-compose.prod.yml" "$OVERRIDE"
echo "    wrote $OVERRIDE"

say "Validating before anything is applied"
if ! docker compose -f "$MAIN_COMPOSE" -f "$OVERRIDE" config -q; then
    rm -f "$OVERRIDE"
    die "compose config is invalid. The override has been removed and nothing
     was changed. The live site is untouched."
fi
echo "    configuration parses"

# --------------------------------------------------------------------------
say "Building"
# --------------------------------------------------------------------------

cd "$COMPOSE_DIR"
docker compose build ai-vaerksted-kbh
docker compose up -d ai-vaerksted-kbh ai-vaerksted-kbh-cron

# --------------------------------------------------------------------------
say "First run, so the site is not empty"
# --------------------------------------------------------------------------

# --no-ai because the claude CLI is not authenticated in the container. See
# DEPLOY_VPS.md. Numbers, scoring and geometry all work without it.
docker compose exec -T ai-vaerksted-kbh-cron \
    python -m kbh.pipeline run --no-ai --no-alerts || \
    warn "The first pipeline run failed. The site will load but be empty."

# --------------------------------------------------------------------------
say "Verifying"
# --------------------------------------------------------------------------

echo "    containers:"
docker compose ps --format '      {{.Name}}  {{.Status}}' | grep kbh || true

echo "    unauthenticated request (expect 401):"
curl -sS -o /dev/null -w '      %{http_code}\n' https://ai-vaerksted.cloud/boligjagt/ || true

echo "    cron schedule:"
docker compose logs --tail 5 ai-vaerksted-kbh-cron 2>/dev/null | sed 's/^/      /' || true

echo "    listings in the database:"
docker compose exec -T ai-vaerksted-kbh \
    python -c "import sqlite3;print('     ', sqlite3.connect('/data/kbh.sqlite3').execute('select count(*) from listings').fetchone()[0], 'listings')" \
    2>/dev/null || warn "could not read the database"

say "Done"
echo "    https://ai-vaerksted.cloud/boligjagt/"
echo "    Roll back with:"
echo "      rm ${OVERRIDE} && cp ${MAIN_COMPOSE}.bak-${STAMP} ${MAIN_COMPOSE} && docker compose up -d"
