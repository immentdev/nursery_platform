import { Copy, Check } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatDateTime } from "@/lib/labels";

export default function InviteLinkDialog({ invite, onClose }) {
  const [copied, setCopied] = useState(false);
  const reset = invite?.kind === "RESET";
  const link = invite ? `${window.location.origin}/${reset ? "reimposta" : "invito"}/${invite.invite_token}` : "";

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(link);
    } catch {
      const el = document.getElementById("invite-link-input");
      el?.select();
      document.execCommand("copy");
    }
    setCopied(true);
    toast.success("Link copiato negli appunti");
  };

  return (
    <Dialog open={!!invite} onOpenChange={(o) => { if (!o) { setCopied(false); onClose(); } }}>
      <DialogContent data-testid="invite-link-dialog">
        <DialogHeader>
          <DialogTitle>{reset ? "Link di reimpostazione password" : "Link di invito"}</DialogTitle>
          <DialogDescription>
            In questo prototipo non inviamo email: copia il link e invialo a {invite?.user?.email}.
            Scade il {formatDateTime(invite?.expires_at)}. Il link viene mostrato solo ora{reset ? " e annulla eventuali link precedenti" : ""}.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Input id="invite-link-input" readOnly value={link} className="font-mono text-xs" data-testid="invite-link-input" />
          <Button onClick={copy} data-testid="invite-link-copy-button">
            {copied ? <Check className="mr-2 h-4 w-4" /> : <Copy className="mr-2 h-4 w-4" />}
            {copied ? "Copiato" : "Copia"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
