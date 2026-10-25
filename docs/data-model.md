# Modello dati — Piattaforma Nursery (Modulo 1)

Prototipo su MongoDB, progettato per la migrazione su PostgreSQL (Supabase).
Ogni collezione corrisponde a una tabella. Nessun oggetto principale annidato.

## Convenzioni comuni

| Campo | Tipo | Note |
|---|---|---|
| id | UUID (stringa) | Chiave primaria, generata dal backend |
| created_at | timestamp ISO 8601 con offset Europe/Rome | Es. `2026-10-25T09:00:00+01:00` |
| updated_at | timestamp ISO 8601 Europe/Rome | Aggiornato a ogni modifica |
| created_by | UUID → users.id, nullable | `NULL` per i record creati dal sistema (seed) |
| deleted_at | timestamp, nullable | Cancellazione logica: i record non vengono mai eliminati fisicamente |

Le date senza ora (es. `data_costituzione`) sono in formato `AAAA-MM-GG`.
Il campo `_id` interno di MongoDB non viene mai esposto dalle API e non va migrato.

## Entità

### organizations
Soggetti della piattaforma. Esiste una sola organizzazione `NURSERY`. Ogni startup ha una propria organizzazione `STARTUP` (relazione 1:1).

| Campo | Tipo | Vincoli |
|---|---|---|
| type | enum `NURSERY` \| `PROVIDER` \| `STARTUP` | obbligatorio; una sola NURSERY (indice univoco parziale) |
| name | testo | obbligatorio; per le STARTUP è sincronizzato con `startups.denominazione` |

### users
| Campo | Tipo | Vincoli |
|---|---|---|
| organization_id | UUID → organizations.id | obbligatorio |
| nome, cognome | testo | obbligatori |
| email | testo | obbligatorio, univoco (minuscolo) su tutti i record, inclusi i cancellati |
| telefono | testo | facoltativo |
| role | enum `ADMIN_NURSERY` \| `OPERATORE_NURSERY` \| `OPERATIVO_PROVIDER` \| `PROFESSIONISTA_PROVIDER` \| `ADMIN_STARTUP` \| `OPERATIVO_STARTUP` | obbligatorio; deve essere coerente col tipo di organizzazione |
| competence_areas | array di enum `CONTABILITA` \| `PAGHE` | solo per utenti PROVIDER, altrimenti vuoto |
| status | enum `INVITATO` \| `ATTIVO` \| `DISATTIVATO` | obbligatorio |
| password_hash | testo (bcrypt) | nullable finché l'invito non è accettato; mai esposto dalle API |

Coerenza ruolo/organizzazione: NURSERY → ADMIN_NURSERY, OPERATORE_NURSERY; PROVIDER → OPERATIVO_PROVIDER, PROFESSIONISTA_PROVIDER; STARTUP → ADMIN_STARTUP, OPERATIVO_STARTUP.

### startups
| Campo | Tipo | Vincoli |
|---|---|---|
| organization_id | UUID → organizations.id (type STARTUP) | obbligatorio, univoco |
| denominazione | testo | obbligatorio |
| codice_breve | testo | obbligatorio, regex `^[A-Z]{3,6}$`, univoco tra le startup non cancellate |
| codice_fiscale | testo | obbligatorio, 11 cifre |
| partita_iva | testo | obbligatorio, 11 cifre |
| sede_legale | testo | obbligatorio |
| pec | testo | obbligatorio, formato email |
| telefono | testo | facoltativo (aggiunto su richiesta: modificabile dall'ADMIN_STARTUP) |
| data_costituzione | data | obbligatorio |
| startup_innovativa | booleano | default false |
| data_iscrizione_sezione_speciale | data | obbligatoria se `startup_innovativa = true`, altrimenti NULL |
| data_chiusura_esercizio | testo `MM-GG` | default `12-31` |
| regime_iva | enum `MENSILE` \| `TRIMESTRALE` | obbligatorio |
| provider_organization_id | UUID → organizations.id (type PROVIDER) | facoltativo (assente per clienti "solo cash flow") |
| service_profile_id | UUID → service_profiles.id | obbligatorio |
| servizi_attivi | array di enum `AFC_COMPLETO` \| `SOLO_CASH_FLOW` \| `FATTURAZIONE_PER_CONTO` \| `PAGHE` | almeno uno |
| referente_nursery_user_id | UUID → users.id (ruolo Nursery, non disattivato) | obbligatorio |
| link_impresa_digitale | URL http(s) | facoltativo |
| stato_cliente | enum `ONBOARDING` \| `ATTIVO` \| `SOSPESO` \| `CESSATO` | default ONBOARDING |

Regole sui servizi (verificate nel backend):
1. almeno un servizio attivo;
2. `SOLO_CASH_FLOW` esclude `AFC_COMPLETO`;
3. `AFC_COMPLETO` e `PAGHE` richiedono `provider_organization_id`;
4. `FATTURAZIONE_PER_CONTO` è combinabile liberamente.

Cancellazione: solo ADMIN_NURSERY e solo in stato ONBOARDING. Le altre startup si chiudono con stato CESSATO.

### service_profiles
| Campo | Tipo | Vincoli |
|---|---|---|
| nome | testo | obbligatorio, univoco tra i non cancellati |
| descrizione | testo | facoltativo |

Cancellazione logica consentita solo se nessuna startup non cessata lo usa.

### invitations
Entità tecnica per i link di invito (non prevista esplicitamente dalla specifica, separata da `users` per normalizzazione).

| Campo | Tipo | Vincoli |
|---|---|---|
| user_id | UUID → users.id | obbligatorio |
| token_hash | testo (SHA-256 del token) | obbligatorio; il token in chiaro non è mai salvato |
| expires_at | timestamp | creazione + 7 giorni |
| used_at | timestamp, nullable | valorizzato all'accettazione |
| revoked_at | timestamp, nullable | valorizzato quando l'invito viene rigenerato o annullato |

### event_logs
Registro di tutte le azioni. Non viene mai modificato.

| Campo | Tipo | Vincoli |
|---|---|---|
| actor_user_id | UUID → users.id, nullable | NULL = sistema |
| entity_type | enum `STARTUP` \| `USER` \| `ORGANIZATION` \| `SERVICE_PROFILE` | obbligatorio |
| entity_id | UUID | obbligatorio (riferimento polimorfico) |
| startup_id | UUID → startups.id, nullable | startup di riferimento, per la cronologia della scheda (campo aggiunto) |
| action | testo | es. STARTUP_CREATED, STARTUP_UPDATED, STARTUP_STATUS_CHANGED, STARTUP_DELETED, USER_INVITED, USER_UPDATED, ROLE_CHANGED, USER_DEACTIVATED, USER_REACTIVATED, INVITE_CANCELLED, INVITE_REGENERATED, INVITE_ACCEPTED, PASSWORD_CHANGED, ORGANIZATION_CREATED/UPDATED/DELETED, SERVICE_PROFILE_CREATED/UPDATED/DELETED |
| details | JSON | per le modifiche: `{"changes": {"campo": {"from": ..., "to": ...}}}` |
| visibility | enum `ALL` \| `NURSERY_ONLY` | vedi docs/permissions.md |
| nursery_alert | booleano | true per inviti e cambi di ruolo verso ADMIN_STARTUP (pagina Segnalazioni) |
| timestamp | timestamp Europe/Rome | obbligatorio |

### login_attempts (tecnica)
Protezione da tentativi ripetuti: `identifier` (email), `count`, `locked_until`. Non è un'entità di dominio.

## Relazioni

- organizations 1 — N users
- organizations (STARTUP) 1 — 1 startups
- organizations (PROVIDER) 1 — N startups (`provider_organization_id`)
- service_profiles 1 — N startups
- users (Nursery) 1 — N startups (`referente_nursery_user_id`)
- users 1 — N invitations
- startups 1 — N event_logs (`startup_id`)

## Schema PostgreSQL equivalente

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE organization_type AS ENUM ('NURSERY', 'PROVIDER', 'STARTUP');
CREATE TYPE user_role AS ENUM ('ADMIN_NURSERY', 'OPERATORE_NURSERY', 'OPERATIVO_PROVIDER',
  'PROFESSIONISTA_PROVIDER', 'ADMIN_STARTUP', 'OPERATIVO_STARTUP');
CREATE TYPE user_status AS ENUM ('INVITATO', 'ATTIVO', 'DISATTIVATO');
CREATE TYPE competence_area AS ENUM ('CONTABILITA', 'PAGHE');
CREATE TYPE regime_iva AS ENUM ('MENSILE', 'TRIMESTRALE');
CREATE TYPE servizio AS ENUM ('AFC_COMPLETO', 'SOLO_CASH_FLOW', 'FATTURAZIONE_PER_CONTO', 'PAGHE');
CREATE TYPE stato_cliente AS ENUM ('ONBOARDING', 'ATTIVO', 'SOSPESO', 'CESSATO');
CREATE TYPE event_visibility AS ENUM ('ALL', 'NURSERY_ONLY');
CREATE TYPE entity_type AS ENUM ('STARTUP', 'USER', 'ORGANIZATION', 'SERVICE_PROFILE');

CREATE TABLE organizations (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  type        organization_type NOT NULL,
  name        text NOT NULL CHECK (length(trim(name)) > 0),
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  created_by  uuid NULL,
  deleted_at  timestamptz NULL
);
CREATE UNIQUE INDEX organizations_single_nursery ON organizations (type) WHERE type = 'NURSERY' AND deleted_at IS NULL;

CREATE TABLE users (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id   uuid NOT NULL REFERENCES organizations(id),
  nome              text NOT NULL,
  cognome           text NOT NULL,
  email             text NOT NULL UNIQUE CHECK (email = lower(email)),
  telefono          text NULL,
  role              user_role NOT NULL,
  competence_areas  competence_area[] NOT NULL DEFAULT '{}',
  status            user_status NOT NULL DEFAULT 'INVITATO',
  password_hash     text NULL,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),
  created_by        uuid NULL REFERENCES users(id),
  deleted_at        timestamptz NULL,
  CHECK (status = 'INVITATO' OR status = 'DISATTIVATO' OR password_hash IS NOT NULL),
  CHECK (cardinality(competence_areas) = 0 OR role IN ('OPERATIVO_PROVIDER', 'PROFESSIONISTA_PROVIDER'))
);
CREATE INDEX users_organization_idx ON users (organization_id);
-- La coerenza ruolo/tipo organizzazione è applicata dal backend (o da un trigger in Supabase).

ALTER TABLE organizations ADD CONSTRAINT organizations_created_by_fk FOREIGN KEY (created_by) REFERENCES users(id);

CREATE TABLE service_profiles (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  nome         text NOT NULL,
  descrizione  text NOT NULL DEFAULT '',
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now(),
  created_by   uuid NULL REFERENCES users(id),
  deleted_at   timestamptz NULL
);
CREATE UNIQUE INDEX service_profiles_nome_uq ON service_profiles (nome) WHERE deleted_at IS NULL;

CREATE TABLE startups (
  id                                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id                   uuid NOT NULL UNIQUE REFERENCES organizations(id),
  denominazione                     text NOT NULL,
  codice_breve                      varchar(6) NOT NULL CHECK (codice_breve ~ '^[A-Z]{3,6}$'),
  codice_fiscale                    char(11) NOT NULL CHECK (codice_fiscale ~ '^[0-9]{11}$'),
  partita_iva                       char(11) NOT NULL CHECK (partita_iva ~ '^[0-9]{11}$'),
  sede_legale                       text NOT NULL,
  pec                               text NOT NULL,
  telefono                          text NULL,
  data_costituzione                 date NOT NULL,
  startup_innovativa                boolean NOT NULL DEFAULT false,
  data_iscrizione_sezione_speciale  date NULL,
  data_chiusura_esercizio           char(5) NOT NULL DEFAULT '12-31'
                                    CHECK (data_chiusura_esercizio ~ '^(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$'),
  regime_iva                        regime_iva NOT NULL,
  provider_organization_id          uuid NULL REFERENCES organizations(id),
  service_profile_id                uuid NOT NULL REFERENCES service_profiles(id),
  servizi_attivi                    servizio[] NOT NULL CHECK (cardinality(servizi_attivi) > 0),
  referente_nursery_user_id         uuid NOT NULL REFERENCES users(id),
  link_impresa_digitale             text NULL CHECK (link_impresa_digitale IS NULL OR link_impresa_digitale ~ '^https?://'),
  stato_cliente                     stato_cliente NOT NULL DEFAULT 'ONBOARDING',
  created_at                        timestamptz NOT NULL DEFAULT now(),
  updated_at                        timestamptz NOT NULL DEFAULT now(),
  created_by                        uuid NULL REFERENCES users(id),
  deleted_at                        timestamptz NULL,
  CHECK ((startup_innovativa AND data_iscrizione_sezione_speciale IS NOT NULL)
         OR (NOT startup_innovativa AND data_iscrizione_sezione_speciale IS NULL)),
  CHECK (NOT ('SOLO_CASH_FLOW' = ANY (servizi_attivi) AND 'AFC_COMPLETO' = ANY (servizi_attivi))),
  CHECK (provider_organization_id IS NOT NULL
         OR NOT ('AFC_COMPLETO' = ANY (servizi_attivi) OR 'PAGHE' = ANY (servizi_attivi)))
);
CREATE UNIQUE INDEX startups_codice_breve_uq ON startups (codice_breve) WHERE deleted_at IS NULL;
CREATE INDEX startups_provider_idx ON startups (provider_organization_id);
CREATE INDEX startups_referente_idx ON startups (referente_nursery_user_id);
-- Tipo organizzazione (STARTUP/PROVIDER) e ruolo del referente sono verificati dal backend (o da trigger).

CREATE TABLE invitations (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid NOT NULL REFERENCES users(id),
  token_hash  char(64) NOT NULL UNIQUE,
  expires_at  timestamptz NOT NULL,
  used_at     timestamptz NULL,
  revoked_at  timestamptz NULL,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  created_by  uuid NULL REFERENCES users(id),
  deleted_at  timestamptz NULL
);
CREATE INDEX invitations_user_idx ON invitations (user_id);

CREATE TABLE event_logs (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_user_id  uuid NULL REFERENCES users(id),
  entity_type    entity_type NOT NULL,
  entity_id      uuid NOT NULL,
  startup_id     uuid NULL REFERENCES startups(id),
  action         text NOT NULL,
  details        jsonb NOT NULL DEFAULT '{}'::jsonb,
  visibility     event_visibility NOT NULL DEFAULT 'ALL',
  nursery_alert  boolean NOT NULL DEFAULT false,
  timestamp      timestamptz NOT NULL DEFAULT now(),
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now(),
  created_by     uuid NULL REFERENCES users(id),
  deleted_at     timestamptz NULL
);
CREATE INDEX event_logs_startup_idx ON event_logs (startup_id, timestamp DESC);
CREATE INDEX event_logs_alert_idx ON event_logs (timestamp DESC) WHERE nursery_alert;

CREATE TABLE login_attempts (
  identifier    text PRIMARY KEY,
  count         integer NOT NULL DEFAULT 0,
  locked_until  timestamptz NULL
);
```

Nota sul fuso: in PostgreSQL i timestamp sono `timestamptz`; la sessione va impostata con `SET TIME ZONE 'Europe/Rome'` per riprodurre il formato del prototipo.
