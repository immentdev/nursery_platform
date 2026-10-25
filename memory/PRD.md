# PRD — Piattaforma Nursery

## Problema originale
Vedi il testo completo del cliente: "PROGETTO: Piattaforma Nursery — Modulo 1: Fondamenta" (Nursery/Imment S.r.l., provider "Factory" Ida Servizi S.r.l., startup SRL; canale unico, responsabilità unica/accesso multiplo, Nursery supervisiona, neutralità provider). Modulo 1: Organization, User, Startup, ServiceProfile, EventLog; regole di accesso per 6 ruoli; login + inviti a 7 giorni (link mostrato, niente email); schermate 1-9; dati di esempio; docs/data-model.md (con SQL PostgreSQL) e docs/permissions.md. Fuori perimetro: attività, pratiche, scadenze, documenti, chat, notifiche, call, integrazioni.

Scelte del cliente: EventLog.visibility ALL/NURSERY_ONLY (referente, profilo, servizi attivi, utenti Nursery = NURSERY_ONLY); OPERATORE_NURSERY gestisce utenti Provider/Startup; stile chiaro istituzionale con design token centralizzati; telefono aggiunto alla Startup; eliminazione startup solo ONBOARDING (ADMIN_NURSERY), provider/profili solo se non collegati a startup non cessate; regole minime sui servizi; inviti rigenerabili; ADMIN_STARTUP invita ADMIN/OPERATIVO della propria startup, segnalazione a Nursery, vincolo ultimo admin.

## Architettura
- Backend FastAPI: core.py (db, auth JWT Bearer, permessi, EventLog), routes_auth/users/startups/admin.py, seed.py
- MongoDB: collezioni normalizzate con UUID, soft delete, timestamp Europe/Rome
- Frontend React + shadcn; token in src/theme/tokens.css mappati in tailwind.config.js

## Personas
Admin Nursery, Operatore Nursery, Operativo/Professionista provider, Admin startup, Operativo startup.

## Implementato (2026-10-25)
- Tutte le schermate 1-9 + pagina Segnalazioni (vista filtrata dell'EventLog)
- Matrice permessi applicata nel backend; 34 test API superati, flussi UI verificati
- docs/data-model.md, docs/permissions.md, README con credenziali

## Backlog
- P1: Modulo 2 (assegnazioni predefinite attività nei profili di servizio) — su indicazione del cliente
- P2: date picker uniforme nel form; posizione toast
