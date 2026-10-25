import { useCallback, useEffect, useState } from "react";
import { Search, UserPlus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { isNursery } from "@/lib/perms";
import { ORG_TYPE_LABELS, ROLE_LABELS, USER_STATUS } from "@/lib/labels";
import { PageHeader } from "@/components/common";
import UsersList from "@/components/UsersList";
import InviteUserDialog from "@/components/InviteUserDialog";
import InviteLinkDialog from "@/components/InviteLinkDialog";

const ALL = "ALL";

function Filter({ value, onChange, placeholder, options, testId }) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="bg-surface" data-testid={testId}><SelectValue /></SelectTrigger>
      <SelectContent>
        <SelectItem value={ALL}>{placeholder}</SelectItem>
        {options.map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}
      </SelectContent>
    </Select>
  );
}

export default function UsersPage() {
  const { user } = useAuth();
  const nursery = isNursery(user);
  const [users, setUsers] = useState([]);
  const [f, setF] = useState({ q: "", org_type: ALL, role: ALL, status: ALL });
  const [open, setOpen] = useState(false);
  const [invite, setInvite] = useState(null);

  const load = useCallback(() => {
    const params = Object.fromEntries(Object.entries(f).filter(([, v]) => v && v !== ALL));
    return api.get("/users", { params }).then(({ data }) => setUsers(data));
  }, [f]);

  useEffect(() => {
    const t = setTimeout(load, 200);
    return () => clearTimeout(t);
  }, [load]);

  const set = (k) => (v) => setF({ ...f, [k]: v });
  const fixedOrg = nursery ? null : user.organization;
  const orgTypeOf = (u) => u.organization_type || user.organization.type;

  return (
    <div>
      <PageHeader
        title="Utenti"
        subtitle={nursery ? "Utenti di tutte le organizzazioni" : `Utenti di ${user.organization.name}`}
        actions={<Button onClick={() => setOpen(true)} data-testid="invite-user-button"><UserPlus className="mr-2 h-4 w-4" />Invita utente</Button>}
      />
      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="relative sm:col-span-2 lg:col-span-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" />
          <Input className="bg-surface pl-9" placeholder="Cerca nome o email" value={f.q} onChange={(e) => set("q")(e.target.value)} data-testid="users-search-input" />
        </div>
        {nursery && <Filter value={f.org_type} onChange={set("org_type")} placeholder="Tutte le organizzazioni" options={Object.entries(ORG_TYPE_LABELS)} testId="users-filter-org-type" />}
        <Filter value={f.role} onChange={set("role")} placeholder="Tutti i ruoli" options={Object.entries(ROLE_LABELS)} testId="users-filter-role" />
        <Filter value={f.status} onChange={set("status")} placeholder="Tutti gli stati" options={Object.entries(USER_STATUS)} testId="users-filter-status" />
      </div>
      <UsersList users={users} orgTypeOf={orgTypeOf} showOrg={nursery} onChanged={load} />
      <InviteUserDialog open={open} onOpenChange={setOpen} fixedOrg={fixedOrg} onInvited={(d) => { setInvite(d); load(); }} />
      <InviteLinkDialog invite={invite} onClose={() => setInvite(null)} />
    </div>
  );
}
