import os
import shutil
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

os.makedirs("data", exist_ok=True)

# If root bi_prototype.db exists but data/bi_prototype.db doesn't, copy it over
if os.path.exists("bi_prototype.db") and not os.path.exists("data/bi_prototype.db"):
    try:
        shutil.copy("bi_prototype.db", "data/bi_prototype.db")
    except Exception:
        pass

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/bi_prototype.db")

connect_args = {"check_same_thread": False, "timeout": 30} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def ensure_schema():
    """Add columns introduced after the first SQLite create_all()."""
    with engine.begin() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(projects)")).fetchall()}
        if cols:
            if "advice_focus" not in cols:
                conn.execute(text("ALTER TABLE projects ADD COLUMN advice_focus VARCHAR"))
            if "analysis" not in cols:
                conn.execute(text("ALTER TABLE projects ADD COLUMN analysis JSON"))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
