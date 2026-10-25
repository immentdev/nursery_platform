import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { Building2, Users, Briefcase, Layers, UserCircle, LogOut, Menu, Bell, Home } from "lucide-react";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { isNursery, isProvider, isAdminNursery, canManageUsers } from "@/lib/perms";
import { ROLE_LABELS } from "@/lib/labels";

function navItems(u) {
  const items = [];
  if (isNursery(u) || isProvider(u)) items.push({ to: "/startup", label: "Startup", icon: Building2, id: "startup" });
  else items.push({ to: "/mia-startup", label: "La mia startup", icon: Home, id: "mia-startup" });
  if (canManageUsers(u)) items.push({ to: "/utenti", label: "Utenti", icon: Users, id: "utenti" });
  if (isNursery(u)) items.push({ to: "/segnalazioni", label: "Segnalazioni", icon: Bell, id: "segnalazioni" });
  if (isAdminNursery(u)) {
    items.push({ to: "/provider", label: "Provider", icon: Briefcase, id: "provider" });
    items.push({ to: "/profili", label: "Profili di servizio", icon: Layers, id: "profili" });
  }
  items.push({ to: "/profilo", label: "Area personale", icon: UserCircle, id: "profilo" });
  return items;
}

function SideNav({ onNavigate }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  return (
    <div className="flex h-full flex-col">
      <div className="px-5 py-6">
        <div className="font-heading text-xl font-semibold text-brand" data-testid="brand-name">Nursery</div>
        <div className="text-xs text-ink-muted">Piattaforma collaborativa</div>
      </div>
      <nav className="flex-1 space-y-1 px-3">
        {navItems(user).map(({ to, label, icon: Icon, id }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onNavigate}
            data-testid={`nav-${id}`}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                isActive ? "bg-brand-soft font-medium text-brand" : "text-ink-soft hover:bg-subtle hover:text-ink"
              }`
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t px-5 py-4">
        <div className="truncate text-sm font-medium text-ink" data-testid="current-user-name">{user.nome} {user.cognome}</div>
        <div className="truncate text-xs text-ink-muted" data-testid="current-user-role">{ROLE_LABELS[user.role]} · {user.organization?.name}</div>
        <Button
          variant="ghost"
          size="sm"
          className="mt-3 w-full justify-start px-2 text-ink-soft"
          data-testid="logout-button"
          onClick={() => { logout(); navigate("/login"); }}
        >
          <LogOut className="mr-2 h-4 w-4" /> Esci
        </Button>
      </div>
    </div>
  );
}

export default function AppLayout({ children }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="min-h-screen bg-canvas">
      <aside className="fixed inset-y-0 left-0 hidden w-sidebar border-r bg-surface md:block">
        <SideNav />
      </aside>
      <header className="sticky top-0 z-30 flex items-center justify-between border-b bg-surface px-4 py-3 md:hidden">
        <span className="font-heading text-lg font-semibold text-brand">Nursery</span>
        <Button variant="ghost" size="icon" onClick={() => setOpen(true)} data-testid="mobile-menu-button" aria-label="Apri menu">
          <Menu className="h-5 w-5" />
        </Button>
      </header>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="left" className="w-sidebar p-0">
          <SheetTitle className="sr-only">Menu</SheetTitle>
          <SideNav onNavigate={() => setOpen(false)} />
        </SheetContent>
      </Sheet>
      <main className="md:pl-[var(--sidebar-width)]">
        <div className="mx-auto max-w-content px-4 py-6 sm:px-6 lg:px-10 lg:py-10 fade-in">{children}</div>
      </main>
    </div>
  );
}
