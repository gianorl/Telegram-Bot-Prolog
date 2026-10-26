"""/hutang: money I lent (piutang) and money I owe (hutang), per person.

    lend     I lend or pay for someone   money leaves my account   they owe me more
    collect  they pay me back            money enters my account   they owe me less
    borrow   I borrow from someone       money enters my account   I owe more
    repay    I pay them back             money leaves my account   I owe less

None of these count as spending or income.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
)

from app import db
from app.formatters import debt_line, rupiah
from app.handlers.shared import (
    ACCOUNT_PREFIX,
    TEXT,
    account_keyboard,
    button,
    no_accounts,
    parse_id,
    picked_account,
    reply_error,
    start_flow,
    tap_a_button,
    two_per_row,
)
from app.validators import parse_amount, validate_person_name

KIND_PREFIX = "debt:"  # debt:lend
PERSON_PREFIX = "person:"  # person:4

# kind: (button label, account question, does money leave my account?)
KINDS = {
    "lend": ("Aku pinjamkan / talangi", "Dari akun mana?", True),
    "collect": ("Dia bayar ke aku", "Masuk ke akun mana?", False),
    "borrow": ("Aku pinjam", "Masuk ke akun mana?", False),
    "repay": ("Aku bayar hutang", "Dari akun mana?", True),
}


def summary():
    rows = db.debts()
    if not rows:
        return "🤝 Belum ada hutang atau piutang."
    return "🤝 Hutang & piutang\n" + "\n".join(
        debt_line(r["name"], r["owed"]) for r in rows
    )


def people_for(kind):
    """Paying back only makes sense with someone who has an open balance."""
    if kind == "collect":
        return [r for r in db.debts() if r["owed"] > 0]
    if kind == "repay":
        return [r for r in db.debts() if r["owed"] < 0]
    return db.people()


async def start_hutang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db.accounts():
        return await no_accounts(update)
    start_flow(update, context)
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(label, callback_data=KIND_PREFIX + kind)]
            for kind, (label, _, _) in KINDS.items()
        ]
    )
    await update.message.reply_text(summary(), reply_markup=keyboard)
    return "debt_kind"


async def debt_kind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kind = query.data.removeprefix(KIND_PREFIX)
    if kind not in KINDS:  # button data is untrusted
        return "debt_kind"

    candidates = people_for(kind)
    if kind in ("collect", "repay") and not candidates:
        await query.edit_message_text(
            "Tidak ada yang berutang ke kamu."
            if kind == "collect"
            else "Kamu tidak punya hutang. 🎉"
        )
        return ConversationHandler.END

    context.user_data["kind"] = kind
    buttons = [
        InlineKeyboardButton(p["name"], callback_data=f"{PERSON_PREFIX}{p['id']}")
        for p in candidates
    ]
    question = "Dengan siapa?"
    if kind in ("lend", "borrow"):
        question += "\nPilih atau ketik nama baru."
    keyboard = two_per_row(buttons) if buttons else None  # no one yet: just type
    await query.edit_message_text(question, reply_markup=keyboard)
    return "debt_person"


async def debt_person_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    person_id = parse_id(query.data, PERSON_PREFIX)
    kind = context.user_data["kind"]
    allowed = {p["id"] for p in people_for(kind)}
    if person_id not in allowed:
        await reply_error(update, "Pilihan tidak valid.")
        return "debt_person"

    context.user_data["person"] = dict(db.get_person(person_id))
    return await ask_account(update, context)


async def debt_person_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kind = context.user_data["kind"]
    if kind in ("collect", "repay"):
        await update.message.reply_text("Pilih dari tombol di atas ya.")
        return "debt_person"
    try:
        name = validate_person_name(update.message.text)
    except ValueError as error:
        await reply_error(update, error)
        return "debt_person"

    # The person is only created when the entry is saved, so /batal leaves no trace
    context.user_data["person"] = {"id": None, "name": name}
    return await ask_account(update, context)


async def ask_account(update, context):
    question = KINDS[context.user_data["kind"]][1]
    person = context.user_data["person"]["name"]
    await update.effective_message.reply_text(
        f"{person} · {question}", reply_markup=account_keyboard()
    )
    return "debt_account"


async def debt_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    account = picked_account(query)
    if account is None:
        await reply_error(update, "Akun tidak valid.", account_keyboard())
        return "debt_account"

    context.user_data["account"] = dict(account)
    person = context.user_data["person"]
    text = f"{person['name']} · {account['name']}\nBerapa?"
    if person["id"] and context.user_data["kind"] in ("collect", "repay"):
        text += f" (sisa {rupiah(abs(db.debt_with(person['id'])))})"
    await query.edit_message_text(text)
    return "debt_amount"


async def debt_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    kind, person, account = data["kind"], data["person"], data["account"]
    try:
        amount = parse_amount(update.message.text)
        if kind in ("collect", "repay"):
            open_amount = abs(db.debt_with(person["id"]))
            if amount > open_amount:
                raise ValueError(f"Maksimal {rupiah(open_amount)} (sisa hutangnya).")
    except ValueError as error:
        await reply_error(update, error)
        return "debt_amount"

    person_id = person["id"] or db.find_or_add_person(person["name"])
    leaves_my_account = KINDS[kind][2]
    db.add_transaction(
        kind,
        f"{KINDS[kind][0]}: {person['name']}",
        amount,
        data["sent_at"].isoformat(),
        from_account_id=account["id"] if leaves_my_account else None,
        to_account_id=None if leaves_my_account else account["id"],
        person_id=person_id,
    )
    context.user_data.clear()

    owed = db.debt_with(person_id)
    status = (
        debt_line(person["name"], owed) if owed else f"Lunas dengan {person['name']} 🎉"
    )
    direction = "dari" if leaves_my_account else "ke"
    await update.message.reply_text(
        f"✅ {KINDS[kind][0]}: {person['name']} {rupiah(amount)} "
        f"({direction} {account['name']})\n{status}"
    )
    return ConversationHandler.END


ENTRY_POINTS = [CommandHandler("hutang", start_hutang)]

STATES = {
    "debt_kind": [button(debt_kind, KIND_PREFIX), MessageHandler(TEXT, tap_a_button)],
    "debt_person": [
        button(debt_person_button, PERSON_PREFIX),
        MessageHandler(TEXT, debt_person_text),
    ],
    "debt_account": [
        button(debt_account, ACCOUNT_PREFIX),
        MessageHandler(TEXT, tap_a_button),
    ],
    "debt_amount": [MessageHandler(TEXT, debt_amount)],
}
