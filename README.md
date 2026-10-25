# Piattaforma Nursery — Modulo 1: Fondamenta

Ambiente collaborativo tra Nursery (Imment S.r.l.), provider esterni e startup.
Stack prototipo: React + FastAPI + MongoDB (migrazione prevista su PostgreSQL/Supabase).

- Modello dati e schema SQL: [docs/data-model.md](docs/data-model.md)
- Matrice permessi: [docs/permissions.md](docs/permissions.md)
- Design token (colori, font, spaziature): `frontend/src/theme/tokens.css`

## Credenziali di prova

Dati di esempio fittizi (domini `.test`), caricati al primo avvio.

| Ruolo | Email | Password | Organizzazione |
|---|---|---|---|
| ADMIN_NURSERY | admin@imment.it | Nursery2026! | Nursery |
| OPERATORE_NURSERY | operatore@imment.test | Prova2026! | Nursery |
| OPERATIVO_PROVIDER | operativo@idaservizi.test | Prova2026! | Ida Servizi S.r.l. |
| PROFESSIONISTA_PROVIDER | professionista@idaservizi.test | Prova2026! | Ida Servizi S.r.l. |
| ADMIN_STARTUP | admin@alfa.test | Prova2026! | Alfa Robotics (ALFA) |
| OPERATIVO_STARTUP | operativo@alfa.test | Prova2026! | Alfa Robotics (ALFA) |
| ADMIN_STARTUP | admin@beta.test | Prova2026! | Beta Lab (BETA) |
| ADMIN_STARTUP | admin@gamma.test | Prova2026! | Gamma Flow (GAMMA) |

Startup di esempio:
- **ALFA** — Alfa Robotics S.r.l.: "Startup seguita in tutto", provider Ida Servizi, AFC completo + Paghe.
- **BETA** — Beta Lab S.r.l.: "Startup con amministrativo interno", provider Ida Servizi, AFC completo + Fatturazione per conto.
- **GAMMA** — Gamma Flow S.r.l.: solo cash flow, senza provider.

Le password di seed sono definite in `backend/.env` (`ADMIN_PASSWORD`, `DEMO_PASSWORD`).
