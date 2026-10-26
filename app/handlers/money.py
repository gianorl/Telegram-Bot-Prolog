"""Flows: /catat (spending), /masuk (income), /pindah (transfer),
/akun (add account), /sesuaikan (fix a balance that drifted).

Each module exports ENTRY_POINTS and STATES; handlers/flows.py puts them all
into ONE ConversationHandler.
"""

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
)

from app import db
from app.formatters import budget_line, rupiah
from app.handlers.shared import (
    ACCOUNT_PREFIX,
    CATEGORY_PREFIX,
    TEXT,
    account_keyboard,
    button,
    category_keyboard,
    cycle_bounds,
    no_accounts,
    picked_account,
    picked_category,
    reply_error,
    start_flow,
    tap_a_button,
)
from app.validators import (
    MAX_BALANCE,
    parse_amount,
    validate_account_name,
    validate_item,
)

FROM_PREFIX = "from:"
TO_PREFIX = "to:"
ADJUST_PREFIX = "adj:"


# ---------- /catat: spending ----------


async def start_catat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db.accounts():
        return await no_accounts(update)
    start_flow(update, context)
    await update.message.reply_text("Kategori?", reply_markup=category_keyboard())
    return "catat_category"


async def catat_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # stops the loading spinner on the button
    category = picked_category(query)
    if category is None:
        await reply_error(update, "Kategori tidak valid.", category_keyboard())
        return "catat_category"

    context.user_data["category"] = dict(category)
    await query.edit_message_text(f"Kategori: {category['name']}\nApa yang kamu beli?")
    return "catat_item"


async def catat_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        item = validate_item(update.message.text)
    except ValueError as error:
        await reply_error(update, error)
        return "catat_item"
    context.user_data["item"] = item
    category = context.user_data["category"]["name"]
    await update.message.reply_text(
        f"{category} · {item}\nBayar pakai akun apa?", reply_markup=account_keyboard()
    )
    return "catat_account"


async def catat_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    account = picked_account(query)
    if account is None:
        await reply_error(update, "Akun tidak valid.", account_keyboard())
        return "catat_account"

    context.user_data["account"] = dict(account)
    data = context.user_data
    await query.edit_message_text(
        f"{data['category']['name']} · {data['item']} · {account['name']}\nBerapa?"
    )
    return "catat_amount"


async def catat_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = parse_amount(update.message.text)
    except ValueError as error:
        await reply_error(update, error)
        return "catat_amount"  # stay on this step

    data = context.user_data
    item, category, account = data["item"], data["category"], data["account"]
    sent_at = data["sent_at"]
    db.add_transaction(
        "expense",
        item,
        amount,
        sent_at.isoformat(),
        category_id=category["id"],
        from_account_id=account["id"],
    )
    reply = f"✅ {item} ({category['name']}, {account['name']}) {rupiah(amount)}"

    # Budget check for this pay cycle (BR-17)
    limit = db.budget_for(category["id"])
    if limit:
        start, end = cycle_bounds(sent_at)
        spent = db.spent_in_category(category["id"], start, end)
        reply += "\n\n" + budget_line(category["name"], spent, limit)

    context.user_data.clear()
    await update.message.reply_text(reply)
    return ConversationHandler.END


# ---------- /masuk: income ----------


async def start_masuk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db.accounts():
        return await no_accounts(update)
    start_flow(update, context)
    await update.message.reply_text("Pemasukan apa? (contoh: Gaji Oktober)")
    return "masuk_item"


async def masuk_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["item"] = validate_item(update.message.text)
    except ValueError as error:
        await reply_error(update, error)
        return "masuk_item"
    await update.message.reply_text(
        "Masuk ke akun mana?", reply_markup=account_keyboard()
    )
    return "masuk_account"


async def masuk_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    account = picked_account(query)
    if account is None:
        await reply_error(update, "Akun tidak valid.", account_keyboard())
        return "masuk_account"

    context.user_data["account"] = dict(account)
    await query.edit_message_text(f"Masuk ke {account['name']}\nBerapa?")
    return "masuk_amount"


async def masuk_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = parse_amount(update.message.text)
    except ValueError as error:
        await reply_error(update, error)
        return "masuk_amount"

    data = context.user_data
    item, account = data["item"], data["account"]
    db.add_transaction(
        "income", item, amount, data["sent_at"].isoformat(), to_account_id=account["id"]
    )
    # Read everything BEFORE clear(): `data` is the same dict, so it empties too
    context.user_data.clear()
    await update.message.reply_text(
        f"✅ Masuk: {item} → {account['name']} {rupiah(amount)}"
    )
    return ConversationHandler.END


# ---------- /pindah: move money between accounts (not spending) ----------


async def start_pindah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(db.accounts()) < 2:
        await update.message.reply_text(
            "Butuh minimal 2 akun untuk pindah dana. Tambah dengan /akun."
        )
        return ConversationHandler.END
    start_flow(update, context)
    await update.message.reply_text(
        "Pindah dari akun mana?", reply_markup=account_keyboard(FROM_PREFIX)
    )
    return "pindah_from"


async def pindah_from(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    account = picked_account(query, FROM_PREFIX)
    if account is None:
        await reply_error(update, "Akun tidak valid.", account_keyboard(FROM_PREFIX))
        return "pindah_from"

    context.user_data["from"] = dict(account)
    await query.edit_message_text(
        f"Dari {account['name']} ke akun mana?",
        reply_markup=account_keyboard(TO_PREFIX, exclude_id=account["id"]),
    )
    return "pindah_to"


async def pindah_to(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    source = context.user_data["from"]
    account = picked_account(query, TO_PREFIX)
    if account is None or account["id"] == source["id"]:
        await reply_error(
            update,
            "Akun tujuan tidak valid.",
            account_keyboard(TO_PREFIX, exclude_id=source["id"]),
        )
        return "pindah_to"

    context.user_data["to"] = dict(account)
    await query.edit_message_text(f"{source['name']} → {account['name']}\nBerapa?")
    return "pindah_amount"


async def pindah_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = parse_amount(update.message.text)
    except ValueError as error:
        await reply_error(update, error)
        return "pindah_amount"

    data = context.user_data
    source, target = data["from"], data["to"]
    db.add_transaction(
        "transfer",
        f"Pindah {source['name']} → {target['name']}",
        amount,
        data["sent_at"].isoformat(),
        from_account_id=source["id"],
        to_account_id=target["id"],
    )
    context.user_data.clear()
    await update.message.reply_text(
        f"✅ Pindah: {source['name']} → {target['name']} {rupiah(amount)}"
    )
    return ConversationHandler.END


# ---------- /akun: add an account ----------


async def start_akun(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_flow(update, context)
    existing = ", ".join(a["name"] for a in db.accounts()) or "belum ada"
    await update.message.reply_text(
        f"Akun sekarang: {existing}\n\nNama akun baru? (contoh: CIMB, SeaBank, GoPay, Cash)"
    )
    return "akun_name"


async def akun_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        name = validate_account_name(update.message.text)
    except ValueError as error:
        await reply_error(update, error)
        return "akun_name"
    if db.find_account(name):
        await update.message.reply_text(
            f"Akun {name} sudah ada. Nama lain? (atau /batal)"
        )
        return "akun_name"

    context.user_data["name"] = name
    await update.message.reply_text(
        f"Saldo {name} sekarang berapa? (cek di aplikasinya, 0 kalau kosong)"
    )
    return "akun_balance"


async def akun_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        balance = parse_amount(update.message.text, minimum=0, maximum=MAX_BALANCE)
    except ValueError as error:
        await reply_error(update, error)
        return "akun_balance"

    name = context.user_data["name"]
    db.add_account(name, balance, context.user_data["sent_at"].isoformat())
    context.user_data.clear()
    await update.message.reply_text(
        f"✅ Akun {name} ditambahkan, saldo {rupiah(balance)}.\n"
        "Tambah lagi: /akun · Lihat semua: /saldo"
    )
    return ConversationHandler.END


# ---------- /sesuaikan: the real app says a different balance ----------


async def start_sesuaikan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db.accounts():
        return await no_accounts(update)
    start_flow(update, context)
    await update.message.reply_text(
        "Sesuaikan saldo akun mana?", reply_markup=account_keyboard(ADJUST_PREFIX)
    )
    return "adjust_account"


async def adjust_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    account = picked_account(query, ADJUST_PREFIX)
    if account is None:
        await reply_error(update, "Akun tidak valid.", account_keyboard(ADJUST_PREFIX))
        return "adjust_account"

    context.user_data["account"] = dict(account)
    await query.edit_message_text(
        f"Saldo {account['name']} di Prolog: {rupiah(db.balance_of(account['id']))}\n"
        f"Saldo asli di aplikasi {account['name']} sekarang berapa?"
    )
    return "adjust_amount"


async def adjust_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        real = parse_amount(update.message.text, minimum=0, maximum=MAX_BALANCE)
    except ValueError as error:
        await reply_error(update, error)
        return "adjust_amount"

    account, sent_at = context.user_data["account"], context.user_data["sent_at"]
    difference = real - db.balance_of(account["id"])
    context.user_data.clear()
    if difference == 0:
        await update.message.reply_text(f"Saldo {account['name']} sudah sama ✅")
        return ConversationHandler.END

    # Positive: money appeared (it goes "to" the account). Negative: it vanished.
    db.add_transaction(
        "adjustment",
        "Penyesuaian saldo",
        abs(difference),
        sent_at.isoformat(),
        to_account_id=account["id"] if difference > 0 else None,
        from_account_id=account["id"] if difference < 0 else None,
    )
    sign = "+" if difference > 0 else "-"
    await update.message.reply_text(
        f"✅ {account['name']} disesuaikan {sign}{rupiah(abs(difference))}, "
        f"sekarang {rupiah(real)}.\n"
        "Tidak dihitung sebagai pengeluaran atau pemasukan."
    )
    return ConversationHandler.END


ENTRY_POINTS = [
    CommandHandler("catat", start_catat),
    CommandHandler("masuk", start_masuk),
    CommandHandler("pindah", start_pindah),
    CommandHandler("akun", start_akun),
    CommandHandler("sesuaikan", start_sesuaikan),
]

STATES = {
    "catat_category": [
        button(catat_category, CATEGORY_PREFIX),
        MessageHandler(TEXT, tap_a_button),
    ],
    "catat_item": [MessageHandler(TEXT, catat_item)],
    "catat_account": [
        button(catat_account, ACCOUNT_PREFIX),
        MessageHandler(TEXT, tap_a_button),
    ],
    "catat_amount": [MessageHandler(TEXT, catat_amount)],
    "masuk_item": [MessageHandler(TEXT, masuk_item)],
    "masuk_account": [
        button(masuk_account, ACCOUNT_PREFIX),
        MessageHandler(TEXT, tap_a_button),
    ],
    "masuk_amount": [MessageHandler(TEXT, masuk_amount)],
    "pindah_from": [
        button(pindah_from, FROM_PREFIX),
        MessageHandler(TEXT, tap_a_button),
    ],
    "pindah_to": [button(pindah_to, TO_PREFIX), MessageHandler(TEXT, tap_a_button)],
    "pindah_amount": [MessageHandler(TEXT, pindah_amount)],
    "akun_name": [MessageHandler(TEXT, akun_name)],
    "akun_balance": [MessageHandler(TEXT, akun_balance)],
    "adjust_account": [
        button(adjust_account, ADJUST_PREFIX),
        MessageHandler(TEXT, tap_a_button),
    ],
    "adjust_amount": [MessageHandler(TEXT, adjust_amount)],
}
