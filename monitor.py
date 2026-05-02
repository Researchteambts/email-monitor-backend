import json, os
from datetime import datetime

LOG_FILE = "email_log.json"

def load_log():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            return json.load(f)
    return []

def append_log(entry):
    log = load_log()
    log.insert(0, entry)       # newest first
    log = log[:200]            # keep last 200 entries
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)

# ── CONFIG ──────────────────────────────────────────────────────────────
YOUR_EMAIL    = "researchteambts8@gmail.com"       # your personal email (receives all forwards)
YOUR_PASSWORD = "umam hewx riur nzix"   # app password if Gmail, regular if Outlook
YOUR_PROVIDER = "gmail"               # "gmail" or "outlook"
Client_password = "fcho nvvh gnux tkwi"
CHECK_INTERVAL = 30
SEEN_FILE      = "seen_emails.json"
LOOKBACK_DAYS  = 1 
import imaplib
import smtplib
import email
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import json
import os
import time



ACCOUNTS = [
    {"email": "researchteambts10@gmail.com",   "password": Client_password,  "provider": "gmail"},
    #{"email": "sanjaykumar0691@outlook.com", "password": "sanjaykumar@0691", "provider": "outlook"},
    # {"email": "client3@gmail.com",   "password": "app_password",  "provider": "gmail"},
    # {"email": "client4@hotmail.com", "password": "their_password", "provider": "outlook"},
    # # add all your accounts here — mix freely
]


SEEN_FILE      = "seen_emails.json"
# ────────────────────────────────────────────────────────────────────────

# Server settings
IMAP_SERVERS = {
    "gmail":   ("imap.gmail.com",          993),
    "outlook": ("imap-mail.outlook.com",   993),
}

SMTP_SERVERS = {
    "gmail":   ("smtp.gmail.com",          465, "SSL"),
    "outlook": ("smtp-mail.outlook.com",   587, "TLS"),
}

# ── HELPERS ──────────────────────────────────────────────────────────────

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return json.load(f)
    return {}

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(seen, f, indent=2)
def extract_body(msg) -> str:
    """Extract plain text body from email message."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))
            if ctype == "text/plain" and "attachment" not in disposition:
                body = part.get_payload(decode=True).decode(errors="replace")
                break  # take first plain text part
    else:
        body = msg.get_payload(decode=True).decode(errors="replace")
    return body.strip()

def send_email(forward_msg):
    """Send using YOUR account's provider."""
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

def build_forward(original_msg, monitored_account):
    """Wrap the original email into a forward addressed to you."""
    subject = original_msg.get("Subject", "(no subject)")
    sender  = original_msg.get("From",    "unknown")
    date    = original_msg.get("Date",    "")

    forward = MIMEMultipart("mixed")
    forward["From"]    = YOUR_EMAIL
    forward["To"]      = YOUR_EMAIL
    forward["Subject"] = f"[FWD • {monitored_account}] {subject}"

    plain_header = (
        f"--- Forwarded from: {monitored_account} ---\n"
        f"From:    {sender}\n"
        f"Date:    {date}\n"
        f"Subject: {subject}\n"
        f"{'─' * 50}\n\n"
    )
    html_header = (
        f"<div style='color:#555;border-left:3px solid #ccc;padding:8px 12px;margin-bottom:12px'>"
        f"<b>Forwarded from:</b> {monitored_account}<br>"
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
            attachment.add_header("Content-Disposition", f'attachment; filename="{filename}"')
            forward.attach(attachment)

        elif ctype == "text/plain" and "attachment" not in disposition and not has_plain:
            body = part.get_payload(decode=True).decode(errors="replace")
            forward.attach(MIMEText(plain_header + body, "plain"))
            has_plain = True

        elif ctype == "text/html" and "attachment" not in disposition and not has_html:
            body = part.get_payload(decode=True).decode(errors="replace")
            forward.attach(MIMEText(html_header + body, "html"))
            has_html = True

    # Fallback if no body was found
    if not has_plain and not has_html:
        forward.attach(MIMEText(plain_header + "(no readable body)", "plain"))

    return forward

# ── CORE LOGIC ───────────────────────────────────────────────────────────

def check_account(account, seen):
    mail_id  = account["email"]
    provider = account.get("provider", "gmail")
    imap_host, imap_port = IMAP_SERVERS[provider]

    print(f"  Checking {mail_id} ...")
    try:
        mail = imaplib.IMAP4_SSL(imap_host, imap_port)
        mail.login(mail_id, account["password"])
        mail.select("inbox")

        since_date = (datetime.now() - timedelta(days=LOOKBACK_DAYS)).strftime("%d-%b-%Y")
        _, data = mail.search(None, f'(UNSEEN SINCE "{since_date}")')
        uids = data[0].split()

        if not uids:
            print(f"    No new mail.")
            mail.logout()
            return

        if mail_id not in seen:
            seen[mail_id] = []

        for uid in uids:
            uid_str = uid.decode()
            if uid_str in seen[mail_id]:
                continue

            _, msg_data = mail.fetch(uid, "(RFC822)")
            original_msg = email.message_from_bytes(msg_data[0][1])
            subject      = original_msg.get("Subject", "(no subject)")

            print(f"    New email: {subject}")
            forward_msg = build_forward(original_msg, mail_id)

            if send_email(forward_msg):
                seen[mail_id].append(uid_str)
                append_log({
                    "id": uid_str,
                    "account": mail_id,
                    "from": original_msg.get("From", "unknown"),
                    "subject": original_msg.get("Subject", "(no subject)"),
                    "date": original_msg.get("Date", ""),
                    "body": extract_body(original_msg),   # ← add this
                    "forwarded_at": datetime.now().isoformat(),
                    "status": "forwarded"
                })
                print(f"    Forwarded OK.")
            else:
                print(f"    Forward FAILED — will retry next cycle.")

        mail.logout()

    except imaplib.IMAP4.error as e:
        print(f"  [IMAP error] {mail_id}: {e}")
    except Exception as e:
        print(f"  [Unexpected error] {mail_id}: {e}")

def main():
    print("=" * 50)
    print("Email monitor started.")
    print(f"Monitoring {len(ACCOUNTS)} accounts.")
    print(f"Forwarding to: {YOUR_EMAIL}")
    print(f"Check interval: {CHECK_INTERVAL // 60} minutes")
    print("=" * 50)

    while True:
        print(f"\n[{time.strftime('%H:%M:%S')}] Running check...")
        seen = load_seen()
        for account in ACCOUNTS:
            check_account(account, seen)
        save_seen(seen)
        print(f"Done. Next check in {CHECK_INTERVAL // 60} min.")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()