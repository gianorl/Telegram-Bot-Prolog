"""/langganan: recurring payments (Netflix, kos, cicilan, listrik...).

On the due day the bot asks "Sudah bayar?". Nothing is logged until I tap,
because the amount or account can differ (a PLN bill changes every month).

The laptop may be asleep on the due day, so instead of one fixed alarm a
check runs every 30 minutes (and right after startup) and sends any reminder
that is due and not yet sent this month.
"""

import calendar
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
)

from app import db
from app.config import OWNER_ID
from app.formatters import rupiah
from app.handlers.shared import (
    ACCOUNT_PREFIX,
    CATEGORY_PREFIX,
    TEXT,
    account_keyboard,
    button,
    category_keyboard,
    no_accounts,
    now,
    parse_id,
    picked_account,
    picked_category,
    reply_error,
    start_flow,
    tap_a_button,
)
from app.validators import parse_amount, parse_day, validate_item

CHECK_EVERY_SECONDS = 30 * 60
ADD = "sub:add"
DELETE_PREFIX = "sub:del:"  # sub:del:3
# Reminder buttons carry the month, so an old reminder can't pay a new month
PAY = re.compile(r"^subpay:(\d+):(\d{4}-\d{2})$")
SKIP = re.compile(r"^subskip:(\d+):(\d{4}-\d{2})$")
OTHER_AMOUNT = re.compile(r"^subamt:(\d+):(\d{4}-\d{2})$")


def due_day(day, today):
    """Day 31 in a 30-day month (or February) is due on the last day."""
    return min(day, calendar.monthrange(today.year, today.month)[1])


def month_of(moment):
    return moment.strftime("%Y-%m")


# ---------- /langganan: list, add, delete ----------


def list_text_and_keyboard():
    subs = db.subscriptions()
    if subs:
        lines = ["🔁 Langganan & tagihan rutin"]
        lines += [
            f"Tgl {s['day']}: {s['name']} {rupiah(s['amount'])} ({s['category']}, {s['account']})"
            for s in subs
        ]
        lines.append(f"\nTotal per bulan: {rupiah(sum(s['amount'] for s in subs))}")
    else:
        lines = ["🔁 Belum ada langganan.", "Contoh: Netflix, kos, cicilan, listrik."]
    rows = [[InlineKeyboardButton("➕ Tambah", callback_data=ADD)]]
    rows += [
        [
            InlineKeyboardButton(
                f"🗑 {s['name']}", callback_data=f"{DELETE_PREFIX}{s['id']}"
            )
        ]
        for s in subs
    ]
    return "\n".join(lines), InlineKeyboardMarkup(rows)


async def langganan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, keyboard = list_text_and_keyboard()
    await update.message.reply_text(text, reply_markup=keyboard)


async def delete_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    subscription_id = parse_id(query.data, DELETE_PREFIX)
    subscription = db.get_subscription(subscription_id) if subscription_id else None
    if subscription is None:
        await query.answer("Sudah tidak ada.")
        return
    db.delete_subscription(subscription_id)
    await query.answer(f"{subscription['name']} dihapus")
    text, keyboard = list_text_and_keyboard()
    await query.edit_message_text(text, reply_markup=keyboard)


async def start_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not db.accounts():
        return await no_accounts(update)
    start_flow(update, context)
    await query.message.reply_text("Nama langganan? (contoh: Netflix, Kos, Listrik)")
    return "sub_name"


async def sub_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["name"] = validate_item(update.message.text)
    except ValueError as error:
        await reply_error(update, error)
        return "sub_name"
    await update.message.reply_text("Kategori?", reply_markup=category_keyboard())
    return "sub_category"


async def sub_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = picked_category(query)
    if category is None:
        await reply_error(update, "Kategori tidak valid.", category_keyboard())
        return "sub_category"
    context.user_data["category"] = dict(category)
    await query.edit_message_text(
        f"Kategori: {category['name']}\nBiasanya bayar dari akun apa?",
        reply_markup=account_keyboard(),
    )
    return "sub_account"


async def sub_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    account = picked_account(query)
    if account is None:
        await reply_error(update, "Akun tidak valid.", account_keyboard())
        return "sub_account"
    context.user_data["account"] = dict(account)
    await query.edit_message_text(
        f"{account['name']}\nBerapa per bulan? (kira-kira, kalau berubah-ubah)"
    )
    return "sub_amount"


async def sub_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["amount"] = parse_amount(update.message.text)
    except ValueError as error:
        await reply_error(update, error)
        return "sub_amount"
    await update.message.reply_text("Jatuh tempo tanggal berapa? (1 sampai 31)")
    return "sub_day"


async def sub_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        day = parse_day(update.message.text)
    except ValueError as error:
        await reply_error(update, error)
        return "sub_day"

    data = context.user_data
    today = data["sent_at"].date()
    # Already past this month's due day: don't remind for this month, it's
    # probably paid. The first reminder comes next month.
    already_due = due_day(day, today) <= today.day
    db.add_subscription(
        data["name"],
        data["amount"],
        data["category"]["id"],
        data["account"]["id"],
        day,
        month_of(today) if already_due else None,
        data["sent_at"].isoformat(),
    )
    when = "bulan depan" if already_due else "bulan ini"
    reply = (
        f"✅ {data['name']} {rupiah(data['amount'])} tiap tanggal {day} "
        f"({data['category']['name']}, {data['account']['name']}).\n"
        f"Pengingat pertama: tanggal {day} {when}."
    )
    context.user_data.clear()
    await update.message.reply_text(reply)
    return ConversationHandler.END


# ---------- reminders ----------


def reminder_keyboard(subscription_id, month):
    key = f"{subscription_id}:{month}"
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Sudah bayar", callback_data=f"subpay:{key}")],
            [InlineKeyboardButton("✏️ Jumlahnya beda", callback_data=f"subamt:{key}")],
            [InlineKeyboardButton("Lewati bulan ini", callback_data=f"subskip:{key}")],
        ]
    )


async def send_due_reminders(context: ContextTypes.DEFAULT_TYPE):
    today = now().date()
    month = month_of(today)
    for s in db.subscriptions():
        if s["last_reminded"] == month or due_day(s["day"], today) > today.day:
            continue
        db.mark_reminded(s["id"], month)  # first, so a crash can't spam reminders
        await context.bot.send_message(
            OWNER_ID,
            f"🔁 Jatuh tempo: {s['name']} {rupiah(s['amount'])} "
            f"(tgl {s['day']}, dari {s['account']})",
            reply_markup=reminder_keyboard(s["id"], month),
        )


def payable(match):
    """Untrusted button -> (subscription, month). Raises ValueError if not allowed."""
    subscription = db.get_subscription(int(match.group(1)))
    month = match.group(2)
    if subscription is None:
        raise ValueError("Langganan ini sudah dihapus.")
    if month > month_of(now()):  # "2026-12" > "2026-11": text order = time order
        raise ValueError("Belum jatuh tempo.")
    if subscription["last_paid"] == month:
        raise ValueError("Sudah dicatat untuk bulan ini.")
    return subscription, month


def log_payment(subscription, month, amount):
    db.add_transaction(
        "expense",
        subscription["name"],
        amount,
        now().isoformat(),
        category_id=subscription["category_id"],
        from_account_id=subscription["account_id"],
    )
    db.mark_paid(subscription["id"], month)
    return (
        f"✅ {subscription['name']} ({subscription['category']}, "
        f"{subscription['account']}) {rupiah(amount)}"
    )


async def pay_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        subscription, month = payable(PAY.match(query.data))
    except ValueError as error:
        await query.edit_message_text(str(error))
        return
    await query.edit_message_text(
        log_payment(subscription, month, subscription["amount"])
    )


async def skip_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Oke, dilewati bulan ini.")


async def start_other_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        subscription, month = payable(OTHER_AMOUNT.match(query.data))
    except ValueError as error:
        await query.edit_message_text(str(error))
        return ConversationHandler.END
    start_flow(update, context)
    context.user_data["subscription_id"] = subscription["id"]
    context.user_data["month"] = month
    await query.edit_message_text(f"{subscription['name']}: berapa bulan ini?")
    return "sub_pay_amount"


async def sub_pay_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = parse_amount(update.message.text)
    except ValueError as error:
        await reply_error(update, error)
        return "sub_pay_amount"
    subscription = db.get_subscription(context.user_data["subscription_id"])
    month = context.user_data["month"]
    context.user_data.clear()
    # Check again: the plain "Sudah bayar" button may have been tapped meanwhile
    if subscription is None or subscription["last_paid"] == month:
        await update.message.reply_text("Sudah dicatat atau sudah dihapus.")
        return ConversationHandler.END
    await update.message.reply_text(log_payment(subscription, month, amount))
    return ConversationHandler.END


ENTRY_POINTS = [
    CallbackQueryHandler(start_add, pattern=f"^{ADD}$"),
    CallbackQueryHandler(start_other_amount, pattern=OTHER_AMOUNT),
]

STATES = {
    "sub_name": [MessageHandler(TEXT, sub_name)],
    "sub_category": [
        button(sub_category, CATEGORY_PREFIX),
        MessageHandler(TEXT, tap_a_button),
    ],
    "sub_account": [
        button(sub_account, ACCOUNT_PREFIX),
        MessageHandler(TEXT, tap_a_button),
    ],
    "sub_amount": [MessageHandler(TEXT, sub_amount)],
    "sub_day": [MessageHandler(TEXT, sub_day)],
    "sub_pay_amount": [MessageHandler(TEXT, sub_pay_amount)],
}


def register(app):
    app.add_handler(CommandHandler("langganan", langganan))
    app.add_handler(CallbackQueryHandler(delete_button, pattern=f"^{DELETE_PREFIX}"))
    app.add_handler(CallbackQueryHandler(pay_button, pattern=PAY))
    app.add_handler(CallbackQueryHandler(skip_button, pattern=SKIP))
    app.job_queue.run_repeating(
        send_due_reminders, interval=CHECK_EVERY_SECONDS, first=10
    )
