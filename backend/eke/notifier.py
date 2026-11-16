from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(__file__).parent.parent.parent / ".env"
load_dotenv(ENV_PATH)


def send_new_listings_email(listings: list[dict]) -> None:
    """Email a summary of newly found listings to GMAIL_RECIPIENT (default: GMAIL_ADDRESS).

    No-ops silently if GMAIL_ADDRESS/GMAIL_APP_PASSWORD aren't configured, or if
    `listings` is empty. Never raises — a broken mail config can't abort a fetch run.
    """
    if not listings:
        return

    sender = os.environ.get("GMAIL_ADDRESS", "").strip()
    app_password = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    if not sender or not app_password:
        return
    recipient = os.environ.get("GMAIL_RECIPIENT", "").strip() or sender

    count = len(listings)
    subject = f"eke: {count} new listing{'s' if count != 1 else ''} found"

    lines = [f"{count} new listing(s) found:\n"]
    for i, listing in enumerate(listings, 1):
        lines.append(
            f"{i}. {listing.get('title') or '(no title)'}\n"
            f"   Price: {listing.get('price') or '-'}  "
            f"Size: {listing.get('size') or '-'}  "
            f"Rooms: {listing.get('rooms') or '-'}\n"
            f"   Location: {listing.get('location') or '-'}\n"
            f"   Search: {listing.get('search_name') or '-'}\n"
            f"   {listing.get('url') or ''}\n"
        )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content("\n".join(lines))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as smtp:
            smtp.login(sender, app_password)
            smtp.send_message(msg)
    except Exception as e:
        print(f"Warning: failed to send notification email: {e}")
