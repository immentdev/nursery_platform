import { useState } from "react";
import { toast } from "sonner";
import { MoreHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { canManage } from "@/lib/perms";
import { COMPETENCE, ROLE_LABELS } from "@/lib/labels";
import { StatusBadge, Empty, ConfirmDialog } from "@/components/common";
import { EditUserDialog, RoleDialog } from "@/components/UserDialogs";
import InviteLinkDialog from "@/components/InviteLinkDialog";

function UserActions({ u, orgType, onEdit, onRole, onAction }) {
  const { user } = useAuth();
  if (!canManage(user, orgType, u.organization_id, u.role)) return null;
  const self = user.id === u.id;
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" data-testid={`user-actions-${u.id}`} aria-label="Azioni utente">
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => onEdit(u)} data-testid="user-action-edit">Modifica dati</DropdownMenuItem>
        {!self && <DropdownMenuItem onClick={() => onRole(u)} data-testid="user-action-role">Cambia ruolo</DropdownMenuItem>}
        {u.status === "INVITATO" && <DropdownMenuItem onClick={() => onAction(u, "regenerate")} data-testid="user-action-regenerate">Rigenera link di invito</DropdownMenuItem>}
        {!self && u.status !== "DISATTIVATO" && <DropdownMenuSeparator />}
        {!self && u.status === "INVITATO" && <DropdownMenuItem className="text-danger-fg" onClick={() => onAction(u, "cancel")} data-testid="user-action-cancel">Annulla invito</DropdownMenuItem>}
        {!self && u.status === "ATTIVO" && <DropdownMenuItem className="text-danger-fg" onClick={() => onAction(u, "deactivate")} data-testid="user-action-deactivate">Disattiva</DropdownMenuItem>}
        {u.status === "DISATTIVATO" && <DropdownMenuItem onClick={() => onAction(u, "reactivate")} data-testid="user-action-reactivate">Riattiva</DropdownMenuItem>}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

const CONFIRM = {
  cancel: { title: "Annullare l'invito?", text: "Il link di invito non sarà più valido e l'utente risulterà disattivato." },
  deactivate: { title: "Disattivare l'utente?", text: "L'utente non potrà più accedere alla piattaforma." },
};

export default function UsersList({ users, orgTypeOf, showOrg, onChanged }) {
  const [edit, setEdit] = useState(null);
  const [role, setRole] = useState(null);
  const [confirm, setConfirm] = useState(null);
  const [invite, setInvite] = useState(null);

  const run = async (u, kind) => {
    const path = { regenerate: "regenerate-invite", cancel: "deactivate", deactivate: "deactivate", reactivate: "reactivate" }[kind];
    try {
      const { data } = await api.post(`/users/${u.id}/${path}`);
      if (kind === "regenerate") setInvite(data);
      else toast.success("Operazione completata");
      onChanged();
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };
  const onAction = (u, kind) => (CONFIRM[kind] ? setConfirm({ u, kind }) : run(u, kind));

  if (!users.length) return <Empty testId="users-empty">Nessun utente trovato.</Empty>;
  return (
    <>
      <ul className="divide-y rounded-lg border bg-surface" data-testid="users-list">
        {users.map((u) => (
          <li key={u.id} className="flex items-start gap-3 px-4 py-3 sm:items-center" data-testid={`user-row-${u.id}`}>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-ink">{u.nome} {u.cognome}</span>
                <StatusBadge kind="user" value={u.status} testId={`user-status-${u.id}`} />
              </div>
              <div className="truncate text-sm text-ink-muted">{u.email}{u.telefono ? ` · ${u.telefono}` : ""}</div>
              <div className="mt-1 text-xs text-ink-soft">
                <span data-testid={`user-role-${u.id}`}>{ROLE_LABELS[u.role]}</span>
                {showOrg && u.organization_name ? ` · ${u.organization_name}` : ""}
                {u.competence_areas?.length ? ` · ${u.competence_areas.map((a) => COMPETENCE[a]).join(", ")}` : ""}
              </div>
            </div>
            <UserActions u={u} orgType={orgTypeOf(u)} onEdit={setEdit} onRole={setRole} onAction={onAction} />
          </li>
        ))}
      </ul>
      <EditUserDialog target={edit} orgType={edit && orgTypeOf(edit)} onClose={() => setEdit(null)} onSaved={onChanged} />
      <RoleDialog target={role} orgType={role && orgTypeOf(role)} onClose={() => setRole(null)} onSaved={onChanged} />
      <InviteLinkDialog invite={invite} onClose={() => setInvite(null)} />
      <ConfirmDialog
        open={!!confirm}
        onOpenChange={(o) => !o && setConfirm(null)}
        title={confirm && CONFIRM[confirm.kind].title}
        description={confirm && CONFIRM[confirm.kind].text}
        destructive
        onConfirm={() => run(confirm.u, confirm.kind)}
      />
    </>
  );
}
