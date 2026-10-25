import SimpleCrud from "@/components/SimpleCrud";

export default function ServiceProfilesPage() {
  return (
    <SimpleCrud
      title="Profili di servizio"
      subtitle="Modelli di servizio assegnabili alle startup"
      endpoint="/service-profiles"
      fields={[{ key: "nome", label: "Nome" }, { key: "descrizione", label: "Descrizione", multiline: true }]}
      newLabel="Nuovo profilo"
      testPrefix="profile"
      renderMeta={(p) => (
        <>
          <div className="mt-1 text-sm text-ink-soft">{p.descrizione}</div>
          <div className="mt-1 text-xs text-ink-muted">{p.startup_count} startup collegate</div>
        </>
      )}
    />
  );
}
