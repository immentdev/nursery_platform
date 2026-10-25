import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, errorMessage } from "@/lib/api";

export default function ContattiDialog({ open, onOpenChange, startup, onSaved }) {
  const [form, setForm] = useState({ pec: "", sede_legale: "", telefono: "" });
  useEffect(() => {
    if (open) setForm({ pec: startup.pec, sede_legale: startup.sede_legale, telefono: startup.telefono || "" });
  }, [open, startup]);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const save = async (e) => {
    e.preventDefault();
    try {
      await api.patch(`/startups/${startup.id}/contatti`, form);
      toast.success("Contatti aggiornati");
      onOpenChange(false);
      onSaved();
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="contatti-dialog">
        <DialogHeader>
          <DialogTitle>Modifica contatti</DialogTitle>
          <DialogDescription>Puoi aggiornare PEC, sede legale e telefono. Gli altri dati sono gestiti da Nursery.</DialogDescription>
        </DialogHeader>
        <form onSubmit={save} className="space-y-4">
          <div className="space-y-1.5"><Label>PEC</Label><Input value={form.pec} onChange={set("pec")} data-testid="contatti-pec" /></div>
          <div className="space-y-1.5"><Label>Sede legale</Label><Input value={form.sede_legale} onChange={set("sede_legale")} data-testid="contatti-sede" /></div>
          <div className="space-y-1.5"><Label>Telefono</Label><Input value={form.telefono} onChange={set("telefono")} data-testid="contatti-telefono" /></div>
          <DialogFooter><Button type="submit" data-testid="contatti-save">Salva</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
