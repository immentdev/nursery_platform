import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";
import { ACTION_LABELS, ROLE_LABELS, formatDateTime } from "@/lib/labels";
import { PageHeader, Empty } from "@/components/common";

export default function AlertsPage() {
  const [items, setItems] = useState(null);
  useEffect(() => {
    api.get("/alerts").then(({ data }) => setItems(data));
  }, []);
  return (
    <div>
      <PageHeader title="Segnalazioni" subtitle="Inviti e cambi di ruolo verso Amministratore startup, tratti dal registro eventi" />
      {items === null ? <div className="text-sm text-ink-muted">Caricamento…</div> : !items.length ? (
        <Empty testId="alerts-empty">Nessuna segnalazione.</Empty>
      ) : (
        <ul className="divide-y rounded-lg border bg-surface shadow-card" data-testid="alerts-list">
          {items.map((e) => (
            <li key={e.id} className="flex gap-3 px-4 py-4" data-testid={`alert-${e.id}`}>
              <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-warn-fg" />
              <div className="min-w-0 text-sm">
                <div className="font-medium text-ink">
                  {ACTION_LABELS[e.action]}: {e.target_name || e.details?.email} → {ROLE_LABELS[e.details?.to || e.details?.role]}
                </div>
                <div className="text-xs text-ink-muted">
                  {formatDateTime(e.timestamp)} · da {e.actor_name}
                  {e.startup_id && (e.startup_deleted
                    ? <> · {e.startup_name} (eliminata)</>
                    : <> · <Link to={`/startup/${e.startup_id}`} className="text-brand underline">{e.startup_name}</Link></>)}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
