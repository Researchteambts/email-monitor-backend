from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
import threading

from database import get_db, engine, Base
import models  # noqa
import crud
from monitor import main as run_monitor

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Email Monitor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def start_monitor():
    t = threading.Thread(target=run_monitor, daemon=True)
    t.start()


# ── Schemas ───────────────────────────────────────────────────────────────
class AccountIn(BaseModel):
    email:    str
    password: str
    provider: str = "gmail"

class ToggleIn(BaseModel):
    is_active: bool


# ── Account routes ────────────────────────────────────────────────────────
@app.get("/api/accounts")
def list_accounts(db: Session = Depends(get_db)):
    accounts = crud.get_all_accounts(db)
    return [
        {
            "id":           acc.id,
            "email":        acc.email,
            "provider":     acc.provider,
            "is_active":    acc.is_active,
            "created_at":   acc.created_at,
            "total_emails": len(acc.emails),
            "last_active":  acc.emails[0].received_at.isoformat() if acc.emails and acc.emails[0].received_at else None,
        }
        for acc in accounts
    ]

@app.post("/api/accounts")
def add_account(body: AccountIn, db: Session = Depends(get_db)):
    acc = crud.add_account(db, body.email, body.password, body.provider)
    return {"message": "Account added", "id": acc.id, "email": acc.email}

@app.patch("/api/accounts/{account_id}/toggle")
def toggle_account(account_id: int, body: ToggleIn, db: Session = Depends(get_db)):
    acc = crud.toggle_account(db, account_id, body.is_active)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"message": "Updated", "is_active": acc.is_active}

@app.delete("/api/accounts/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    acc = crud.delete_account(db, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"message": f"Account {account_id} deleted"}

@app.delete("/api/emails/{email_id}")
def delete_email(email_id: int, db: Session = Depends(get_db)):
    email = crud.delete_email(db, email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return {"message": f"Email {email_id} deleted"}

# ── Email routes ──────────────────────────────────────────────────────────
@app.get("/api/emails")
def list_emails(db: Session = Depends(get_db)):
    emails = crud.get_all_emails(db)
    return [
        {
            "id":           e.id,
            "account_id":   e.account_id,
            "uid":          e.uid,
            "from":         e.from_address,
            "subject":      e.subject,
            "body":         e.body,
            "received_at":  e.received_at.isoformat() if e.received_at else None,
            "forwarded_at": e.forwarded_at,
            "status":       e.status,
            "folder":       e.folder
        }
        for e in emails
    ]

@app.get("/api/emails/{account_id}")
def list_emails_by_account(account_id: int, db: Session = Depends(get_db)):
    acc = crud.get_account_by_id(db, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    emails = crud.get_emails_by_account(db, account_id)
    return [
        {
            "id":           e.id,
            "account_id":   e.account_id,
            "uid":          e.uid,
            "from":         e.from_address,
            "subject":      e.subject,
            "body":         e.body,
            "received_at":  e.received_at.isoformat() if e.received_at else None,
            "forwarded_at": e.forwarded_at,
            "status":       e.status,
        }
        for e in emails
    ]