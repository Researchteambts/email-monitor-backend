import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

try:
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    print("Connected to Neon!")
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")