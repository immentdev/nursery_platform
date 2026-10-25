import SimpleCrud from "@/components/SimpleCrud";

const PARAMS = { type: "PROVIDER" };

export default function ProvidersPage() {
  return (
    <SimpleCrud
      title="Organizzazioni provider"
      subtitle="Studi esterni che erogano contabilità, adempimenti e paghe"
      endpoint="/organizations"
      params={PARAMS}
      fields={[
        { key: "name", label: "Ragione sociale *" },
        { key: "partita_iva", label: "Partita IVA *" },
        { key: "pec", label: "PEC *" },
        { key: "nome_portale", label: "Nome portale (es. Impresa Digitale)" },
        { key: "url_portale", label: "URL portale" },
        { key: "referente_nome", label: "Nome referente" },
        { key: "referente_email", label: "Email referente" },
        { key: "referente_telefono", label: "Telefono referente" },
      ]}
      newLabel="Nuovo provider"
      testPrefix="provider"
      renderMeta={(o) => (
        <>
          {o.dati_incompleti && <span className="mr-2 inline-block rounded-full bg-warn-bg px-2 py-0.5 text-xs font-medium text-warn-fg" data-testid={`provider-incomplete-${o.id}`}>Dati incompleti</span>}
          <div className="mt-1 text-xs text-ink-muted">P.IVA {o.partita_iva || "—"} · PEC {o.pec || "—"} · Portale {o.nome_portale || "—"}</div>
          <div className="text-xs text-ink-muted">{o.startup_count} startup · {o.user_count} utenti</div>
        </>
      )}
    />
  );
}
