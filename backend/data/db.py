from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./bi_prototype.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 30}
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
