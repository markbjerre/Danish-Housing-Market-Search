# Deploy the Copenhagen apartment monitor on ai-vaerksted.cloud

**Last updated:** 2026-08

Flask under gunicorn behind Traefik, plus a second container running the daily
pipeline on cron. Follows the same shape as `wedding-shopping-list`, with three
deliberate differences noted below.

## How this differs from the wedding app

Read these before starting. Each one will bite otherwise.

**It is on a subdomain, not a path prefix.** The wedding app sits at
`/wedding-shopping/`. This one cannot: the templates use root relative links
throughout (`href="/bolig/.."`, `fetch('/api/rate')`) and contain no `url_for`
at all, so serving it under `/kbh` breaks every link and every API call on the
page. A subdomain costs one DNS record. A path prefix costs a rewrite of six
templates and the JavaScript in them.

**It has state.** The wedding app is stateless and keeps everything in
Supabase. This keeps a SQLite file, so both containers mount a named volume at
`/data`. Losing that volume is survivable, a full run rebuilds it from
Boligsiden, but it also loses every star rating and comment, which are the only
things in there that cannot be refetched. Back it up.

**It has no authentication whatsoever.** No login, no Supabase Auth, nothing.
The pages carry private ratings and written notes about specific homes. Traefik
basic auth is the minimum before it faces the public internet, and it is
configured below. If you would rather it never be public at all, see
"Tailscale only" at the end.

## 1. DNS

Add an A record before anything else, or the certificate request fails and
Traefik will keep retrying against Let's Encrypt rate limits:

```
boliger.ai-vaerksted.cloud.   A   72.61.179.126
```

Confirm it resolves before continuing:

```bash
dig +short boliger.ai-vaerksted.cloud
```

## 2. Repo on the server

```bash
ssh root@72.61.179.126
cd /opt/ai-vaerksted
git clone -b kbh-apartment-monitor \
  https://github.com/markbjerre/Danish-Housing-Market-Search.git
# or: cd Danish-Housing-Market-Search && git pull
```

The build context is the **repository root**, not `kbh/`, because the package is
imported as `kbh.something` and needs its parent on the path.

## 3. Secrets in /root/.env

```bash
# Telegram, for alerts and the morning digest. Without these the pipeline still
# runs and scores, it just has no way to tell you anything.
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHAT_ID=987654321

# Basic auth for the web UI. Generate with:
#   htpasswd -nbB mark 'a-real-password' | sed -e 's/\$/\$\$/g'
# The doubled dollar signs are required. Compose eats single ones and you get
# a login that rejects the correct password with no useful error.
KBH_BASIC_AUTH=mark:$$2y$$05$$...
```

## 4. docker-compose services

Copy both services and the `volumes:` block from
`kbh/docker-compose.prod.yml` into `/root/docker-compose.yml`, alongside
`ai-vaerksted-wedding-shopping`.

## 5. Build and run

```bash
cd /root
docker compose build ai-vaerksted-kbh
docker compose up -d ai-vaerksted-kbh ai-vaerksted-kbh-cron
```

## 6. First run, to populate the database

The volume starts empty, so the site has nothing to show until a pipeline run
has happened. Do not wait for 07:00:

```bash
docker compose exec ai-vaerksted-kbh-cron \
  python -m kbh.pipeline run --no-ai --no-alerts
```

About two minutes for roughly 1.050 listings. Then check:

```bash
docker compose exec ai-vaerksted-kbh-cron \
  python -m kbh.pipeline top -n 10
```

## 7. Verify

```bash
curl -sI https://boliger.ai-vaerksted.cloud/ | head -5     # expect 401
curl -sI -u mark:PASSWORD https://boliger.ai-vaerksted.cloud/ | head -5   # expect 200
docker compose logs --tail 20 ai-vaerksted-kbh-cron        # expect the cron schedule line
```

The cron container prints its schedule on start. If it does not, cron is not
running and the daily update will never happen.

## The AI verdicts do not move to the server for free

This is the one part that does not lift and shift, so `KBH_AI_ENABLED` is `0`
in the compose file.

The verdicts shell out to the **`claude` CLI**, not to the Anthropic API. That
is deliberate and it is the whole cost model: 195 verdicts cost 3,57 USD
because they bill an existing subscription rather than API rates. The CLI is
not in the image, and installing it is the easy half. Authenticating it is the
problem: that is an interactive OAuth flow, and a container has nobody to click
anything.

Three options, in the order I would try them:

1. **Leave verdicts on the laptop.** The VPS serves the site and runs the
   numbers daily; the Windows scheduled task keeps producing verdicts against
   the local database. Simplest, and it works today, but you then have two
   databases and have to pick one as the truth.
2. **Install and authenticate the CLI on the VPS host**, then mount the
   credential directory into the cron container and set `KBH_AI_ENABLED=1`.
   Authenticate once by hand over SSH. Check where the CLI stores its token
   before relying on this, and treat the mount as a secret.
3. **Switch to the Anthropic API with a key.** Cleanest to operate, and it
   changes the economics: you pay list price for what a subscription currently
   covers. Only worth it if the verdicts move to a bigger model anyway.

Numbers, scoring, geometry, alerts and the whole web UI work on the VPS without
any of this. Only the verdict text is affected.

## Tailscale only, if you would rather it not be public

The VPS is already on Tailscale at `100.77.253.18`. Binding the service to the
Tailscale interface instead of giving it a Traefik router means the site is
reachable from your own devices and from nowhere else, and the basic auth
becomes unnecessary. Given that the pages contain private notes about homes you
may be bidding on, this is the option I would pick.

## Backups

The ratings are the only irreplaceable data:

```bash
docker compose exec ai-vaerksted-kbh \
  python -c "import sqlite3,json;c=sqlite3.connect('/data/kbh.sqlite3');print(json.dumps([dict(zip([d[0] for d in c.execute('select * from ratings').description], r)) for r in c.execute('select * from ratings')],ensure_ascii=False))" \
  > ratings-backup-$(date +%F).json
```
