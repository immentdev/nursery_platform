import "@/App.css";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { isNursery, isProvider, isAdminNursery, canManageUsers } from "@/lib/perms";
import AppLayout from "@/components/AppLayout";
import LoginPage from "@/pages/LoginPage";
import AcceptInvitePage from "@/pages/AcceptInvitePage";
import StartupsPage from "@/pages/StartupsPage";
import StartupDetailPage from "@/pages/StartupDetailPage";
import StartupFormPage from "@/pages/StartupFormPage";
import UsersPage from "@/pages/UsersPage";
import ProvidersPage from "@/pages/ProvidersPage";
import ServiceProfilesPage from "@/pages/ServiceProfilesPage";
import ProfilePage from "@/pages/ProfilePage";
import AlertsPage from "@/pages/AlertsPage";
import MyStartupPage from "@/pages/MyStartupPage";

function Guard({ allow, children }) {
  const { user } = useAuth();
  if (user === null) return <div className="p-10 text-sm text-ink-muted" data-testid="auth-loading">Caricamento…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (allow && !allow(user)) return <Navigate to="/" replace />;
  return <AppLayout>{children}</AppLayout>;
}

function Home() {
  const { user } = useAuth();
  if (user === null) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={isNursery(user) || isProvider(user) ? "/startup" : "/mia-startup"} replace />;
}

const listAccess = (u) => isNursery(u) || isProvider(u);

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/invito/:token" element={<AcceptInvitePage />} />
          <Route path="/startup" element={<Guard allow={listAccess}><StartupsPage /></Guard>} />
          <Route path="/startup/nuova" element={<Guard allow={isNursery}><StartupFormPage /></Guard>} />
          <Route path="/startup/:id" element={<Guard><StartupDetailPage /></Guard>} />
          <Route path="/startup/:id/modifica" element={<Guard allow={isNursery}><StartupFormPage /></Guard>} />
          <Route path="/mia-startup" element={<Guard><MyStartupPage /></Guard>} />
          <Route path="/utenti" element={<Guard allow={canManageUsers}><UsersPage /></Guard>} />
          <Route path="/provider" element={<Guard allow={isAdminNursery}><ProvidersPage /></Guard>} />
          <Route path="/profili" element={<Guard allow={isAdminNursery}><ServiceProfilesPage /></Guard>} />
          <Route path="/segnalazioni" element={<Guard allow={isNursery}><AlertsPage /></Guard>} />
          <Route path="/profilo" element={<Guard><ProfilePage /></Guard>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors closeButton />
    </AuthProvider>
  );
}
