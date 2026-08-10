"""Interactive Telegram bot.

Separate process from the pipeline. The pipeline pushes alerts out through
notify.py; this is for asking questions back:

    /top [n]          the n best scoring listings
    /nye [dage]       listings first seen in the last n days
    /prisfald         listings that have cut their price
    /vand [meter]     listings within n metres of the water
    /kvarter <navn>   listings in one neighbourhood
    /bolig <søgeord>  look up by address
    /status           pool size, last run, spend
    /hjaelp           this list

Read only. Nothing here can change a score or trigger a fetch, so it is safe
to leave running.

    python -m kbh.bot
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Sequence

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from . import ai, config, db, notify

logging.basicConfig(
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def _authorised(update: Update) -> bool:
    """Only the configured chat may talk to the bot."""
    runtime = config.RuntimeConfig()
    if not runtime.telegram_chat_id:
        return True
    return str(update.effective_chat.id) == str(runtime.telegram_chat_id)


def _rows(
    where: str = "", params: Sequence[Any] = (), limit: int = 5
) -> List[Dict[str, Any]]:
    with db.session() as conn:
        sql = f"{db.LISTING_VIEW} WHERE l.is_active = 1 AND l.excluded = 0"
        if where:
            sql += f" AND {where}"
        sql += f" ORDER BY s.total DESC NULLS LAST LIMIT {int(limit)}"
        found = conn.execute(sql, tuple(params)).fetchall()
        out = []
        for row in found:
            data = dict(row)
            data["verdict"] = ai.verdict_from_row(row)
            out.append(data)
        return out


def _int_arg(args: Sequence[str], default: int) -> int:
    for arg in args:
        try:
            return int(arg)
        except ValueError:
            continue
    return default


async def _reply_listings(
    update: Update, rows: List[Dict[str, Any]], empty: str
) -> None:
    if not rows:
        await update.message.reply_text(empty)
        return
    for row in rows:
        text = notify.format_listing(
            row, row.get("verdict"), row.get("headline") or "", kind="digest"
        )
        await update.message.reply_text(
            text, parse_mode=ParseMode.HTML, disable_web_page_preview=True
        )


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

HELP = """<b>Kommandoer</b>
/top [n] , de bedst scorende boliger
/nye [dage] , boliger set inden for n dage
/prisfald , boliger der har sat prisen ned
/vand [meter] , boliger tæt på vandet
/kvarter &lt;navn&gt; , boliger i et kvarter
/bolig &lt;søgeord&gt; , slå op på adresse
/status , antal, sidste kørsel og forbrug
/hjaelp , denne liste"""


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorised(update):
        return
    await update.message.reply_text(HELP, parse_mode=ParseMode.HTML)


async def cmd_top(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorised(update):
        return
    limit = min(_int_arg(ctx.args, 5), 10)
    await _reply_listings(update, _rows(limit=limit), "Databasen er tom.")


async def cmd_new(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorised(update):
        return
    days = _int_arg(ctx.args, 3)
    rows = _rows(
        "l.first_seen >= datetime('now', ?)",
        (f"-{days} days",),
        limit=8,
    )
    await _reply_listings(update, rows, f"Ingen nye boliger de sidste {days} dage.")


async def cmd_drops(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorised(update):
        return
    rows = _rows("l.price_change_pct < 0", (), limit=8)
    await _reply_listings(update, rows, "Ingen prisfald lige nu.")


async def cmd_water(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorised(update):
        return
    metres = _int_arg(ctx.args, 300)
    rows = _rows("s.water_distance_m <= ?", (metres,), limit=8)
    await _reply_listings(
        update, rows, f"Ingen boliger inden for {metres} m af vandet."
    )


async def cmd_hood(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorised(update):
        return
    if not ctx.args:
        with db.session() as conn:
            names = conn.execute(
                "SELECT neighbourhood, COUNT(*) c FROM scores "
                "WHERE neighbourhood IS NOT NULL GROUP BY 1 ORDER BY c DESC"
            ).fetchall()
        listing = "\n".join(f"{r['neighbourhood']} ({r['c']})" for r in names)
        await update.message.reply_text(f"Angiv et kvarter:\n{listing}")
        return
    needle = " ".join(ctx.args)
    rows = _rows("s.neighbourhood LIKE ?", (f"%{needle}%",), limit=8)
    await _reply_listings(update, rows, f"Ingen boliger i {needle}.")


async def cmd_lookup(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorised(update):
        return
    if not ctx.args:
        await update.message.reply_text("Brug: /bolig <søgeord i adressen>")
        return
    needle = " ".join(ctx.args)
    rows = _rows("l.address LIKE ?", (f"%{needle}%",), limit=5)
    await _reply_listings(update, rows, f"Fandt ingen adresse der matcher {needle}.")


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorised(update):
        return
    with db.session() as conn:
        active = conn.execute(
            "SELECT COUNT(*) c FROM listings WHERE is_active = 1 AND excluded = 0"
        ).fetchone()["c"]
        excluded = conn.execute(
            "SELECT COUNT(*) c FROM listings WHERE is_active = 1 AND excluded = 1"
        ).fetchone()["c"]
        verdicts = conn.execute("SELECT COUNT(*) c FROM ai_verdicts").fetchone()["c"]
        recommended = conn.execute(
            "SELECT COUNT(*) c FROM ai_verdicts WHERE verdict LIKE '%\"se den\"%'"
        ).fetchone()["c"]
        run = conn.execute(
            "SELECT started_at, finished_at, seen, new_listings, price_drops, delisted "
            "FROM runs WHERE finished_at IS NOT NULL ORDER BY id DESC LIMIT 1"
        ).fetchone()
        best = conn.execute("SELECT MAX(total) m FROM scores").fetchone()["m"]

    lines = [
        "<b>Status</b>",
        f"{active} aktive boliger, {excluded} frafiltreret",
        f"{verdicts} vurderinger, {recommended} anbefalet",
        f"Højeste score: {best:.0f}" if best else "Ingen score endnu",
    ]
    if run:
        lines.append(
            f"Sidste kørsel {run['started_at'][:16].replace('T', ' ')}: "
            f"{run['new_listings']} nye, {run['price_drops']} prisfald, "
            f"{run['delisted']} taget af markedet"
        )
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def fallback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorised(update):
        return
    await update.message.reply_text(
        "Jeg forstår kun kommandoer. Skriv /hjaelp for listen."
    )


def main() -> None:
    runtime = config.RuntimeConfig()
    if not runtime.telegram_token:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN is not set. See kbh/README.md for how to create the bot."
        )

    app = Application.builder().token(runtime.telegram_token).build()
    app.add_handler(CommandHandler(["hjaelp", "help", "start"], cmd_help))
    app.add_handler(CommandHandler("top", cmd_top))
    app.add_handler(CommandHandler(["nye", "ny"], cmd_new))
    app.add_handler(CommandHandler(["prisfald", "drops"], cmd_drops))
    app.add_handler(CommandHandler("vand", cmd_water))
    app.add_handler(CommandHandler(["kvarter", "hood"], cmd_hood))
    app.add_handler(CommandHandler(["bolig", "find"], cmd_lookup))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback))

    logger.info("Bot running. Send /hjaelp in Telegram.")
    app.run_polling()


if __name__ == "__main__":
    main()
