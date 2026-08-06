"""SQLite engine configuration and session management for LaneSight."""

from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from lanesight import models  # noqa: F401  (registers tables)

_DB_DIR = Path(__file__).resolve().parent.parent
DB_PATH = _DB_DIR / "lanesight.db"

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
