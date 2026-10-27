"""Every SQL query lives here. Handlers only call these functions.

PostgreSQL is a separate program (a server), not a file. We keep a small pool
of open connections to it, like a warung keeping a few gas tanks ready:

    bot ──► pool ──► [conn] [conn] ──► PostgreSQL ──► data on disk

Placeholders are %s (psycopg's style). They are still parameters: the values
travel separately from the SQL text, so user input can never become SQL.
"""

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

pool = None  # set by init_db()


# ---------- migrations ----------


def _initial_schema(c):
    """The full schema as of R2.5. The SQLite history before this is in git."""
    c.execute("""
        CREATE TABLE accounts (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name TEXT NOT NULL,
            opening_balance BIGINT NOT NULL DEFAULT 0,  -- up to Rp10 miliar
            created_at TIMESTAMPTZ NOT NULL
        )
    """)
    # "CIMB" and "cimb" are the same account
    c.execute("CREATE UNIQUE INDEX accounts_name_unique ON accounts (lower(name))")
    c.execute("""
        CREATE TABLE people (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name TEXT NOT NULL
        )
    """)
    c.execute("CREATE UNIQUE INDEX people_name_unique ON people (lower(name))")
    c.execute("""
        CREATE TABLE transactions (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            kind TEXT NOT NULL CHECK (kind IN (
                'expense', 'income', 'transfer', 'adjustment',
                'lend', 'collect', 'borrow', 'repay'
            )),
            item TEXT NOT NULL,
            amount INTEGER NOT NULL CHECK (amount > 0),
            category TEXT,
            from_account_id INTEGER REFERENCES accounts(id),
            to_account_id INTEGER REFERENCES accounts(id),
            person_id INTEGER REFERENCES people(id),
            created_at TIMESTAMPTZ NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE budgets (
            category TEXT PRIMARY KEY,
            amount INTEGER NOT NULL CHECK (amount > 0)
        )
    """)
    c.execute("""
        CREATE TABLE subscriptions (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name TEXT NOT NULL,
            amount INTEGER NOT NULL CHECK (amount > 0),
            category TEXT NOT NULL,
            account_id INTEGER NOT NULL REFERENCES accounts(id),
            day INTEGER NOT NULL CHECK (day BETWEEN 1 AND 31),
            last_reminded TEXT,  -- "2026-11": month we last sent the reminder
            last_paid TEXT,      -- "2026-11": month it was logged as paid
            created_at TIMESTAMPTZ NOT NULL
        )
    """)


DEFAULT_CATEGORIES = ["Makan", "Transport", "Belanja", "Tagihan", "Hiburan", "Lainnya"]


def _categories_table(c):
    """Categories get their own table. Other tables point to it by id (FK).

    Before: transactions.category = "Makan"  (text, checked only by Python)
    After:  transactions.category_id = 1  ──►  categories(1, "Makan")
    Renaming "Makan" later changes ONE row, and Postgres blocks unknown ids.
    """
    c.execute("""
        CREATE TABLE categories (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name TEXT NOT NULL
        )
    """)
    c.execute("CREATE UNIQUE INDEX categories_name_unique ON categories (lower(name))")
    for name in DEFAULT_CATEGORIES:
        c.execute("INSERT INTO categories (name) VALUES (%s)", (name,))
    # Any other name already used in old rows becomes a category too, so no
    # row loses its category in the move
    c.execute("""
        INSERT INTO categories (name)
        SELECT DISTINCT category FROM (
            SELECT category FROM transactions
            UNION SELECT category FROM subscriptions
            UNION SELECT category FROM budgets
        ) used
        WHERE category IS NOT NULL
          AND lower(category) NOT IN (SELECT lower(name) FROM categories)
    """)

    # transactions: text column -> id column (empty for non-spending kinds)
    c.execute("""
        ALTER TABLE transactions
        ADD COLUMN category_id INTEGER REFERENCES categories(id)
    """)
    c.execute("""
        UPDATE transactions t SET category_id = c.id
        FROM categories c WHERE lower(c.name) = lower(t.category)
    """)
    c.execute("ALTER TABLE transactions DROP COLUMN category")
    # Spending must always have a category; now the database checks it too
    c.execute("""
        ALTER TABLE transactions ADD CONSTRAINT expense_has_category
        CHECK (kind <> 'expense' OR category_id IS NOT NULL)
    """)

    # subscriptions: every row needs a category
    c.execute("""
        ALTER TABLE subscriptions
        ADD COLUMN category_id INTEGER REFERENCES categories(id)
    """)
    c.execute("""
        UPDATE subscriptions s SET category_id = c.id
        FROM categories c WHERE lower(c.name) = lower(s.category)
    """)
    c.execute("ALTER TABLE subscriptions DROP COLUMN category")
    c.execute("ALTER TABLE subscriptions ALTER COLUMN category_id SET NOT NULL")

    # budgets: one budget per category, so category_id is the primary key
    c.execute("""
        ALTER TABLE budgets
        ADD COLUMN category_id INTEGER REFERENCES categories(id)
    """)
    c.execute("""
        UPDATE budgets b SET category_id = c.id
        FROM categories c WHERE lower(c.name) = lower(b.category)
    """)
    c.execute("ALTER TABLE budgets DROP COLUMN category")  # drops the old key too
    c.execute("ALTER TABLE budgets ADD PRIMARY KEY (category_id)")


# Append new migrations at the end. Never reorder or edit old ones:
# position 1 = version 1, position 2 = version 2, ...
MIGRATIONS = [_initial_schema, _categories_table]


def migrate(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
    row = conn.execute("SELECT MAX(version) AS version FROM schema_version").fetchone()
    version = row["version"] or 0
    for number, migration in enumerate(MIGRATIONS, start=1):
        if number > version:
            # All or nothing: if a migration fails halfway, Postgres undoes
            # the whole thing, including CREATE TABLE. SQLite couldn't do that.
            with conn.transaction():
                migration(conn)
                conn.execute(
                    "INSERT INTO schema_version (version) VALUES (%s)", (number,)
                )


def init_db(url, timezone="Asia/Jakarta"):
    global pool

    def configure(conn):
        # Dates come back as Jakarta time, not UTC
        conn.execute("SELECT set_config('TimeZone', %s, false)", (timezone,))

    pool = ConnectionPool(
        url,
        min_size=1,
        max_size=4,
        # autocommit: each statement is saved right away, like before.
        # dict_row: rows come back as dicts, so row["name"] works.
        kwargs={"autocommit": True, "row_factory": dict_row},
        configure=configure,
        check=ConnectionPool.check_connection,  # replace dead connections
        open=True,
    )
    pool.wait(timeout=10)  # fail at startup if Postgres isn't reachable
    with pool.connection() as conn:
        migrate(conn)


def close_db():
    pool.close()


# Three small helpers so each query below is one line of intent
def _all(sql, params=()):
    with pool.connection() as conn:
        return conn.execute(sql, params).fetchall()


def _one(sql, params=()):
    with pool.connection() as conn:
        return conn.execute(sql, params).fetchone()


def _run(sql, params=()):
    with pool.connection() as conn:
        conn.execute(sql, params)


# ---------- categories ----------


def categories():
    return _all("SELECT id, name FROM categories ORDER BY id")


def get_category(category_id):
    return _one("SELECT id, name FROM categories WHERE id = %s", (category_id,))


def find_category(name):
    """Typed text: "makan" finds "Makan"."""
    return _one(
        "SELECT id, name FROM categories WHERE lower(name) = lower(%s)",
        ((name or "").strip(),),
    )


# ---------- accounts ----------


def add_account(name, opening_balance, created_at):
    _run(
        "INSERT INTO accounts (name, opening_balance, created_at) VALUES (%s, %s, %s)",
        (name, opening_balance, created_at),
    )


def find_account(name):
    return _one(
        "SELECT id, name FROM accounts WHERE lower(name) = lower(%s)", (name,)
    )  # so "cimb" finds "CIMB"


def get_account(account_id):
    return _one("SELECT id, name FROM accounts WHERE id = %s", (account_id,))


def accounts():
    """Most recently used first, so your usual account is the first button."""
    return _all("""
        SELECT a.id, a.name FROM accounts a
        ORDER BY (
            SELECT MAX(t.id) FROM transactions t
            WHERE t.from_account_id = a.id OR t.to_account_id = a.id
        ) DESC NULLS LAST, a.id
    """)


# One rule for every kind of transaction (BR-14):
# starting balance + money that came IN to it - money that went OUT of it
_BALANCE = """
    a.opening_balance
    + COALESCE((SELECT SUM(amount) FROM transactions WHERE to_account_id = a.id), 0)
    - COALESCE((SELECT SUM(amount) FROM transactions WHERE from_account_id = a.id), 0)
"""


def balances():
    """[{id, name, balance}, ...]"""
    return _all(
        "SELECT a.id, a.name, " + _BALANCE + " AS balance FROM accounts a ORDER BY a.id"
    )


def balance_of(account_id):
    row = _one(
        "SELECT " + _BALANCE + " AS balance FROM accounts a WHERE a.id = %s",
        (account_id,),
    )
    return row["balance"]


# ---------- transactions ----------


def add_transaction(
    kind,
    item,
    amount,
    created_at,
    category_id=None,
    from_account_id=None,
    to_account_id=None,
    person_id=None,
):
    _run(
        """
        INSERT INTO transactions (kind, item, amount, category_id,
            from_account_id, to_account_id, person_id, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            kind,
            item,
            amount,
            category_id,
            from_account_id,
            to_account_id,
            person_id,
            created_at,
        ),
    )


# Every read of a transaction joins in the account and person names
_SELECT_TRANSACTION = """
    SELECT t.id, t.kind, t.item, t.amount, t.created_at,
           t.category_id, t.from_account_id, t.to_account_id, t.person_id,
           c.name AS category, f.name AS from_account, d.name AS to_account,
           p.name AS person
    FROM transactions t
    LEFT JOIN categories c ON c.id = t.category_id
    LEFT JOIN accounts f ON f.id = t.from_account_id
    LEFT JOIN accounts d ON d.id = t.to_account_id
    LEFT JOIN people p ON p.id = t.person_id
"""


def get_transaction(transaction_id):
    return _one(_SELECT_TRANSACTION + " WHERE t.id = %s", (transaction_id,))


def last_transaction():
    return _one(_SELECT_TRANSACTION + " ORDER BY t.id DESC LIMIT 1")


def all_transactions():
    """Everything, oldest first (for /ekspor)."""
    return _all(_SELECT_TRANSACTION + " ORDER BY t.created_at, t.id")


def recent_transactions(offset, limit):
    """Newest first. Asks for one extra row to know if there's a next page."""
    return _all(
        _SELECT_TRANSACTION + " ORDER BY t.id DESC LIMIT %s OFFSET %s",
        (limit, offset),
    )


# Column names can't be %s placeholders, so each editable field gets its own
# fixed SQL. The field name picks the statement; it never becomes SQL text.
_UPDATE_SQL = {
    "item": "UPDATE transactions SET item = %s WHERE id = %s",
    "amount": "UPDATE transactions SET amount = %s WHERE id = %s",
    "category_id": "UPDATE transactions SET category_id = %s WHERE id = %s",
    "from_account_id": "UPDATE transactions SET from_account_id = %s WHERE id = %s",
    "to_account_id": "UPDATE transactions SET to_account_id = %s WHERE id = %s",
}


def update_transaction(transaction_id, field, value):
    _run(_UPDATE_SQL[field], (value, transaction_id))


def delete_transaction(transaction_id):
    _run("DELETE FROM transactions WHERE id = %s", (transaction_id,))


# ---------- reports (start/end are ISO strings; end is NOT included) ----------


def sum_by_kind(kind, start, end):
    row = _one(
        """
        SELECT COALESCE(SUM(amount), 0) AS total FROM transactions
        WHERE kind = %s AND created_at >= %s AND created_at < %s
        """,
        (kind, start, end),
    )
    return row["total"]


def spending_by_category(start, end):
    return _all(
        """
        SELECT c.name AS category, SUM(t.amount) AS amount
        FROM transactions t JOIN categories c ON c.id = t.category_id
        WHERE t.kind = 'expense' AND t.created_at >= %s AND t.created_at < %s
        GROUP BY c.id, c.name
        ORDER BY amount DESC
        """,
        (start, end),
    )


def spent_in_category(category_id, start, end):
    row = _one(
        """
        SELECT COALESCE(SUM(amount), 0) AS total FROM transactions
        WHERE kind = 'expense' AND category_id = %s
          AND created_at >= %s AND created_at < %s
        """,
        (category_id, start, end),
    )
    return row["total"]


# ---------- budgets ----------


def set_budget(category_id, amount):
    _run(
        """
        INSERT INTO budgets (category_id, amount) VALUES (%s, %s)
        ON CONFLICT (category_id) DO UPDATE SET amount = excluded.amount
        """,
        (category_id, amount),
    )


def delete_budget(category_id):
    _run("DELETE FROM budgets WHERE category_id = %s", (category_id,))


def budgets():
    """[{category_id, category, amount}, ...] in category order."""
    return _all("""
        SELECT b.category_id, c.name AS category, b.amount
        FROM budgets b JOIN categories c ON c.id = b.category_id
        ORDER BY c.id
    """)


def budget_for(category_id):
    """The budget amount, or None if this category has no budget."""
    row = _one("SELECT amount FROM budgets WHERE category_id = %s", (category_id,))
    return row["amount"] if row else None


# ---------- people and debts (hutang / piutang) ----------


def find_or_add_person(name):
    """Returns the person's id. "andi" and "Andi" are the same person."""
    row = _one("SELECT id FROM people WHERE lower(name) = lower(%s)", (name,))
    if row:
        return row["id"]
    # RETURNING hands back the new row's id in the same trip
    return _one("INSERT INTO people (name) VALUES (%s) RETURNING id", (name,))["id"]


def get_person(person_id):
    return _one("SELECT id, name FROM people WHERE id = %s", (person_id,))


# Positive = they owe me (piutang). Negative = I owe them (hutang).
_DEBT = """
    COALESCE((SELECT SUM(CASE t.kind
        WHEN 'lend' THEN t.amount
        WHEN 'collect' THEN -t.amount
        WHEN 'borrow' THEN -t.amount
        WHEN 'repay' THEN t.amount
    END) FROM transactions t WHERE t.person_id = p.id), 0)
"""


def debts():
    """[{id, name, owed}, ...] for everyone with an open balance, biggest first."""
    # Postgres can't use the alias "owed" in WHERE, so compute it in an inner query
    return _all(
        "SELECT * FROM (SELECT p.id, p.name, " + _DEBT + " AS owed FROM people p) d"
        " WHERE owed != 0 ORDER BY ABS(owed) DESC, name"
    )


def debt_with(person_id):
    row = _one(
        "SELECT " + _DEBT + " AS owed FROM people p WHERE p.id = %s", (person_id,)
    )
    return row["owed"] if row else 0


def people():
    return _all("SELECT id, name FROM people ORDER BY name")


# ---------- subscriptions (recurring payments) ----------


def add_subscription(
    name, amount, category_id, account_id, day, last_reminded, created_at
):
    _run(
        """
        INSERT INTO subscriptions
            (name, amount, category_id, account_id, day, last_reminded, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (name, amount, category_id, account_id, day, last_reminded, created_at),
    )


_SELECT_SUBSCRIPTION = """
    SELECT s.id, s.name, s.amount, s.category_id, s.account_id, s.day,
           s.last_reminded, s.last_paid, c.name AS category, a.name AS account
    FROM subscriptions s
    JOIN accounts a ON a.id = s.account_id
    JOIN categories c ON c.id = s.category_id
"""


def subscriptions():
    return _all(_SELECT_SUBSCRIPTION + " ORDER BY s.day, s.name")


def get_subscription(subscription_id):
    return _one(_SELECT_SUBSCRIPTION + " WHERE s.id = %s", (subscription_id,))


def delete_subscription(subscription_id):
    _run("DELETE FROM subscriptions WHERE id = %s", (subscription_id,))


def mark_reminded(subscription_id, month):
    _run(
        "UPDATE subscriptions SET last_reminded = %s WHERE id = %s",
        (month, subscription_id),
    )


def mark_paid(subscription_id, month):
    _run(
        "UPDATE subscriptions SET last_paid = %s WHERE id = %s",
        (month, subscription_id),
    )
