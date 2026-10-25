import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api, errorMessage } from "@/lib/api";
import { REGIMI_IVA, STATO_CLIENTE } from "@/lib/labels";
import ServicesEditor from "@/components/ServicesEditor";
import { Card, PageHeader } from "@/components/common";

const EMPTY = {
  denominazione: "", codice_breve: "", codice_fiscale: "", partita_iva: "", sede_legale: "", pec: "", telefono: "",
  data_costituzione: "", startup_innovativa: false, data_iscrizione_sezione_speciale: "", chiusura: "31/12",
  regime_iva: "", provider_organization_id: "NONE", service_profile_id: "", servizi: [],
  referente_nursery_user_id: "", link_portale_provider: "", stato_cliente: "ONBOARDING",
};

const toForm = (s) => {
  const [m, d] = s.data_chiusura_esercizio.split("-");
  return { ...EMPTY, ...s, telefono: s.telefono || "", data_iscrizione_sezione_speciale: s.data_iscrizione_sezione_speciale || "",
    link_portale_provider: s.link_portale_provider || "", provider_organization_id: s.provider_organization_id || "NONE", chiusura: `${d}/${m}`,
    servizi: s.servizi.map((r) => ({ id: r.id, service_id: r.service_id, data_attivazione: r.data_attivazione, data_cessazione: r.data_cessazione || "" })) };
};

const toPayload = (f) => {
  const [d = "", m = ""] = f.chiusura.split("/");
  const { chiusura, ...rest } = f;
  const keys = Object.keys(EMPTY).filter((k) => k !== "chiusura");
  const out = Object.fromEntries(keys.map((k) => [k, rest[k]]));
  return { ...out, provider_organization_id: f.provider_organization_id === "NONE" ? null : f.provider_organization_id,
    servizi: f.servizi.map((r) => ({ id: r.id || null, service_id: r.service_id, data_attivazione: r.data_attivazione, data_cessazione: r.data_cessazione || null })),
    data_chiusura_esercizio: `${m.padStart(2, "0")}-${d.padStart(2, "0")}` };
};

function F({ label, children, hint }) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {children}
      {hint && <p className="text-xs text-ink-muted">{hint}</p>}
    </div>
  );
}

function Sel({ value, onChange, options, placeholder, testId }) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger data-testid={testId}><SelectValue placeholder={placeholder} /></SelectTrigger>
      <SelectContent>{options.map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}</SelectContent>
    </Select>
  );
}

export default function StartupFormPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [f, setF] = useState(id ? null : EMPTY);
  const [lk, setLk] = useState({ providers: [], service_profiles: [], nursery_users: [] });
  const [catalog, setCatalog] = useState([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get("/lookups").then(({ data }) => setLk(data));
    api.get("/services").then(({ data }) => setCatalog(data));
    if (id) api.get(`/startups/${id}`).then(({ data }) => setF(toForm(data)));
  }, [id]);

  if (!f) return <div className="text-sm text-ink-muted">Caricamento…</div>;
  const set = (k) => (e) => setF({ ...f, [k]: e?.target ? e.target.value : e });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const payload = toPayload(f);
      const { data } = id ? await api.put(`/startups/${id}`, payload) : await api.post("/startups", payload);
      toast.success(id ? "Startup aggiornata" : "Startup creata");
      navigate(`/startup/${data.id}`);
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} data-testid="startup-form">
      <Link to={id ? `/startup/${id}` : "/startup"} className="mb-4 inline-flex items-center text-sm text-ink-muted hover:text-ink"><ArrowLeft className="mr-1 h-4 w-4" />Indietro</Link>
      <PageHeader title={id ? "Modifica startup" : "Nuova startup"} />
      <div className="space-y-6">
        <Card title="Dati anagrafici">
          <div className="grid gap-4 sm:grid-cols-2">
            <F label="Denominazione"><Input value={f.denominazione} onChange={set("denominazione")} data-testid="form-denominazione" /></F>
            <F label="Codice breve" hint="Da 3 a 6 lettere maiuscole, univoco. Usato nei nomi dei file.">
              <Input value={f.codice_breve} maxLength={6} onChange={(e) => setF({ ...f, codice_breve: e.target.value.toUpperCase().replace(/[^A-Z]/g, "") })} className="font-mono" data-testid="form-codice-breve" />
            </F>
            <F label="Codice fiscale"><Input value={f.codice_fiscale} inputMode="numeric" onChange={set("codice_fiscale")} className="font-mono" data-testid="form-codice-fiscale" /></F>
            <F label="Partita IVA"><Input value={f.partita_iva} inputMode="numeric" onChange={set("partita_iva")} className="font-mono" data-testid="form-partita-iva" /></F>
            <F label="Sede legale"><Input value={f.sede_legale} onChange={set("sede_legale")} data-testid="form-sede" /></F>
            <F label="PEC"><Input type="email" value={f.pec} onChange={set("pec")} data-testid="form-pec" /></F>
            <F label="Telefono (facoltativo)"><Input value={f.telefono} onChange={set("telefono")} data-testid="form-telefono" /></F>
            <F label="Data di costituzione"><Input type="date" value={f.data_costituzione} onChange={set("data_costituzione")} data-testid="form-costituzione" /></F>
            <F label="Link al portale del provider (facoltativo)" hint="Il pulsante mostra il nome del portale del provider assegnato."><Input value={f.link_portale_provider} placeholder="https://" onChange={set("link_portale_provider")} data-testid="form-link-portale" /></F>
          </div>
        </Card>
        <Card title="Dati fiscali">
          <div className="grid gap-4 sm:grid-cols-2">
            <F label="Regime IVA"><Sel value={f.regime_iva} onChange={set("regime_iva")} options={Object.entries(REGIMI_IVA)} placeholder="Seleziona" testId="form-regime-iva" /></F>
            <F label="Chiusura esercizio (gg/mm)"><Input value={f.chiusura} onChange={set("chiusura")} placeholder="31/12" data-testid="form-chiusura" /></F>
            <div className="flex items-center gap-3 sm:col-span-2">
              <Switch checked={f.startup_innovativa} onCheckedChange={set("startup_innovativa")} data-testid="form-innovativa" />
              <Label>Startup innovativa</Label>
            </div>
            {f.startup_innovativa && (
              <F label="Data iscrizione sezione speciale"><Input type="date" value={f.data_iscrizione_sezione_speciale} onChange={set("data_iscrizione_sezione_speciale")} data-testid="form-data-iscrizione" /></F>
            )}
          </div>
        </Card>
        <Card title="Servizi e assegnazioni">
          <div className="space-y-5">
            <div>
              <Label>Servizi</Label>
              <div className="mt-2">
                <ServicesEditor value={f.servizi} onChange={(v) => setF({ ...f, servizi: v })} catalog={catalog} />
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <F label="Provider"><Sel value={f.provider_organization_id} onChange={set("provider_organization_id")} options={[["NONE", "Nessun provider"], ...lk.providers.map((p) => [p.id, p.name])]} testId="form-provider" /></F>
              <F label="Profilo di servizio"><Sel value={f.service_profile_id} onChange={set("service_profile_id")} options={lk.service_profiles.map((p) => [p.id, p.nome])} placeholder="Seleziona" testId="form-profilo" /></F>
              <F label="Referente Nursery"><Sel value={f.referente_nursery_user_id} onChange={set("referente_nursery_user_id")} options={lk.nursery_users.map((u) => [u.id, u.name])} placeholder="Seleziona" testId="form-referente" /></F>
              <F label="Stato cliente"><Sel value={f.stato_cliente} onChange={set("stato_cliente")} options={Object.entries(STATO_CLIENTE)} testId="form-stato" /></F>
            </div>
          </div>
        </Card>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={() => navigate(-1)} data-testid="form-cancel">Annulla</Button>
          <Button type="submit" disabled={busy} data-testid="form-submit">{busy ? "Salvataggio…" : "Salva"}</Button>
        </div>
      </div>
    </form>
  );
}
