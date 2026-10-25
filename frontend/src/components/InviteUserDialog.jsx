import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { canManage } from "@/lib/perms";
import { COMPETENCE, ORG_TYPE_LABELS, ROLES_BY_ORG_TYPE, ROLE_LABELS } from "@/lib/labels";

const EMPTY = { nome: "", cognome: "", email: "", telefono: "", role: "", competence_areas: [] };

export default function InviteUserDialog({ open, onOpenChange, fixedOrg, onInvited }) {
  const { user } = useAuth();
  const [orgs, setOrgs] = useState([]);
  const [orgId, setOrgId] = useState("");
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    setForm(EMPTY);
    if (fixedOrg) {
      setOrgs([fixedOrg]);
      setOrgId(fixedOrg.id);
    } else {
      setOrgId("");
      api.get("/organizations").then(({ data }) => setOrgs(data));
    }
  }, [open, fixedOrg]);

  const org = orgs.find((o) => o.id === orgId);
  const roles = org ? ROLES_BY_ORG_TYPE[org.type].filter((r) => canManage(user, org.type, org.id, r)) : [];
  const manageableOrgs = orgs.filter((o) => ROLES_BY_ORG_TYPE[o.type].some((r) => canManage(user, o.type, o.id, r)));
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const toggleArea = (a) => setForm({
    ...form,
    competence_areas: form.competence_areas.includes(a) ? form.competence_areas.filter((x) => x !== a) : [...form.competence_areas, a],
  });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const { data } = await api.post("/users", { ...form, organization_id: orgId });
      toast.success("Invito creato");
      onOpenChange(false);
      onInvited(data);
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto" data-testid="invite-user-dialog">
        <DialogHeader><DialogTitle>Invita utente</DialogTitle></DialogHeader>
        <form onSubmit={submit} className="space-y-4">
          <div className="space-y-1.5">
            <Label>Organizzazione</Label>
            <Select value={orgId} onValueChange={(v) => { setOrgId(v); setForm({ ...form, role: "", competence_areas: [] }); }} disabled={!!fixedOrg}>
              <SelectTrigger data-testid="invite-org-select"><SelectValue placeholder="Seleziona organizzazione" /></SelectTrigger>
              <SelectContent>
                {manageableOrgs.map((o) => (
                  <SelectItem key={o.id} value={o.id}>{o.name} · {ORG_TYPE_LABELS[o.type]}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Ruolo</Label>
            <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })} disabled={!org}>
              <SelectTrigger data-testid="invite-role-select"><SelectValue placeholder="Seleziona ruolo" /></SelectTrigger>
              <SelectContent>
                {roles.map((r) => <SelectItem key={r} value={r}>{ROLE_LABELS[r]}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5"><Label>Nome</Label><Input value={form.nome} onChange={set("nome")} required data-testid="invite-nome-input" /></div>
            <div className="space-y-1.5"><Label>Cognome</Label><Input value={form.cognome} onChange={set("cognome")} required data-testid="invite-cognome-input" /></div>
          </div>
          <div className="space-y-1.5"><Label>Email</Label><Input type="email" value={form.email} onChange={set("email")} required data-testid="invite-email-input" /></div>
          <div className="space-y-1.5"><Label>Telefono (facoltativo)</Label><Input value={form.telefono} onChange={set("telefono")} data-testid="invite-telefono-input" /></div>
          {org?.type === "PROVIDER" && (
            <div className="space-y-2">
              <Label>Aree di competenza</Label>
              <div className="flex gap-6">
                {Object.entries(COMPETENCE).map(([k, l]) => (
                  <label key={k} className="flex items-center gap-2 text-sm">
                    <Checkbox checked={form.competence_areas.includes(k)} onCheckedChange={() => toggleArea(k)} data-testid={`invite-area-${k}`} />
                    {l}
                  </label>
                ))}
              </div>
            </div>
          )}
          <DialogFooter>
            <Button type="submit" disabled={busy || !orgId || !form.role} data-testid="invite-submit-button">
              {busy ? "Creazione…" : "Crea invito"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
