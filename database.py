from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Neon requires SSL — engine handles it via the connection string
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,      # auto-reconnect if connection drops
    pool_size=5,             # keep 5 connections ready
    max_overflow=10,         # allow 10 extra under load
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# ── Dependency for FastAPI routes ─────────────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()