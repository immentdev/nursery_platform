import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { canManage } from "@/lib/perms";
import { COMPETENCE, ROLES_BY_ORG_TYPE, ROLE_LABELS } from "@/lib/labels";

export function EditUserDialog({ target, orgType, onClose, onSaved }) {
  const [form, setForm] = useState(null);
  useEffect(() => {
    if (target) setForm({ nome: target.nome, cognome: target.cognome, telefono: target.telefono || "", competence_areas: target.competence_areas || [] });
  }, [target]);
  if (!target || !form) return null;
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const toggle = (a) => setForm({
    ...form,
    competence_areas: form.competence_areas.includes(a) ? form.competence_areas.filter((x) => x !== a) : [...form.competence_areas, a],
  });
  const save = async (e) => {
    e.preventDefault();
    try {
      await api.patch(`/users/${target.id}`, form);
      toast.success("Dati utente aggiornati");
      onSaved();
      onClose();
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="edit-user-dialog">
        <DialogHeader>
          <DialogTitle>Modifica utente</DialogTitle>
          <DialogDescription>{target.email}</DialogDescription>
        </DialogHeader>
        <form onSubmit={save} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5"><Label>Nome</Label><Input value={form.nome} onChange={set("nome")} data-testid="edit-user-nome" /></div>
            <div className="space-y-1.5"><Label>Cognome</Label><Input value={form.cognome} onChange={set("cognome")} data-testid="edit-user-cognome" /></div>
          </div>
          <div className="space-y-1.5"><Label>Telefono</Label><Input value={form.telefono} onChange={set("telefono")} data-testid="edit-user-telefono" /></div>
          {orgType === "PROVIDER" && (
            <div className="flex gap-6">
              {Object.entries(COMPETENCE).map(([k, l]) => (
                <label key={k} className="flex items-center gap-2 text-sm">
                  <Checkbox checked={form.competence_areas.includes(k)} onCheckedChange={() => toggle(k)} data-testid={`edit-user-area-${k}`} />{l}
                </label>
              ))}
            </div>
          )}
          <DialogFooter><Button type="submit" data-testid="edit-user-save">Salva</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function RoleDialog({ target, orgType, onClose, onSaved }) {
  const { user } = useAuth();
  const [role, setRole] = useState("");
  useEffect(() => {
    if (target) setRole(target.role);
  }, [target]);
  if (!target) return null;
  const roles = ROLES_BY_ORG_TYPE[orgType].filter((r) => canManage(user, orgType, target.organization_id, r));
  const save = async () => {
    try {
      await api.post(`/users/${target.id}/role`, { role });
      toast.success("Ruolo aggiornato");
      onSaved();
      onClose();
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="role-dialog">
        <DialogHeader>
          <DialogTitle>Cambia ruolo</DialogTitle>
          <DialogDescription>{target.nome} {target.cognome} · {target.email}</DialogDescription>
        </DialogHeader>
        <Select value={role} onValueChange={setRole}>
          <SelectTrigger data-testid="role-select"><SelectValue /></SelectTrigger>
          <SelectContent>{roles.map((r) => <SelectItem key={r} value={r}>{ROLE_LABELS[r]}</SelectItem>)}</SelectContent>
        </Select>
        <DialogFooter><Button onClick={save} disabled={role === target.role} data-testid="role-save">Salva ruolo</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
