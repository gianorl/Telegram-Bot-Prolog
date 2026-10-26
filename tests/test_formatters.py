from datetime import datetime

from app.formatters import (
    budget_line,
    debt_line,
    describe_transaction,
    history_label,
    progress_bar,
    rupiah,
)


def test_rupiah():
    assert rupiah(0) == "Rp0"
    assert rupiah(25000) == "Rp25.000"
    assert rupiah(1000000) == "Rp1.000.000"
    assert rupiah(-50000) == "-Rp50.000"


def test_progress_bar():
    assert progress_bar(0, 100) == "░░░░░░░░░░"
    assert progress_bar(80, 100) == "████████░░"
    assert progress_bar(250, 100) == "██████████"  # over budget never overflows


def test_budget_line_warnings():
    assert "⚠️" not in budget_line("Makan", 500, 1000)
    assert "⚠️" in budget_line("Makan", 800, 1000)
    assert "🚨" in budget_line("Makan", 1200, 1000)
    assert "sisa -Rp200" in budget_line("Makan", 1200, 1000)


def row(**fields):
    base = {
        "item": "nasi",
        "amount": 25000,
        "category": None,
        "from_account": None,
        "to_account": None,
        "person": None,
        "created_at": datetime.fromisoformat("2026-10-28T12:00:00+07:00"),
    }
    return base | fields


def test_describe_transaction():
    cases = [
        (
            row(kind="expense", category="Makan", from_account="GoPay"),
            "nasi (Makan, GoPay) Rp25.000",
        ),
        (row(kind="expense", category="Makan"), "nasi (Makan) Rp25.000"),
        (
            row(kind="income", item="Gaji", to_account="CIMB"),
            "Masuk: Gaji → CIMB Rp25.000",
        ),
        (
            row(kind="transfer", from_account="CIMB", to_account="GoPay"),
            "Pindah: CIMB → GoPay Rp25.000",
        ),
        (row(kind="adjustment", to_account="CIMB"), "Penyesuaian CIMB +Rp25.000"),
        (row(kind="adjustment", from_account="CIMB"), "Penyesuaian CIMB -Rp25.000"),
        (
            row(kind="lend", person="Andi", from_account="CIMB"),
            "Pinjamkan ke Andi Rp25.000 (dari CIMB)",
        ),
        (
            row(kind="collect", person="Andi", to_account="CIMB"),
            "Andi bayar ke kamu Rp25.000 (ke CIMB)",
        ),
        (
            row(kind="borrow", person="Budi", to_account="CIMB"),
            "Pinjam dari Budi Rp25.000 (ke CIMB)",
        ),
        (
            row(kind="repay", person="Budi", from_account="CIMB"),
            "Bayar hutang ke Budi Rp25.000 (dari CIMB)",
        ),
        (row(kind="lend", person="Andi"), "Pinjamkan ke Andi Rp25.000 (tanpa akun)"),
        (row(kind="borrow", person="Budi"), "Pinjam dari Budi Rp25.000 (tanpa akun)"),
    ]
    for t, expected in cases:
        assert describe_transaction(t) == expected


def test_history_label():
    assert history_label(row(kind="expense")) == "28/10 nasi -Rp25.000"
    assert history_label(row(kind="income")) == "28/10 nasi +Rp25.000"
    assert history_label(row(kind="transfer")) == "28/10 nasi ⇄ Rp25.000"
    assert history_label(row(kind="adjustment", to_account="CIMB")).endswith(
        "+Rp25.000"
    )
    long = history_label(row(kind="expense", item="x" * 40))
    assert "…" in long


def test_debt_line():
    assert debt_line("Andi", 50000) == "Andi berutang ke kamu: Rp50.000"
    assert debt_line("Budi", -50000) == "Kamu berutang ke Budi: Rp50.000"
