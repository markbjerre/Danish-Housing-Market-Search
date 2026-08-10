"""Telegram output.

Deliberately built on plain HTTP against the Bot API rather than an async
framework: the pipeline is a synchronous cron job, and dragging an event loop
into it buys nothing. The interactive bot in bot.py is a separate process and
does use the async library.

Nothing here raises on a delivery failure. A Telegram outage must not take the
pipeline down or lose a scoring run.
"""

from __future__ import annotations

import html
import logging
from typing import Any, Dict, List, Optional, Sequence

import requests

from . import config

logger = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org/bot{token}/{method}"


def _kr(value: Optional[float]) -> str:
    if value is None:
        return "?"
    return f"{value:,.0f}".replace(",", ".")


def _esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


class Telegram:
    def __init__(self, token: str = "", chat_id: str = "") -> None:
        runtime = config.RuntimeConfig()
        self.token = token or runtime.telegram_token
        self.chat_id = chat_id or runtime.telegram_chat_id

    @property
    def ready(self) -> bool:
        return bool(self.token and self.chat_id)

    def _call(self, method: str, payload: Dict[str, Any]) -> bool:
        if not self.ready:
            logger.warning("Telegram not configured, dropping %s", method)
            return False
        try:
            response = requests.post(
                API_BASE.format(token=self.token, method=method),
                json={"chat_id": self.chat_id, **payload},
                timeout=30,
            )
            if response.status_code != 200:
                logger.error(
                    "Telegram %s failed: %s %s",
                    method,
                    response.status_code,
                    response.text[:200],
                )
                return False
            return True
        except Exception as exc:
            logger.error("Telegram %s raised: %s", method, exc)
            return False

    def send(self, text: str, disable_preview: bool = True) -> bool:
        return self._call(
            "sendMessage",
            {
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": disable_preview,
            },
        )

    def send_photo(self, photo_url: str, caption: str) -> bool:
        ok = self._call(
            "sendPhoto",
            {
                "photo": photo_url,
                "caption": caption[:1024],
                "parse_mode": "HTML",
            },
        )
        if not ok:
            # Telegram refuses some CDN images. The words matter more than the
            # picture, so fall back rather than dropping the alert.
            return self.send(caption)
        return True


# --------------------------------------------------------------------------
# Formatting
# --------------------------------------------------------------------------

VERDICT_MARK = {"se den": "JA", "måske": "MÅSKE", "spring over": "NEJ"}


def format_listing(
    row: Dict[str, Any],
    verdict: Optional[Dict[str, Any]] = None,
    headline: str = "",
    kind: str = "new",
) -> str:
    """One listing, formatted for a Telegram card."""
    title = {
        "new": "Ny bolig",
        "price_drop": "Prisfald",
        "digest": "",
    }.get(kind, "")

    score = row.get("score")
    lines: List[str] = []

    if title:
        lines.append(f"<b>{title}</b>")

    lines.append(f"<b>{_esc(row.get('address'))}</b>")
    lines.append(
        f"{_kr(row.get('price'))} kr. · {_kr(row.get('living_area'))} m² · "
        f"{_kr(row.get('per_area_price'))} kr/m²"
    )

    bits: List[str] = []
    if row.get("number_of_rooms"):
        bits.append(f"{row['number_of_rooms']:.0f} vær.")
    if row.get("floor"):
        bits.append(f"{_esc(row['floor'])}. sal")
    if row.get("has_balcony") or row.get("has_balcony_text"):
        bits.append("altan")
    if row.get("has_elevator"):
        bits.append("elevator")
    if row.get("energy_label"):
        bits.append(f"energi {_esc(str(row['energy_label']).upper())}")
    if bits:
        lines.append(" · ".join(bits))

    lines.append("")
    if score is not None:
        lines.append(
            f"<b>Score {score:.0f}</b> / 100 · {_esc(row.get('neighbourhood'))}"
        )

    ratio = row.get("sqm_price_ratio")
    if ratio:
        delta = (ratio - 1) * 100
        word = "under" if delta < 0 else "over"
        lines.append(
            f"{abs(delta):.0f} pct. {word} sognet ({_esc(row.get('parish'))}, "
            f"{_kr(row.get('parish_sqm_price'))} kr/m²)"
        )

    if row.get("water_distance_m") is not None:
        lines.append(
            f"{row['water_distance_m']:.0f} m til {_esc(row.get('water_name') or 'vandet')}"
        )

    if row.get("monthly_expense"):
        lines.append(f"Ejerudgift {_kr(row['monthly_expense'])} kr/md.")

    if row.get("days_listed") is not None:
        drop = row.get("price_change_pct")
        tail = f", sat ned {abs(drop):.1f} pct." if drop and drop < 0 else ""
        lines.append(f"{row['days_listed']} dage til salg{tail}")

    if row.get("page_views"):
        lines.append(
            f"{row['page_views']} visninger, {row.get('favourites') or 0} favoritter"
        )

    if verdict:
        mark = VERDICT_MARK.get(verdict.get("verdict", ""), "")
        lines.append("")
        lines.append(
            f"<b>Vurdering: {mark}</b> ({verdict.get('confidence', '?')} pct. sikker)"
        )
        lines.append(_esc(verdict.get("one_liner", "")))
        for flag in (verdict.get("red_flags") or [])[:3]:
            lines.append(f"− {_esc(flag)}")
        for flag in (verdict.get("green_flags") or [])[:3]:
            lines.append(f"+ {_esc(flag)}")
        for item in (verdict.get("tjek_hos_maegler") or [])[:3]:
            lines.append(f"? {_esc(item)}")
        if verdict.get("price_assessment"):
            lines.append("")
            lines.append(_esc(verdict["price_assessment"]))
    elif headline:
        lines.append("")
        lines.append(_esc(headline))

    lines.append("")
    if row.get("boligsiden_url"):
        lines.append(f'<a href="{_esc(row["boligsiden_url"])}">Boligsiden</a>')
    if row.get("case_url"):
        lines.append(f'<a href="{_esc(row["case_url"])}">Mægler</a>')

    return "\n".join(lines)


def format_digest(
    items: Sequence[Dict[str, Any]], changes: Dict[str, int], summary: str = ""
) -> str:
    lines = [f"<b>Boligoversigt</b>"]
    lines.append(
        f"{changes.get('new', 0)} nye · {changes.get('price_drops', 0)} prisfald · "
        f"{changes.get('delisted', 0)} taget af markedet · "
        f"{changes.get('active', 0)} aktive i alt"
    )

    if summary:
        lines.append("")
        lines.append(_esc(summary))

    lines.append("")
    lines.append("<b>Toppen lige nu</b>")
    for index, row in enumerate(items, start=1):
        verdict = row.get("verdict") or {}
        mark = VERDICT_MARK.get(verdict.get("verdict", ""), "")
        ratio = row.get("sqm_price_ratio")
        delta = f"{(ratio - 1) * 100:+.0f}%" if ratio else ""
        url = row.get("boligsiden_url") or "#"
        lines.append(f'{index}. <a href="{_esc(url)}">{_esc(row.get("address"))}</a>')
        lines.append(
            f"    {row.get('score', 0):.0f} · {_kr(row.get('price'))} kr · "
            f"{_kr(row.get('living_area'))} m² · {delta} vs. sogn · "
            f"{_esc(row.get('neighbourhood'))} {mark}"
        )
        if verdict.get("one_liner"):
            lines.append(f"    <i>{_esc(verdict['one_liner'])}</i>")

    return "\n".join(lines)


def format_run_error(message: str) -> str:
    return f"<b>Kørslen fejlede</b>\n<pre>{_esc(message[:1500])}</pre>"
