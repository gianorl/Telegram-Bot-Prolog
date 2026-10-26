"""Helpers used by several handler modules."""

from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, ConversationHandler, filters

from app import db
from app.config import PAYDAY_DAY, TZ
from app.cycles import cycle_for

# New text messages only: not commands, not edits of old messages
TEXT = filters.UpdateType.MESSAGE & filters.TEXT & ~filters.COMMAND

# Button data has a prefix so each step only picks up its own buttons
CATEGORY_PREFIX = "cat:"  # cat:1 (category id)
ACCOUNT_PREFIX = "acc:"  # acc:3 (account id)


def start_flow(update, context):
    context.user_data.clear()  # fresh start, also when a flow is sent mid-flow
    # When you SENT the command, not when the bot processed it. If the laptop
    # was off, Telegram holds the message and the bot may only see it later.
    # Flows started from a button (not a typed command) use the current time.
    sent = update.message.date if update.message else datetime.now(TZ)
    context.user_data["sent_at"] = sent.astimezone(TZ)


def now():
    return datetime.now(TZ)


def button(callback, prefix):
    return CallbackQueryHandler(callback, pattern=f"^{prefix}")


def two_per_row(buttons):
    return InlineKeyboardMarkup([buttons[i : i + 2] for i in range(0, len(buttons), 2)])


def category_keyboard(prefix=CATEGORY_PREFIX):
    return two_per_row(
        [
            InlineKeyboardButton(c["name"], callback_data=f"{prefix}{c['id']}")
            for c in db.categories()
        ]
    )


def account_keyboard(prefix=ACCOUNT_PREFIX, exclude_id=None):
    return two_per_row(
        [
            InlineKeyboardButton(a["name"], callback_data=f"{prefix}{a['id']}")
            for a in db.accounts()
            if a["id"] != exclude_id
        ]
    )


def parse_id(data, prefix):
    """ "acc:3" -> 3. Button data is untrusted: anything else -> None."""
    raw = data.removeprefix(prefix)
    if raw.isascii() and raw.isdigit():
        return int(raw)
    return None


def picked_category(query, prefix=CATEGORY_PREFIX):
    """Must be a number AND an existing category."""
    category_id = parse_id(query.data, prefix)
    return db.get_category(category_id) if category_id is not None else None


def picked_account(query, prefix=ACCOUNT_PREFIX):
    """Must be a number AND an existing account."""
    account_id = parse_id(query.data, prefix)
    return db.get_account(account_id) if account_id is not None else None


async def reply_error(update, error, keyboard=None):
    await update.effective_message.reply_text(str(error), reply_markup=keyboard)


async def tap_a_button(update, context):
    """Text typed at a step that wants a button.

    Returns nothing, and returning nothing (None) keeps the flow on the same step.
    """
    await update.message.reply_text("Pilih dari tombol di atas ya.")


async def no_accounts(update):
    await update.effective_message.reply_text(
        "Belum ada akun. Tambah dulu dengan /akun (contoh: CIMB, SeaBank, GoPay, Cash)."
    )
    return ConversationHandler.END


def cycle_bounds(moment):
    """ISO strings for the start and end of the pay cycle containing `moment`."""
    start, end = cycle_for(moment.date(), PAYDAY_DAY)
    return (
        datetime.combine(start, datetime.min.time(), TZ).isoformat(),
        datetime.combine(end, datetime.min.time(), TZ).isoformat(),
    )
