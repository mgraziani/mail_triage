"""
Pet medication reminder — state management.

Usage:
  python reminder.py status          → current state as JSON
  python reminder.py decision        → what to do right now (send|idle|waiting|recently_sent|reactivated)
  python reminder.py mark-sent [thread_id]
  python reminder.py mark-fatto <email>
  python reminder.py reset           → reset to active (for testing)
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

STATE_FILE = Path(__file__).parent / "state.json"

RECIPIENTS = ["maura.graziani86@gmail.com", "emanuele.conforti88@gmail.com"]
EMAIL_SUBJECT = "Promemoria: antiparassitario per gli animali"
EMAIL_BODY = """\
Ciao!

È ora di mettere l'antiparassitario agli animali! 🐾

Quando hai completato il trattamento, rispondi a questa email con "fatto" \
per mettere in pausa i promemoria per un mese.

Grazie!
"""

# Hours at which the daily reminder is sent (window: HH:00–HH:29)
SEND_HOURS = [8, 20]


def _default_state():
    return {
        "mode": "active",          # "active" | "waiting"
        "last_sent_at": None,      # ISO datetime of last send
        "wait_until": None,        # ISO datetime when waiting ends
        "sent_thread_ids": [],     # Gmail thread IDs from sent reminders
        "fatto_received_from": []  # emails that replied "fatto"
    }


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return _default_state()


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def get_decision(state=None):
    """Return (decision_str, state_dict). May mutate and save state."""
    if state is None:
        state = load_state()

    now = datetime.now()

    if state["mode"] == "waiting":
        if state.get("wait_until"):
            wait_until = datetime.fromisoformat(state["wait_until"])
            if now >= wait_until:
                # Re-activate after the 1-month pause
                state.update({
                    "mode": "active",
                    "fatto_received_from": [],
                    "wait_until": None,
                    "sent_thread_ids": [],
                    "last_sent_at": None,
                })
                save_state(state)
                return "reactivated", state
        return "waiting", state

    # Active mode — check the 30-minute send window
    if state.get("last_sent_at"):
        last_sent = datetime.fromisoformat(state["last_sent_at"])
        if (now - last_sent).total_seconds() < 1800:
            return "recently_sent", state

    in_window = any(h == now.hour and 0 <= now.minute < 30 for h in SEND_HOURS)
    return ("send" if in_window else "idle"), state


def mark_sent(thread_id=None):
    state = load_state()
    state["last_sent_at"] = datetime.now().isoformat()
    if thread_id and thread_id not in state.get("sent_thread_ids", []):
        state.setdefault("sent_thread_ids", []).append(thread_id)
    save_state(state)


def mark_fatto(from_email):
    state = load_state()
    if from_email not in state.get("fatto_received_from", []):
        state.setdefault("fatto_received_from", []).append(from_email)
    wait_until = datetime.now() + timedelta(days=30)
    state.update({
        "mode": "waiting",
        "wait_until": wait_until.isoformat(),
        "sent_thread_ids": [],
    })
    save_state(state)
    return wait_until


def get_status():
    state = load_state()
    decision, _ = get_decision(dict(state))  # don't mutate for status display
    return {
        "mode": state["mode"],
        "decision": decision,
        "last_sent_at": state["last_sent_at"],
        "wait_until": state["wait_until"],
        "fatto_received_from": state.get("fatto_received_from", []),
        "sent_thread_ids": state.get("sent_thread_ids", []),
    }


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "status":
        print(json.dumps(get_status(), indent=2, ensure_ascii=False))

    elif cmd == "decision":
        decision, state = get_decision()
        print(json.dumps({
            "decision": decision,
            "sent_thread_ids": state.get("sent_thread_ids", []),
            "wait_until": state.get("wait_until"),
        }, indent=2))

    elif cmd == "mark-sent":
        tid = sys.argv[2] if len(sys.argv) > 2 else None
        mark_sent(tid)
        print(f"Marked as sent. thread_id={tid}")

    elif cmd == "mark-fatto":
        if len(sys.argv) < 3:
            print("Usage: reminder.py mark-fatto <email>", file=sys.stderr)
            sys.exit(1)
        email = sys.argv[2]
        until = mark_fatto(email)
        print(f"Fatto ricevuto da {email}. Pausa fino a {until.strftime('%Y-%m-%d %H:%M')}.")

    elif cmd == "reset":
        save_state(_default_state())
        print("Stato resettato ad 'active'.")

    else:
        print(f"Comando sconosciuto: {cmd}", file=sys.stderr)
        sys.exit(1)
