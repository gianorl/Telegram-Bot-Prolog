import psycopg
import pytest

from app import db

NOW = "2026-10-28T10:00:00+07:00"
CYCLE = ("2026-10-27T00:00:00+07:00", "2026-11-27T00:00:00+07:00")

pytestmark = pytest.mark.usefixtures("fresh_db")  # every test starts empty


def account_id(name):
    return db.find_account(name)["id"]


def cat(name):
    return db.find_category(name)["id"]


def test_fresh_db_gets_full_schema():
    rows = db._all(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
    )
    tables = {row["table_name"] for row in rows}
    assert {"accounts", "transactions", "budgets", "people", "subscriptions"} <= tables
    row = db._one("SELECT MAX(version) AS version FROM schema_version")
    assert row["version"] == len(db.MIGRATIONS)


def test_migrate_twice_does_nothing():
    with db.pool.connection() as conn:
        db.migrate(conn)  # tables already exist: would crash if it ran again
    assert db._one("SELECT COUNT(*) AS n FROM schema_version")["n"] == len(
        db.MIGRATIONS
    )


def test_dates_come_back_as_jakarta_time():
    db.add_account("Cash", 0, "2026-10-28T03:00:00+00:00")  # 03:00 UTC
    created = db._one("SELECT created_at FROM accounts")["created_at"]
    assert (created.hour, str(created.utcoffset())) == (10, "7:00:00")


def test_default_categories_in_order():
    assert [c["name"] for c in db.categories()] == db.DEFAULT_CATEGORIES


def test_find_category_ignores_case_and_spaces():
    assert db.find_category(" makan ")["name"] == "Makan"
    assert db.find_category("jajan") is None
    assert db.find_category("Makan; DROP TABLE categories") is None


def test_unknown_category_id_is_rejected_by_database():
    db.add_account("Cash", 0, NOW)
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        db.add_transaction(
            "expense", "x", 1, NOW, category_id=9999, from_account_id=account_id("Cash")
        )


def test_expense_without_category_is_rejected_by_database():
    db.add_account("Cash", 0, NOW)
    with pytest.raises(psycopg.errors.CheckViolation):
        db.add_transaction("expense", "x", 1, NOW, from_account_id=account_id("Cash"))


def test_renaming_a_category_renames_it_everywhere():
    db.add_account("Cash", 0, NOW)
    db.add_transaction(
        "expense",
        "x",
        1,
        NOW,
        category_id=cat("Makan"),
        from_account_id=account_id("Cash"),
    )
    db._run("UPDATE categories SET name = 'Makan & Minum' WHERE name = 'Makan'")
    assert db.last_transaction()["category"] == "Makan & Minum"


def test_old_text_categories_move_to_ids():
    """Version 1 data (category as text) survives migration 2."""
    with db.pool.connection() as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
        conn.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
        db.MIGRATIONS[0](conn)
        conn.execute("INSERT INTO schema_version VALUES (1)")
        conn.execute(
            "INSERT INTO accounts (name, created_at) VALUES ('Cash', %s)", (NOW,)
        )
        conn.execute(
            "INSERT INTO transactions (kind, item, amount, category, from_account_id,"
            " created_at) VALUES ('expense', 'nasi', 100, 'makan', 1, %s),"
            " ('expense', 'obat', 50, 'Kesehatan', 1, %s)",
            (NOW, NOW),
        )
        conn.execute("INSERT INTO budgets VALUES ('Makan', 1000)")
        db.migrate(conn)

    assert db.get_transaction(1)["category"] == "Makan"  # matched ignoring case
    assert db.get_transaction(2)["category"] == "Kesehatan"  # unknown name kept
    assert [(b["category"], b["amount"]) for b in db.budgets()] == [("Makan", 1000)]


def test_account_names_are_unique_ignoring_case():
    db.add_account("CIMB", 0, NOW)
    assert db.find_account("cimb")["name"] == "CIMB"
    with pytest.raises(psycopg.IntegrityError):
        db.add_account("Cimb", 0, NOW)


def test_balances_follow_every_movement():
    db.add_account("CIMB", 1_000_000, NOW)
    db.add_account("GoPay", 50_000, NOW)
    cimb, gopay = account_id("CIMB"), account_id("GoPay")

    db.add_transaction("income", "Gaji", 6_000_000, NOW, to_account_id=cimb)
    db.add_transaction(
        "transfer", "Top up", 200_000, NOW, from_account_id=cimb, to_account_id=gopay
    )
    db.add_transaction(
        "expense",
        "ojol",
        25_000,
        NOW,
        category_id=cat("Transport"),
        from_account_id=gopay,
    )

    assert {r["name"]: r["balance"] for r in db.balances()} == {
        "CIMB": 1_000_000 + 6_000_000 - 200_000,
        "GoPay": 50_000 + 200_000 - 25_000,
    }


def test_transfer_is_not_spending():
    db.add_account("CIMB", 0, NOW)
    db.add_account("GoPay", 0, NOW)
    db.add_transaction(
        "transfer",
        "Top up",
        200_000,
        NOW,
        from_account_id=account_id("CIMB"),
        to_account_id=account_id("GoPay"),
    )
    assert db.sum_by_kind("expense", *CYCLE) == 0
    assert db.spending_by_category(*CYCLE) == []


def test_cycle_range_includes_start_and_excludes_end():
    db.add_account("Cash", 0, NOW)
    cash = account_id("Cash")
    for when in [
        "2026-10-26T23:59:00+07:00",  # last cycle
        "2026-10-27T00:00:00+07:00",  # first minute of this cycle
        "2026-11-26T23:59:00+07:00",  # last minute of this cycle
        "2026-11-27T00:00:00+07:00",  # next cycle
    ]:
        db.add_transaction(
            "expense", "x", 1000, when, category_id=cat("Makan"), from_account_id=cash
        )

    assert db.sum_by_kind("expense", *CYCLE) == 2000
    assert db.spent_in_category(cat("Makan"), *CYCLE) == 2000


def test_spending_by_category_biggest_first():
    db.add_account("Cash", 0, NOW)
    cash = account_id("Cash")
    db.add_transaction(
        "expense", "a", 5000, NOW, category_id=cat("Makan"), from_account_id=cash
    )
    db.add_transaction(
        "expense", "b", 9000, NOW, category_id=cat("Transport"), from_account_id=cash
    )
    db.add_transaction(
        "expense", "c", 1000, NOW, category_id=cat("Makan"), from_account_id=cash
    )
    db.add_transaction("income", "gaji", 99999, NOW, to_account_id=cash)

    assert [(r["category"], r["amount"]) for r in db.spending_by_category(*CYCLE)] == [
        ("Transport", 9000),
        ("Makan", 6000),
    ]


def test_budgets_set_update_delete():
    makan = cat("Makan")
    db.set_budget(makan, 1_500_000)
    db.set_budget(makan, 1_200_000)  # second time updates, no duplicate
    assert [(b["category"], b["amount"]) for b in db.budgets()] == [
        ("Makan", 1_200_000)
    ]
    assert db.budget_for(makan) == 1_200_000
    assert db.budget_for(cat("Transport")) is None
    db.delete_budget(makan)
    assert db.budgets() == []


def test_last_and_delete():
    db.add_account("Cash", 0, NOW)
    cash = account_id("Cash")
    db.add_transaction(
        "expense", "nasi", 25000, NOW, category_id=cat("Makan"), from_account_id=cash
    )
    db.add_transaction("income", "gaji", 100, NOW, to_account_id=cash)

    last = db.last_transaction()
    assert (last["kind"], last["to_account"]) == ("income", "Cash")

    db.delete_transaction(last["id"])
    assert db.last_transaction()["item"] == "nasi"


def test_most_recently_used_account_comes_first():
    db.add_account("CIMB", 0, NOW)
    db.add_account("GoPay", 0, NOW)
    db.add_account("Cash", 0, NOW)
    assert [a["name"] for a in db.accounts()] == ["CIMB", "GoPay", "Cash"]

    db.add_transaction(
        "expense",
        "x",
        1,
        NOW,
        category_id=cat("Makan"),
        from_account_id=account_id("GoPay"),
    )
    assert [a["name"] for a in db.accounts()] == ["GoPay", "CIMB", "Cash"]


def test_amount_must_be_positive_in_database_too():
    with pytest.raises(psycopg.IntegrityError):
        db.add_transaction("expense", "x", 0, NOW, category_id=cat("Makan"))


def test_adjustment_changes_balance_but_is_not_income_or_spending():
    db.add_account("CIMB", 1000, NOW)
    cimb = account_id("CIMB")
    db.add_transaction("adjustment", "Penyesuaian", 300, NOW, from_account_id=cimb)
    assert db.balance_of(cimb) == 700
    db.add_transaction("adjustment", "Penyesuaian", 50, NOW, to_account_id=cimb)
    assert db.balance_of(cimb) == 750
    assert db.sum_by_kind("expense", *CYCLE) == 0
    assert db.sum_by_kind("income", *CYCLE) == 0


def test_people_are_unique_ignoring_case():
    first = db.find_or_add_person("Andi")
    assert db.find_or_add_person("andi") == first
    assert db.get_person(first)["name"] == "Andi"


def test_debts_both_directions():
    db.add_account("CIMB", 1_000_000, NOW)
    cimb = account_id("CIMB")
    andi = db.find_or_add_person("Andi")
    budi = db.find_or_add_person("Budi")

    db.add_transaction("lend", "x", 100_000, NOW, from_account_id=cimb, person_id=andi)
    db.add_transaction("collect", "x", 40_000, NOW, to_account_id=cimb, person_id=andi)
    db.add_transaction("borrow", "x", 200_000, NOW, to_account_id=cimb, person_id=budi)
    db.add_transaction("repay", "x", 50_000, NOW, from_account_id=cimb, person_id=budi)

    assert db.debt_with(andi) == 60_000  # Andi still owes me
    assert db.debt_with(budi) == -150_000  # I still owe Budi
    assert [(r["name"], r["owed"]) for r in db.debts()] == [
        ("Budi", -150_000),
        ("Andi", 60_000),
    ]
    assert db.balance_of(cimb) == 1_000_000 - 100_000 + 40_000 + 200_000 - 50_000
    assert db.sum_by_kind("expense", *CYCLE) == 0  # debts are not spending


def test_past_debt_without_account_keeps_balances():
    db.add_account("CIMB", 500_000, NOW)
    andi = db.find_or_add_person("Andi")
    db.add_transaction("lend", "x", 100_000, NOW, person_id=andi)  # no account
    assert db.debt_with(andi) == 100_000
    assert db.balance_of(account_id("CIMB")) == 500_000


def test_settled_debt_disappears_from_list():
    db.add_account("CIMB", 0, NOW)
    cimb = account_id("CIMB")
    andi = db.find_or_add_person("Andi")
    db.add_transaction("lend", "x", 100, NOW, from_account_id=cimb, person_id=andi)
    db.add_transaction("collect", "x", 100, NOW, to_account_id=cimb, person_id=andi)
    assert db.debts() == []


def test_update_transaction_fields():
    db.add_account("CIMB", 0, NOW)
    db.add_account("GoPay", 0, NOW)
    db.add_transaction(
        "expense",
        "nasi",
        100,
        NOW,
        category_id=cat("Makan"),
        from_account_id=account_id("CIMB"),
    )
    tid = db.last_transaction()["id"]

    db.update_transaction(tid, "item", "nasi padang")
    db.update_transaction(tid, "amount", 25000)
    db.update_transaction(tid, "category_id", cat("Lainnya"))
    db.update_transaction(tid, "from_account_id", account_id("GoPay"))

    t = db.get_transaction(tid)
    assert (t["item"], t["amount"], t["category"], t["from_account"]) == (
        "nasi padang",
        25000,
        "Lainnya",
        "GoPay",
    )


def test_update_rejects_unknown_field():
    with pytest.raises(KeyError):
        db.update_transaction(1, "kind; DROP TABLE transactions", "x")


def test_recent_transactions_pages():
    db.add_account("Cash", 0, NOW)
    for i in range(1, 6):
        db.add_transaction(
            "expense",
            f"x{i}",
            i,
            NOW,
            category_id=cat("Makan"),
            from_account_id=account_id("Cash"),
        )
    assert [t["item"] for t in db.recent_transactions(0, 2)] == ["x5", "x4"]
    assert [t["item"] for t in db.recent_transactions(4, 2)] == ["x1"]


def test_subscriptions():
    db.add_account("CIMB", 0, NOW)
    db.add_subscription(
        "Netflix", 54000, cat("Hiburan"), account_id("CIMB"), 5, None, NOW
    )
    sub = db.subscriptions()[0]
    assert (sub["name"], sub["category"], sub["account"], sub["day"]) == (
        "Netflix",
        "Hiburan",
        "CIMB",
        5,
    )

    db.mark_reminded(sub["id"], "2026-11")
    db.mark_paid(sub["id"], "2026-11")
    sub = db.get_subscription(sub["id"])
    assert (sub["last_reminded"], sub["last_paid"]) == ("2026-11", "2026-11")

    db.delete_subscription(sub["id"])
    assert db.subscriptions() == []
