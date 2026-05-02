import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id          SERIAL PRIMARY KEY,
        email       TEXT UNIQUE NOT NULL,
        password    TEXT NOT NULL,
        provider    TEXT NOT NULL DEFAULT 'gmail',
        created_at  TIMESTAMP DEFAULT NOW()
    );
""")

cur.execute("""
    CREATE TABLE IF NOT EXISTS emails (
        id            SERIAL PRIMARY KEY,
        account       TEXT NOT NULL,
        from_address  TEXT,
        subject       TEXT,
        body          TEXT,
        received_at   TEXT,
        forwarded_at  TIMESTAMP DEFAULT NOW(),
        status        TEXT DEFAULT 'forwarded'
    );
""")

conn.commit()
cur.close()
conn.close()
print("✅ Tables created successfully!")