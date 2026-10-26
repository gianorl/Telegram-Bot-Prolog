import os

import pytest

from app import db

# A separate database just for tests. NEVER point this at your real data:
# every test wipes it.
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "postgresql:///prolog_test")


@pytest.fixture(scope="session")
def pool():
    db.init_db(TEST_DATABASE_URL)
    with db.pool.connection() as conn:
        name = conn.execute("SELECT current_database() AS name").fetchone()["name"]
    assert name.endswith("_test"), f"refusing to wipe {name!r}, not a test database"
    yield db.pool
    db.close_db()


@pytest.fixture
def fresh_db(pool):
    """Empty database with the full schema, for every test that asks for it."""
    with pool.connection() as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
        db.migrate(conn)
