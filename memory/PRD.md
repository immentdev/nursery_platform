# PRD — Piattaforma Nursery

## Problema originale
Testo integrale del cliente: "PROGETTO: Piattaforma Nursery — Modulo 1: Fondamenta" (Nursery/Imment S.r.l., provider "Factory" Ida Servizi S.r.l., startup SRL; canale unico, responsabilità unica/accesso multiplo, Nursery supervisiona, neutralità provider). Entità Organization, User, Startup, ServiceProfile, EventLog; 6 ruoli; inviti a 7 giorni senza email; 9 schermate; dati di esempio; docs/data-model.md (SQL PostgreSQL) e docs/permissions.md. Fuori perimetro: attività, pratiche, scadenze, documenti, chat, notifiche, call, integrazioni.
Poi "Modulo 1 — Correzioni dal collaudo" (9 correzioni): catalogo servizi + StartupService con date; menu organizzazione ricercabile; invito dalla scheda startup (Nursery); dati provider + link_portale_provider; link reimpostazione password; profilo di servizio riservato e contatti referente; filtri pertinenti; LegalDocument/LegalAcceptance; segnalazioni con azione attesa.
Regola del cliente: non ipotizzare, chiedere quando qualcosa non è chiaro.

## Architettura
FastAPI (core.py, routes_auth/users/startups/admin/services/legal.py, seed.py con migrate idempotente) + MongoDB normalizzato (UUID, soft delete, Europe/Rome) + React/shadcn con token in src/theme/tokens.css.

## Implementato
- 2026-10-25: Modulo 1 completo (iteration_1/2 superate); link Impresa Digitale corretto in https://impresadigitale.eu/
- 2026-10-25: 9 correzioni dal collaudo (iteration_3: 26/26 API, flussi UI desktop e mobile superati); dati di test rimossi

## Backlog
- Modulo 2 solo su istruzioni del cliente
