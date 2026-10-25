# Matrice ruoli-permessi — Piattaforma Nursery (Modulo 1)

Tutti i controlli sono applicati nel backend (`backend/core.py`, `routes_*.py`). L'interfaccia nasconde solo i comandi non consentiti.
Errori: `401` non autenticato, `403` operazione non consentita, `404` risorsa inesistente **o non visibile** (una startup non accessibile risponde 404 per non rivelarne l'esistenza), `409` conflitto di regola, `422` dati non validi.

Legenda: ✅ consentito · 👁 sola lettura · ❌ negato

## Startup

| Azione | ADMIN_NURSERY | OPERATORE_NURSERY | OPERATIVO / PROFESSIONISTA PROVIDER | ADMIN_STARTUP | OPERATIVO_STARTUP |
|---|---|---|---|---|---|
| Elenco startup (`GET /api/startups`) | ✅ tutte | ✅ tutte | 👁 solo quelle con `provider_organization_id` = proprio provider | ❌ (usa la home) | ❌ (usa la home) |
| Scheda startup (`GET /api/startups/{id}`) | ✅ | ✅ | 👁 solo assegnate | 👁 solo la propria | 👁 solo la propria |
| Creare startup | ✅ | ✅ | ❌ | ❌ | ❌ |
| Modificare tutti i dati (`PUT`) | ✅ | ✅ | ❌ | ❌ | ❌ |
| Modificare contatti: pec, sede, telefono (`PATCH /contatti`) | ✅ | ✅ | ❌ | ✅ solo la propria | ❌ |
| Eliminare (logico) | ✅ solo se ONBOARDING | ❌ | ❌ | ❌ | ❌ |
| Utenti collegati (`GET /{id}/users`) | ✅ | ✅ | 👁 se startup assegnata | 👁 propria | 👁 propria |
| Cronologia (`GET /{id}/events`) | ✅ tutti gli eventi | ✅ tutti gli eventi | 👁 solo `visibility = ALL` | 👁 solo `ALL` | 👁 solo `ALL` |

## Utenti

| Azione | ADMIN_NURSERY | OPERATORE_NURSERY | PROVIDER | ADMIN_STARTUP | OPERATIVO_STARTUP |
|---|---|---|---|---|---|
| Elenco utenti (`GET /api/users`) | ✅ tutti | ✅ tutti (lettura degli utenti Nursery) | ❌ | ✅ solo propria startup | ❌ |
| Invitare | ✅ ogni organizzazione e ruolo | ✅ utenti Provider e Startup | ❌ | ✅ ADMIN_STARTUP e OPERATIVO_STARTUP della propria startup | ❌ |
| Modificare dati anagrafici | ✅ | ✅ non Nursery | ❌ | ✅ propria startup | ❌ |
| Cambiare ruolo | ✅ | ✅ non Nursery | ❌ | ✅ propria startup (vedi regole) | ❌ |
| Disattivare / annullare invito | ✅ | ✅ non Nursery | ❌ | ✅ propria startup (vedi regole) | ❌ |
| Riattivare | ✅ | ✅ non Nursery | ❌ | ✅ propria startup | ❌ |
| Rigenerare link di invito | ✅ | ✅ non Nursery | ❌ | ✅ propria startup | ❌ |
| Modificare utenti Nursery o Provider | ✅ | Provider ✅ / Nursery ❌ | ❌ | ❌ | ❌ |

Regole aggiuntive:
- Il ruolo assegnato deve essere coerente col tipo di organizzazione (es. un utente Startup non può diventare Provider).
- Nessun utente può cambiare il proprio ruolo né disattivare se stesso.
- Un ADMIN_STARTUP non può disattivare né declassare l'ultimo ADMIN_STARTUP **attivo** della propria startup. Poiché l'attore è a sua volta un ADMIN_STARTUP attivo e non può agire su se stesso (403), la regola è garantita già dal divieto di auto-operazione; il controllo esplicito (409) resta come salvaguardia. Gli utenti Nursery non hanno questo vincolo.
- Codice breve duplicato: 409; formato non valido: 422.
- Rigenerare un invito annulla il link precedente. Il link vale 7 giorni ed è mostrato una sola volta a chi lo genera.
- Annullare un invito = disattivare un utente in stato INVITATO (gli inviti pendenti vengono revocati).
- Ogni invito o cambio di ruolo verso ADMIN_STARTUP è marcato `nursery_alert = true` e compare nella pagina **Segnalazioni**, visibile solo agli utenti Nursery.

## Organizzazioni provider e profili di servizio

| Azione | ADMIN_NURSERY | OPERATORE_NURSERY | Altri |
|---|---|---|---|
| Elenco provider (`GET /api/organizations`) | ✅ | ✅ (lettura, per filtri e moduli) | 👁 solo la propria organizzazione |
| Creare / modificare / eliminare provider | ✅ | ❌ | ❌ |
| Elenco profili di servizio | ✅ | ✅ (lettura) | ❌ |
| Creare / modificare / eliminare profili | ✅ | ❌ | ❌ |
| Segnalazioni (`GET /api/alerts`) | ✅ | ✅ | ❌ |

Eliminazione di provider e profili: logica, consentita solo se non collegati ad alcuna startup non cessata; altrimenti 409 con l'elenco delle startup collegate. Eliminando un provider i suoi utenti vengono disattivati (evento registrato).

## Area personale

Ogni utente attivo può leggere il proprio profilo, modificare nome, cognome e telefono e cambiare la propria password. Email, ruolo e organizzazione si modificano solo tramite la gestione utenti.

## Visibilità della cronologia (EventLog)

Ogni evento ha `visibility`:

- **NURSERY_ONLY**:
  - modifiche di `referente_nursery_user_id` (cambio referente Nursery);
  - modifiche di `service_profile_id` (cambio profilo di servizio);
  - modifiche di `servizi_attivi`;
  - tutti gli eventi che riguardano utenti di Nursery;
  - eventi sui profili di servizio ed eliminazione di una startup.
- **ALL**: tutti gli altri eventi.

Se una singola modifica tocca sia campi riservati sia campi ordinari, il backend registra due eventi distinti (uno `NURSERY_ONLY`, uno `ALL`), così nessun dato riservato è visibile a Provider e Startup.

Gli utenti Nursery vedono tutti gli eventi. Gli utenti Provider e Startup vedono solo gli eventi `ALL` relativi alle startup che possono vedere (filtro su `startup_id`).
