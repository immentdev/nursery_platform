import { Lock } from "lucide-react";
import { ACTION_LABELS, ALERT_AZIONI, FIELD_LABELS, ROLE_LABELS, displayValue, formatDate, formatDateTime } from "@/lib/labels";
import { Empty } from "@/components/common";

function Details({ e }) {
  const d = e.details || {};
  if (d.changes) {
    return (
      <ul className="mt-2 space-y-1 text-xs text-ink-soft">
        {d.servizio && <li className="font-medium text-ink">{d.servizio}</li>}
        {Object.entries(d.changes).map(([f, c]) => (
          <li key={f}>
            <span className="font-medium text-ink">{FIELD_LABELS[f] || f}</span>: {displayValue(f, c.from)} → {displayValue(f, c.to)}
          </li>
        ))}
      </ul>
    );
  }
  const parts = [];
  if (d.servizio) parts.push(d.servizio);
  if (d.data_attivazione) parts.push(`dal ${formatDate(d.data_attivazione)}`);
  if (d.data_cessazione) parts.push(`al ${formatDate(d.data_cessazione)}`);
  if (d.documenti) parts.push(d.documenti.join(", "));
  if (d.azione) parts.push(ALERT_AZIONI[d.azione] || d.azione);
  if (d.email) parts.push(d.email);
  if (d.role) parts.push(ROLE_LABELS[d.role]);
  if (d.from && d.to) parts.push(`${ROLE_LABELS[d.from]} → ${ROLE_LABELS[d.to]}`);
  if (d.codice_breve) parts.push(`${d.denominazione} (${d.codice_breve})`);
  if (d.motivo) parts.push(d.motivo);
  if (d.origine) parts.push(d.origine);
  return parts.length ? <div className="mt-1 text-xs text-ink-soft">{parts.join(" · ")}</div> : null;
}

export default function EventTimeline({ events }) {
  if (!events.length) return <Empty testId="events-empty">Nessun evento registrato.</Empty>;
  return (
    <ol className="relative space-y-5 border-l pl-6" data-testid="event-timeline">
      {events.map((e) => (
        <li key={e.id} className="relative" data-testid={`event-${e.id}`}>
          <span className="absolute -left-[calc(var(--space-unit)*7.5)] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-surface bg-brand" />
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="font-medium text-ink">{ACTION_LABELS[e.action] || e.action}</span>
            {e.visibility === "NURSERY_ONLY" && (
              <span className="inline-flex items-center gap-1 rounded-full bg-subtle px-2 py-0.5 text-xs text-ink-muted" data-testid="event-nursery-only">
                <Lock className="h-3 w-3" /> Solo Nursery
              </span>
            )}
          </div>
          <div className="text-xs text-ink-muted">{formatDateTime(e.timestamp)} · {e.actor_name}</div>
          <Details e={e} />
        </li>
      ))}
    </ol>
  );
}
