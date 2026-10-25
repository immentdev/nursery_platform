import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { api, errorMessage } from "@/lib/api";
import { PageHeader, Empty, ConfirmDialog } from "@/components/common";

// Gestione elenco semplice (provider, profili di servizio) con crea/modifica/elimina logica.
export default function SimpleCrud({ title, subtitle, endpoint, params, fields, newLabel, testPrefix, renderMeta }) {
  const [items, setItems] = useState([]);
  const [edit, setEdit] = useState(null);
  const [del, setDel] = useState(null);

  const load = useCallback(() => api.get(endpoint, { params }).then(({ data }) => setItems(data)), [endpoint, params]);
  useEffect(() => {
    load();
  }, [load]);

  const empty = Object.fromEntries(fields.map((f) => [f.key, ""]));
  const save = async (e) => {
    e.preventDefault();
    try {
      const body = Object.fromEntries(fields.map((f) => [f.key, edit.form[f.key]]));
      if (edit.id) await api.put(`${endpoint}/${edit.id}`, body);
      else await api.post(endpoint, body);
      toast.success("Salvato");
      setEdit(null);
      load();
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };
  const remove = async () => {
    try {
      await api.delete(`${endpoint}/${del.id}`);
      toast.success("Eliminato");
      load();
    } catch (err) {
      toast.error(errorMessage(err), { duration: 8000 });
    }
  };

  return (
    <div>
      <PageHeader title={title} subtitle={subtitle}
        actions={<Button onClick={() => setEdit({ form: empty })} data-testid={`${testPrefix}-new-button`}><Plus className="mr-2 h-4 w-4" />{newLabel}</Button>} />
      {!items.length ? <Empty testId={`${testPrefix}-empty`}>Nessun elemento.</Empty> : (
        <ul className="divide-y rounded-lg border bg-surface shadow-card" data-testid={`${testPrefix}-list`}>
          {items.map((it) => (
            <li key={it.id} className="flex items-start gap-3 px-4 py-4" data-testid={`${testPrefix}-row-${it.id}`}>
              <div className="min-w-0 flex-1">
                <div className="font-medium text-ink">{it[fields[0].key]}</div>
                {renderMeta(it)}
              </div>
              <Button variant="ghost" size="icon" aria-label="Modifica" data-testid={`${testPrefix}-edit-${it.id}`}
                onClick={() => setEdit({ id: it.id, form: Object.fromEntries(fields.map((f) => [f.key, it[f.key] || ""])) })}>
                <Pencil className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="icon" aria-label="Elimina" className="text-danger-fg" data-testid={`${testPrefix}-delete-${it.id}`} onClick={() => setDel(it)}>
                <Trash2 className="h-4 w-4" />
              </Button>
            </li>
          ))}
        </ul>
      )}
      <Dialog open={!!edit} onOpenChange={(o) => !o && setEdit(null)}>
        <DialogContent data-testid={`${testPrefix}-dialog`}>
          <DialogHeader><DialogTitle>{edit?.id ? "Modifica" : newLabel}</DialogTitle></DialogHeader>
          {edit && (
            <form onSubmit={save} className="space-y-4">
              {fields.map((f) => (
                <div key={f.key} className="space-y-1.5">
                  <Label>{f.label}</Label>
                  {f.multiline
                    ? <Textarea value={edit.form[f.key]} onChange={(e) => setEdit({ ...edit, form: { ...edit.form, [f.key]: e.target.value } })} data-testid={`${testPrefix}-field-${f.key}`} />
                    : <Input value={edit.form[f.key]} onChange={(e) => setEdit({ ...edit, form: { ...edit.form, [f.key]: e.target.value } })} data-testid={`${testPrefix}-field-${f.key}`} />}
                </div>
              ))}
              <DialogFooter><Button type="submit" data-testid={`${testPrefix}-save`}>Salva</Button></DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>
      <ConfirmDialog open={!!del} onOpenChange={(o) => !o && setDel(null)} destructive confirmLabel="Elimina"
        title="Confermi l'eliminazione?"
        description="Eliminazione logica: è consentita solo se non ci sono startup non cessate collegate."
        onConfirm={remove} />
    </div>
  );
}
