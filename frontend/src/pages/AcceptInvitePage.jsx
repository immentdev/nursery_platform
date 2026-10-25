import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { formatDateTime } from "@/lib/labels";
import { AuthShell } from "./LoginPage";

export default function AcceptInvitePage({ mode }) {
  const reset = mode === "reset";
  const { token } = useParams();
  const { startSession } = useAuth();
  const navigate = useNavigate();
  const [info, setInfo] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.get(reset ? `/auth/reset/${token}` : `/auth/invitation/${token}`).then(({ data }) => setInfo(data)).catch((e) => setLoadError(errorMessage(e)));
  }, [token, reset]);

  const submit = async (e) => {
    e.preventDefault();
    if (pw !== pw2) {
      setError("Le due password non coincidono");
      return;
    }
    try {
      const { data } = await api.post(reset ? "/auth/reset-password" : "/auth/accept-invite", { token, password: pw });
      startSession(data);
      navigate("/");
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  if (loadError) {
    return (
      <AuthShell title={reset ? "Link non disponibile" : "Invito non disponibile"}>
        <p className="text-sm text-danger-fg" data-testid="invite-error">{loadError}</p>
        <Link to="/login" className="mt-4 inline-block text-sm text-brand underline" data-testid="invite-go-login">Vai al login</Link>
      </AuthShell>
    );
  }
  if (!info) return <AuthShell title="Verifica link…" />;

  const subtitle = reset
    ? `Imposta una nuova password per ${info.email}. Link valido fino al ${formatDateTime(info.expires_at)}.`
    : `Imposta la password per ${info.email} (${info.organization_name}). Invito valido fino al ${formatDateTime(info.expires_at)}.`;
  return (
    <AuthShell title={reset ? "Reimposta password" : `Benvenuto, ${info.nome}`} subtitle={subtitle}>
      <form onSubmit={submit} className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="pw">Nuova password</Label>
          <Input id="pw" type="password" value={pw} onChange={(e) => setPw(e.target.value)} required data-testid="invite-password-input" />
          <p className="text-xs text-ink-muted">Almeno 8 caratteri, con lettere e numeri.</p>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="pw2">Conferma password</Label>
          <Input id="pw2" type="password" value={pw2} onChange={(e) => setPw2(e.target.value)} required data-testid="invite-password-confirm-input" />
        </div>
        {error && <p className="rounded-md bg-danger-bg px-3 py-2 text-sm text-danger-fg" data-testid="invite-submit-error">{error}</p>}
        <Button type="submit" className="w-full" data-testid="invite-set-password-button">Imposta password e accedi</Button>
      </form>
    </AuthShell>
  );
}
