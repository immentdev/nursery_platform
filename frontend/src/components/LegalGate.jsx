import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { LEGAL_TIPI, formatDateTime } from "@/lib/labels";
import { AuthShell } from "@/pages/LoginPage";

export default function LegalGate() {
  const { user, refresh, logout } = useAuth();
  const [docs, setDocs] = useState([]);
  const [open, setOpen] = useState(null);
  const [checked, setChecked] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get("/legal/current").then(({ data }) => setDocs(data));
  }, []);

  const pendingIds = user.pending_legal.map((d) => d.id);
  const accept = async () => {
    setBusy(true);
    try {
      await api.post("/legal/accept", { document_ids: pendingIds });
      toast.success("Accettazione registrata");
      await refresh();
    } catch (e) {
      toast.error(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Termini d'uso e informativa privacy"
      subtitle="Per usare la piattaforma devi leggere e accettare i documenti in vigore.">
      <ul className="mb-5 space-y-2" data-testid="legal-docs-list">
        {docs.map((d) => (
          <li key={d.id} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
            <span>{LEGAL_TIPI[d.tipo]} · v{d.versione}{pendingIds.includes(d.id) ? "" : " (già accettato)"}</span>
            <button type="button" className="text-brand underline" onClick={() => setOpen(d)} data-testid={`legal-read-${d.tipo}`}>Leggi</button>
          </li>
        ))}
      </ul>
      <label className="mb-5 flex items-start gap-2 text-sm">
        <Checkbox checked={checked} onCheckedChange={(v) => setChecked(!!v)} data-testid="legal-accept-checkbox" className="mt-0.5" />
        <span>Ho letto e accetto i termini d'uso e l'informativa privacy</span>
      </label>
      <Button className="w-full" disabled={!checked || busy} onClick={accept} data-testid="legal-accept-button">Accetta e continua</Button>
      <Button variant="ghost" className="mt-2 w-full" onClick={logout} data-testid="legal-logout-button">Esci</Button>
      <Dialog open={!!open} onOpenChange={(o) => !o && setOpen(null)}>
        <DialogContent className="max-h-[85vh] overflow-y-auto" data-testid="legal-text-dialog">
          <DialogHeader><DialogTitle>{open && `${LEGAL_TIPI[open.tipo]} · v${open.versione}`}</DialogTitle></DialogHeader>
          <p className="text-xs text-ink-muted">Pubblicato il {formatDateTime(open?.data_pubblicazione)}</p>
          <div className="whitespace-pre-wrap text-sm text-ink" data-testid="legal-text">{open?.testo}</div>
        </DialogContent>
      </Dialog>
    </AuthShell>
  );
}
