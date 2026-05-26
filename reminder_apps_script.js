// ============================================================
// Reminder antiparassitario — Google Apps Script
// Incolla questo codice su https://script.google.com
// ============================================================

const RECIPIENTS = ['maura.graziani86@gmail.com', 'emanuele.conforti88@gmail.com'];
const SUBJECT    = 'Promemoria: antiparassitario per gli animali';
const BODY       = `Ciao!

È ora di mettere l'antiparassitario agli animali! 🐾

Quando hai completato il trattamento, rispondi a questa email con "fatto"
per mettere in pausa i promemoria per un mese.

Grazie!`;

const TIMEZONE   = 'Europe/Rome';
const SEND_HOURS = [8, 20];          // 08:00 e 20:00 ora italiana
const PROPS      = PropertiesService.getScriptProperties();

// ── Funzione principale (da collegare al trigger orario) ─────
function checkAndSend() {
  const now    = new Date();
  const hour   = parseInt(Utilities.formatDate(now, TIMEZONE, 'H'));
  const minute = parseInt(Utilities.formatDate(now, TIMEZONE, 'm'));
  const mode   = PROPS.getProperty('mode') || 'active';

  Logger.log(`[${Utilities.formatDate(now, TIMEZONE, 'yyyy-MM-dd HH:mm')}] mode=${mode}`);

  // 1. Controlla se il periodo di attesa è terminato
  if (mode === 'waiting') {
    const waitUntil = PROPS.getProperty('waitUntil');
    if (waitUntil && now >= new Date(waitUntil)) {
      PROPS.setProperties({ mode: 'active', lastSentAt: '', waitUntil: '', fattoDa: '' });
      Logger.log('Periodo di attesa terminato — riattivo i reminder.');
    } else {
      Logger.log(`In pausa fino a ${waitUntil}`);
      return;
    }
  }

  // 2. Cerca risposte "fatto"
  const fattoFrom = checkForFatto();
  if (fattoFrom) {
    const waitUntil = new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000);
    PROPS.setProperties({
      mode: 'waiting',
      waitUntil: waitUntil.toISOString(),
      fattoDa: fattoFrom,
      lastSentAt: '',
    });
    Logger.log(`"Fatto" ricevuto da ${fattoFrom}. Pausa fino al ${waitUntil.toDateString()}.`);
    return;
  }

  // 3. Verifica finestra di invio (HH:00–HH:29)
  if (!SEND_HOURS.includes(hour) || minute >= 30) {
    Logger.log(`Fuori finestra (${hour}:${String(minute).padStart(2,'0')}) — nessuna azione.`);
    return;
  }

  // 4. Evita doppio invio nella stessa finestra
  const lastSentAt = PROPS.getProperty('lastSentAt');
  if (lastSentAt) {
    const diffMin = (now - new Date(lastSentAt)) / 60000;
    if (diffMin < 30) {
      Logger.log(`Email già inviata ${Math.round(diffMin)} min fa — skip.`);
      return;
    }
  }

  // 5. Invia il reminder
  GmailApp.sendEmail(RECIPIENTS.join(','), SUBJECT, BODY);
  PROPS.setProperty('lastSentAt', now.toISOString());
  Logger.log(`✓ Email inviata a: ${RECIPIENTS.join(', ')}`);
}

// ── Cerca "fatto" nelle risposte recenti ─────────────────────
function checkForFatto() {
  const lastSentAt = PROPS.getProperty('lastSentAt');
  if (!lastSentAt) return null;

  const since   = Utilities.formatDate(new Date(lastSentAt), TIMEZONE, 'yyyy/MM/dd');
  const threads = GmailApp.search(`subject:"antiparassitario" after:${since}`);

  for (const thread of threads) {
    for (const msg of thread.getMessages()) {
      const from = msg.getFrom().toLowerCase();
      const body = msg.getPlainBody().toLowerCase();
      const isRecipient = RECIPIENTS.some(r => from.includes(r.toLowerCase()));
      if (isRecipient && body.includes('fatto')) {
        return msg.getFrom();
      }
    }
  }
  return null;
}

// ── Utilità ──────────────────────────────────────────────────

/** Mostra lo stato corrente nel log */
function getStatus() {
  Logger.log(JSON.stringify(PROPS.getProperties(), null, 2));
}

/** Resetta tutto (utile per test) */
function reset() {
  PROPS.deleteAllProperties();
  Logger.log('Stato resettato.');
}
