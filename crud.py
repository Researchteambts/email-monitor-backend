from sqlalchemy.orm import Session
from models import Account, Email


# ── Accounts ──────────────────────────────────────────────────────────────

def get_active_accounts(db: Session):
    return db.query(Account).filter(Account.is_active == True).all()

def get_all_accounts(db: Session):
    return db.query(Account).order_by(Account.created_at.desc()).all()

def get_account_by_id(db: Session, account_id: int):
    return db.query(Account).filter(Account.id == account_id).first()

def add_account(db: Session, email: str, password: str, provider: str = "gmail"):
    acc = Account(email=email, password=password, provider=provider)
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc

def toggle_account(db: Session, account_id: int, is_active: bool):
    acc = get_account_by_id(db, account_id)
    if acc:
        acc.is_active = is_active
        db.commit()
        db.refresh(acc)
    return acc

def delete_account(db: Session, account_id: int):
    acc = get_account_by_id(db, account_id)
    if acc:
        db.delete(acc)
        db.commit()
    return acc


# ── Emails ────────────────────────────────────────────────────────────────

def is_uid_seen(db: Session, account_id: int, uid: str) -> bool:
    return db.query(Email).filter(
        Email.account_id == account_id,
        Email.uid        == uid
    ).first() is not None

def save_email(
    db: Session,
    account_id: int,
    uid: str,
    from_address: str,
    subject: str,
    body: str,
    received_at: str,
    status: str = "forwarded"
):
    entry = Email(
        account_id   = account_id,
        uid          = uid,
        from_address = from_address,
        subject      = subject,
        body         = body[:500],
        received_at  = received_at,
        status       = status,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

def get_all_emails(db: Session, limit: int = 200):
    return (
        db.query(Email)
        .order_by(Email.forwarded_at.desc())
        .limit(limit)
        .all()
    )

def get_emails_by_account(db: Session, account_id: int, limit: int = 200):
    return (
        db.query(Email)
        .filter(Email.account_id == account_id)
        .order_by(Email.forwarded_at.desc())
        .limit(limit)
        .all()
    )

def get_failed_emails(db: Session):
    """Fetch emails that failed to forward — for retry logic."""
    return db.query(Email).filter(Email.status == "forward_failed").all()

def mark_email_forwarded(db: Session, email_id: int):
    entry = db.query(Email).filter(Email.id == email_id).first()
    if entry:
        entry.status = "forwarded"
        db.commit()
    return entry