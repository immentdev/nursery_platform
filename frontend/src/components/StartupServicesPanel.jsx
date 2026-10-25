import { useAuth } from "@/context/AuthContext";
import { isNursery } from "@/lib/perms";
import { CATEGORIE, formatDate } from "@/lib/labels";
import { Card, Field, StatusBadge } from "@/components/common";

function ServicesTable({ s, nursery }) {
  if (!s.servizi.length) return <p className="text-sm text-ink-muted">Nessun servizio.</p>;
  return (
    <ul className="divide-y rounded-md border" data-testid="startup-services-list">
      {s.servizi.map((x) => (
        <li key={x.id || `${x.service_id}-${x.data_attivazione}`} className="flex flex-wrap items-center gap-3 px-3 py-2 text-sm" data-testid={`startup-service-${x.codice}`}>
          <span className="flex-1 font-medium text-ink">{x.nome}</span>
          <StatusBadge kind="servizio" value={x.stato} />
          {nursery ? (
            <span className="text-xs text-ink-muted">
              {CATEGORIE[x.categoria]} · dal {formatDate(x.data_attivazione)}{x.data_cessazione ? ` al ${formatDate(x.data_cessazione)}` : ""}
            </span>
          ) : x.stato === "PROGRAMMATO" && <span className="text-xs text-ink-muted">dal {formatDate(x.data_attivazione)}</span>}
        </li>
      ))}
    </ul>
  );
}

function ProviderInfo({ p, full }) {
  if (!p) return "Nessun provider (commercialista proprio)";
  if (!full) return p.name;
  return (
    <div className="space-y-0.5">
      <div>{p.name}</div>
      <div className="text-xs text-ink-soft">P.IVA {p.partita_iva || "—"} · PEC {p.pec || "—"}</div>
      <div className="text-xs text-ink-soft">Portale: {p.nome_portale || "—"}{p.url_portale ? ` (${p.url_portale})` : ""}</div>
      <div className="text-xs text-ink-soft">Referente: {[p.referente_nome, p.referente_email, p.referente_telefono].filter(Boolean).join(" · ") || "—"}</div>
    </div>
  );
}

export default function StartupServicesPanel({ s }) {
  const { user } = useAuth();
  const nursery = isNursery(user);
  const startupUser = ["ADMIN_STARTUP", "OPERATIVO_STARTUP"].includes(user.role);
  return (
    <div className="space-y-6">
      <Card title={nursery ? "Servizi e storico attivazioni" : "Servizi attivi e programmati"} testId="startup-services-card">
        <ServicesTable s={s} nursery={nursery} />
      </Card>
      <Card>
        <dl className="grid gap-6 sm:grid-cols-2">
          {nursery && <Field label="Profilo di servizio" testId="field-profilo">{s.service_profile_name}</Field>}
          <Field label="Provider" testId="field-provider"><ProviderInfo p={s.provider} full={!startupUser} /></Field>
          <Field label="Referente Nursery" testId="field-referente">
            {nursery || !s.referente ? s.referente_name : (
              <div className="space-y-0.5">
                <div>{s.referente.nome} {s.referente.cognome}</div>
                <div className="text-xs text-ink-soft" data-testid="field-referente-contatti">{s.referente.email}{s.referente.telefono ? ` · ${s.referente.telefono}` : ""}</div>
              </div>
            )}
          </Field>
        </dl>
      </Card>
    </div>
  );
}
