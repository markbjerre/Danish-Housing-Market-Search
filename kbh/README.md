# Copenhagen apartment monitor

Watches the Copenhagen market for homes between 5 and 10 million kroner, scores
every listing against hyperlocal benchmarks, asks Claude to read the listing the
way a sceptical buyer would, and pushes the good ones to Telegram.

Independent of the villa pipeline in `src/` and `webapp/`: own SQLite file, own
config, own web app, own port. Nothing in `kbh/` touches the PostgreSQL
database.

## Quick start

```bash
python -m venv .venv
.\.venv\Scripts\activate          # Windows
pip install -r kbh/requirements.txt

# First pass. Fetch and score everything, then read the 25 best listings.
# Fetching and scoring all 1.050 takes about two minutes; the AI verdicts are
# the slow part, so start capped and lift the cap when you trust it.
python -m kbh.pipeline run --no-alerts --ai-limit 25

# The full backfill: 195 verdicts, about 25 minutes, about 3,60 USD.
python -m kbh.pipeline run --no-alerts

# Look at it
python -m kbh.webapp.app          # http://127.0.0.1:5001
python -m kbh.pipeline top -n 20  # or from the terminal
```

## What it monitors

| Scope | Municipality | Type |
|-------|--------------|------|
| Ejerlejlighed | København (101) | `condo` |
| Ejerlejlighed | Frederiksberg (147) | `condo` |
| Villa | København (101) | `villa` |
| Rækkehus | København (101) | `terraced house` |

Roughly 1.050 listings in the price band, of which about 500 clear the hard
filters. Adjust in `config.py`.

## Hard filters

A listing failing any of these is stored but never scored, alerted or shown by
default. They are visible at `/udelukkede` with the reason, so a wrong filter
can be spotted rather than silently swallowing half the market.

- Minimum 90 m² living area
- No ground floor or basement (condos only)
- Price must be stated
- No houseboats

The houseboat filter is not an obvious one. Boligsiden files them as
`addressType: villa`, and because a berth in Sydhavn asks around 41.000 kr/m²
against a Sydhavn benchmark of 70.250, they land straight at the top of a value
ranking while being a different asset class: leased berth, no land, financing
that is not a normal realkreditlån. Two of them held rank two and three until
this was added, and the AI verdict is what found them: it opened with "Det er en
husbåd, ikke en villa".

Detection is on the listing text, and the pattern has to separate the boat being
sold from boats in the view. The first version wrongly flagged two ordinary
flats, one describing the outlook over "de karakterfulde husbåde" next door and
one offering a "privat bådplads i den private marina" as a purchasable extra. So
a berth never counts, and only the singular forms of husbåd do: nobody sells you
several. Both cases are pinned in `tests.py` with the real wording.

Balcony and terrace are **not** hard filters. They add a capped bonus, because
making them mandatory would drop a third of the pool and would also trust a
field that turns out to be wrong (see below).

## Scoring

Ten weighted factors, each normalised to 0 to 100. Weights live in
`config.WEIGHTS` and are validated at import to sum to 100.

| Factor | Weight | What it measures |
|--------|--------|------------------|
| Kvadratmeterpris mod sognet | 27 | Asking kr/m² against the local benchmark |
| Kvarter | 15 | Neighbourhood preference tier |
| Størrelse | 10 | Absolute m², from the 90 m² floor up to 160 |
| Værelser og rumfordeling | 8 | Room count, with a deduction for cupboards |
| Afstand til metro og S-tog | 8 | Metres to the nearest platform |
| Stand, energi og alder | 8 | Energy label, effective year, BBR fixtures |
| Afstand til vand | 7 | Metres to harbour, canals, the lakes or the coast |
| Vejstøj og banestøj | 6 | Exposure to road and rail noise |
| Forhandlingsposition | 6 | Days listed, price cuts, weak demand |
| Ejerudgift | 5 | Monthly cost per m² against the pool median |

Plus a bonus capped at 5 points: balcony 3, terrace 2, lift 1.5.

### Weight profiles

The table above is the `Balanceret` profile. Four are built in, switchable from
the top of the list page, plus a custom one with sliders:

| Profile | Leans on | m² price | Kvarter | Vand | Størrelse | Værelser | Tog | Støj |
|---------|----------|---------:|--------:|-----:|----------:|---------:|----:|-----:|
| **Balanceret** (default) | Price and neighbourhood | 27 | 15 | 7 | 10 | 8 | 8 | 6 |
| **Ved vandet** | Harbour, canals and lakes | 26 | 15 | 14 | 9 | 7 | 6 | 5 |
| **Værdijæger** | Underpricing and a tired seller | 40 | 8 | 4 | 8 | 5 | 5 | 4 |
| **Plads for pengene** | Square metres and rooms | 26 | 10 | 4 | 22 | 12 | 6 | 5 |

**A saved custom weighting inherits factors added after it was saved.** This is
not cosmetic. The first run after rooms, transit and noise were added scored
all 501 listings with those three at weight zero, because the stored custom
profile had no key for them and normalising treated absent as "slider dragged
to zero". The pipeline logged it and looked entirely normal doing it. Absent
now means "never asked" and inherits the default, while an explicit zero from
the slider form still means off.

**Switching costs nothing and re-evaluates nothing.** Every factor's 0 to 100
score is already stored per listing, so a profile change is arithmetic on
numbers we have: the whole pool of 500 re-ranks in about 0,15 seconds with no
API call and no model involved. The AI verdict describes the flat itself and is
unaffected by how the flat is weighted.

What it does change is real. Mean distance to water across the top ten:

| Profile | Mean distance to water, top 10 |
|---------|-------------------------------:|
| Ved vandet | 195 m |
| Balanceret | 329 m |
| Værdijæger | 551 m |

`Værdijæger` surfaces Valby, Nordvest and Vejlands Allé, none of which appear
anywhere near the top under `Ved vandet`.

The active profile is stored in the database, not in the session, so the web
app, the pipeline and the Telegram alerts all rank the same way. `?profil=<key>`
previews one without saving it. A custom weighting takes any slider values and
normalises them to sum to 100.

Every factor returns its own reasoning string, so the score is auditable line by
line on the detail page. A missing input scores an explicit neutral 50 and is
flagged rather than being punished as a zero.

### The benchmark is two benchmarks

The obvious approach is to compare a flat's kr/m² to realised sales in its own
parish (sogn), which Boligsiden exposes as GeoJSON with prices attached.
Copenhagen splits into 56 parishes and the spread is wide, from about 90.700
kr/m² in Nordhavn down to 35.600 in Husumvold.

That alone produces a wrong answer. Parishes are administrative, not economic.
The Islands Brygges parish covers both Islands Brygge at roughly 73.000 kr/m²
and all of Ørestad at roughly 53.000. Benchmarked against its parish, every
Ørestad flat looks 25 to 45 pct. underpriced. The first version of this scorer
returned a top twelve that was nine tenths Ørestad.

So each listing is also benchmarked against its immediate competition: the
median asking kr/m² of comparable listings within 1.200 m, with a 3 pct.
haircut for the gap between asking and realised prices. The two are combined
with `min()`, so "cheap" has to mean cheap against both the wider area and the
flats you would actually be bidding against. About half the pool ends up
scored on the peer benchmark.

### Water

Copenhagen harbour is tidal seawater, so OpenStreetMap's `natural=coastline`
traces Øresund and the whole harbour including Nordhavn, Islands Brygge,
Christianshavn and Sluseholmen in a single pull. Canals and the three lakes on
Søerne come separately. Geometry is cached to `kbh/data/water.geojson` on first
use.

Prime water (harbour, canals, the lakes, the coast) scores on the full curve:
100 points at 150 m or closer, zero at 1.800 m. Secondary water (ponds, moats,
inland lakes) is capped at 55.

Ørestad's drainage canals are demoted to secondary. OSM tags them as canals,
which would otherwise rank a flat facing a narrow concrete channel between two
office blocks the same as one on Christianshavns Kanal.

### Transit

Metro, S-tog and regional platforms from OpenStreetMap, cached to
`kbh/data/transit.geojson`. 106 stations: 44 metro, 53 S-tog, 9 regional.

The classification is not obvious. OSM Denmark tags the Metro as
`station=subway` as you would expect, but tags the S-tog as
`station=light_rail`, which is wrong in spirit: an S-tog is heavy suburban rail
and nothing like a tram. The regional stops carry no `station` tag at all.

The curve starts falling at 250 m, not at a comfortable five minute walk.
Measured against the real pool, a gentler curve put half of all listings at 98
or better and separated nothing. Median distance across the pool is 437 m.

### Noise

**Road noise is modelled from lane count and speed limit, not from the OSM
highway class.** That is forced by how Denmark is tagged, and getting it wrong
makes the factor worse than useless.

Danish OSM reserves `primary` and `secondary` for the national numbered road
network. Every major urban artery in Copenhagen is therefore `tertiary`:
H.C. Andersens Boulevard, Åboulevard, Vesterbrogade, Jagtvej, Tagensvej,
Amagerbrogade and Østerbrogade are all the same class as a quiet residential
through street. The first version of this factor was built on highway class
and scored the busiest road in the country as silent, while a flat on
Østerbrogade came out at a perfect 100.

Lanes and speed are tagged on 90 pct. and 99 pct. of those ways respectively,
and they separate the same streets correctly: H.C. Andersens Boulevard runs 3
to 5 lanes at 50 to 60, while Nørrebrogade runs 1 to 2 lanes at 40 because it
has been traffic calmed. That difference is real and the class tag cannot see
it.

Two things the implementation has to get right or the numbers are nonsense:

- **Sources combine in energy, not by addition.** Adding penalties straight up
  put 123 of 501 listings under 40 and zeroed an ordinary Frederiksberg address
  that merely had four moderate streets around it, level with a flat on a
  railway embankment. Sound adds logarithmically and the loudest source
  dominates, so the penalties are combined the same way.
- **One street contributes once.** OSM splits Åboulevard into 24 separate ways.
  Charging a flat once per way puts any address near a busy road at zero, so
  hits are grouped by street name and only the nearest is counted.

The result reads correctly against addresses you can walk to: the worst in the
pool are Torvegade, Vester Søgade at Gyldenløvesgade, and Tagensvej 77. Median
78, with 44 listings genuinely quiet.

This is a proxy for traffic volume, not measured sound. Denmark publishes
modelled Lden contours under the EU noise directive, which would be strictly
better; the portal serving them needs a registered account, so it sits in
`TODO.md` rather than in here.

### Neighbourhoods

Labels come from the postal code groups Boligsiden itself uses, which match how
Copenhageners talk about the city. Named sub-areas in `config.NAMED_AREAS`
override the postal code where it is too coarse:

- **Upwards**: Amager Strandpark, Islands Brygge, Christianshavn, Amagerbro and
  Havneholmen all sit in postal codes whose average understates them.
- **Downwards**: Ørestad shares postal code 2300 with Amager Strandpark and is a
  completely different place, so it overrides the tier down rather than up.

## AI verdicts

Every listing above the score gate gets read by Claude: the full realtor text,
the photo descriptions, the score breakdown, the sale history of that exact flat,
and the demand numbers. It returns structured JSON, not prose to be parsed.

This shells out to the `claude` CLI rather than the Anthropic API, so there is no
key to manage and it bills against the existing subscription.

### Three things keep the cost down

**Haiku, not Sonnet.** The model is reading structured facts and a realtor text
against an explicit checklist. That does not need a larger model.

**Photo descriptions instead of photos.** Every image on Boligsiden carries a
machine written description, for example "En altan med trædæk har en åben dør,
potteplanter og en bænk med puder". That answers "what do the photos show" for
free, where five actual images cost around 55.000 input tokens per listing. Set
`KBH_AI_USE_PHOTOS=1` to send real images for a shortlist that has earned it;
vision is used only when a single listing is evaluated on its own.

**Batching.** Every CLI call carries roughly 38.000 tokens of fixed Claude Code
system prompt before a word of listing text, and `--strict-mcp-config
--setting-sources ""` are what got it down to that from 63.700. Paying it once
per listing is the single largest cost in a backfill. Six listings per call
amortises it.

Together these took a verdict from **0.229 USD to 0.018 USD per listing**, a
factor of twelve. The real backfill on 10 August 2026 read 195 listings in 33
calls for **3,57 USD total** with no errors. The same work one listing at a time
with Sonnet and photos would have been about 45 USD.

### Photos: what the model must not conclude

**Boligsiden hands out exactly five images per listing.** Measured across 50
listings: 49 had five, one had four. No parameter unlocks more, on either the
search or the detail endpoint. The realtor's own advertisement almost always has
twenty or more.

The first version of the prompt did not know this, and told the model that
missing photographs of the kitchen or the bathroom were a signal. They are not.
They are an artefact of our data source. **67 pct. of the first 201 verdicts
carried a red flag of that kind, and 116 of those had been pushed below "se den"
partly on that basis.** All 201 were thrown away and re-run.

The rule now: a room not being photographed says nothing and must never appear
in `red_flags` or reduce confidence. What it produces instead is
`tjek_hos_maegler`, a short list of what to look at in the realtor's own
advertisement, shown on the detail page next to a link straight to it.

One photo observation stays a genuine red flag: images that are 3D renders or
styled visualisations rather than photographs of the actual home. That is real
information, because it means the flat is a projektsalg that may not be built.

### The public valuation is a constant, not a signal

The same class of error, found later and fixed the same way. The prompt handed
the model `OFFENTLIG VURDERING` as a bare number, and the model correctly
observed that asking prices sat far above it. On the top scoring listing it
reported a public valuation of 5,4 mio. against an asking price of 9,7 mio. as
a finding.

It is not a finding. Copenhagen flats are still assessed at the frozen 2011 and
2012 level, so **the median asking price across the pool is 3,44 times the
public valuation**, with a tenth percentile of 2,78 and a ninetieth of 4,66.
Every flat in the city looks individually overpriced by a factor of three,
which means none of them do. One verdict flagged a "5,7x afvigelse" as critical
when 5,7 is barely outside the normal range.

Six of 209 verdicts carried it as a red flag. Those six were deleted so they
get re-read; the rest were unaffected and were left alone.

The prompt now states the listing's own ratio **and** the pool median together,
and says the number is only worth mentioning when the two differ sharply. The
median is computed per run in `MarketContext`, so it tracks the market rather
than being a constant someone has to remember to update.

### Floor plans

`floor_plan_url` is stored for 442 of 1.049 listings and shown on the detail
page, with a `plan` badge on the list card.

Boligsiden serves images from a whitelist of sizes rather than resizing on
demand. `600x400` is what the search payload carries and is unreadable for a
plantegning; `1440x960` is the largest that answers, while `800x600` and
`1920x1080` both return 403. The detail page swaps the size segment up.

**Why not scrape the realtor?** It was checked rather than assumed. The chains
are fragmented (nybolig 15, home 10, danbolig 7, edc 5, lokalbolig 5,
realmæglerne 4, plus a long tail) and nybolig and danbolig, the two largest,
render their galleries in JavaScript and return zero image URLs in static HTML.
It would need a headless browser plus a bespoke parser per chain, each breaking
on every redesign. Not worth it for pictures that a single click on the
"Mægler" link already gives you.

### Batches are dealt, not sliced

Listings are sorted by score before batching, and adjacent scores are very often
two flats in the same building. Slicing put Flyndervej 3B and 3C in one batch and
the model wrote "samme projekt som 3C" and "den mindste af alle udbudte". The
first is meaningless read alone in Telegram; the second is simply false, since
the model sees six flats out of five hundred.

So the sorted list is dealt round robin into batches instead, which puts six
unrelated flats from different neighbourhoods in each one. The prompt also
forbids set-relative superlatives outright.

### When a call hangs

Occasionally a CLI invocation starts and never spawns its child process, then
sits at zero CPU until it times out. It happened once in a 33 batch run. Every
call therefore has a 420 second timeout, a timed out batch is treated as
unanswered, and its listings are retried one at a time afterwards. Nothing is
lost, the run just takes a few minutes longer.

If a whole run dies, rerunning is safe and cheap: verdicts already stored are
not requested again, so it picks up exactly where it stopped.

Batching has one failure mode worth knowing about: the model starts writing
"same as listing 2, but smaller", which is useless when the verdict arrives on
its own in Telegram. The instructions forbid it explicitly. Verdicts are matched
back to listings by an echoed id rather than by position, so a reordered or
short response can never attach a verdict to the wrong flat, and anything the
batch fails to answer for is retried on its own.

### Cost in practice

The score gate (`KBH_AI_MIN_SCORE`, default 62) keeps the backfill to the ~195
listings worth reading rather than all 500. That was 3,57 USD and 24 minutes.
Use `--ai-limit` to spread it over several runs.

After the backfill only listings that are new or have changed price get re-read,
a handful per day, so steady state is cents. Every run reports what it spent.

A verdict is re-requested when the asking price moves, because a price
assessment written against 9,2 mio. is stale advice once the seller drops to
8,4 mio.

A verdict is re-requested when the asking price moves, because a price
assessment written against 9,2 mio. is stale advice once the seller drops to
8,4 mio.

### What it actually catches

From the first backfill, things the numbers alone would have missed:

- "Alle billeder er renders" on two newbuilds, so nothing shown exists yet.
- "Købt for 5,55 mio. i nov. 2024, nu 7 mio. uden dokumenteret renovering", a
  26 pct. markup in nine months, spotted off the sale history.
- "Ejerbofællesskab med fælles forpligtelser, ikke en almindelig ejerlejlighed."
- Repeatedly: no photographs of the kitchen or the bathroom, in listings with
  five or more photographs of everything else.
- On the top scoring listing, that the public valuation is 5,4 mio. against an
  asking price of 9,7 mio.

It also found the houseboat problem described above, which then became a filter.

### The model corrects the data

`hasBalcony` from the API is unreliable in both directions, so each verdict
returns `balcony_confirmed` judged from the listing text and the photo
descriptions together. That is written back to `listings.balcony_ai` in its own
column, never overwriting the API value, so the disagreement stays visible. From
the next scoring pass onwards the model's reading is what decides the balcony
bonus, the "altan" badge and the balcony filter. A run reports how many listings
it disagreed with the API about.

## Rating and taste

The score encodes what Mark *said* he wants. The ratings measure what he
actually picks, and the two are not the same thing.

**Rating** is 1 to 5 stars plus a written comment, available in three places:

- `/bedoem` is the fast one. One listing at a time, photo, key facts and the AI
  verdict, then `1` to `5` for stars, type a comment, `Enter` to save and
  advance, `S` to skip. Built for volume, because the analysis needs tens of
  judgements and nobody produces those from a page that reloads.
- The list at `/` has inline stars on every card. Clicking the star you already
  gave clears the rating.
- The detail page has stars and a full comment box.

**The comment matters more than the stars.** Stars say which flats; a sentence
says why, and why is what generalises to the next listing.

**`/moenstre`** turns that into:

| Section | What it answers |
|---------|-----------------|
| Comment analysis | Claude reads every comment and names the pattern, including one thing the ratings reveal that Mark has probably not said out loud |
| Separating factors | Mean of each attribute among 4 and 5 star flats against 1 and 2 star flats, ranked by how sharply it separates them |
| Neighbourhoods by stars | His own ranking, to hold against the tiers in `config.py` |
| Score agreement | Rank correlation between the model's score and his stars, from minus 1 to 1. This is the model being marked, not the flats |
| Suggested weights | What `WEIGHTS` would look like if it followed his ratings |

Two rules the analysis holds to, because the alternative is a machine sounding
confident about eleven data points:

- Nothing numeric is reported below 4 ratings on each side. One sided ratings
  produce no findings at all, and the page says so rather than inventing a
  pattern.
- Nothing is applied automatically. The suggested weights are printed for a
  human to accept or ignore. A handful of ratings must not silently rewrite the
  model. They do sum to exactly 100 so they can be pasted into `config.py`
  followed by a `rescore`.

## Telegram

Two separate paths:

- **Alerts** are pushed by the pipeline through plain HTTP (`notify.py`). Instant
  ping for anything above `KBH_ALERT_THRESHOLD`, or for a price cut of 2 pct. or
  more on something already tracked. One message per listing per event kind,
  never repeated. On the first run with alerts enabled every listing on the
  market counts as new, so instant pings are suppressed and the backlog goes out
  as a single digest instead. Real alerts start from the second run.
- **The bot** (`bot.py`) is a long running process for asking questions back:
  `/top`, `/nye`, `/prisfald`, `/vand 300`, `/kvarter Nørrebro`, `/bolig
  Strandvej`, `/status`. Read only.

### Setup

1. Message [@BotFather](https://t.me/BotFather) in Telegram, send
   `/newbot`, and copy the token.
2. Send your new bot any message, then open
   `https://api.telegram.org/bot<TOKEN>/getUpdates` and read `result[0].message.chat.id`.
3. Put both in `.env`:

```
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHAT_ID=987654321
```

Without them the pipeline still runs and scores; it just logs a warning and
prints the digest instead of sending it.

## Commands

```bash
python -m kbh.pipeline run                    # full pass, alerts on
python -m kbh.pipeline run --no-alerts        # silent
python -m kbh.pipeline run --no-ai            # numbers only, about 2 minutes
python -m kbh.pipeline run --ai-limit 25      # cap the model calls
python -m kbh.pipeline run --ai-min-score 70  # raise the gate
python -m kbh.pipeline rescore                # rescore stored data, no search calls
python -m kbh.pipeline digest                 # send the morning summary
python -m kbh.pipeline top -n 20              # leaderboard in the terminal

python -m kbh.webapp.app                      # web UI on port 5001
python -m kbh.bot                             # interactive Telegram bot
```

## Tests

```bash
python -m kbh.tests
```

70 tests, no network and no database. They cover the logic that fails silently:
hard filter boundaries, houseboat detection, the shape of every scoring curve,
the neighbourhood overrides in both directions, the peer benchmark, and the
batch response parser. That last one matters most, because a batch reply that
gets matched back by position instead of by id would attach a verdict to the
wrong flat and look entirely normal doing it.

Everything else (the API, the database, the model) fails loudly on the first run,
so it is not mocked.

## Scheduling

One task, every morning at 07:00: fetch, score, read anything new or repriced,
send instant alerts, then send the digest.

It is a single task rather than a separate fetch and digest, because two tasks
race: the digest fires while the run is still fetching and summarises
yesterday's board.

### What is registered

```powershell
Get-ScheduledTaskInfo -TaskName "KBH boliger morgen"
```

Everything goes through `kbh/scripts/daily_update.ps1`, not straight at the
module. A scheduled run has no console and nobody watching it, so a failure
that prints to stderr and dies looks exactly like a quiet market. The wrapper
logs every line to `kbh/data/logs/kbh-YYYY-MM-DD.log` and keeps a month.

Exit codes: 0 fine, 1 the run failed, 2 the run worked but the digest did not.
The digest is deliberately non-fatal, because fresh data with no summary beats
neither.

To register it on another machine:

```powershell
$script = "C:\Users\MarkBjerregaard\Documents\Private\Housing Project\kbh\scripts\daily_update.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$script`""
$trigger = New-ScheduledTaskTrigger -Daily -At 07:00
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
  -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries `
  -ExecutionTimeLimit (New-TimeSpan -Hours 2)
Register-ScheduledTask -TaskName "KBH boliger morgen" -Action $action `
  -Trigger $trigger -Settings $settings -Force
```

Use the `ScheduledTasks` cmdlets, not `schtasks /create`. The project path
contains a space and `schtasks` mangles the quoting of `/tr` around it.

**`-StartWhenAvailable` matters on a laptop.** The machine is usually asleep at
07:00. Without it a missed trigger is simply skipped and the first anyone knows
is stale data; with it the run happens when the lid next opens.

### Never route it through cmd.exe

The obvious `schtasks /tr "cmd /c cd /d ... && python -m kbh.pipeline run"` is
wrong, and it fails in the worst possible way. The AI verdicts shell out to the
`claude` CLI, and `shutil.which("claude")` returns `claude.CMD`, an npm shim.
**A `cmd.exe` started from a process with no console never hands off to its
child**, so the shim sits there and the CLI never starts. Nothing errors. The
run hangs until the two hour limit kills it.

`ai.py` resolves the shim to the real `.exe` for exactly this reason. Do not
simplify that away, and do not add a `cmd /c` wrapper back.

Verified by running the registered task under the real scheduler with the model
enabled, not by assuming.

### On the VPS

```cron
0 7 * * * cd /root/housing && .venv/bin/python -m kbh.pipeline run >> /var/log/kbh.log 2>&1
```

No shim problem on Linux. The `claude` CLI has to be installed and
authenticated as the user cron runs as, or set `KBH_AI_ENABLED=0` and accept
numbers without verdicts.

### Checking it worked

```powershell
Get-ScheduledTaskInfo -TaskName "KBH boliger morgen"   # LastTaskResult 0 is good
Get-Content "kbh\data\logs\kbh-$(Get-Date -Format 'yyyy-MM-dd').log" -Tail 30
```

Or from the data itself, which is the answer that cannot lie:

```bash
python -c "import sqlite3;c=sqlite3.connect('kbh/data/kbh.sqlite3');print(c.execute('select started_at,finished_at,seen,new_listings,price_drops,delisted from runs order by id desc limit 3').fetchall())"
```

Runs are idempotent. Running twice in a row changes nothing but `last_seen`,
and verdicts already stored are never re-requested, so a manual run after a
scheduled one costs nothing.

### Running it by hand

```powershell
# The real thing
.\kbh\scripts\daily_update.ps1

# Plumbing only. No model calls, no Telegram, no cost.
.\kbh\scripts\daily_update.ps1 -NoAi -NoAlerts
```

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `TELEGRAM_BOT_TOKEN` | | Required for alerts and the bot |
| `TELEGRAM_CHAT_ID` | | Required for alerts |
| `KBH_DB_PATH` | `kbh/data/kbh.sqlite3` | Database location |
| `KBH_ALERT_THRESHOLD` | 72 | Score needed for an instant ping |
| `KBH_AI_ENABLED` | 1 | Set to 0 to skip verdicts entirely |
| `KBH_AI_MIN_SCORE` | 62 | Score gate for verdicts |
| `KBH_AI_MODEL` | `claude-haiku-4-5-20251001` | Per listing verdicts |
| `KBH_AI_SYNTHESIS_MODEL` | `claude-opus-5` | Daily digest summary |
| `KBH_AI_WORKERS` | 3 | Concurrent CLI processes |
| `KBH_AI_BATCH_SIZE` | 6 | Listings per CLI call |
| `KBH_AI_USE_PHOTOS` | 0 | Send real images instead of their descriptions |
| `KBH_AI_MAX_IMAGES` | 5 | Photos per verdict when images are on |
| `KBH_CLAUDE_BIN` | found on PATH | Force a specific claude binary |
| `KBH_WEB_PORT` | 5001 | Web app port |

## Boligsiden API notes

Verified live on 10 August 2026. Several of these contradict the notes in the
root `claude.md`, which were written for the villa pipeline and are now partly
out of date.

**Endpoints the villa pipeline does not use:**

| Endpoint | What it gives |
|----------|---------------|
| `/cases/bulk/stats?caseID=..` | Page views, clicks, favourites. Max 25 ids |
| `/cases/{id}/timeline` | Price events on the listing |
| `/addresses/{id}/timeline` | Sale history back to the early 1990s, plus year built |
| `/case/stats/municipality-average` | Average price and m² by room count. Note the singular `/case/` |
| `/municipalities/{code}/parish_divisions/heatmap` | Parish polygons with realised m² prices |
| `/municipalities/{code}/zip_codes/heatmap` | The same per postal code |
| `/municipalities/{code}/institutions` | Schools and daycare with coordinates |
| `/search/ai?q=..` | Parses natural language into a search query |

**Quirks, all found by testing rather than documentation:**

- `/search/cases` accepts **59** filters, including `polygon`, `multiPolygon`,
  `radius`, `balcony`, `elevator`, `terrace`, `energyLabels`, `costMin/Max`,
  `filterPriceDrop` and `freeText` with `semantic`.
- `municipalities` takes exactly one name. A comma separated list returns zero
  hits rather than an error, which is a silent trap. `zipCodes` behaves the same
  way.
- `sortBy=semanticRanking` is rejected by `/search/cases` even though the
  frontend bundle lists it as valid.
- `/cases/bulk/stats` answers 400 above 25 ids.
- `/search/cases` already returns the full payload including `descriptionBody`,
  `images`, `floorPlanImages` and `nextOpenHouse`. **No detail call is needed**,
  which is why one pass over the whole pool takes seconds.
- The parish heatmap returns either `sold_per_area_price` from recent sales or
  `sold_per_area_price_yearly` over a wider window where volume is thin. Some
  parishes return neither. Which one was used is carried into the score
  reasoning, because a twelve month window deserves less confidence.
- **`hasBalcony` is not reliable.** Case `66f18380` on Århusgade returns
  `hasBalcony: false` while its own headline reads "Klassisk Østerbro-charme med
  altan". Both the flag and a text search are kept, and the text is allowed to
  win.
- **Exactly five images per listing, always.** Not a coincidence and not a
  per-listing choice: it is a hard cap. `imageCount`, `per_image_page` and
  `includeImages` are all ignored. Do not let anything downstream conclude
  anything from a room being unphotographed. `floorPlanImages` is separate and
  ranges from 0 to 3.
- Each image carries machine written Danish alt text describing what it shows,
  which is a free substitute for sending the image itself to a model.

## Found but not used yet

Endpoints and filters that exist and would each add something, listed so the
discovery is not lost:

| Thing | What it would give |
|-------|--------------------|
| `/search/foreclosure-cases` | Tvangsauktioner. A separate, cheaper supply nobody watches |
| `/search/rentals` | Rent for comparable flats, so a listing can be scored on yield as well as price |
| `/municipalities/{code}/institutions` | 123 schools and daycares in Copenhagen with coordinates. Walking distance as a factor |
| `polygon` and `multiPolygon` search filters | Draw the exact catchment on a map instead of approximating it with postal codes |
| `/cases/{id}/oblique` | Oblique aerial photography, which shows what the listing photos crop out |
| Demand over time | `/cases/bulk/stats` is captured every run, so favourites per day is already accumulating. A flat whose interest has flatlined is about to drop its price |
| Parish price drift | Benchmarks are stored per run, so a parish that is cooling faster than the city could be detected rather than guessed |
| Relisting detection | A flat sold and relisted gets a new `caseID` against the same `addressID`. Worth flagging: it usually means a sale fell through |

## Files

```
kbh/
├── config.py       search scope, hard filters, neighbourhood tiers, weights
├── boligsiden.py   API client, rate limited, retries
├── parse.py        case payload to listing row, hard filters
├── geo.py          water distance, parish lookup, neighbourhood resolution
├── benchmarks.py   parish, postal code, municipality and peer benchmarks
├── scoring.py      the seven factors and the weighted total
├── taste.py        what the 1 to 5 ratings say about what he actually likes
├── ai.py           Claude verdicts via the CLI, cost meter
├── notify.py       Telegram formatting and delivery
├── bot.py          interactive Telegram bot
├── db.py           SQLite schema, reads and writes
├── pipeline.py     the run, and the command line
├── tests.py        39 tests, no network, no database
├── webapp/         Flask UI on port 5001
└── data/           SQLite file and cached water geometry
```
