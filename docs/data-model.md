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
| name | testo | obbligatorio; per le STARTUP è sincronizzato con `startups.denominazione`; per i PROVIDER è la ragione sociale |
| partita_iva | testo, nullable | solo PROVIDER; obbligatoria alla creazione di un nuovo provider, 11 cifre |
| pec | testo, nullable | solo PROVIDER; obbligatoria alla creazione, formato email |
| nome_portale | testo, nullable | solo PROVIDER (es. "Impresa Digitale"); etichetta del pulsante nella scheda startup |
| url_portale | URL, nullable | solo PROVIDER, facoltativo |
| referente_nome, referente_email, referente_telefono | testo, nullable | solo PROVIDER, facoltativi |

Un provider con ragione sociale, partita IVA o PEC vuote è segnalato come "Dati incompleti" (campo calcolato `dati_incompleti`, non salvato). Ida Servizi è stato migrato con questi campi vuoti, tranne nome_portale "Impresa Digitale" e url_portale https://impresadigitale.eu/.

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
| referente_nursery_user_id | UUID → users.id (ruolo Nursery, non disattivato) | obbligatorio |
| link_portale_provider | URL http(s) | facoltativo (rinominato da `link_impresa_digitale`) |
| stato_cliente | enum `ONBOARDING` \| `ATTIVO` \| `SOSPESO` \| `CESSATO` | default ONBOARDING |

I servizi della startup sono record di `startup_services` (vedi sotto); il campo `servizi_attivi` è stato eliminato.

Cancellazione: solo ADMIN_NURSERY e solo in stato ONBOARDING. Le altre startup si chiudono con stato CESSATO.

### service_profiles
| Campo | Tipo | Vincoli |
|---|---|---|
| nome | testo | obbligatorio, univoco tra i non cancellati |
| descrizione | testo | facoltativo |

Cancellazione logica consentita solo se nessuna startup non cessata lo usa.

### services
Catalogo dei servizi, gestito da ADMIN_NURSERY.

| Campo | Tipo | Vincoli |
|---|---|---|
| codice | testo | obbligatorio, regex `^[A-Z][A-Z0-9_]{1,29}$`, univoco su tutti i record, non modificabile |
| nome | testo | obbligatorio |
| descrizione | testo | facoltativo |
| categoria | enum `SERVIZIO_PROVIDER` \| `SERVIZIO_NURSERY` | obbligatorio |
| richiede_provider | booleano | default false |
| attivo | booleano | se false non è selezionabile per nuove assegnazioni, ma resta sulle startup che lo hanno |
| ordine | intero | ordine di visualizzazione |

Cancellazione logica consentita solo se il servizio non ha record in `startup_services` di startup non cessate; altrimenti si può solo disattivare.
Servizi migrati: AFC_COMPLETO (SERVIZIO_PROVIDER, richiede provider), SOLO_CASH_FLOW (SERVIZIO_NURSERY), FATTURAZIONE_PER_CONTO (SERVIZIO_NURSERY), PAGHE (SERVIZIO_PROVIDER, richiede provider); incompatibilità SOLO_CASH_FLOW ↔ AFC_COMPLETO.

### service_incompatibilities
Relazione reciproca: una riga per coppia, con `service_a_id < service_b_id`.

| Campo | Tipo | Vincoli |
|---|---|---|
| service_a_id | UUID → services.id | obbligatorio |
| service_b_id | UUID → services.id | obbligatorio, diverso da service_a_id; coppia univoca tra le righe non cancellate |

### startup_services
Periodi di attivazione dei servizi di una startup.

| Campo | Tipo | Vincoli |
|---|---|---|
| startup_id | UUID → startups.id | obbligatorio |
| service_id | UUID → services.id | obbligatorio; per nuove assegnazioni il servizio deve essere attivo |
| data_attivazione | data | obbligatoria, inserita da Nursery (proposta: oggi), anche passata o futura |
| data_cessazione | data, nullable | non può precedere data_attivazione |

Stato calcolato (non salvato): PROGRAMMATO se data_attivazione > oggi; CESSATO se data_cessazione < oggi; altrimenti ATTIVO.
Regole verificate nel backend a ogni salvataggio della startup, ricavate dalle proprietà dei servizi:
1. almeno un servizio ATTIVO o PROGRAMMATO (non si applica alle startup CESSATE);
2. ogni servizio non cessato con `richiede_provider` richiede `provider_organization_id`;
3. servizi incompatibili non possono avere periodi sovrapposti;
4. lo stesso servizio non può avere due periodi sovrapposti.
Un record registrato non si elimina: si imposta la data di cessazione. Migrazione: un record per ogni servizio precedente, con data_attivazione = data di creazione della startup nella piattaforma.

### legal_documents
| Campo | Tipo | Vincoli |
|---|---|---|
| tipo | enum `TERMINI_USO` \| `INFORMATIVA_PRIVACY` | obbligatorio |
| versione | testo | obbligatorio, univoco per tipo |
| testo | testo | obbligatorio |
| data_pubblicazione | timestamp, nullable | NULL = bozza modificabile; valorizzata alla pubblicazione, poi immutabile |
| attivo | booleano | una sola versione attiva per tipo: la pubblicazione disattiva la precedente |

Precaricate: versione 1.0 di entrambi, con testo marcato "TESTO PROVVISORIO".

### legal_acceptances
| Campo | Tipo | Vincoli |
|---|---|---|
| user_id | UUID → users.id | obbligatorio |
| legal_document_id | UUID → legal_documents.id | obbligatorio; coppia univoca |
| tipo, versione | testo | copia del documento accettato |
| accepted_at | timestamp Europe/Rome | obbligatorio |

Finché un utente non ha accettato tutte le versioni attive, il backend risponde 403 a ogni API tranne `/api/auth/me`, `/api/legal/current`, `/api/legal/accept`.

### alert_handlings
Gestione delle segnalazioni (eventi con `nursery_alert = true`); l'EventLog resta immutabile.

| Campo | Tipo | Vincoli |
|---|---|---|
| event_log_id | UUID → event_logs.id | obbligatorio, univoco |
| handled_by_user_id | UUID → users.id (utente Nursery) | obbligatorio |
| handled_at | timestamp | obbligatorio |
| azione | enum `PRESA_VISIONE` \| `INVITO_ANNULLATO` \| `RUOLO_CAMBIATO` | obbligatorio |

### invitations
Entità tecnica per i link di invito e di reimpostazione password (separata da `users` per normalizzazione).

| Campo | Tipo | Vincoli |
|---|---|---|
| user_id | UUID → users.id | obbligatorio |
| tipo | enum `INVITO` \| `RESET_PASSWORD` | INVITO: 7 giorni, utente INVITATO; RESET_PASSWORD: 24 ore, utente ATTIVO. Un nuovo link annulla i precedenti dello stesso tipo |
| token_hash | testo (SHA-256 del token) | obbligatorio; il token in chiaro non è mai salvato |
| expires_at | timestamp | creazione + 7 giorni |
| used_at | timestamp, nullable | valorizzato all'accettazione |
| revoked_at | timestamp, nullable | valorizzato quando l'invito viene rigenerato o annullato |

### event_logs
Registro di tutte le azioni. Non viene mai modificato.

| Campo | Tipo | Vincoli |
|---|---|---|
| actor_user_id | UUID → users.id, nullable | NULL = sistema |
| entity_type | enum `STARTUP` \| `USER` \| `ORGANIZATION` \| `SERVICE_PROFILE` \| `SERVICE` \| `STARTUP_SERVICE` \| `LEGAL_DOCUMENT` \| `ALERT` | obbligatorio |
| entity_id | UUID | obbligatorio (riferimento polimorfico) |
| startup_id | UUID → startups.id, nullable | startup di riferimento, per la cronologia della scheda (campo aggiunto) |
| action | testo | es. STARTUP_CREATED, STARTUP_UPDATED, STARTUP_STATUS_CHANGED, STARTUP_DELETED, USER_INVITED, USER_UPDATED, ROLE_CHANGED, USER_DEACTIVATED, USER_REACTIVATED, INVITE_CANCELLED, INVITE_REGENERATED, INVITE_ACCEPTED, PASSWORD_CHANGED, PASSWORD_RESET_LINK_CREATED, PASSWORD_RESET_COMPLETED, STARTUP_SERVICE_ADDED, STARTUP_SERVICE_UPDATED, SERVICE_CREATED/UPDATED/DEACTIVATED/DELETED, LEGAL_DRAFT_CREATED/UPDATED/DELETED, LEGAL_PUBLISHED, LEGAL_ACCEPTED, ALERT_HANDLED, ORGANIZATION_CREATED/UPDATED/DELETED, SERVICE_PROFILE_CREATED/UPDATED/DELETED |
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
- startups 1 — N startup_services N — 1 services
- services N — N services (service_incompatibilities)
- users 1 — N legal_acceptances N — 1 legal_documents
- event_logs 1 — 0..1 alert_handlings
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
CREATE TYPE service_categoria AS ENUM ('SERVIZIO_PROVIDER', 'SERVIZIO_NURSERY');
CREATE TYPE legal_tipo AS ENUM ('TERMINI_USO', 'INFORMATIVA_PRIVACY');
CREATE TYPE alert_azione AS ENUM ('PRESA_VISIONE', 'INVITO_ANNULLATO', 'RUOLO_CAMBIATO');
CREATE TYPE token_tipo AS ENUM ('INVITO', 'RESET_PASSWORD');
CREATE TYPE stato_cliente AS ENUM ('ONBOARDING', 'ATTIVO', 'SOSPESO', 'CESSATO');
CREATE TYPE event_visibility AS ENUM ('ALL', 'NURSERY_ONLY');
CREATE TYPE entity_type AS ENUM ('STARTUP', 'USER', 'ORGANIZATION', 'SERVICE_PROFILE', 'SERVICE', 'STARTUP_SERVICE', 'LEGAL_DOCUMENT', 'ALERT');

CREATE TABLE organizations (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  type        organization_type NOT NULL,
  name        text NOT NULL CHECK (length(trim(name)) > 0),
  partita_iva text NULL CHECK (partita_iva IS NULL OR partita_iva ~ '^[0-9]{11}$'),
  pec         text NULL,
  nome_portale text NULL,
  url_portale text NULL CHECK (url_portale IS NULL OR url_portale ~ '^https?://'),
  referente_nome text NULL,
  referente_email text NULL,
  referente_telefono text NULL,
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
  referente_nursery_user_id         uuid NOT NULL REFERENCES users(id),
  link_portale_provider             text NULL CHECK (link_portale_provider IS NULL OR link_portale_provider ~ '^https?://'),
  stato_cliente                     stato_cliente NOT NULL DEFAULT 'ONBOARDING',
  created_at                        timestamptz NOT NULL DEFAULT now(),
  updated_at                        timestamptz NOT NULL DEFAULT now(),
  created_by                        uuid NULL REFERENCES users(id),
  deleted_at                        timestamptz NULL,
  CHECK ((startup_innovativa AND data_iscrizione_sezione_speciale IS NOT NULL)
         OR (NOT startup_innovativa AND data_iscrizione_sezione_speciale IS NULL))
);
CREATE UNIQUE INDEX startups_codice_breve_uq ON startups (codice_breve) WHERE deleted_at IS NULL;
CREATE INDEX startups_provider_idx ON startups (provider_organization_id);
CREATE INDEX startups_referente_idx ON startups (referente_nursery_user_id);
-- Tipo organizzazione (STARTUP/PROVIDER) e ruolo del referente sono verificati dal backend (o da trigger).

CREATE TABLE invitations (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid NOT NULL REFERENCES users(id),
  tipo        token_tipo NOT NULL DEFAULT 'INVITO',
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

CREATE TABLE services (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  codice             varchar(30) NOT NULL UNIQUE CHECK (codice ~ '^[A-Z][A-Z0-9_]{1,29}$'),
  nome               text NOT NULL,
  descrizione        text NOT NULL DEFAULT '',
  categoria          service_categoria NOT NULL,
  richiede_provider  boolean NOT NULL DEFAULT false,
  attivo             boolean NOT NULL DEFAULT true,
  ordine             integer NOT NULL DEFAULT 0,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now(),
  created_by         uuid NULL REFERENCES users(id),
  deleted_at         timestamptz NULL
);
-- codice immutabile: trigger BEFORE UPDATE che rifiuta NEW.codice <> OLD.codice (in Supabase).

CREATE TABLE service_incompatibilities (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  service_a_id  uuid NOT NULL REFERENCES services(id),
  service_b_id  uuid NOT NULL REFERENCES services(id),
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now(),
  created_by    uuid NULL REFERENCES users(id),
  deleted_at    timestamptz NULL,
  CHECK (service_a_id < service_b_id)
);
CREATE UNIQUE INDEX service_incompat_pair_uq ON service_incompatibilities (service_a_id, service_b_id) WHERE deleted_at IS NULL;

CREATE TABLE startup_services (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  startup_id        uuid NOT NULL REFERENCES startups(id),
  service_id        uuid NOT NULL REFERENCES services(id),
  data_attivazione  date NOT NULL,
  data_cessazione   date NULL,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),
  created_by        uuid NULL REFERENCES users(id),
  deleted_at        timestamptz NULL,
  CHECK (data_cessazione IS NULL OR data_cessazione >= data_attivazione)
);
CREATE INDEX startup_services_startup_idx ON startup_services (startup_id);
-- Sovrapposizioni e incompatibilità sono verificate dal backend (in PostgreSQL: daterange + exclusion constraint o trigger).

CREATE TABLE legal_documents (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tipo                legal_tipo NOT NULL,
  versione            text NOT NULL,
  testo               text NOT NULL,
  data_pubblicazione  timestamptz NULL,
  attivo              boolean NOT NULL DEFAULT false,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  created_by          uuid NULL REFERENCES users(id),
  deleted_at          timestamptz NULL,
  CHECK (NOT attivo OR data_pubblicazione IS NOT NULL)
);
CREATE UNIQUE INDEX legal_documents_versione_uq ON legal_documents (tipo, versione) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX legal_documents_attivo_uq ON legal_documents (tipo) WHERE attivo AND deleted_at IS NULL;

CREATE TABLE legal_acceptances (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id            uuid NOT NULL REFERENCES users(id),
  legal_document_id  uuid NOT NULL REFERENCES legal_documents(id),
  tipo               legal_tipo NOT NULL,
  versione           text NOT NULL,
  accepted_at        timestamptz NOT NULL DEFAULT now(),
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now(),
  created_by         uuid NULL REFERENCES users(id),
  deleted_at         timestamptz NULL,
  UNIQUE (user_id, legal_document_id)
);

CREATE TABLE alert_handlings (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_log_id        uuid NOT NULL UNIQUE REFERENCES event_logs(id),
  handled_by_user_id  uuid NOT NULL REFERENCES users(id),
  handled_at          timestamptz NOT NULL DEFAULT now(),
  azione              alert_azione NOT NULL,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  created_by          uuid NULL REFERENCES users(id),
  deleted_at          timestamptz NULL
);

CREATE TABLE login_attempts (
  identifier    text PRIMARY KEY,
  count         integer NOT NULL DEFAULT 0,
  locked_until  timestamptz NULL
);
```

Nota sul fuso: in PostgreSQL i timestamp sono `timestamptz`; la sessione va impostata con `SET TIME ZONE 'Europe/Rome'` per riprodurre il formato del prototipo.
