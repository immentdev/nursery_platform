import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { ShieldAlert, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api, errorMessage } from "@/lib/api";
import { ACTION_LABELS, ALERT_AZIONI, ROLE_LABELS, formatDateTime } from "@/lib/labels";
import { PageHeader, Empty, ConfirmDialog } from "@/components/common";
import { ALERTS_EVENT } from "@/components/AppLayout";

const EXPECTED = "Verifica che questa persona debba essere amministratore della startup: prendi visione, oppure annulla l'invito o cambia il ruolo in Operativo startup.";

function AlertItem({ e, onAction }) {
  const h = e.handling;
  const canCancel = !h && e.target_status === "INVITATO";
  const canRole = !h && e.target_role === "ADMIN_STARTUP" && e.target_status !== "DISATTIVATO";
  return (
    <li className="flex gap-3 px-4 py-4" data-testid={`alert-${e.id}`}>
      {h ? <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-ok-fg" /> : <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-warn-fg" />}
      <div className="min-w-0 flex-1 text-sm">
        <div className="font-medium text-ink">
          {ACTION_LABELS[e.action]}: {e.target_name || e.details?.email} → {ROLE_LABELS[e.details?.to || e.details?.role]}
        </div>
        <div className="text-xs text-ink-muted">
          {formatDateTime(e.timestamp)} · da {e.actor_name}
          {e.startup_id && (e.startup_deleted ? <> · {e.startup_name} (eliminata)</>
            : <> · <Link to={`/startup/${e.startup_id}`} className="text-brand underline">{e.startup_name}</Link></>)}
        </div>
        {h ? (
          <div className="mt-2 text-xs text-ok-fg" data-testid={`alert-handled-${e.id}`}>
            Presa visione da {h.handled_by_name} il {formatDateTime(h.handled_at)}{h.azione !== "PRESA_VISIONE" ? ` (${ALERT_AZIONI[h.azione]})` : ""}
          </div>
        ) : (
          <>
            <p className="mt-2 rounded-md bg-warn-bg px-3 py-2 text-xs text-warn-fg" data-testid={`alert-expected-${e.id}`}>{EXPECTED}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button size="sm" onClick={() => onAction(e, "ack")} data-testid={`alert-ack-${e.id}`}>Preso visione</Button>
              {canCancel && <Button size="sm" variant="outline" onClick={() => onAction(e, "cancel")} data-testid={`alert-cancel-${e.id}`}>Annulla invito</Button>}
              {canRole && <Button size="sm" variant="outline" onClick={() => onAction(e, "role")} data-testid={`alert-role-${e.id}`}>Cambia ruolo</Button>}
            </div>
          </>
        )}
      </div>
    </li>
  );
}

const CONFIRM = {
  cancel: ["Annullare l'invito?", "Il link non sarà più valido e l'utente risulterà disattivato. Vale anche come presa visione."],
  role: ["Cambiare il ruolo in Operativo startup?", "L'utente perde i permessi di amministratore della startup. Vale anche come presa visione."],
};

export default function AlertsCenter() {
  const [items, setItems] = useState(null);
  const [tab, setTab] = useState("DA_GESTIRE");
  const [azione, setAzione] = useState("ALL");
  const [confirm, setConfirm] = useState(null);
  const load = useCallback(() => api.get("/alerts").then(({ data }) => setItems(data)), []);
  useEffect(() => {
    load();
  }, [load]);

  const run = async (e, kind) => {
    try {
      if (kind === "ack") await api.post(`/alerts/${e.id}/ack`);
      if (kind === "cancel") await api.post(`/alerts/${e.id}/cancel-invite`);
      if (kind === "role") await api.post(`/alerts/${e.id}/change-role`, { role: "OPERATIVO_STARTUP" });
      toast.success("Segnalazione gestita");
      window.dispatchEvent(new Event(ALERTS_EVENT));
      load();
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };
  const onAction = (e, kind) => (CONFIRM[kind] ? setConfirm({ e, kind }) : run(e, kind));

  const open = (items || []).filter((e) => !e.handling);
  const done = (items || []).filter((e) => e.handling && (azione === "ALL" || e.handling.azione === azione));
  const shown = tab === "DA_GESTIRE" ? open : done;

  return (
    <div>
      <PageHeader title="Segnalazioni" subtitle="Inviti e cambi di ruolo verso Amministratore startup: per ognuna è indicato cosa ci si aspetta da te" />
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList>
            <TabsTrigger value="DA_GESTIRE" data-testid="alerts-tab-open">Da gestire ({open.length})</TabsTrigger>
            <TabsTrigger value="GESTITE" data-testid="alerts-tab-done">Gestite</TabsTrigger>
          </TabsList>
        </Tabs>
        {tab === "GESTITE" && (
          <Select value={azione} onValueChange={setAzione}>
            <SelectTrigger className="bg-surface sm:w-56" data-testid="alerts-filter-azione"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">Tutte le azioni</SelectItem>
              {Object.entries(ALERT_AZIONI).map(([k, l]) => <SelectItem key={k} value={k}>{l}</SelectItem>)}
            </SelectContent>
          </Select>
        )}
      </div>
      {items === null ? <div className="text-sm text-ink-muted">Caricamento…</div> : !shown.length ? (
        <Empty testId="alerts-empty">{tab === "DA_GESTIRE" ? "Nessuna segnalazione da gestire." : "Nessuna segnalazione gestita."}</Empty>
      ) : (
        <ul className="divide-y rounded-lg border bg-surface shadow-card" data-testid="alerts-list">
          {shown.map((e) => <AlertItem key={e.id} e={e} onAction={onAction} />)}
        </ul>
      )}
      <ConfirmDialog open={!!confirm} onOpenChange={(o) => !o && setConfirm(null)} confirmLabel="Conferma"
        title={confirm && CONFIRM[confirm.kind][0]} description={confirm && CONFIRM[confirm.kind][1]}
        onConfirm={() => run(confirm.e, confirm.kind)} />
    </div>
  );
}
