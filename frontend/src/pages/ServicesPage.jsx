import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api, errorMessage } from "@/lib/api";
import { CATEGORIE } from "@/lib/labels";
import { Chip, ConfirmDialog, Empty, PageHeader } from "@/components/common";
import { MultiSelect } from "@/components/Pickers";

const EMPTY = { codice: "", nome: "", descrizione: "", categoria: "SERVIZIO_NURSERY", richiede_provider: false, servizi_incompatibili: [], attivo: true, ordine: 0 };

function ServiceForm({ edit, setEdit, services, onSave }) {
  const set = (k) => (v) => setEdit({ ...edit, [k]: v?.target ? v.target.value : v });
  const toggle = (id) => set("servizi_incompatibili")(edit.servizi_incompatibili.includes(id)
    ? edit.servizi_incompatibili.filter((x) => x !== id) : [...edit.servizi_incompatibili, id]);
  return (
    <form onSubmit={onSave} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5"><Label>Codice</Label>
          <Input value={edit.codice} disabled={!!edit.id} className="font-mono" onChange={(e) => set("codice")(e.target.value.toUpperCase())} data-testid="service-field-codice" />
          <p className="text-xs text-ink-muted">Maiuscolo, univoco, non modificabile dopo la creazione.</p></div>
        <div className="space-y-1.5"><Label>Nome</Label><Input value={edit.nome} onChange={set("nome")} data-testid="service-field-nome" /></div>
      </div>
      <div className="space-y-1.5"><Label>Descrizione</Label><Textarea value={edit.descrizione} onChange={set("descrizione")} data-testid="service-field-descrizione" /></div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5"><Label>Categoria</Label>
          <Select value={edit.categoria} onValueChange={set("categoria")}>
            <SelectTrigger data-testid="service-field-categoria"><SelectValue /></SelectTrigger>
            <SelectContent>{Object.entries(CATEGORIE).map(([k, l]) => <SelectItem key={k} value={k}>{l}</SelectItem>)}</SelectContent>
          </Select></div>
        <div className="space-y-1.5"><Label>Ordine di visualizzazione</Label>
          <Input type="number" value={edit.ordine} onChange={(e) => set("ordine")(Number(e.target.value))} data-testid="service-field-ordine" /></div>
      </div>
      <div className="space-y-1.5"><Label>Servizi incompatibili (relazione reciproca)</Label>
        <MultiSelect options={services.filter((s) => s.id !== edit.id).map((s) => ({ value: s.id, label: s.nome, hint: s.attivo ? s.codice : "disattivato" }))}
          selected={edit.servizi_incompatibili} onToggle={toggle} placeholder="Nessuno" testId="service-field-incompatibili" /></div>
      <label className="flex items-center gap-3 text-sm"><Switch checked={edit.richiede_provider} onCheckedChange={set("richiede_provider")} data-testid="service-field-richiede-provider" />Richiede un provider assegnato</label>
      <label className="flex items-center gap-3 text-sm"><Switch checked={edit.attivo} onCheckedChange={set("attivo")} data-testid="service-field-attivo" />Attivo (selezionabile per nuove assegnazioni)</label>
      <DialogFooter><Button type="submit" data-testid="service-save">Salva</Button></DialogFooter>
    </form>
  );
}

export default function ServicesPage() {
  const [items, setItems] = useState([]);
  const [edit, setEdit] = useState(null);
  const [del, setDel] = useState(null);
  const load = useCallback(() => api.get("/services").then(({ data }) => setItems(data)), []);
  useEffect(() => {
    load();
  }, [load]);
  const names = Object.fromEntries(items.map((s) => [s.id, s.nome]));

  const save = async (e) => {
    e.preventDefault();
    try {
      const { id, ...body } = edit;
      const payload = Object.fromEntries(Object.keys(EMPTY).map((k) => [k, body[k]]));
      if (id) await api.put(`/services/${id}`, payload);
      else await api.post("/services", payload);
      toast.success("Servizio salvato");
      setEdit(null);
      load();
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };
  const remove = async () => {
    try {
      await api.delete(`/services/${del.id}`);
      toast.success("Servizio eliminato");
      load();
    } catch (err) {
      toast.error(errorMessage(err), { duration: 8000 });
    }
  };

  return (
    <div>
      <PageHeader title="Servizi" subtitle="Catalogo dei servizi assegnabili alle startup e relative regole"
        actions={<Button onClick={() => setEdit({ ...EMPTY })} data-testid="service-new-button"><Plus className="mr-2 h-4 w-4" />Nuovo servizio</Button>} />
      {!items.length ? <Empty testId="services-empty">Nessun servizio.</Empty> : (
        <ul className="divide-y rounded-lg border bg-surface shadow-card" data-testid="services-list">
          {items.map((s) => (
            <li key={s.id} className="flex items-start gap-3 px-4 py-4" data-testid={`service-row-${s.codice}`}>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-ink">{s.nome}</span>
                  <span className="font-mono text-xs text-ink-muted">{s.codice}</span>
                  {!s.attivo && <span className="rounded-full bg-danger-bg px-2 py-0.5 text-xs text-danger-fg" data-testid={`service-inactive-${s.codice}`}>Disattivato</span>}
                </div>
                {s.descrizione && <div className="mt-1 text-sm text-ink-soft">{s.descrizione}</div>}
                <div className="mt-2 flex flex-wrap gap-1">
                  <Chip>{CATEGORIE[s.categoria]}</Chip>
                  {s.richiede_provider && <Chip>Richiede provider</Chip>}
                  {s.servizi_incompatibili.map((i) => <Chip key={i}>Incompatibile con {names[i]}</Chip>)}
                </div>
                <div className="mt-1 text-xs text-ink-muted">Ordine {s.ordine} · {s.startup_count} startup non cessate collegate</div>
              </div>
              <Button variant="ghost" size="icon" aria-label="Modifica" onClick={() => setEdit({ ...s })} data-testid={`service-edit-${s.codice}`}><Pencil className="h-4 w-4" /></Button>
              <Button variant="ghost" size="icon" aria-label="Elimina" className="text-danger-fg" onClick={() => setDel(s)} data-testid={`service-delete-${s.codice}`}><Trash2 className="h-4 w-4" /></Button>
            </li>
          ))}
        </ul>
      )}
      <Dialog open={!!edit} onOpenChange={(o) => !o && setEdit(null)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto" data-testid="service-dialog">
          <DialogHeader><DialogTitle>{edit?.id ? "Modifica servizio" : "Nuovo servizio"}</DialogTitle></DialogHeader>
          {edit && <ServiceForm edit={edit} setEdit={setEdit} services={items} onSave={save} />}
        </DialogContent>
      </Dialog>
      <ConfirmDialog open={!!del} onOpenChange={(o) => !o && setDel(null)} destructive confirmLabel="Elimina" onConfirm={remove}
        title="Eliminare il servizio?" description="Eliminazione logica, consentita solo se il servizio non è collegato a startup non cessate. Altrimenti puoi solo disattivarlo." />
    </div>
  );
}
