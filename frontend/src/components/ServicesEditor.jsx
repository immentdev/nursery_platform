import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { MultiSelect } from "@/components/Pickers";
import { StatusBadge } from "@/components/common";
import { serviceStatus, todayRome } from "@/lib/labels";

// value: [{ id?, service_id, data_attivazione, data_cessazione }]; catalog: servizi da /api/services
export default function ServicesEditor({ value, onChange, catalog }) {
  const byId = Object.fromEntries(catalog.map((s) => [s.id, s]));
  const newIds = value.filter((r) => !r.id).map((r) => r.service_id);
  const toggle = (sid) => onChange(newIds.includes(sid)
    ? value.filter((r) => r.id || r.service_id !== sid)
    : [...value, { service_id: sid, data_attivazione: todayRome(), data_cessazione: "" }]);
  const update = (i, k, v) => onChange(value.map((r, j) => (j === i ? { ...r, [k]: v } : r)));

  return (
    <div className="space-y-3">
      <MultiSelect
        options={catalog.filter((s) => s.attivo).map((s) => ({ value: s.id, label: s.nome, hint: s.codice }))}
        selected={newIds} onToggle={toggle} placeholder="Aggiungi servizi attivi del catalogo" searchPlaceholder="Cerca servizio…"
        testId="form-servizi-select"
      />
      {value.length > 0 && (
        <ul className="divide-y rounded-md border" data-testid="form-servizi-list">
          {value.map((r, i) => (
            <li key={r.id || `new-${r.service_id}`} className="grid gap-2 px-3 py-3 sm:grid-cols-[1fr_auto_auto_auto] sm:items-end" data-testid={`form-servizio-row-${byId[r.service_id]?.codice}`}>
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span className="font-medium text-ink">{byId[r.service_id]?.nome}</span>
                {r.data_attivazione && <StatusBadge kind="servizio" value={serviceStatus(r)} />}
                {!r.id && <span className="text-xs text-ink-muted">nuovo</span>}
                {byId[r.service_id] && !byId[r.service_id].attivo && <span className="text-xs text-ink-muted">(servizio disattivato nel catalogo)</span>}
              </div>
              <label className="text-xs text-ink-muted">Attivazione
                <Input type="date" value={r.data_attivazione || ""} onChange={(e) => update(i, "data_attivazione", e.target.value)} data-testid={`form-servizio-att-${i}`} />
              </label>
              <label className="text-xs text-ink-muted">Cessazione (facoltativa)
                <Input type="date" value={r.data_cessazione || ""} onChange={(e) => update(i, "data_cessazione", e.target.value)} data-testid={`form-servizio-cess-${i}`} />
              </label>
              {!r.id ? (
                <Button type="button" variant="ghost" size="icon" aria-label="Rimuovi" onClick={() => toggle(r.service_id)} data-testid={`form-servizio-remove-${i}`}><X className="h-4 w-4" /></Button>
              ) : <span />}
            </li>
          ))}
        </ul>
      )}
      <p className="text-xs text-ink-muted">
        Le regole (almeno un servizio attivo o programmato, servizi che richiedono un provider, servizi incompatibili su periodi sovrapposti) sono verificate al salvataggio.
        Un servizio già registrato non si rimuove: si imposta la data di cessazione.
      </p>
    </div>
  );
}
