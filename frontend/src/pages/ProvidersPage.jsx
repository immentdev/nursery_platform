import SimpleCrud from "@/components/SimpleCrud";

const PARAMS = { type: "PROVIDER" };

export default function ProvidersPage() {
  return (
    <SimpleCrud
      title="Organizzazioni provider"
      subtitle="Studi esterni che erogano contabilità, adempimenti e paghe"
      endpoint="/organizations"
      params={PARAMS}
      fields={[{ key: "name", label: "Ragione sociale" }]}
      newLabel="Nuovo provider"
      testPrefix="provider"
      renderMeta={(o) => <div className="text-xs text-ink-muted">{o.startup_count} startup · {o.user_count} utenti</div>}
    />
  );
}
