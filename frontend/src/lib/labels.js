export const ROLE_LABELS = {
  ADMIN_NURSERY: "Amministratore Nursery",
  OPERATORE_NURSERY: "Operatore Nursery",
  OPERATIVO_PROVIDER: "Operativo provider",
  PROFESSIONISTA_PROVIDER: "Professionista provider",
  ADMIN_STARTUP: "Amministratore startup",
  OPERATIVO_STARTUP: "Operativo startup",
};

export const ROLES_BY_ORG_TYPE = {
  NURSERY: ["ADMIN_NURSERY", "OPERATORE_NURSERY"],
  PROVIDER: ["OPERATIVO_PROVIDER", "PROFESSIONISTA_PROVIDER"],
  STARTUP: ["ADMIN_STARTUP", "OPERATIVO_STARTUP"],
};

export const ORG_TYPE_LABELS = { NURSERY: "Nursery", PROVIDER: "Provider", STARTUP: "Startup" };

export const STATO_CLIENTE = { ONBOARDING: "Onboarding", ATTIVO: "Attivo", SOSPESO: "Sospeso", CESSATO: "Cessato" };

export const USER_STATUS = { INVITATO: "Invitato", ATTIVO: "Attivo", DISATTIVATO: "Disattivato" };

export const SERVIZI = {
  AFC_COMPLETO: "AFC completo",
  SOLO_CASH_FLOW: "Solo cash flow",
  FATTURAZIONE_PER_CONTO: "Fatturazione per conto",
  PAGHE: "Paghe",
};

export const REGIMI_IVA = { MENSILE: "Mensile", TRIMESTRALE: "Trimestrale" };

export const COMPETENCE = { CONTABILITA: "Contabilità", PAGHE: "Paghe" };

export const ACTION_LABELS = {
  STARTUP_CREATED: "Startup creata",
  STARTUP_UPDATED: "Dati startup modificati",
  STARTUP_STATUS_CHANGED: "Stato cliente modificato",
  STARTUP_DELETED: "Startup eliminata",
  USER_INVITED: "Utente invitato",
  USER_UPDATED: "Dati utente modificati",
  ROLE_CHANGED: "Ruolo modificato",
  USER_DEACTIVATED: "Utente disattivato",
  USER_REACTIVATED: "Utente riattivato",
  INVITE_CANCELLED: "Invito annullato",
  INVITE_REGENERATED: "Link di invito rigenerato",
  INVITE_ACCEPTED: "Invito accettato",
  PASSWORD_CHANGED: "Password modificata",
};

export const FIELD_LABELS = {
  denominazione: "Denominazione",
  codice_breve: "Codice breve",
  codice_fiscale: "Codice fiscale",
  partita_iva: "Partita IVA",
  sede_legale: "Sede legale",
  pec: "PEC",
  telefono: "Telefono",
  data_costituzione: "Data di costituzione",
  startup_innovativa: "Startup innovativa",
  data_iscrizione_sezione_speciale: "Iscrizione sezione speciale",
  data_chiusura_esercizio: "Chiusura esercizio",
  regime_iva: "Regime IVA",
  provider_organization_id: "Provider",
  service_profile_id: "Profilo di servizio",
  servizi_attivi: "Servizi attivi",
  referente_nursery_user_id: "Referente Nursery",
  link_impresa_digitale: "Link Impresa Digitale",
  stato_cliente: "Stato cliente",
  nome: "Nome",
  cognome: "Cognome",
  competence_areas: "Aree di competenza",
};

const TZ = "Europe/Rome";

export function formatDate(iso) {
  if (!iso) return "—";
  const [y, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${y}`;
}

export function formatDateTime(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("it-IT", { timeZone: TZ, dateStyle: "short", timeStyle: "short" });
}

export function formatChiusura(mmdd) {
  if (!mmdd) return "—";
  const [m, d] = mmdd.split("-");
  return `${d}/${m}`;
}

export function displayValue(field, value) {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) return value.map((v) => SERVIZI[v] || COMPETENCE[v] || v).join(", ") || "—";
  if (typeof value === "boolean") return value ? "Sì" : "No";
  if (field === "stato_cliente") return STATO_CLIENTE[value] || value;
  if (field === "regime_iva") return REGIMI_IVA[value] || value;
  if (field === "data_chiusura_esercizio") return formatChiusura(value);
  if (field?.startsWith("data_")) return formatDate(value);
  return ROLE_LABELS[value] || String(value);
}
