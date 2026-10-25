import { STATO_CLIENTE, USER_STATUS } from "@/lib/labels";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";

const TONES = {
  ATTIVO: "bg-ok-bg text-ok-fg",
  ONBOARDING: "bg-brand-soft text-brand",
  INVITATO: "bg-warn-bg text-warn-fg",
  SOSPESO: "bg-warn-bg text-warn-fg",
  CESSATO: "bg-neutral-bg text-neutral-fg",
  DISATTIVATO: "bg-danger-bg text-danger-fg",
};

export const StatusBadge = ({ value, kind = "stato", testId }) => (
  <span
    data-testid={testId}
    className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${TONES[value] || "bg-neutral-bg text-neutral-fg"}`}
  >
    {(kind === "user" ? USER_STATUS : STATO_CLIENTE)[value] || value}
  </span>
);

export const Chip = ({ children, testId }) => (
  <span data-testid={testId} className="inline-flex items-center rounded-md border bg-subtle px-2 py-0.5 text-xs text-ink-soft">
    {children}
  </span>
);

export const PageHeader = ({ title, subtitle, actions }) => (
  <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
    <div>
      <h1 className="text-2xl font-semibold tracking-tight text-ink sm:text-3xl" data-testid="page-title">{title}</h1>
      {subtitle && <p className="mt-1 text-sm text-ink-muted">{subtitle}</p>}
    </div>
    {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
  </div>
);

export const Card = ({ title, actions, children, className = "", testId }) => (
  <section data-testid={testId} className={`rounded-lg border bg-surface shadow-card ${className}`}>
    {title && (
      <div className="flex items-center justify-between border-b px-5 py-4">
        <h2 className="text-base font-semibold text-ink">{title}</h2>
        {actions}
      </div>
    )}
    <div className="p-5">{children}</div>
  </section>
);

export const Field = ({ label, children, testId }) => (
  <div>
    <dt className="text-xs font-medium uppercase tracking-wide text-ink-muted">{label}</dt>
    <dd className="mt-1 break-words text-sm text-ink" data-testid={testId}>{children}</dd>
  </div>
);

export const Empty = ({ children, testId }) => (
  <div data-testid={testId} className="rounded-lg border border-dashed bg-surface px-6 py-12 text-center text-sm text-ink-muted">
    {children}
  </div>
);

export function ConfirmDialog({ open, onOpenChange, title, description, confirmLabel = "Conferma", onConfirm, destructive }) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent data-testid="confirm-dialog">
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel data-testid="confirm-cancel">Annulla</AlertDialogCancel>
          <AlertDialogAction
            data-testid="confirm-ok"
            className={destructive ? "bg-danger-fg text-brand-fg hover:bg-danger-fg/90" : ""}
            onClick={onConfirm}
          >
            {confirmLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
