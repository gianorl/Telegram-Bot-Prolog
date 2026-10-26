"""ONE ConversationHandler for every multi-step flow in every module.

Why one: if /catat and /hutang had separate handlers, both could be "active"
at the same time and fight over your next message. With one handler, starting
any flow cleanly replaces the one in progress (allow_reentry).

To add a module: give it ENTRY_POINTS and STATES, then add it to MODULES.
State names are strings ("catat_item"), so modules can't clash by accident.
"""

import warnings

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler, TypeHandler
from telegram.warnings import PTBUserWarning

from app.handlers import debts, history, money, subscriptions

MODULES = [money, debts, subscriptions, history]
TIMEOUT_SECONDS = 5 * 60  # BR-09


async def batal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Dibatalkan.")
    return ConversationHandler.END


async def timed_out(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await context.bot.send_message(
        update.effective_chat.id,
        "Waktu habis (5 menit). Dibatalkan, tidak ada yang disimpan.",
    )


def all_states():
    states = {}
    for module in MODULES:
        for name, handlers in module.STATES.items():
            assert name not in states, f"state {name!r} defined twice"
            states[name] = handlers
    states[ConversationHandler.TIMEOUT] = [TypeHandler(Update, timed_out)]
    return states


# PTB warns that buttons are tracked per chat, not per message. That is what we
# want (one flow per chat), so hide this one warning.
warnings.filterwarnings(
    "ignore", message="If 'per_message=False'", category=PTBUserWarning
)

conversation = ConversationHandler(
    entry_points=[entry for module in MODULES for entry in module.ENTRY_POINTS],
    states=all_states(),
    fallbacks=[CommandHandler("batal", batal)],
    conversation_timeout=TIMEOUT_SECONDS,
    allow_reentry=True,  # a new flow in the middle of a flow starts over
)
