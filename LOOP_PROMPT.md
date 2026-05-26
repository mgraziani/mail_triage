# Istruzioni loop — Reminder antiparassitario

Esegui i passi seguenti nell'ordine indicato.

---

## Passo 1 — Leggi la decisione corrente

```bash
python /home/user/mail_triage/reminder.py decision
```

L'output JSON contiene `decision` che può valere:
- `send` → è ora di inviare il reminder
- `idle` → non è nell'orario di invio, ma controlla eventuali risposte
- `recently_sent` → email già inviata nella finestra corrente, controlla risposte
- `waiting` → periodo di pausa attivo, non fare nulla
- `reactivated` → la pausa è terminata, al prossimo ciclo verrà inviato

---

## Passo 2a — Se `decision == "send"`

1. Invia un'email (usa lo strumento Gmail **create_draft** o direttamente) a:
   - `maura.graziani86@gmail.com`
   - `emanuele.conforti88@gmail.com`
   - Oggetto: `Promemoria: antiparassitario per gli animali`
   - Corpo:
     ```
     Ciao!

     È ora di mettere l'antiparassitario agli animali! 🐾

     Quando hai completato il trattamento, rispondi a questa email con "fatto"
     per mettere in pausa i promemoria per un mese.

     Grazie!
     ```

2. Salva il thread ID restituito:
   ```bash
   python /home/user/mail_triage/reminder.py mark-sent <THREAD_ID>
   ```

---

## Passo 2b — Se `decision == "idle"` oppure `"recently_sent"` oppure `"reactivated"`

Cerca risposte "fatto" dai destinatari. Usa la ricerca Gmail con query:

```
from:(maura.graziani86@gmail.com OR emanuele.conforti88@gmail.com) subject:"antiparassitario" newer_than:2d
```

Per ogni thread trovato nei `sent_thread_ids` (vedi output del Passo 1):
- Recupera il thread completo e verifica se ci sono messaggi di risposta
- Se il corpo di un messaggio contiene "fatto" (case-insensitive):
  ```bash
  python /home/user/mail_triage/reminder.py mark-fatto <EMAIL_MITTENTE>
  ```

---

## Passo 2c — Se `decision == "waiting"`

Non fare nulla. Il sistema è in pausa per un mese.

---

## Note

- La finestra di invio è: 08:00–08:29 e 20:00–20:29 ogni giorno.
- Una volta ricevuto "fatto" da **qualsiasi** destinatario, il reminder si mette in pausa per **30 giorni**.
- Dopo 30 giorni il sistema si riattiva automaticamente.
- Per vedere lo stato completo: `python /home/user/mail_triage/reminder.py status`
- Per resettare manualmente: `python /home/user/mail_triage/reminder.py reset`
