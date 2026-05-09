from sqlalchemy.orm import Session
from models import Account, Email, Notification


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

def delete_email(db: Session, email_id: int):
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        return None
    db.delete(email)
    db.commit()
    return email

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
    status: str = "forwarded",
    folder: str = "inbox"
):
    entry = Email(
        account_id   = account_id,
        uid          = uid,
        from_address = from_address,
        subject      = subject,
        body         = body,
        received_at  = received_at,
        status       = status,
        folder       = folder
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

def mark_email_read(db: Session, email_id: int, is_read: bool = True):
    entry = db.query(Email).filter(Email.id == email_id).first()
    if not entry:
        return None
    entry.is_read = is_read
    db.commit()
    db.refresh(entry)
    return entry

def get_unread_count(db: Session, account_id: int) -> int:
    return db.query(Email).filter(
        Email.account_id == account_id,
        Email.is_read    == False
    ).count()

def get_failed_emails(db: Session):
    return db.query(Email).filter(Email.status == "forward_failed").all()

def mark_email_forwarded(db: Session, email_id: int):
    entry = db.query(Email).filter(Email.id == email_id).first()
    if entry:
        entry.status = "forwarded"
        db.commit()
    return entry


# ── Notifications ─────────────────────────────────────────────────────────

def create_notification(
    db: Session,
    account_id: int,
    account_email: str,
    from_address: str,
    subject: str,
    email_id: int | None = None,
):
    notif = Notification(
        account_id    = account_id,
        email_id      = email_id,
        account_email = account_email,
        from_address  = from_address,
        subject       = subject,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif

def get_all_notifications(db: Session, limit: int = 50):
    return (
        db.query(Notification)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )

def mark_notification_seen(db: Session, notification_id: int):
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if notif:
        notif.is_seen = True
        db.commit()
        db.refresh(notif)
    return notif

def clear_all_notifications(db: Session):
    db.query(Notification).delete()
    db.commit()