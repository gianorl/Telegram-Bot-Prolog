def rupiah(n):
    if n < 0:
        return "-" + rupiah(-n)
    return f"Rp{n:,}".replace(",", ".")


def progress_bar(spent, limit, width=10):
    """(1200000, 1500000) -> "████████░░" """
    filled = min(width, round(width * spent / limit)) if limit > 0 else width
    return "█" * filled + "░" * (width - filled)


def budget_line(category, spent, limit):
    percent = round(100 * spent / limit)
    warning = " 🚨" if spent > limit else " ⚠️" if percent >= 80 else ""
    return (
        f"{category} {progress_bar(spent, limit)} {percent}%{warning}\n"
        f"   {rupiah(spent)} / {rupiah(limit)}, sisa {rupiah(limit - spent)}"
    )


def describe_transaction(t):
    """One line for any kind of transaction row (from db.get_transaction)."""
    kind, amount = t["kind"], rupiah(t["amount"])
    if kind == "income":
        return f"Masuk: {t['item']} → {t['to_account']} {amount}"
    if kind == "transfer":
        return f"Pindah: {t['from_account']} → {t['to_account']} {amount}"
    if kind == "adjustment":
        if t["to_account"]:
            return f"Penyesuaian {t['to_account']} +{amount}"
        return f"Penyesuaian {t['from_account']} -{amount}"
    if kind == "lend":
        return f"Pinjamkan ke {t['person']} {amount} (dari {t['from_account']})"
    if kind == "collect":
        return f"{t['person']} bayar ke kamu {amount} (ke {t['to_account']})"
    if kind == "borrow":
        return f"Pinjam dari {t['person']} {amount} (ke {t['to_account']})"
    if kind == "repay":
        return f"Bayar hutang ke {t['person']} {amount} (dari {t['from_account']})"
    where = ", ".join(x for x in (t["category"], t["from_account"]) if x)
    return f"{t['item']} ({where}) {amount}"


# Money coming into my accounts shows +, going out shows -, moving shows ⇄
_SIGN = {
    "expense": "-",
    "lend": "-",
    "repay": "-",
    "income": "+",
    "collect": "+",
    "borrow": "+",
    "transfer": "⇄ ",
}


def history_label(t):
    """Short text for a history button: "25/10 nasi padang -Rp25.000" """
    day = f"{t['created_at']:%d/%m}"  # created_at is a datetime from Postgres
    if t["kind"] == "adjustment":
        sign = "+" if t["to_account"] else "-"
    else:
        sign = _SIGN[t["kind"]]
    name = t["item"] if len(t["item"]) <= 22 else t["item"][:21] + "…"
    return f"{day} {name} {sign}{rupiah(t['amount'])}"


def debt_line(name, owed):
    if owed > 0:
        return f"{name} berutang ke kamu: {rupiah(owed)}"
    return f"Kamu berutang ke {name}: {rupiah(-owed)}"
