"""Apply auth schema. Run: python scripts/run_auth_migration.py"""
from pathlib import Path

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://fitwise:fitwise@localhost:5432/fitwise",
)

sql = Path(__file__).with_name("03_auth.sql").read_text()
engine = create_engine(DATABASE_URL)
with engine.begin() as conn:
    conn.execute(text(sql))
print("Auth migration applied.")
