import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from core.config import settings

# Para SQLite relativo, ancora o caminho na pasta do backend (independente do CWD do uvicorn)
_db_url = settings.DATABASE_URL
if "sqlite" in _db_url and "///./" in _db_url:
    _backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _db_path = os.path.join(_backend_dir, "erp.db")
    _db_url = f"sqlite:///{_db_path}"

engine = create_engine(
    _db_url,
    connect_args={"check_same_thread": False} if "sqlite" in _db_url else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass
