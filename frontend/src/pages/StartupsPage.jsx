import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Search, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { isNursery } from "@/lib/perms";
import { SERVIZI, STATO_CLIENTE } from "@/lib/labels";
import { PageHeader, StatusBadge, Chip, Empty } from "@/components/common";

const ALL = "ALL";

function FilterSelect({ value, onChange, placeholder, options, testId }) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="bg-surface" data-testid={testId}><SelectValue placeholder={placeholder} /></SelectTrigger>
      <SelectContent>
        <SelectItem value={ALL}>{placeholder}</SelectItem>
        {options.map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}
      </SelectContent>
    </Select>
  );
}

function StartupRow({ s }) {
  return (
    <Link to={`/startup/${s.id}`} className="group flex items-center gap-4 px-4 py-4 transition-colors hover:bg-subtle" data-testid={`startup-row-${s.codice_breve}`}>
      <div className="w-16 shrink-0 font-mono text-sm font-medium text-brand">{s.codice_breve}</div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium text-ink">{s.denominazione}</span>
          <StatusBadge value={s.stato_cliente} />
        </div>
        <div className="mt-1 text-xs text-ink-muted">
          Provider: {s.provider_name || "nessuno"} · Referente: {s.referente_name || "—"}
        </div>
        <div className="mt-2 flex flex-wrap gap-1">{s.servizi_attivi.map((x) => <Chip key={x}>{SERVIZI[x]}</Chip>)}</div>
      </div>
      <ChevronRight className="h-4 w-4 shrink-0 text-ink-muted transition-transform group-hover:translate-x-0.5" />
    </Link>
  );
}

export default function StartupsPage() {
  const { user } = useAuth();
  const nursery = isNursery(user);
  const [items, setItems] = useState(null);
  const [lookups, setLookups] = useState({ providers: [], nursery_users: [] });
  const [f, setF] = useState({ q: "", stato_cliente: ALL, provider_organization_id: ALL, servizio: ALL, referente_nursery_user_id: ALL });

  useEffect(() => {
    if (nursery) api.get("/lookups").then(({ data }) => setLookups(data));
  }, [nursery]);

  useEffect(() => {
    const params = Object.fromEntries(Object.entries(f).filter(([, v]) => v && v !== ALL));
    const t = setTimeout(() => api.get("/startups", { params }).then(({ data }) => setItems(data)), 200);
    return () => clearTimeout(t);
  }, [f]);

  const referenti = useMemo(() => {
    if (nursery) return lookups.nursery_users.map((u) => [u.id, u.name]);
    const m = new Map((items || []).map((s) => [s.referente_nursery_user_id, s.referente_name]));
    return [...m.entries()];
  }, [nursery, lookups, items]);

  const set = (k) => (v) => setF({ ...f, [k]: v });

  return (
    <div>
      <PageHeader
        title="Startup"
        subtitle={nursery ? "Tutte le startup clienti di Nursery" : "Startup assegnate al tuo studio (sola lettura)"}
        actions={nursery && (
          <Button asChild data-testid="new-startup-button"><Link to="/startup/nuova"><Plus className="mr-2 h-4 w-4" />Nuova startup</Link></Button>
        )}
      />
      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <div className="relative sm:col-span-2 lg:col-span-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" />
          <Input className="bg-surface pl-9" placeholder="Cerca nome o codice" value={f.q} onChange={(e) => set("q")(e.target.value)} data-testid="startup-search-input" />
        </div>
        <FilterSelect value={f.stato_cliente} onChange={set("stato_cliente")} placeholder="Tutti gli stati" options={Object.entries(STATO_CLIENTE)} testId="filter-stato" />
        {nursery && (
          <FilterSelect value={f.provider_organization_id} onChange={set("provider_organization_id")} placeholder="Tutti i provider"
            options={[["NONE", "Senza provider"], ...lookups.providers.map((p) => [p.id, p.name])]} testId="filter-provider" />
        )}
        <FilterSelect value={f.servizio} onChange={set("servizio")} placeholder="Tutti i servizi" options={Object.entries(SERVIZI)} testId="filter-servizio" />
        <FilterSelect value={f.referente_nursery_user_id} onChange={set("referente_nursery_user_id")} placeholder="Tutti i referenti" options={referenti} testId="filter-referente" />
      </div>
      {items === null ? (
        <div className="text-sm text-ink-muted">Caricamento…</div>
      ) : items.length === 0 ? (
        <Empty testId="startups-empty">Nessuna startup corrisponde ai filtri.</Empty>
      ) : (
        <div className="divide-y overflow-hidden rounded-lg border bg-surface shadow-card" data-testid="startups-list">
          {items.map((s) => <StartupRow key={s.id} s={s} />)}
        </div>
      )}
      {items && <p className="mt-3 text-xs text-ink-muted" data-testid="startups-count">{items.length} startup</p>}
    </div>
  );
}
