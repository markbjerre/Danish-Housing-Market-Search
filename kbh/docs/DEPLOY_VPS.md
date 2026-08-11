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

**Authentication is basic auth, and it is also the login system.** There is no
login page and there should not be one for two people. Traefik validates the
password and forwards the username, and the app reads that username to decide
whose ratings a click becomes. One account each.

## Two people rating the same homes

This is the part that needed real work rather than a config line.

Ratings used to be keyed on `case_id` alone: **one opinion per home, for
everybody**. The moment a second person gave a flat five stars, the first
person's stars and written comment were gone, and `/moenstre` started
describing a buyer who does not exist. Nothing would have errored.

Ratings are now keyed on `(case_id, rater)`:

- Each person has their own stars, their own comments, and their own rating
  queue at `/bedoem` showing what *they* have not judged.
- `/moenstre` runs per person. Averaging two buyers produces a preference
  profile that describes neither, so it does not.
- **`/uenighed`** is new and is the reason to bother: the homes you scored
  differently, widest gap first, with both comments side by side. Agreement
  needs no discussion. A three star gap is the conversation to have before
  spending a Saturday on a viewing.
- The header shows whose name the current session is rating as, because a
  rating landing on the wrong name is otherwise invisible until the taste
  analysis goes strange.

Existing ratings were migrated to the `KBH_RATER` default, `mark`. The old
single rater table is kept as `ratings_single_rater` rather than dropped,
because those judgements are the only data in the system that cannot be
refetched from Boligsiden.

Add the second person's display name to `RATER_NAMES` in `kbh/config.py` so
the header says "Anna" rather than "anna". The username in the htpasswd entry
is the rater key: keep it lowercase, and do not rename it later, because
renaming a login orphans that person's ratings under the old name.

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

# Basic auth for the web UI, and the app's only notion of who is who.
# One entry per person, joined with a comma. Generate each with:
#   htpasswd -nbB mark 'password-one' | sed -e 's/\$/\$\$/g'
#   htpasswd -nbB anna 'password-two' | sed -e 's/\$/\$\$/g'
# The doubled dollar signs are required. Compose eats single ones and you get
# a login that rejects the correct password with no useful error.
# The username becomes the rater key, so keep it lowercase and stable.
KBH_BASIC_AUTH=mark:$$2y$$05$$...,anna:$$2y$$05$$...
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
curl -sI https://boliger.ai-vaerksted.cloud/ | head -5                    # expect 401
curl -sI -u mark:PASSWORD https://boliger.ai-vaerksted.cloud/ | head -5   # expect 200
docker compose logs --tail 20 ai-vaerksted-kbh-cron       # expect the cron schedule line
```

The cron container prints its schedule on start. If it does not, cron is not
running and the daily update will never happen.

**Check that identity is arriving**, because a broken header degrades quietly
rather than failing. Log in as each person and confirm the name in the top
right of the page matches who you signed in as. If both people see the same
name, Traefik is not forwarding the Authorization header and every rating is
landing on one account.

```bash
curl -s -u anna:PASSWORD https://boliger.ai-vaerksted.cloud/ | grep -o 'whoami[^<]*<[^<]*'
```

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

## Why not Tailscale only

It was the tighter option and it is ruled out by the requirement: a second
person needs access from her own phone and laptop, and Tailscale means
installing a VPN client on every device she uses and keeping it connected. A
URL and a password is the right trade here. Basic auth over TLS, on a
subdomain nobody links to, for a site whose worst case disclosure is which
flats two people liked.

If that ever stops feeling sufficient, the upgrade is Traefik's forward auth
against an identity provider, not a login page bolted onto Flask.

## Backups

The ratings are the only irreplaceable data:

```bash
docker compose exec ai-vaerksted-kbh \
  python -c "import sqlite3,json;c=sqlite3.connect('/data/kbh.sqlite3');print(json.dumps([dict(zip([d[0] for d in c.execute('select * from ratings').description], r)) for r in c.execute('select * from ratings')],ensure_ascii=False))" \
  > ratings-backup-$(date +%F).json
```
