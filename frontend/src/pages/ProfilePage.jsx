import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { COMPETENCE, ROLE_LABELS } from "@/lib/labels";
import { Card, Field, PageHeader } from "@/components/common";

function PasswordForm() {
  const [f, setF] = useState({ current_password: "", new_password: "", confirm: "" });
  const submit = async (e) => {
    e.preventDefault();
    if (f.new_password !== f.confirm) {
      toast.error("Le due password non coincidono");
      return;
    }
    try {
      await api.post("/auth/change-password", { current_password: f.current_password, new_password: f.new_password });
      toast.success("Password aggiornata");
      setF({ current_password: "", new_password: "", confirm: "" });
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="space-y-1.5"><Label>Password attuale</Label><Input type="password" value={f.current_password} onChange={set("current_password")} required data-testid="pw-current" /></div>
      <div className="space-y-1.5"><Label>Nuova password</Label><Input type="password" value={f.new_password} onChange={set("new_password")} required data-testid="pw-new" />
        <p className="text-xs text-ink-muted">Almeno 8 caratteri, con lettere e numeri.</p></div>
      <div className="space-y-1.5"><Label>Conferma nuova password</Label><Input type="password" value={f.confirm} onChange={set("confirm")} required data-testid="pw-confirm" /></div>
      <Button type="submit" data-testid="pw-submit">Cambia password</Button>
    </form>
  );
}

export default function ProfilePage() {
  const { user, setUser } = useAuth();
  const [f, setF] = useState({ nome: user.nome, cognome: user.cognome, telefono: user.telefono || "" });
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const save = async (e) => {
    e.preventDefault();
    try {
      const { data } = await api.patch("/auth/me", f);
      setUser(data);
      toast.success("Profilo aggiornato");
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };
  return (
    <div>
      <PageHeader title="Area personale" subtitle="I tuoi dati e la sicurezza dell'account" />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Profilo">
          <dl className="mb-6 grid gap-4 sm:grid-cols-2">
            <Field label="Email" testId="profile-email">{user.email}</Field>
            <Field label="Ruolo" testId="profile-role">{ROLE_LABELS[user.role]}</Field>
            <Field label="Organizzazione" testId="profile-org">{user.organization?.name}</Field>
            {user.competence_areas?.length > 0 && <Field label="Aree di competenza">{user.competence_areas.map((a) => COMPETENCE[a]).join(", ")}</Field>}
          </dl>
          <form onSubmit={save} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5"><Label>Nome</Label><Input value={f.nome} onChange={set("nome")} data-testid="profile-nome" /></div>
              <div className="space-y-1.5"><Label>Cognome</Label><Input value={f.cognome} onChange={set("cognome")} data-testid="profile-cognome" /></div>
            </div>
            <div className="space-y-1.5"><Label>Telefono</Label><Input value={f.telefono} onChange={set("telefono")} data-testid="profile-telefono" /></div>
            <Button type="submit" data-testid="profile-save">Salva profilo</Button>
          </form>
        </Card>
        <Card title="Cambio password"><PasswordForm /></Card>
      </div>
    </div>
  );
}
