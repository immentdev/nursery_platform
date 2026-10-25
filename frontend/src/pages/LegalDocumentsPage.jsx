import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api, errorMessage } from "@/lib/api";
import { LEGAL_TIPI, formatDateTime } from "@/lib/labels";
import { Card, ConfirmDialog, PageHeader } from "@/components/common";
import { useAuth } from "@/context/AuthContext";

const docState = (d) => (!d.data_pubblicazione ? ["Bozza", "bg-warn-bg text-warn-fg"] : d.attivo ? ["In vigore", "bg-ok-bg text-ok-fg"] : ["Archiviata", "bg-neutral-bg text-neutral-fg"]);

function DocRow({ d, onEdit, onView, onPublish, onDelete }) {
  const [label, tone] = docState(d);
  const draft = !d.data_pubblicazione;
  return (
    <li className="flex flex-wrap items-center gap-3 px-4 py-3" data-testid={`legal-doc-${d.id}`}>
      <span className="font-mono text-sm text-ink">v{d.versione}</span>
      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${tone}`}>{label}</span>
      <span className="flex-1 text-xs text-ink-muted">{draft ? `Creata il ${formatDateTime(d.created_at)}` : `Pubblicata il ${formatDateTime(d.data_pubblicazione)}`}</span>
      <Button size="sm" variant="ghost" onClick={() => (draft ? onEdit(d) : onView(d))} data-testid={`legal-open-${d.id}`}>{draft ? "Modifica" : "Visualizza"}</Button>
      {draft && <Button size="sm" onClick={() => onPublish(d)} data-testid={`legal-publish-${d.id}`}>Pubblica</Button>}
      {draft && <Button size="sm" variant="ghost" className="text-danger-fg" onClick={() => onDelete(d)} data-testid={`legal-delete-${d.id}`}>Elimina</Button>}
    </li>
  );
}

export default function LegalDocumentsPage() {
  const [docs, setDocs] = useState([]);
  const [edit, setEdit] = useState(null);
  const [view, setView] = useState(null);
  const [confirm, setConfirm] = useState(null);
  const { refresh } = useAuth();
  const load = useCallback(() => api.get("/legal/documents").then(({ data }) => setDocs(data)), []);
  useEffect(() => {
    load();
  }, [load]);

  const save = async (e) => {
    e.preventDefault();
    try {
      const body = { tipo: edit.tipo, versione: edit.versione, testo: edit.testo };
      if (edit.id) await api.put(`/legal/documents/${edit.id}`, body);
      else await api.post("/legal/documents", body);
      toast.success("Bozza salvata");
      setEdit(null);
      load();
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };
  const run = async () => {
    try {
      if (confirm.kind === "publish") await api.post(`/legal/documents/${confirm.d.id}/publish`);
      else await api.delete(`/legal/documents/${confirm.d.id}`);
      toast.success(confirm.kind === "publish" ? "Versione pubblicata" : "Bozza eliminata");
      if (confirm.kind === "publish") await refresh();
      else load();
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  return (
    <div>
      <PageHeader title="Documenti legali" subtitle="Termini d'uso e informativa privacy: le nuove versioni nascono come bozza e vanno pubblicate"
        actions={<Button onClick={() => setEdit({ tipo: "TERMINI_USO", versione: "", testo: "" })} data-testid="legal-new-button"><Plus className="mr-2 h-4 w-4" />Nuova versione</Button>} />
      <div className="space-y-6">
        {Object.entries(LEGAL_TIPI).map(([tipo, label]) => (
          <Card key={tipo} title={label} testId={`legal-card-${tipo}`}>
            <ul className="-m-5 divide-y">
              {docs.filter((d) => d.tipo === tipo).map((d) => (
                <DocRow key={d.id} d={d} onEdit={(x) => setEdit({ ...x })} onView={setView}
                  onPublish={(x) => setConfirm({ kind: "publish", d: x })} onDelete={(x) => setConfirm({ kind: "delete", d: x })} />
              ))}
            </ul>
          </Card>
        ))}
      </div>
      <Dialog open={!!edit} onOpenChange={(o) => !o && setEdit(null)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto" data-testid="legal-edit-dialog">
          <DialogHeader><DialogTitle>{edit?.id ? "Modifica bozza" : "Nuova versione (bozza)"}</DialogTitle></DialogHeader>
          {edit && (
            <form onSubmit={save} className="space-y-4">
              <div className="space-y-1.5"><Label>Documento</Label>
                <Select value={edit.tipo} onValueChange={(v) => setEdit({ ...edit, tipo: v })}>
                  <SelectTrigger data-testid="legal-field-tipo"><SelectValue /></SelectTrigger>
                  <SelectContent>{Object.entries(LEGAL_TIPI).map(([k, l]) => <SelectItem key={k} value={k}>{l}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5"><Label>Versione</Label><Input value={edit.versione} onChange={(e) => setEdit({ ...edit, versione: e.target.value })} placeholder="es. 1.1" data-testid="legal-field-versione" /></div>
              <div className="space-y-1.5"><Label>Testo</Label><Textarea rows={12} value={edit.testo} onChange={(e) => setEdit({ ...edit, testo: e.target.value })} data-testid="legal-field-testo" /></div>
              <DialogFooter><Button type="submit" data-testid="legal-save">Salva bozza</Button></DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>
      <Dialog open={!!view} onOpenChange={(o) => !o && setView(null)}>
        <DialogContent className="max-h-[85vh] overflow-y-auto" data-testid="legal-view-dialog">
          <DialogHeader><DialogTitle>{view && `${LEGAL_TIPI[view.tipo]} · v${view.versione}`}</DialogTitle></DialogHeader>
          <div className="whitespace-pre-wrap text-sm">{view?.testo}</div>
        </DialogContent>
      </Dialog>
      <ConfirmDialog open={!!confirm} onOpenChange={(o) => !o && setConfirm(null)} onConfirm={run}
        destructive={confirm?.kind === "delete"} confirmLabel={confirm?.kind === "publish" ? "Pubblica" : "Elimina"}
        title={confirm?.kind === "publish" ? "Pubblicare questa versione?" : "Eliminare la bozza?"}
        description={confirm?.kind === "publish"
          ? "La versione diventa quella in vigore e non sarà più modificabile. Ogni utente dovrà accettarla al prossimo accesso."
          : "Eliminazione logica della bozza."} />
    </div>
  );
}
