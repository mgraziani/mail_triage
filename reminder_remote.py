"""
Reminder antiparassitario — script autonomo per GitHub Actions.

Variabili d'ambiente richieste:
  GMAIL_USER          indirizzo Gmail mittente (es. maura.graziani86@gmail.com)
  GMAIL_APP_PASSWORD  App Password Gmail (16 caratteri, senza spazi)
"""

import email as email_lib
import imaplib
import json
import os
import smtplib
import sys
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Rome")
STATE_FILE = Path(__file__).parent / "state.json"

GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

RECIPIENTS = ["maura.graziani86@gmail.com", "emanuele.conforti88@gmail.com"]
EMAIL_SUBJECT = "Promemoria: antiparassitario per gli animali"
EMAIL_BODY = """\
Ciao!

È ora di mettere l'antiparassitario agli animali! 🐾

Quando hai completato il trattamento, rispondi a questa email con "fatto"
per mettere in pausa i promemoria per un mese.

Grazie!
"""

SEND_HOURS = [8, 20]


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "mode": "active",
        "last_sent_at": None,
        "wait_until": None,
        "sent_message_ids": [],
        "fatto_received_from": [],
    }


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def in_send_window(now):
    return any(h == now.hour and 0 <= now.minute < 30 for h in SEND_HOURS)


def recently_sent(state, now):
    if not state.get("last_sent_at"):
        return False
    last = datetime.fromisoformat(state["last_sent_at"])
    return (now - last).total_seconds() < 1800


def send_reminder(now):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = EMAIL_SUBJECT
    msg["From"] = GMAIL_USER
    msg["To"] = ", ".join(RECIPIENTS)
    msg.attach(MIMEText(EMAIL_BODY, "plain", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, RECIPIENTS, msg.as_string())

    print(f"✓ Email inviata a {', '.join(RECIPIENTS)}")
    return msg.get("Message-ID")


def _extract_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    return part.get_payload(decode=True).decode("utf-8", errors="ignore")
                except Exception:
                    pass
    else:
        try:
            return msg.get_payload(decode=True).decode("utf-8", errors="ignore")
        except Exception:
            pass
    return ""


def check_for_fatto(state):
    """Cerca risposte 'fatto' dai destinatari. Restituisce l'email del mittente se trovata."""
    if not state.get("last_sent_at"):
        return None

    last_sent = datetime.fromisoformat(state["last_sent_at"])
    since = last_sent.strftime("%d-%b-%Y")

    try:
        with imaplib.IMAP4_SSL("imap.gmail.com") as imap:
            imap.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            imap.select("INBOX")

            for recipient in RECIPIENTS:
                if recipient in state.get("fatto_received_from", []):
                    continue

                _, msg_ids = imap.search(None, f'FROM "{recipient}" SINCE {since}')
                if not msg_ids or not msg_ids[0]:
                    continue

                for msg_id in msg_ids[0].split():
                    _, data = imap.fetch(msg_id, "(RFC822)")
                    if not data or not data[0]:
                        continue
                    msg = email_lib.message_from_bytes(data[0][1])
                    subject = msg.get("Subject", "").lower()
                    body = _extract_body(msg).lower()

                    if "antiparassitario" in subject and "fatto" in body:
                        print(f"✓ Risposta 'fatto' ricevuta da {recipient}")
                        return recipient
    except Exception as exc:
        print(f"⚠ Errore IMAP: {exc}", file=sys.stderr)

    return None


def main():
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print("Errore: GMAIL_USER e GMAIL_APP_PASSWORD non impostati.", file=sys.stderr)
        sys.exit(1)

    state = load_state()
    now = datetime.now(TZ)
    print(f"[{now.strftime('%Y-%m-%d %H:%M %Z')}] modalità={state['mode']}")

    # 1. Controlla se il periodo di attesa è terminato
    if state["mode"] == "waiting":
        wait_until = state.get("wait_until")
        if wait_until and now >= datetime.fromisoformat(wait_until):
            print("Periodo di attesa terminato — riattivo i reminder.")
            state.update({
                "mode": "active",
                "fatto_received_from": [],
                "wait_until": None,
                "last_sent_at": None,
                "sent_message_ids": [],
            })
            save_state(state)
        else:
            until_str = datetime.fromisoformat(wait_until).strftime("%Y-%m-%d") if wait_until else "?"
            print(f"In pausa fino a {until_str} — nessuna azione.")
            return

    # 2. Cerca risposte "fatto" anche fuori dalla finestra di invio
    fatto_from = check_for_fatto(state)
    if fatto_from:
        wait_until = now + timedelta(days=30)
        if fatto_from not in state.get("fatto_received_from", []):
            state.setdefault("fatto_received_from", []).append(fatto_from)
        state.update({
            "mode": "waiting",
            "wait_until": wait_until.isoformat(),
            "sent_message_ids": [],
        })
        save_state(state)
        print(f"Sistema in pausa per 30 giorni. Prossimo invio: {wait_until.strftime('%Y-%m-%d')}")
        return

    # 3. Invia se nella finestra oraria e non già inviato di recente
    if in_send_window(now) and not recently_sent(state, now):
        msg_id = send_reminder(now)
        state["last_sent_at"] = now.isoformat()
        if msg_id:
            state.setdefault("sent_message_ids", []).append(msg_id)
        save_state(state)
    else:
        print("Fuori finestra di invio — nessuna azione.")


if __name__ == "__main__":
    main()
