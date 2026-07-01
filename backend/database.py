from pathlib import Path
import hashlib
import secrets

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

STALE_JOURNAL = DATA_DIR / "marketsim.db-journal"
if STALE_JOURNAL.exists() and STALE_JOURNAL.stat().st_size == 0:
    try:
        STALE_JOURNAL.unlink()
    except OSError:
        pass

PRIMARY_DB_FILE = DATA_DIR / "marketsim.db"
RUNTIME_DB_FILE = DATA_DIR / "marketsim_runtime.db"
DB_FILE = RUNTIME_DB_FILE if (DATA_DIR / "marketsim.db-journal").exists() else PRIMARY_DB_FILE
DATABASE_URL = f"sqlite:///{DB_FILE}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def configure_sqlite(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=OFF")
    cursor.execute("PRAGMA synchronous=OFF")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    import models

    Base.metadata.create_all(bind=engine)
    _migrate_legacy_tables(models)


def _legacy_password_hash() -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", b"marketsim123", salt.encode("utf-8"), 120000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def _table_columns(table_name: str) -> set[str]:
    inspector = inspect(engine)
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _migrate_legacy_tables(models):
    legacy_tables = ["accounts", "watchlist", "positions", "trades"]
    if not any(_table_columns(table_name) and "user_id" not in _table_columns(table_name) for table_name in legacy_tables):
        return

    with engine.begin() as conn:
        row = conn.execute(text("select id from users order by id limit 1")).mappings().first()
        if row:
            user_id = row["id"]
        else:
            result = conn.execute(
                text("insert into users (username, password_hash, created_at, updated_at) values (:u, :p, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"),
                {"u": "demo", "p": _legacy_password_hash()},
            )
            user_id = result.lastrowid

        for table_name in legacy_tables:
            columns = _table_columns(table_name)
            if not columns or "user_id" in columns:
                continue

            legacy_name = f"{table_name}_legacy"
            conn.execute(text(f"alter table {table_name} rename to {legacy_name}"))
            Base.metadata.tables[table_name].create(bind=conn, checkfirst=False)

            if table_name == "accounts":
                conn.execute(
                    text(
                        f"""
                        insert into accounts (user_id, cash, initial_cash, created_at, updated_at)
                        select :user_id, cash, initial_cash, created_at, updated_at from {legacy_name}
                        """
                    ),
                    {"user_id": user_id},
                )
            elif table_name == "watchlist":
                conn.execute(
                    text(
                        f"""
                        insert into watchlist (user_id, symbol, name, asset_type, note, created_at)
                        select :user_id, symbol, name, asset_type, note, created_at from {legacy_name}
                        """
                    ),
                    {"user_id": user_id},
                )
            elif table_name == "positions":
                conn.execute(
                    text(
                        f"""
                        insert into positions (
                            user_id, symbol, name, asset_type, quantity, avg_cost, current_price,
                            market_value, profit, profit_rate, updated_at
                        )
                        select :user_id, symbol, name, asset_type, quantity, avg_cost, current_price,
                            market_value, profit, profit_rate, updated_at from {legacy_name}
                        """
                    ),
                    {"user_id": user_id},
                )
            elif table_name == "trades":
                conn.execute(
                    text(
                        f"""
                        insert into trades (
                            user_id, symbol, name, asset_type, side, price, quantity, amount,
                            fee, profit, created_at
                        )
                        select :user_id, symbol, name, asset_type, side, price, quantity, amount,
                            fee, profit, created_at from {legacy_name}
                        """
                    ),
                    {"user_id": user_id},
                )
