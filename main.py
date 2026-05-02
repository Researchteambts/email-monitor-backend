from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json, os, threading
from monitor import main as run_monitor, load_log, ACCOUNTS

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Start email monitor in background thread on startup
@app.on_event("startup")
def start_monitor():
    t = threading.Thread(target=run_monitor, daemon=True)
    t.start()

@app.get("/api/emails")
def get_emails():
    return load_log()

@app.get("/api/accounts")
def get_accounts():
    log = load_log()
    result = []
    for acc in ACCOUNTS:
        email = acc["email"]
        provider = acc["provider"]
        # find last activity for this account
        entries = [e for e in log if e["account"] == email]
        last_seen = entries[0]["forwarded_at"] if entries else None
        result.append({
            "email": email,
            "provider": provider,
            "total_forwarded": len(entries),
            "last_active": last_seen,
        })
    return result