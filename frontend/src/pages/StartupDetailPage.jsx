import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ExternalLink, Pencil, Trash2, UserPlus, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { isNursery, isAdminNursery, canManage } from "@/lib/perms";
import { REGIMI_IVA, SERVIZI, formatChiusura, formatDate } from "@/lib/labels";
import { Card, Field, PageHeader, StatusBadge, Chip, ConfirmDialog } from "@/components/common";
import EventTimeline from "@/components/EventTimeline";
import UsersList from "@/components/UsersList";
import InviteUserDialog from "@/components/InviteUserDialog";
import InviteLinkDialog from "@/components/InviteLinkDialog";
import ContattiDialog from "@/components/ContattiDialog";

function Anagrafica({ s }) {
  return (
    <Card>
      <dl className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <Field label="Denominazione" testId="field-denominazione">{s.denominazione}</Field>
        <Field label="Codice breve" testId="field-codice-breve"><span className="font-mono">{s.codice_breve}</span></Field>
        <Field label="Codice fiscale" testId="field-codice-fiscale"><span className="font-mono">{s.codice_fiscale}</span></Field>
        <Field label="Partita IVA" testId="field-partita-iva"><span className="font-mono">{s.partita_iva}</span></Field>
        <Field label="Sede legale" testId="field-sede">{s.sede_legale}</Field>
        <Field label="PEC" testId="field-pec">{s.pec}</Field>
        <Field label="Telefono" testId="field-telefono">{s.telefono || "—"}</Field>
        <Field label="Data di costituzione" testId="field-costituzione">{formatDate(s.data_costituzione)}</Field>
        <Field label="Startup innovativa" testId="field-innovativa">
          {s.startup_innovativa ? `Sì, iscritta dal ${formatDate(s.data_iscrizione_sezione_speciale)}` : "No"}
        </Field>
        <Field label="Chiusura esercizio" testId="field-chiusura">{formatChiusura(s.data_chiusura_esercizio)}</Field>
        <Field label="Regime IVA" testId="field-regime-iva">{REGIMI_IVA[s.regime_iva]}</Field>
        <Field label="Impresa Digitale" testId="field-impresa-digitale">
          {s.link_impresa_digitale ? <a href={s.link_impresa_digitale} target="_blank" rel="noreferrer" className="text-brand underline">{s.link_impresa_digitale}</a> : "—"}
        </Field>
      </dl>
    </Card>
  );
}

function Servizi({ s }) {
  return (
    <Card>
      <dl className="grid gap-6 sm:grid-cols-2">
        <Field label="Servizi attivi" testId="field-servizi">
          <div className="flex flex-wrap gap-1">{s.servizi_attivi.map((x) => <Chip key={x} testId={`servizio-${x}`}>{SERVIZI[x]}</Chip>)}</div>
        </Field>
        <Field label="Profilo di servizio" testId="field-profilo">{s.service_profile_name}</Field>
        <Field label="Provider" testId="field-provider">{s.provider_name || "Nessun provider (commercialista proprio)"}</Field>
        <Field label="Referente Nursery" testId="field-referente">{s.referente_name}</Field>
      </dl>
    </Card>
  );
}

export function StartupView({ id, home }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [s, setS] = useState(null);
  const [users, setUsers] = useState([]);
  const [events, setEvents] = useState([]);
  const [error, setError] = useState("");
  const [inviteOpen, setInviteOpen] = useState(false);
  const [invite, setInvite] = useState(null);
  const [contatti, setContatti] = useState(false);
  const [del, setDel] = useState(false);

  const load = useCallback(async () => {
    try {
      const [a, b, c] = await Promise.all([api.get(`/startups/${id}`), api.get(`/startups/${id}/users`), api.get(`/startups/${id}/events`)]);
      setS(a.data); setUsers(b.data); setEvents(c.data);
    } catch (e) {
      setError(errorMessage(e));
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  if (error) return <div className="rounded-md bg-danger-bg p-4 text-sm text-danger-fg" data-testid="startup-error">{error}</div>;
  if (!s) return <div className="text-sm text-ink-muted">Caricamento…</div>;

  const nursery = isNursery(user);
  const canInvite = canManage(user, "STARTUP", s.organization_id, "OPERATIVO_STARTUP");
  const canContatti = nursery || (user.role === "ADMIN_STARTUP" && user.organization_id === s.organization_id);
  const remove = async () => {
    try {
      await api.delete(`/startups/${s.id}`);
      toast.success("Startup eliminata");
      navigate("/startup");
    } catch (e) {
      toast.error(errorMessage(e));
    }
  };

  return (
    <div>
      {!home && (
        <Link to="/startup" className="mb-4 inline-flex items-center text-sm text-ink-muted hover:text-ink" data-testid="back-to-list">
          <ArrowLeft className="mr-1 h-4 w-4" /> Elenco startup
        </Link>
      )}
      <PageHeader
        title={<span className="flex flex-wrap items-center gap-3">{s.denominazione}<StatusBadge value={s.stato_cliente} testId="startup-stato-badge" /></span>}
        subtitle={<span className="font-mono">{s.codice_breve} · P.IVA {s.partita_iva}</span>}
        actions={<>
          {s.link_impresa_digitale && (
            <Button variant="outline" asChild data-testid="impresa-digitale-button">
              <a href={s.link_impresa_digitale} target="_blank" rel="noreferrer"><ExternalLink className="mr-2 h-4 w-4" />Impresa Digitale</a>
            </Button>
          )}
          {nursery && <Button asChild data-testid="edit-startup-button"><Link to={`/startup/${s.id}/modifica`}><Pencil className="mr-2 h-4 w-4" />Modifica</Link></Button>}
          {!nursery && canContatti && <Button onClick={() => setContatti(true)} data-testid="edit-contatti-button"><Pencil className="mr-2 h-4 w-4" />Modifica contatti</Button>}
          {isAdminNursery(user) && s.stato_cliente === "ONBOARDING" && (
            <Button variant="outline" className="text-danger-fg" onClick={() => setDel(true)} data-testid="delete-startup-button"><Trash2 className="mr-2 h-4 w-4" />Elimina</Button>
          )}
        </>}
      />
      <Tabs defaultValue="anagrafica">
        <TabsList className="mb-4 w-full justify-start overflow-x-auto sm:w-auto">
          <TabsTrigger value="anagrafica" data-testid="tab-anagrafica">Anagrafica</TabsTrigger>
          <TabsTrigger value="servizi" data-testid="tab-servizi">Servizi</TabsTrigger>
          <TabsTrigger value="utenti" data-testid="tab-utenti">Utenti ({users.length})</TabsTrigger>
          <TabsTrigger value="cronologia" data-testid="tab-cronologia">Cronologia</TabsTrigger>
        </TabsList>
        <TabsContent value="anagrafica"><Anagrafica s={s} /></TabsContent>
        <TabsContent value="servizi"><Servizi s={s} /></TabsContent>
        <TabsContent value="utenti">
          {canInvite && (
            <div className="mb-3 flex justify-end">
              <Button size="sm" onClick={() => setInviteOpen(true)} data-testid="startup-invite-user-button"><UserPlus className="mr-2 h-4 w-4" />Invita utente</Button>
            </div>
          )}
          <UsersList users={users} orgTypeOf={() => "STARTUP"} onChanged={load} />
        </TabsContent>
        <TabsContent value="cronologia"><Card><EventTimeline events={events} /></Card></TabsContent>
      </Tabs>
      <InviteUserDialog open={inviteOpen} onOpenChange={setInviteOpen}
        fixedOrg={{ id: s.organization_id, name: s.denominazione, type: "STARTUP" }} onInvited={(d) => { setInvite(d); load(); }} />
      <InviteLinkDialog invite={invite} onClose={() => setInvite(null)} />
      <ContattiDialog open={contatti} onOpenChange={setContatti} startup={s} onSaved={load} />
      <ConfirmDialog open={del} onOpenChange={setDel} title="Eliminare la startup?" destructive confirmLabel="Elimina"
        description="L'eliminazione è logica: il record resta nel database ed è registrata nella cronologia. Gli utenti della startup saranno disattivati."
        onConfirm={remove} />
    </div>
  );
}

export default function StartupDetailPage() {
  const { id } = useParams();
  return <StartupView id={id} />;
}
