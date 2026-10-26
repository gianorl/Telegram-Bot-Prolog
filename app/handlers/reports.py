"""One-step commands: /saldo, /bulan, /budget, /hapus."""

from datetime import date, datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from app import db
from app.config import PAYDAY_DAY, TZ
from app.cycles import cycle_for, cycle_label, next_cycle, previous_cycle
from app.formatters import budget_line, describe_transaction, rupiah
from app.validators import MAX_AMOUNT, parse_amount

BULAN_PREFIX = "bulan:"  # bulan:2026-10-27 (start date of the cycle to show)
HAPUS_YES = "hapus:"  # hapus:42 (transaction id)
HAPUS_NO = "hapus:batal"


def today():
    return datetime.now(TZ).date()


def iso(day):
    """date -> "2026-10-27T00:00:00+07:00", the format created_at uses."""
    return datetime.combine(day, datetime.min.time(), TZ).isoformat()


# ---------- /saldo ----------


async def saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = db.balances()
    if not rows:
        await update.message.reply_text("Belum ada akun. Tambah dengan /akun.")
        return
    lines = ["💳 Saldo"]
    lines += [f"{row['name']}: {rupiah(row['balance'])}" for row in rows]
    lines.append(f"\nTotal: {rupiah(sum(row['balance'] for row in rows))}")
    await update.message.reply_text("\n".join(lines))


# ---------- /bulan: one pay cycle, with buttons to move back and forth ----------


def cycle_report(start, end):
    start_iso, end_iso = iso(start), iso(end)
    income = db.sum_by_kind("income", start_iso, end_iso)
    spending = db.sum_by_kind("expense", start_iso, end_iso)
    difference = income - spending

    lines = [
        f"📅 {cycle_label(start, end)}",
        f"Masuk: {rupiah(income)}",
        f"Keluar: {rupiah(spending)}",
        f"Selisih: {'+' if difference > 0 else ''}{rupiah(difference)}",
    ]

    rows = db.spending_by_category(start_iso, end_iso)
    if rows:
        lines.append("\nPer kategori:")
        lines += [f"{row['category']}: {rupiah(row['amount'])}" for row in rows]

    budgets = db.budgets()
    if budgets:
        lines.append("\nBudget:")
        for b in budgets:
            spent = db.spent_in_category(b["category_id"], start_iso, end_iso)
            lines.append(budget_line(b["category"], spent, b["amount"]))

    prev_start, prev_end = previous_cycle(start, PAYDAY_DAY)
    prev_spending = db.sum_by_kind("expense", iso(prev_start), iso(prev_end))
    if prev_spending:
        change = round(100 * (spending - prev_spending) / prev_spending)
        word = "naik" if change > 0 else "turun"
        lines.append(
            f"\nSiklus lalu keluar {rupiah(prev_spending)} ({word} {abs(change)}%)"
        )
    return "\n".join(lines)


def cycle_buttons(start, end):
    prev_start, _ = previous_cycle(start, PAYDAY_DAY)
    buttons = [
        InlineKeyboardButton(
            "◀ Sebelumnya", callback_data=BULAN_PREFIX + str(prev_start)
        )
    ]
    if end <= today():  # there is a newer cycle
        next_start, _ = next_cycle(end, PAYDAY_DAY)
        buttons.append(
            InlineKeyboardButton(
                "Berikutnya ▶", callback_data=BULAN_PREFIX + str(next_start)
            )
        )
    return InlineKeyboardMarkup([buttons])


async def bulan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start, end = cycle_for(today(), PAYDAY_DAY)
    await update.message.reply_text(
        cycle_report(start, end), reply_markup=cycle_buttons(start, end)
    )


async def bulan_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:  # button data is untrusted: must be a real date, not in the future
        day = date.fromisoformat(query.data.removeprefix(BULAN_PREFIX))
    except ValueError:
        return
    if day > today():
        return
    start, end = cycle_for(day, PAYDAY_DAY)
    await query.edit_message_text(
        cycle_report(start, end), reply_markup=cycle_buttons(start, end)
    )


# ---------- /budget ----------

BUDGET_HELP = (
    "Atur budget per siklus gajian:\n/budget Makan 1500000\nHapus: /budget Makan 0"
)


async def budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args  # words after the command: "/budget Makan 1500000"
    if not args:
        await show_budgets(update)
        return
    if len(args) != 2:
        await update.message.reply_text(BUDGET_HELP)
        return

    try:
        category = db.find_category(args[0])
        if category is None:
            names = ", ".join(c["name"] for c in db.categories())
            raise ValueError(f"Kategori tidak dikenal. Pilihan: {names}")
        amount = parse_amount(args[1], minimum=0, maximum=MAX_AMOUNT)
    except ValueError as error:
        await update.message.reply_text(f"{error}\n\n{BUDGET_HELP}")
        return

    if amount == 0:
        db.delete_budget(category["id"])
        await update.message.reply_text(f"Budget {category['name']} dihapus.")
        return
    db.set_budget(category["id"], amount)
    await update.message.reply_text(
        f"✅ Budget {category['name']}: {rupiah(amount)} per siklus gajian."
    )
    await show_budgets(update)


async def show_budgets(update):
    budgets = db.budgets()
    if not budgets:
        await update.message.reply_text("Belum ada budget.\n\n" + BUDGET_HELP)
        return
    start, end = cycle_for(today(), PAYDAY_DAY)
    lines = [f"🎯 Budget {cycle_label(start, end)}"]
    for b in budgets:
        spent = db.spent_in_category(b["category_id"], iso(start), iso(end))
        lines.append(budget_line(b["category"], spent, b["amount"]))
    await update.message.reply_text("\n".join(lines))


# ---------- /hapus: undo the last transaction ----------


async def hapus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    last = db.last_transaction()
    if last is None:
        await update.message.reply_text("Belum ada catatan untuk dihapus.")
        return

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Ya, hapus", callback_data=f"{HAPUS_YES}{last['id']}"
                ),
                InlineKeyboardButton("Batal", callback_data=HAPUS_NO),
            ]
        ]
    )
    await update.message.reply_text(
        f"Hapus catatan terakhir?\n{describe_transaction(last)}", reply_markup=keyboard
    )


async def hapus_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == HAPUS_NO:
        await query.edit_message_text("Oke, tidak ada yang dihapus.")
        return

    # Button data is untrusted: the id must be a number AND still be the newest
    # record (BR-08: only the last one can be undone, even from an old button)
    raw_id = query.data.removeprefix(HAPUS_YES)
    last = db.last_transaction()
    if (
        not (raw_id.isascii() and raw_id.isdigit())
        or last is None
        or int(raw_id) != last["id"]
    ):
        await query.edit_message_text(
            "Catatan terakhir sudah berubah. Kirim /hapus lagi."
        )
        return

    db.delete_transaction(last["id"])
    await query.edit_message_text(f"🗑️ Dihapus: {describe_transaction(last)}")


def register(app):
    app.add_handler(CommandHandler("saldo", saldo))
    app.add_handler(CommandHandler(["bulan", "total"], bulan))
    app.add_handler(CallbackQueryHandler(bulan_button, pattern=f"^{BULAN_PREFIX}"))
    app.add_handler(CommandHandler("budget", budget))
    app.add_handler(CommandHandler("hapus", hapus))
    app.add_handler(CallbackQueryHandler(hapus_button, pattern="^hapus:"))
