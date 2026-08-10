"""Claude verdicts, via the Claude Code CLI.

The numbers tell you a flat is 9 pct. under its local benchmark. They cannot
tell you the photos are all shot at 24 mm from the doorway, that every window
faces a lysgård, or that "charmerende oprindelige detaljer" is the phrase a
realtor reaches for when the kitchen is from 1988.

So each listing gets read by a model: the full realtor text, up to five
photos, the score breakdown, the sale history of that exact flat, and the
demand numbers. It returns a structured verdict, not prose to be parsed.

This shells out to the ``claude`` CLI rather than the Anthropic SDK, so no API
key is needed and the run bills against the existing Claude subscription. The
photos are written to a temporary directory which becomes the CLI's working
directory, and the Read tool is pre-approved so it can open them without
prompting.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import requests

from . import config

logger = logging.getLogger(__name__)

JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)
JSON_ARRAY = re.compile(r"\[.*\]", re.DOTALL)

RESPONSE_SHAPE = """{
  "id": "boligens id, kopieret uændret fra BOLIG-blokken",
  "one_liner": "én sætning på dansk, maks. 140 tegn, det vigtigste en køber skal vide",
  "verdict": "se den" | "måske" | "spring over",
  "confidence": 0-100,
  "green_flags": ["konkrete fordele, maks. 5"],
  "red_flags": ["konkrete problemer eller risici, maks. 5"],
  "photos_say": "hvad de fem billeder faktisk viser. Aldrig en klage over hvad de ikke viser",
  "tjek_hos_maegler": ["hvad du ikke kunne bedømme og derfor skal se efter i mæglerens egen annonce, maks. 4 punkter"],
  "text_avoids": "hvad mæglerteksten går uden om. Ikke billeder, kun tekst",
  "price_assessment": "er prisen forsvarlig, vær konkret om beløb",
  "renovation_estimate_dkk": heltal eller null,
  "balcony_confirmed": true | false | null,
  "renovation_state": "nyistandsat" | "velholdt" | "brugsslidt" | "trænger" | "ukendt"
}"""

INSTRUCTIONS = (
    """Du er købsrådgiver for en privat køber i København. Din opgave er at \
beskytte ham mod at spilde en lørdag og mod at betale for meget.

Du er hverken mægler eller optimist. Du skriver kort, konkret og på dansk. Du bruger \
aldrig ord som unik, drømmebolig, eftertragtet eller sjælden mulighed, heller ikke i citat.

Læs mæglerteksten kritisk. Mæglertekster er markedsføring, og det de undlader at nævne er \
lige så oplysende som det de fremhæver. Fremhæver teksten potentiale i stedet for stand, \
skal der bruges penge.

VIGTIGT OM BILLEDERNE. Du får altid højst fem billeder, fordi Boligsiden kun udleverer fem. \
Det er en begrænsning i vores datakilde, ikke mæglerens valg. Mæglerens egen annonce har \
næsten altid flere. Derfor:

* At der ikke er billeder af køkken, bad eller soveværelser betyder INTET om boligen. Det \
  må aldrig stå i red_flags, og det må aldrig trække confidence ned.
* Skriv i stedet hvad de fem billeder faktisk viser, og brug feltet tjek_hos_maegler til \
  det du ikke kunne bedømme og derfor skal se på mæglerens egen side.
* Er billederne derimod 3D-visualiseringer, renders eller stylede illustrationer i stedet \
  for fotos af den konkrete bolig, ER det et rigtigt rødt flag. Det siger at boligen er \
  et projektsalg som måske ikke er bygget endnu.
* Er alle billeder taget fra døråbningen med vidvinkel, er rummene mindre end de ser ud, \
  og det må du gerne nævne.

Vurder prisen mod det lokale benchmark du får oplyst, ikke mod din egen fornemmelse af det \
danske marked. Benchmark er realiserede salgspriser i boligens eget sogn, eller udbudspriser \
i nabolaget hvor sognet dækker to forskellige markeder.

Køberens hårde krav er allerede filtreret fra: alt du ser er mindst 90 m2 og ikke i \
stueetagen. Prioriterede kvarterer er Amager Strandpark, Nørrebro, Østerbro, Nordhavn og \
Vesterbro. Nærhed til havnen, kanalerne og søerne vægter tungt. Ørestad er ikke prioriteret.

Brug aldrig tankestreger. Ingen lang tankestreg, ingen kort tankestreg, og ingen bindestreg \
sat ind hvor en tankestreg ville stå. Brug komma, punktum eller kolon i stedet.

Du får en eller flere boliger, hver i sin egen BOLIG-blok med et id. Vurder hver bolig \
for sig. Bland dem aldrig sammen: en oplysning fra én bolig må aldrig indgå i vurderingen \
af en anden.

Hver vurdering skal kunne stå alene. Læseren ser kun én bolig ad gangen, i en besked på \
telefonen, og aner ikke at de andre findes. Henvis derfor aldrig til en anden bolig i \
listen, hverken med nummer, med adresse eller med en omskrivning.

Forbudt, også selv om det er sandt: "som bolig 2", "samme som ovenfor", "billigere end den \
forrige", "samme projekt som Flyndervej 3C", "samme byggeri", "søsterlejligheden", \
"nummer 3B", "den anden lejlighed i opgangen".

Ligger to boliger i samme ejendom, så skriv oplysningen ud i begge vurderinger som om den \
anden ikke fandtes. Gentagelse er præcis hvad der ønskes her.

Brug heller aldrig superlativer eller rangeringer der måler boligen mod de øvrige i \
listen. "Den mindste af alle udbudte", "billigst blandt dem her", "den dyreste", "bedst i \
feltet" er forbudt, fordi du kun ser en håndfuld boliger ud af flere hundrede, og \
påstanden derfor er direkte forkert. Du må kun sammenligne med de benchmarktal du får \
oplyst i BOLIG-blokken, og kun med dem.

Svar udelukkende med et JSON-array med præcis ét objekt pr. bolig, i samme rækkefølge som \
du fik dem. Ingen indledning, ingen forklaring udenfor, ingen markdown-kodeblok. Hvert \
objekt har denne form:

"""
    + RESPONSE_SHAPE
)


@dataclass
class Verdict:
    payload: Dict[str, Any]
    model: str

    @property
    def one_liner(self) -> str:
        return self.payload.get("one_liner", "")

    @property
    def verdict(self) -> str:
        return self.payload.get("verdict", "måske")

    @property
    def is_recommended(self) -> bool:
        return self.verdict == "se den"


class AIUnavailable(RuntimeError):
    """Raised when the claude CLI cannot be found."""


class CostMeter:
    """Running total of what the verdicts cost.

    The CLI reports ``total_cost_usd`` per invocation. Adding it up means a run
    can say what it spent instead of leaving it to be discovered later.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.calls = 0
        self.usd = 0.0
        self.input_tokens = 0
        self.output_tokens = 0

    def record(self, envelope: Dict[str, Any]) -> None:
        usage = envelope.get("usage") or {}
        with self._lock:
            self.calls += 1
            self.usd += float(envelope.get("total_cost_usd") or 0.0)
            self.input_tokens += sum(
                int(usage.get(key) or 0)
                for key in (
                    "input_tokens",
                    "cache_creation_input_tokens",
                    "cache_read_input_tokens",
                )
            )
            self.output_tokens += int(usage.get("output_tokens") or 0)

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "calls": self.calls,
                "usd": round(self.usd, 2),
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "usd_per_call": round(self.usd / self.calls, 3) if self.calls else 0.0,
            }

    def reset(self) -> None:
        with self._lock:
            self.calls = 0
            self.usd = 0.0
            self.input_tokens = 0
            self.output_tokens = 0


COST = CostMeter()


# --------------------------------------------------------------------------
# CLI plumbing
# --------------------------------------------------------------------------


def claude_binary() -> Optional[str]:
    """Locate the CLI. ``KBH_CLAUDE_BIN`` wins so a VM path can be forced.

    On Windows, ``shutil.which`` finds the npm shim ``claude.CMD``, which is a
    two line batch file that calls the real ``claude.exe`` next door. Going
    through the batch layer means going through cmd.exe, and a cmd.exe started
    from a process with no console never hands off to its child: the shell sits
    there, the CLI never starts, and the call hangs silently until it times out.
    That is the failure mode for anything run detached or from Task Scheduler.

    So resolve the shim to the real executable and launch that directly.
    """
    override = os.environ.get("KBH_CLAUDE_BIN")
    if override:
        found = override if Path(override).exists() else shutil.which(override)
        return _resolve_shim(found) if found else None

    found = shutil.which("claude")
    return _resolve_shim(found) if found else None


def _resolve_shim(path: str) -> str:
    """Map an npm .cmd/.ps1 shim onto the executable it wraps."""
    candidate = Path(path)
    if candidate.suffix.lower() not in (".cmd", ".bat", ".ps1"):
        return path
    real = (
        candidate.parent
        / "node_modules"
        / "@anthropic-ai"
        / "claude-code"
        / "bin"
        / "claude.exe"
    )
    return str(real) if real.exists() else path


def cli_available() -> bool:
    return claude_binary() is not None


def _command(binary: str, args: Sequence[str]) -> List[str]:
    """Windows npm shims are .cmd files, which CreateProcess cannot launch
    directly, so they have to go through cmd.exe."""
    if sys.platform == "win32" and binary.lower().endswith((".cmd", ".bat")):
        return ["cmd.exe", "/c", binary, *args]
    return [binary, *args]


def _run_claude(
    prompt: str, workdir: Path, model: str, timeout: int = 420, allow_read: bool = False
) -> str:
    binary = claude_binary()
    if binary is None:
        raise AIUnavailable(
            "claude CLI not found. Put it on PATH or set KBH_CLAUDE_BIN."
        )

    # The prompt goes in on stdin, not as an argument. Passing a multi-line
    # prompt containing quotes through cmd.exe as an argv entry hangs the
    # process, which is how the first version of this failed.
    #
    # --strict-mcp-config and --setting-sources "" strip the MCP tool schemas
    # and the user's global settings out of the system prompt. Measured on 10
    # August 2026 that took a call from 63.700 input tokens and 14 seconds down
    # to 38.400 and 6 seconds, a saving of roughly 60 pct. It also means the
    # verdict is produced in a clean context rather than inheriting whatever
    # skills and instructions the interactive setup happens to carry.
    args = [
        "-p",
        "--output-format",
        "json",
        "--model",
        model,
        "--strict-mcp-config",
        "--setting-sources",
        "",
    ]
    # Without photos there is nothing to read, so the model gets no tools and a
    # single turn. That removes the tool definitions from the prompt as well.
    if allow_read:
        args += ["--allowedTools", "Read", "--max-turns", "6"]
    else:
        args += ["--max-turns", "1"]

    # CREATE_NO_WINDOW matters more than it looks. Without it, a run started
    # from a detached background process or a scheduled task spawns cmd.exe
    # with no console for node to attach to: cmd.exe sits there, node never
    # starts, and the call hangs until it times out with no error to show for
    # it. Reproduced on 10 August 2026 with a backfill that stalled at zero
    # verdicts for 25 minutes.
    kwargs: Dict[str, Any] = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    result = subprocess.run(
        _command(binary, args),
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        cwd=str(workdir),
        **kwargs,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"claude exited {result.returncode}: {(result.stderr or result.stdout)[:400]}"
        )

    # The CLI wraps the answer in an envelope when --output-format json is set.
    raw = result.stdout.strip()
    try:
        envelope = json.loads(raw)
    except json.JSONDecodeError:
        return raw

    if not isinstance(envelope, dict):
        return raw
    COST.record(envelope)
    if envelope.get("is_error"):
        raise RuntimeError(
            f"claude reported an error: {str(envelope.get('result'))[:300]}"
        )
    return envelope.get("result") or ""


def _parse_payload(text: str) -> Any:
    """Pull JSON out of whatever the model wrapped it in."""
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", candidate).strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass
    for pattern in (JSON_ARRAY, JSON_BLOCK):
        match = pattern.search(text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                continue
    raise ValueError(f"no JSON in model output: {text[:300]}")


def _parse_verdicts(
    text: str, expected_ids: Sequence[str]
) -> Dict[str, Dict[str, Any]]:
    """Map a batch response back onto the listings that were sent.

    Matching is by the echoed id, not by position, so a model that reorders or
    drops one does not silently attach a verdict to the wrong flat. Anything
    unmatched is simply absent from the result and the caller retries it.
    """
    payload = _parse_payload(text)
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        raise ValueError(f"expected a JSON array, got {type(payload).__name__}")

    wanted = set(expected_ids)
    out: Dict[str, Dict[str, Any]] = {}
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            continue
        case_id = str(item.get("id") or "").strip()
        if case_id not in wanted:
            # Fall back to position only when the batch lines up exactly, which
            # covers a model that answered in order but omitted the id.
            if len(payload) == len(expected_ids):
                case_id = expected_ids[index]
            else:
                continue
        item.pop("id", None)
        out[case_id] = item
    return out


def _download_images(
    urls: Sequence[str], workdir: Path, limit: int = config.AI_MAX_IMAGES
) -> List[str]:
    names: List[str] = []
    for index, url in enumerate(urls[:limit]):
        try:
            response = requests.get(
                url, timeout=25, headers={"User-Agent": config.USER_AGENT}
            )
            response.raise_for_status()
        except Exception as exc:
            logger.debug("image fetch failed for %s: %s", url, exc)
            continue
        suffix = ".webp" if url.endswith(".webp") else Path(url).suffix or ".jpg"
        name = f"foto_{index + 1}{suffix}"
        (workdir / name).write_bytes(response.content)
        names.append(name)
    return names


# --------------------------------------------------------------------------
# Prompt
# --------------------------------------------------------------------------


def _kr(value: Optional[float]) -> str:
    if value is None:
        return "ukendt"
    return f"{value:,.0f} kr.".replace(",", ".")


def build_brief(
    listing: Dict[str, Any],
    score: Dict[str, Any],
    sale_history: Sequence[Dict[str, Any]],
    benchmark_source: str,
    photo_alts: Sequence[str] = (),
    case_id: str = "",
) -> str:
    """The factual half of the prompt. Everything the model should not have to
    guess at."""
    lines: List[str] = []
    a = lines.append

    a(f"=== BOLIG id: {case_id or listing.get('case_id')} ===")
    a(f"ADRESSE: {listing.get('address')}")
    a(f"TYPE: {listing.get('address_type')}, etage {listing.get('floor') or 'ukendt'}")
    a(f"UDBUDSPRIS: {_kr(listing.get('price'))}")
    area = listing.get("living_area")
    a(f"BOLIGAREAL: {area:.0f} m2" if area else "BOLIGAREAL: ukendt")
    a(f"KVADRATMETERPRIS: {_kr(listing.get('per_area_price'))} pr. m2")
    a(
        f"VÆRELSER: {listing.get('number_of_rooms') or 'ukendt'}, "
        f"badeværelser {listing.get('number_of_bathrooms') or 'ukendt'}"
    )
    a(f"EJERUDGIFT: {_kr(listing.get('monthly_expense'))} pr. md.")
    a(
        f"UDBETALING: {_kr(listing.get('down_payment'))}, "
        f"nettoydelse {_kr(listing.get('net_mortgage'))} pr. md."
    )
    a(
        f"OPFØRT: {listing.get('year_built') or 'ukendt'}"
        + (
            f", renoveret {listing.get('year_renovated')}"
            if listing.get("year_renovated")
            else ""
        )
    )
    a(f"ENERGIMÆRKE: {(listing.get('energy_label') or 'ukendt').upper()}")
    a(f"BBR KØKKEN: {listing.get('kitchen_condition') or 'ikke oplyst'}")
    a(f"BBR BAD: {listing.get('bathroom_condition') or 'ikke oplyst'}")
    a(f"VARME: {listing.get('heating') or 'ikke oplyst'}")
    a(f"OFFENTLIG VURDERING: {_kr(listing.get('latest_valuation'))}")
    a(
        f"MÆGLERENS ALTANFLAG: {'ja' if listing.get('has_balcony') else 'nej'}"
        f" (teksten nævner altan: {'ja' if listing.get('has_balcony_text') else 'nej'})"
    )
    a(f"ELEVATOR: {'ja' if listing.get('has_elevator') else 'nej'}")

    a("")
    a(f"DAGE TIL SALG: {listing.get('days_listed') or 'ukendt'}")
    drop = listing.get("price_change_pct")
    if drop:
        a(f"PRISÆNDRING SIDEN UDBUD: {drop:+.1f} pct.")
    if listing.get("page_views") is not None:
        a(
            f"INTERESSE PÅ BOLIGSIDEN: {listing.get('page_views')} visninger, "
            f"{listing.get('favourites')} favoritter"
        )

    a("")
    a(
        f"LOKALT BENCHMARK ({benchmark_source}): "
        f"{_kr(score.get('parish_sqm_price'))} pr. m2"
    )
    ratio = score.get("sqm_price_ratio")
    if ratio:
        delta = (ratio - 1) * 100
        a(
            f"BOLIGEN LIGGER {abs(delta):.0f} PCT. "
            f"{'UNDER' if delta < 0 else 'OVER'} BENCHMARK"
        )
    a(f"KVARTER: {score.get('neighbourhood')}")
    if score.get("water_distance_m") is not None:
        a(
            f"AFSTAND TIL VAND: {score['water_distance_m']:.0f} m til "
            f"{score.get('water_name') or 'havn eller kyst'}"
        )

    sold = [e for e in sale_history if e.get("event_type") == "sold" and e.get("price")]
    if sold:
        a("")
        a("SALGSHISTORIK FOR PRÆCIS DENNE BOLIG:")
        for event in sold[:6]:
            a(f"  {str(event.get('sold_at'))[:10]}: {_kr(event.get('price'))}")

    a("")
    a("POINTGIVNING (0 til 100 pr. faktor):")
    for factor in score.get("breakdown", []):
        a(f"  {factor['label']}: {factor['score']:.0f} ({factor['reason']})")
    a(f"  SAMLET: {score.get('total')}")

    if photo_alts:
        a("")
        a(f"BILLEDER ({len(photo_alts)} stk., alt-teksten fra Boligsiden):")
        for index, alt in enumerate(photo_alts, start=1):
            a(f"  {index}. {alt}")
        a("Boligsiden udleverer højst fem billeder. Mæglerens egen annonce har flere.")
        a("Manglende rum er derfor ikke et rødt flag, men noget der skal tjekkes.")
    else:
        a("")
        a("BILLEDER: ingen billedbeskrivelser tilgængelige.")

    a("")
    a("MÆGLERENS OVERSKRIFT:")
    a(listing.get("description_title") or "(ingen)")
    a("")
    a("MÆGLERENS BESKRIVELSE:")
    a((listing.get("description_body") or "(ingen beskrivelse)")[:4000])

    return "\n".join(lines)


# --------------------------------------------------------------------------
# Public entry points
# --------------------------------------------------------------------------


@dataclass
class Candidate:
    """One listing packaged for the model."""

    case_id: str
    listing: Dict[str, Any]
    score: Dict[str, Any]
    sale_history: Sequence[Dict[str, Any]]
    benchmark_source: str
    photo_alts: Sequence[str] = ()
    image_urls: Sequence[str] = ()

    def brief(self) -> str:
        return build_brief(
            self.listing,
            self.score,
            self.sale_history,
            self.benchmark_source,
            photo_alts=self.photo_alts,
            case_id=self.case_id,
        )


def evaluate_batch(
    candidates: Sequence[Candidate],
    model: Optional[str] = None,
    use_photos: Optional[bool] = None,
) -> Dict[str, Verdict]:
    """Score a batch of listings in one CLI call.

    Returns a dict keyed by case id, containing only the listings the model
    actually answered for. Missing entries are the caller's problem to retry,
    which is deliberate: a partial answer should never be padded out with
    guesses.
    """
    if not candidates:
        return {}

    model = model or config.AI_MODEL
    use_photos = config.AI_USE_PHOTOS if use_photos is None else use_photos
    ids = [c.case_id for c in candidates]

    with tempfile.TemporaryDirectory(prefix="kbh_ai_") as tmp:
        workdir = Path(tmp)
        parts = [INSTRUCTIONS, "", f"Du får {len(candidates)} bolig(er) nedenfor.", ""]

        if use_photos and len(candidates) == 1:
            # Real vision only makes sense one listing at a time. Reserve it for
            # a shortlist that has already earned the attention.
            photos = _download_images(candidates[0].image_urls, workdir)
            if photos:
                parts.append(
                    f"Der ligger {len(photos)} billeder fra annoncen i den mappe du "
                    f"står i: {', '.join(photos)}. Åbn dem alle med Read først."
                )
                parts.append("")

        for candidate in candidates:
            parts.append(candidate.brief())
            parts.append("")

        text = _run_claude(
            "\n".join(parts),
            workdir,
            model,
            allow_read=bool(use_photos and len(candidates) == 1),
        )

    parsed = _parse_verdicts(text, ids)
    return {
        cid: Verdict(payload=payload, model=model) for cid, payload in parsed.items()
    }


def evaluate(
    candidate: Candidate, model: Optional[str] = None, use_photos: Optional[bool] = None
) -> Verdict:
    """Single listing convenience wrapper."""
    result = evaluate_batch([candidate], model=model, use_photos=use_photos)
    if candidate.case_id not in result:
        raise ValueError("model returned no verdict for the listing")
    return result[candidate.case_id]


DIGEST_INSTRUCTIONS = """Du skriver en kort daglig opsummering til en privat boligkøber i \
København. Du får en liste over de bedst scorende boliger og hvad der er ændret siden i går.

Skriv på dansk, telegrafisk, maks. 120 ord. Ingen indledning, ingen opsummering til sidst, \
intet salgssprog. Peg på det ene eller to der faktisk er værd at handle på, og sig hvorfor. \
Er der intet værd at handle på, så sig det rent ud.

Brug aldrig tankestreger. Ingen lang tankestreg, ingen kort tankestreg, og ingen bindestreg \
sat ind hvor en tankestreg ville stå. Brug komma, punktum eller kolon i stedet.

Svar kun med selve teksten."""


def daily_summary(
    items: Sequence[Dict[str, Any]],
    changes: Dict[str, Any],
    model: Optional[str] = None,
) -> str:
    """One paragraph over the whole board, for the morning digest."""
    model = model or config.AI_SYNTHESIS_MODEL

    lines = [
        DIGEST_INSTRUCTIONS,
        "",
        f"Nye i dag: {changes.get('new', 0)}. "
        f"Prisfald i dag: {changes.get('price_drops', 0)}. "
        f"Taget af markedet: {changes.get('delisted', 0)}.",
        "",
    ]
    for item in items:
        verdict = item.get("verdict") or {}
        lines.append(
            f"{item.get('score', 0):.0f} | {item.get('address')} | "
            f"{_kr(item.get('price'))} | {item.get('living_area') or '?'} m2 | "
            f"{item.get('neighbourhood')} | {verdict.get('verdict', '')} | "
            f"{verdict.get('one_liner', '')}"
        )

    with tempfile.TemporaryDirectory(prefix="kbh_digest_") as tmp:
        return _run_claude("\n".join(lines), Path(tmp), model, timeout=180).strip()


TASTE_INSTRUCTIONS = """Du analyserer en boligkøbers egne bedømmelser for at finde \
mønstre i hvad han rent faktisk kan lide.

Du får hans stjerner fra 1 til 5 og hans egne kommentarer til hver bolig, sammen med \
boligens nøgletal. Kommentarerne vejer tungest: tallene siger hvad boligerne er, \
kommentarerne siger hvorfor han reagerede som han gjorde.

Skriv på dansk, maks. 200 ord, i tre korte afsnit uden overskrifter:

1. Hvad han konsekvent går efter. Vær konkret og brug hans egne ord hvor de er \
tydelige. Skriv ikke "han foretrækker god beliggenhed", det siger intet.
2. Hvad der konsekvent slår en bolig ud for ham, igen konkret.
3. Én ting hans bedømmelser afslører, som han sandsynligvis ikke selv har formuleret. \
Hvis der ikke er nok materiale til det, så sig det rent ud i stedet for at gætte.

Er datagrundlaget for tyndt til overhovedet at sige noget, så skriv kun det. Opfind \
aldrig et mønster ud af tre bedømmelser.

Brug aldrig tankestreger. Ingen lang tankestreg, ingen kort tankestreg, og ingen \
bindestreg sat ind hvor en tankestreg ville stå. Brug komma, punktum eller kolon.

Svar kun med selve teksten."""


def taste_summary(
    comments: Sequence[Dict[str, Any]],
    findings: Sequence[Any] = (),
    model: Optional[str] = None,
) -> str:
    """Read the ratings and the written comments, and name the pattern."""
    if not comments:
        return ""

    model = model or config.AI_SYNTHESIS_MODEL
    lines = [TASTE_INSTRUCTIONS, "", "BEDØMMELSER OG KOMMENTARER:"]
    for c in sorted(comments, key=lambda x: -x["stars"]):
        lines.append(
            f"  {c['stars']} stjerner | {c['address']} | {c.get('neighbourhood')} | "
            f"{_kr(c.get('price'))} | {c.get('living_area') or '?'} m2 | "
            f"{_kr(c.get('per_area_price'))}/m2 | "
            f"{c.get('water_distance_m') and round(c['water_distance_m'])} m til vand"
        )
        lines.append(f'      "{c["note"]}"')

    if findings:
        lines.append("")
        lines.append("MÅLTE FORSKELLE MELLEM HØJT OG LAVT BEDØMTE:")
        for f in list(findings)[:8]:
            lines.append(f"  {f.sentence()}")

    with tempfile.TemporaryDirectory(prefix="kbh_taste_") as tmp:
        return _run_claude("\n".join(lines), Path(tmp), model, timeout=180).strip()


def verdict_from_row(row: Any) -> Optional[Dict[str, Any]]:
    """Decode the stored verdict JSON off a listings view row."""
    raw = row["ai_verdict"] if "ai_verdict" in row.keys() else None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None
