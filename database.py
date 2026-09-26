import os
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker

def is_data_writable():
    return os.path.exists("/data") and os.access("/data", os.W_OK)

def get_sqlite_url():
    if is_data_writable():
        return "sqlite:////data/production.db"
    return "sqlite:///./production.db"

db_url = os.getenv("DATABASE_URL")
if not db_url:
    db_url = get_sqlite_url()
elif db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# If PostgreSQL is configured, verify connection; if unreachable/expired, fallback to SQLite
if db_url.startswith("postgresql"):
    try:
        test_engine = create_engine(db_url, connect_args={"connect_timeout": 5})
        with test_engine.connect() as test_conn:
            test_conn.execute(text("SELECT 1;"))
        test_engine.dispose()
        print("Connected successfully to PostgreSQL database.")
    except Exception as pg_err:
        print(f"WARNING: PostgreSQL database connection failed ({pg_err}). Falling back to SQLite database.")
        db_url = get_sqlite_url()

connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}

engine = create_engine(db_url, connect_args=connect_args)

if db_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
