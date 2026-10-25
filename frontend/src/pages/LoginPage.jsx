import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { errorMessage } from "@/lib/api";

export function AuthShell({ title, subtitle, children }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4 py-10">
      <div className="w-full max-w-md fade-in">
        <div className="mb-8">
          <div className="font-heading text-2xl font-semibold text-brand">Nursery</div>
          <div className="text-sm text-ink-muted">Amministrazione, finanza e controllo per startup</div>
        </div>
        <div className="rounded-lg border bg-surface p-6 shadow-card sm:p-8">
          <h1 className="text-xl font-semibold text-ink">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-ink-muted">{subtitle}</p>}
          <div className="mt-6">{children}</div>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [forgot, setForgot] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Accedi" subtitle="Usa le credenziali ricevute con l'invito.">
      <form onSubmit={submit} className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required data-testid="login-email-input" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="password">Password</Label>
          <Input id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required data-testid="login-password-input" />
        </div>
        {error && <p className="rounded-md bg-danger-bg px-3 py-2 text-sm text-danger-fg" data-testid="login-error">{error}</p>}
        <Button type="submit" className="w-full" disabled={busy} data-testid="login-submit-button">
          {busy ? "Accesso in corso…" : "Accedi"}
        </Button>
        <button type="button" className="text-sm text-brand underline" onClick={() => setForgot(!forgot)} data-testid="forgot-password-link">
          Password dimenticata?
        </button>
        {forgot && (
          <p className="rounded-md bg-brand-soft px-3 py-2 text-sm text-brand" data-testid="forgot-password-message">
            Contatta il tuo referente Nursery o l'amministratore della tua startup per ricevere un link di reimpostazione.
          </p>
        )}
      </form>
    </AuthShell>
  );
}
