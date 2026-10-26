"""/riwayat: browse every entry, open one, edit or delete it.

/riwayat ──► list (8 per page, newest first, ◀ ▶)
               │ tap an entry
               ▼
             detail ──► Ubah nama / jumlah   (asks for text: conversation)
                    ──► Ubah kategori / akun (buttons only)
                    ──► Hapus ──► confirm
"""

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
from app.config import TZ
from app.cycles import MONTHS
from app.formatters import describe_transaction, history_label
from app.handlers.shared import TEXT, reply_error, start_flow, two_per_row
from app.validators import parse_amount, validate_item

PAGE_SIZE = 8

# What can be changed, per kind. Debts and transfers: only the amount.
EDITS = {
    "expense": ["item", "amount", "category", "account"],
    "income": ["item", "amount", "account"],
    "transfer": ["amount"],
    "lend": ["amount"],
    "collect": ["amount"],
    "borrow": ["amount"],
    "repay": ["amount"],
    "adjustment": [],
}
# Spending leaves FROM an account, income goes TO one
ACCOUNT_FIELD = {"expense": "from_account_id", "income": "to_account_id"}

# Button data patterns. All untrusted: the regex checks the shape, the
# handler checks that the entry exists and the edit is allowed for its kind.
PAGE = re.compile(r"^riwayat:(\d{1,6})$")
OPEN = re.compile(r"^tx:(\d+)$")
EDIT_TEXT = re.compile(r"^edit:(item|amount):(\d+)$")
PICK_CATEGORY = re.compile(r"^editcat:(\d+)$")
SET_CATEGORY = re.compile(r"^setcat:(\d+):(\d+)$")
PICK_ACCOUNT = re.compile(r"^editacc:(\d+)$")
SET_ACCOUNT = re.compile(r"^setacc:(\d+):(\d+)$")
DELETE = re.compile(r"^del:(\d+)$")
DELETE_YES = re.compile(r"^delyes:(\d+)$")


def when(t):
    moment = t["created_at"].astimezone(TZ)  # a datetime from Postgres
    return f"{moment.day} {MONTHS[moment.month - 1]} {moment.year}, {moment:%H:%M}"


def allowed(t, field):
    return t is not None and field in EDITS[t["kind"]]


# ---------- list ----------


def page(offset):
    rows = db.recent_transactions(offset, PAGE_SIZE + 1)  # +1: is there more?
    has_older = len(rows) > PAGE_SIZE
    rows = rows[:PAGE_SIZE]
    if not rows:
        return "📜 Belum ada catatan.", None

    keyboard = [
        [InlineKeyboardButton(history_label(t), callback_data=f"tx:{t['id']}")]
        for t in rows
    ]
    nav = []
    if offset > 0:
        newer = max(0, offset - PAGE_SIZE)
        nav.append(
            InlineKeyboardButton("◀ Lebih baru", callback_data=f"riwayat:{newer}")
        )
    if has_older:
        older = offset + PAGE_SIZE
        nav.append(
            InlineKeyboardButton("Lebih lama ▶", callback_data=f"riwayat:{older}")
        )
    if nav:
        keyboard.append(nav)
    return "📜 Riwayat (terbaru di atas). Ketuk untuk ubah atau hapus.", (
        InlineKeyboardMarkup(keyboard)
    )


async def riwayat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, keyboard = page(0)
    await update.message.reply_text(text, reply_markup=keyboard)


async def page_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text, keyboard = page(int(PAGE.match(query.data).group(1)))
    await query.edit_message_text(text, reply_markup=keyboard)


# ---------- detail ----------


def detail(t):
    actions = {
        "item": ("✏️ Nama", f"edit:item:{t['id']}"),
        "amount": ("✏️ Jumlah", f"edit:amount:{t['id']}"),
        "category": ("🏷 Kategori", f"editcat:{t['id']}"),
        "account": ("💳 Akun", f"editacc:{t['id']}"),
    }
    buttons = [
        InlineKeyboardButton(label, callback_data=data)
        for field, (label, data) in actions.items()
        if field in EDITS[t["kind"]]
    ]
    buttons.append(InlineKeyboardButton("🗑 Hapus", callback_data=f"del:{t['id']}"))
    keyboard = two_per_row(buttons).inline_keyboard + (
        (InlineKeyboardButton("« Riwayat", callback_data="riwayat:0"),),
    )
    text = f"{describe_transaction(t)}\n🕒 {when(t)}"
    return text, InlineKeyboardMarkup(keyboard)


async def show_detail(query, transaction_id, note=""):
    t = db.get_transaction(transaction_id)
    if t is None:
        await query.edit_message_text("Catatan ini sudah tidak ada.")
        return
    text, keyboard = detail(t)
    await query.edit_message_text(note + text, reply_markup=keyboard)


async def open_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await show_detail(query, int(OPEN.match(query.data).group(1)))


# ---------- edit with buttons: category, account ----------


async def pick_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    transaction_id = int(PICK_CATEGORY.match(query.data).group(1))
    if not allowed(db.get_transaction(transaction_id), "category"):
        return
    keyboard = two_per_row(
        [
            InlineKeyboardButton(
                c["name"], callback_data=f"setcat:{transaction_id}:{c['id']}"
            )
            for c in db.categories()
        ]
    )
    await query.edit_message_text("Kategori baru?", reply_markup=keyboard)


async def set_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    match = SET_CATEGORY.match(query.data)
    transaction_id, category_id = int(match.group(1)), int(match.group(2))
    if db.get_category(category_id) is None or not allowed(
        db.get_transaction(transaction_id), "category"
    ):
        return
    db.update_transaction(transaction_id, "category_id", category_id)
    await show_detail(query, transaction_id, "✅ Diubah\n")


async def pick_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    transaction_id = int(PICK_ACCOUNT.match(query.data).group(1))
    if not allowed(db.get_transaction(transaction_id), "account"):
        return
    keyboard = two_per_row(
        [
            InlineKeyboardButton(
                a["name"], callback_data=f"setacc:{transaction_id}:{a['id']}"
            )
            for a in db.accounts()
        ]
    )
    await query.edit_message_text("Akun baru?", reply_markup=keyboard)


async def set_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    match = SET_ACCOUNT.match(query.data)
    transaction_id, account_id = int(match.group(1)), int(match.group(2))
    t = db.get_transaction(transaction_id)
    if not allowed(t, "account") or db.get_account(account_id) is None:
        return
    db.update_transaction(transaction_id, ACCOUNT_FIELD[t["kind"]], account_id)
    await show_detail(query, transaction_id, "✅ Diubah\n")


# ---------- delete ----------


async def delete_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    t = db.get_transaction(int(DELETE.match(query.data).group(1)))
    if t is None:
        await query.edit_message_text("Catatan ini sudah tidak ada.")
        return
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Ya, hapus", callback_data=f"delyes:{t['id']}"),
                InlineKeyboardButton("Batal", callback_data=f"tx:{t['id']}"),
            ]
        ]
    )
    await query.edit_message_text(
        f"Hapus catatan ini?\n{describe_transaction(t)}", reply_markup=keyboard
    )


async def delete_yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    t = db.get_transaction(int(DELETE_YES.match(query.data).group(1)))
    if t is None:
        await query.edit_message_text("Catatan ini sudah tidak ada.")
        return
    db.delete_transaction(t["id"])
    await query.edit_message_text(
        f"🗑️ Dihapus: {describe_transaction(t)}",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("« Riwayat", callback_data="riwayat:0")]]
        ),
    )


# ---------- edit with text: name, amount (needs the conversation) ----------


async def start_edit_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    match = EDIT_TEXT.match(query.data)
    field, transaction_id = match.group(1), int(match.group(2))
    t = db.get_transaction(transaction_id)
    if not allowed(t, field):
        return ConversationHandler.END

    start_flow(update, context)
    context.user_data["edit"] = (transaction_id, field)
    question = "Nama baru?" if field == "item" else "Jumlah baru?"
    await query.edit_message_text(f"{describe_transaction(t)}\n\n{question}")
    return "edit_text"


async def edit_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    transaction_id, field = context.user_data["edit"]
    try:
        if field == "item":
            value = validate_item(update.message.text)
        else:
            value = parse_amount(update.message.text)
    except ValueError as error:
        await reply_error(update, error)
        return "edit_text"

    context.user_data.clear()
    if db.get_transaction(transaction_id) is None:
        await update.message.reply_text("Catatan ini sudah tidak ada.")
        return ConversationHandler.END
    db.update_transaction(transaction_id, field, value)
    text, keyboard = detail(db.get_transaction(transaction_id))
    await update.message.reply_text("✅ Diubah\n" + text, reply_markup=keyboard)
    return ConversationHandler.END


ENTRY_POINTS = [CallbackQueryHandler(start_edit_text, pattern=EDIT_TEXT)]

STATES = {"edit_text": [MessageHandler(TEXT, edit_text)]}


def register(app):
    app.add_handler(CommandHandler("riwayat", riwayat))
    for pattern, callback in [
        (PAGE, page_button),
        (OPEN, open_button),
        (PICK_CATEGORY, pick_category),
        (SET_CATEGORY, set_category),
        (PICK_ACCOUNT, pick_account),
        (SET_ACCOUNT, set_account),
        (DELETE, delete_button),
        (DELETE_YES, delete_yes),
    ]:
        app.add_handler(CallbackQueryHandler(callback, pattern=pattern))
