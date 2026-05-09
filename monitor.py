import imaplib, email, time, smtplib, os
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dateutil import parser as dateparser
from dotenv import load_dotenv

from database import SessionLocal
import crud
import re 
load_dotenv()

# ── Central inbox (from .env) ─────────────────────────────────────────────
YOUR_EMAIL    = os.getenv("YOUR_EMAIL")
YOUR_PASSWORD = os.getenv("YOUR_PASSWORD")
YOUR_PROVIDER = os.getenv("YOUR_PROVIDER", "gmail")

# ── Config ────────────────────────────────────────────────────────────────
CHECK_INTERVAL = 1 * 60      # every 5 minutes
LOOKBACK_DAYS  = 5

IMAP_SERVERS = {
    "gmail":   ("imap.gmail.com",        993),
    "outlook": ("imap-mail.outlook.com", 993),
}

SMTP_SERVERS = {
    "gmail":   ("smtp.gmail.com",        465, "SSL"),
    "outlook": ("smtp-mail.outlook.com", 587, "TLS"),
}

# ── Helpers ───────────────────────────────────────────────────────────────
def clean_body(body: str) -> str:
    body = re.sub(r'<[^>]+>', '', body)       # strip HTML tags
    body = re.sub(r'\s+', ' ', body).strip()  # collapse whitespace
    return body

def extract_body(msg) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype       = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))
            if ctype == "text/plain" and "attachment" not in disposition:
                body = part.get_payload(decode=True).decode(errors="replace")
                break
    else:
        body = msg.get_payload(decode=True).decode(errors="replace")
    
    return clean_body(body.strip())


def build_forward(original_msg, monitored_email: str) -> MIMEMultipart:
    subject = original_msg.get("Subject", "(no subject)")
    sender  = original_msg.get("From",    "unknown")
    date    = original_msg.get("Date",    "")

    forward = MIMEMultipart("mixed")
    forward["From"]    = YOUR_EMAIL
    forward["To"]      = YOUR_EMAIL
    forward["Subject"] = f"[FWD • {monitored_email}] {subject}"

    plain_header = (
        f"--- Forwarded from: {monitored_email} ---\n"
        f"From:    {sender}\n"
        f"Date:    {date}\n"
        f"Subject: {subject}\n"
        f"{'─' * 50}\n\n"
    )
    html_header = (
        f"<div style='color:#555;border-left:3px solid #ccc;"
        f"padding:8px 12px;margin-bottom:12px'>"
        f"<b>Forwarded from:</b> {monitored_email}<br>"
        f"<b>From:</b> {sender}<br>"
        f"<b>Date:</b> {date}"
        f"</div>"
    )

    has_plain = False
    has_html  = False

    for part in original_msg.walk():
        ctype       = part.get_content_type()
        disposition = str(part.get("Content-Disposition", ""))

        if "attachment" in disposition:
            filename   = part.get_filename() or "attachment"
            attachment = MIMEBase("application", "octet-stream")
            attachment.set_payload(part.get_payload(decode=True))
            encoders.encode_base64(attachment)
            attachment.add_header(
                "Content-Disposition", f'attachment; filename="{filename}"'
            )
            forward.attach(attachment)

        elif ctype == "text/plain" and not has_plain:
            body = part.get_payload(decode=True).decode(errors="replace")
            forward.attach(MIMEText(plain_header + body, "plain"))
            has_plain = True

        elif ctype == "text/html" and not has_html:
            body = part.get_payload(decode=True).decode(errors="replace")
            forward.attach(MIMEText(html_header + body, "html"))
            has_html = True

    if not has_plain and not has_html:
        forward.attach(MIMEText(plain_header + "(no readable body)", "plain"))

    return forward


def send_forward(forward_msg) -> bool:
    """Always sends using YOUR_EMAIL credentials."""
    smtp_host, smtp_port, mode = SMTP_SERVERS[YOUR_PROVIDER]
    try:
        if mode == "SSL":
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as smtp:
                smtp.login(YOUR_EMAIL, YOUR_PASSWORD)
                smtp.sendmail(YOUR_EMAIL, YOUR_EMAIL, forward_msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.login(YOUR_EMAIL, YOUR_PASSWORD)
                smtp.sendmail(YOUR_EMAIL, YOUR_EMAIL, forward_msg.as_string())
        return True
    except Exception as e:
        print(f"  [SMTP error] {e}")
        return False

# ── Core ──────────────────────────────────────────────────────────────────

def check_account(account, db):
    provider   = account.provider
    mail_email = account.email
    mail_pass  = account.password
    account_id = account.id

    imap_host, imap_port = IMAP_SERVERS.get(provider, IMAP_SERVERS["gmail"])

    print(f"  Checking {mail_email} ...")
    try:
        mail = imaplib.IMAP4_SSL(imap_host, imap_port)
        mail.login(mail_email, mail_pass)
        folders = ["inbox","INBOX","[Gmail]/Spam"] if provider == "gmail" else ["inbox", "Junk"]
        for folder in folders:
            try:
                result, _ = mail.select(folder)
                if result != "OK":
                    print(f"    Skipping folder {folder} (not found)")
                    continue
            except Exception:
                print(f"    Skipping folder {folder} (error)")
                continue

            since_date = (datetime.now() - timedelta(days=LOOKBACK_DAYS)).strftime("%d-%b-%Y")
            _, data    = mail.search(None, f'(UNSEEN SINCE "{since_date}")')
            uids       = data[0].split()

            if not uids:
                print(f"    No new mail in {folder}.")
                continue

            for uid in uids:
                uid_str = uid.decode()

                if crud.is_uid_seen(db, account_id, uid_str):
                    continue

                _, msg_data  = mail.fetch(uid, "(RFC822)")
                original_msg = email.message_from_bytes(msg_data[0][1])

                subject     = original_msg.get("Subject", "(no subject)")
                sender      = original_msg.get("From",    "unknown")
                received_at_raw = original_msg.get("Date", "")
                try:
                    received_at = dateparser.parse(received_at_raw)
                except Exception:
                    received_at = None
                body        = extract_body(original_msg)

                print(f"    [{folder}] New email: {subject}")

                forward_msg = build_forward(original_msg, mail_email)
                forwarded   = send_forward(forward_msg)

                crud.save_email(
                    db           = db,
                    account_id   = account_id,
                    uid          = uid_str,
                    from_address = sender,
                    subject      = subject,
                    body         = body,
                    received_at  = received_at,
                    status       = "forwarded" if forwarded else "forward_failed",
                    folder       = folder
                )

        mail.logout()
        #
    except imaplib.IMAP4.error as e:
        print(f"  [IMAP error] {mail_email}: {e}")
    except Exception as e:
        print(f"  [Unexpected error] {mail_email}: {e}")


def main():
    print("=" * 50)
    print("Email Monitor started.")
    print(f"Forwarding all mail → {YOUR_EMAIL}")
    print(f"Check interval      : {CHECK_INTERVAL // 60} min")
    print("=" * 50)

    while True:
        print(f"\n[{time.strftime('%H:%M:%S')}] Running check...")
        db = SessionLocal()
        try:
            accounts = crud.get_active_accounts(db)
            print(f"  Active accounts: {len(accounts)}")
            for account in accounts:
                check_account(account, db)
        finally:
            db.close()

        print(f"Done. Next check in {CHECK_INTERVAL // 60} min.")
        time.sleep(CHECK_INTERVAL)