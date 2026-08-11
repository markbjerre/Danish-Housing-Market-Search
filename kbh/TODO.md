# Copenhagen apartment monitor, open work

Ordered by what it buys a buyer, not by effort. Everything here was scoped
against the live data rather than guessed at, so the notes include the traps
already found.

## Next up

### 1. Floor plan analysis

The plantegning is stored for 442 of 1.049 listings and is now shown on the
detail page. What it is not yet doing is answering questions.

Three the buyer actually asks, in his own words:

- Is the kitchen open to the living room, which counts as a plus.
- Is the space well used, or is a third of it hallway.
- How big is the bathroom, where bigger is better.

None of these can be read from the API. They can be read from the drawing, and
a floor plan is a single small image rather than five photographs, so vision is
affordable here in a way it was not for the gallery.

Two findings that make it cheap. Boligsiden serves images from a whitelisted
set of sizes, and `1440x960` is the largest that answers: `800x600` and
`1920x1080` both return 403. That is legible enough to read room labels and
areas, which Danish plantegninger almost always print. And one image per
listing costs a fraction of the five-photo gallery that was measured at
roughly 55.000 input tokens.

Implementation: extend the verdict schema with `floor_plan` fields, run it as
its own pass over listings that have a plan and a score above the gate, and
store the result in its own columns so it can be filtered on. Do not fold it
into the main verdict, because the main verdict is already backfilled and
re-running all 203 to add one field would be wasteful.

### 2. Realised sale prices, the feedback loop

Nothing in the system currently learns what anything sold for. `price_events`
holds 1.049 rows and every one says `listed`.

When a listing leaves the market, call `/addresses/{id}/timeline` (already used
in `boligsiden.py`) and record whether a sale completed and at what price.

Three things this unlocks, in order of value:

- The peer benchmark applies a flat 3 pct. haircut for the gap between asking
  and realised prices. That number is a guess. This measures it, per
  neighbourhood, and it moves with the market.
- A flat 20 pct. under benchmark is either mispriced or has a problem the
  photos hide. Today those are indistinguishable. Outcomes tell them apart.
- It is the target variable the hedonic model below needs. Trained on asking
  prices, a model learns to predict what sellers hope for.

A few hundred requests a week. It needs elapsed time more than it needs work,
which is why it should start running early even though it pays out late.

### 3. Hedonic price model

Gradient boosted regression on m², rooms, floor, year, energy label, distance
to water, distance to transit, noise score and parish, predicting realised
price. Score the residual: predicted minus asking. That is underpricing, as
against the current `min(parish, peer)` benchmark which only says "cheap for
its postcode" and cannot tell a top floor 2015 build from a fourth floor 1899
walk-up on the same street.

Blocked on item 2 for an honest target. Do not train it on asking prices.

### 4. Ejerforening finances from the salgsopstilling

The largest unpriced risk in a Copenhagen ejerlejlighed is a fællesgæld and a
facade renovation that the listing text does not mention. It is in the
salgsopstilling PDF, which the realtor links and Boligsiden does not parse.

One PDF fetch plus a targeted read, on the shortlist only. This is where a
200.000 kr. surprise lives.

### 5. Preference model on the ratings

`/moenstre` currently reports means and a rank correlation. Once there are
enough ratings, fit a model on the stored factor vectors and rank the whole
pool by predicted stars alongside the configured score. The disagreements are
the interesting list.

Blocked on ratings. Five is an anecdote.

## Also worth doing

- **Official noise data.** The current noise factor models emissions from lane
  count and speed limit, which is a proxy for traffic volume rather than
  measured sound. Denmark publishes modelled Lden contours under the EU
  environmental noise directive. The obvious endpoints either do not resolve or
  serve HTML rather than WFS capabilities, so it needs a registered account at
  Danmarks Miljøportal. Strictly better than the proxy when it lands.
- **Relisting detection.** A flat sold and relisted gets a new `caseID` against
  the same `addressID`. It usually means a sale fell through, which is worth
  knowing before bidding.
- **Full monthly cost.** Ejerudgift is scored, but the number a buyer feels is
  ejerudgift plus realkredit plus ejendomsværdiskat. `down_payment` and
  `net_mortgage` are already stored.
- **Sun orientation.** Which way the balcony faces. Danish buyers care and the
  listing text usually says.
- **Demand decay as a price cut predictor.** `/cases/bulk/stats` is captured
  every run, so favourites per day is accumulating. A flat whose interest has
  flatlined is about to drop its price. The series is currently only hours
  deep, so this needs the scheduled runs to have been going for a while.
- **Tvangsauktioner** via `/search/foreclosure-cases`, a separate and cheaper
  supply that nobody watches.
- **Schools and daycare** via `/municipalities/{code}/institutions`, 123 of them
  with coordinates.

## Deliberately not doing

- **Lowering the 90 m² floor.** 191 listings sit between 80 and 89 m² at an
  average of 6,96 mio. and are invisible. Raised, considered, declined: the
  floor stays hard.
- **Scraping the realtor sites for more photographs.** Checked rather than
  assumed. The chains are fragmented and the two largest render galleries in
  JavaScript, so it needs a headless browser and a parser per chain, each
  breaking on every redesign. The "Mægler" link is one click.
