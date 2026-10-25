import { useAuth } from "@/context/AuthContext";
import { Empty } from "@/components/common";
import { StartupView } from "./StartupDetailPage";

export default function MyStartupPage() {
  const { user } = useAuth();
  if (!user.startup_id) return <Empty testId="no-startup">Nessuna startup collegata al tuo account.</Empty>;
  return <StartupView id={user.startup_id} home />;
}
