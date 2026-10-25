import os

from core import db, alive, base_fields, now_iso, hash_password, verify_password, log_event

PROVIDER_FIELDS = ("partita_iva", "pec", "nome_portale", "url_portale", "referente_nome", "referente_email", "referente_telefono")
SERVICES = [
    ("AFC_COMPLETO", "AFC completo", "SERVIZIO_PROVIDER", True, 1),
    ("SOLO_CASH_FLOW", "Solo cash flow", "SERVIZIO_NURSERY", False, 2),
    ("FATTURAZIONE_PER_CONTO", "Fatturazione per conto", "SERVIZIO_NURSERY", False, 3),
    ("PAGHE", "Paghe", "SERVIZIO_PROVIDER", True, 4),
]
PLACEHOLDER = ("TESTO PROVVISORIO — {titolo} della Piattaforma Nursery.\n\n"
               "Questo è un testo segnaposto senza valore legale. Deve essere sostituito con il testo definitivo "
               "approvato da Nursery, pubblicando una nuova versione dalla schermata Documenti legali.")


async def ensure_indexes():
    for coll in ("organizations", "users", "startups", "service_profiles", "event_logs", "invitations"):
        await db[coll].create_index("id", unique=True)
    await db.users.create_index("email", unique=True)
    await db.users.create_index("organization_id")
    await db.startups.create_index("codice_breve", unique=True, partialFilterExpression={"deleted_at": {"$type": "null"}})
    await db.startups.create_index("provider_organization_id")
    await db.startups.create_index("organization_id")
    await db.invitations.create_index("token_hash")
    await db.event_logs.create_index([("startup_id", 1), ("timestamp", -1)])
    await db.login_attempts.create_index("identifier")
    await db.services.create_index("codice", unique=True)
    await db.startup_services.create_index("startup_id")
    await db.legal_acceptances.create_index("user_id")
    await db.alert_handlings.create_index("event_log_id", unique=True, partialFilterExpression={"deleted_at": {"$type": "null"}})
    for coll in ("services", "service_incompatibilities", "startup_services", "legal_documents", "legal_acceptances", "alert_handlings"):
        await db[coll].create_index("id", unique=True)


async def migrate():
    if not await db.services.count_documents({}):
        ids = {}
        for codice, nome, cat, req, ordine in SERVICES:
            s = await insert("services", {**base_fields(None), "codice": codice, "nome": nome, "descrizione": "", "categoria": cat,
                                          "richiede_provider": req, "attivo": True, "ordine": ordine})
            ids[codice] = s["id"]
        a, b = sorted([ids["SOLO_CASH_FLOW"], ids["AFC_COMPLETO"]])
        await insert("service_incompatibilities", {**base_fields(None), "service_a_id": a, "service_b_id": b})
    codes = {s["codice"]: s async for s in db.services.find({}, {"_id": 0})}
    async for st in db.startups.find({"servizi_attivi": {"$exists": True}}, {"_id": 0}):
        for c in st["servizi_attivi"]:
            s = codes[c]
            rec = await insert("startup_services", {**base_fields(None), "startup_id": st["id"], "service_id": s["id"],
                                                    "data_attivazione": st["created_at"][:10], "data_cessazione": None})
            await log_event(None, "STARTUP_SERVICE", rec["id"], "STARTUP_SERVICE_ADDED",
                            {"servizio": s["nome"], "data_attivazione": rec["data_attivazione"], "data_cessazione": None, "origine": "migrazione"},
                            "NURSERY_ONLY", st["id"])
        await db.startups.update_one({"id": st["id"]}, {"$unset": {"servizi_attivi": ""}})
    await db.startups.update_many({"link_impresa_digitale": {"$exists": True}}, {"$rename": {"link_impresa_digitale": "link_portale_provider"}})
    async for o in db.organizations.find({"type": "PROVIDER", "nome_portale": {"$exists": False}}, {"_id": 0}):
        fields = {k: None for k in PROVIDER_FIELDS}
        if o["name"] == "Ida Servizi S.r.l.":
            fields.update(nome_portale="Impresa Digitale", url_portale="https://impresadigitale.eu/")
        await db.organizations.update_one({"id": o["id"]}, {"$set": fields})
    if not await db.legal_documents.count_documents({}):
        for tipo, titolo in (("TERMINI_USO", "Termini d'uso"), ("INFORMATIVA_PRIVACY", "Informativa privacy")):
            await insert("legal_documents", {**base_fields(None), "tipo": tipo, "versione": "1.0", "testo": PLACEHOLDER.format(titolo=titolo),
                                             "data_pubblicazione": now_iso(), "attivo": True})


async def insert(coll, doc):
    await db[coll].insert_one(dict(doc))
    return doc


async def seed():
    await ensure_indexes()
    admin_email = os.environ["ADMIN_EMAIL"].lower()
    admin_pw = os.environ["ADMIN_PASSWORD"]
    if await db.organizations.find_one(alive({"type": "NURSERY"})):
        admin = await db.users.find_one({"email": admin_email})
        if admin and not verify_password(admin_pw, admin.get("password_hash")):
            await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_pw)}})
        await migrate()
        return

    demo_pw = hash_password(os.environ["DEMO_PASSWORD"])
    nursery = await insert("organizations", {**base_fields(None), "type": "NURSERY", "name": "Nursery (Imment S.r.l.)"})
    ida = await insert("organizations", {**base_fields(None), "type": "PROVIDER", "name": "Ida Servizi S.r.l."})
    p_full = await insert("service_profiles", {**base_fields(None), "nome": "Startup seguita in tutto",
                                               "descrizione": "Nursery e il provider seguono l'intera amministrazione della startup."})
    p_int = await insert("service_profiles", {**base_fields(None), "nome": "Startup con amministrativo interno",
                                              "descrizione": "La startup ha una risorsa amministrativa interna che collabora con Nursery e il provider."})

    def user(org, nome, cognome, email, role, pw, areas=None):
        return {**base_fields(None), "organization_id": org["id"], "nome": nome, "cognome": cognome, "email": email,
                "telefono": None, "role": role, "competence_areas": areas or [], "status": "ATTIVO", "password_hash": pw}

    admin = await insert("users", user(nursery, "Amministratore", "Nursery", admin_email, "ADMIN_NURSERY", hash_password(admin_pw)))
    oper = await insert("users", user(nursery, "Giulia", "Operatrice", "operatore@imment.test", "OPERATORE_NURSERY", demo_pw))
    await insert("users", user(ida, "Marco", "Operativo", "operativo@idaservizi.test", "OPERATIVO_PROVIDER", demo_pw, ["CONTABILITA"]))
    await insert("users", user(ida, "Laura", "Professionista", "professionista@idaservizi.test", "PROFESSIONISTA_PROVIDER", demo_pw, ["CONTABILITA", "PAGHE"]))

    samples = [
        ("Alfa Robotics S.r.l.", "ALFA", "10000000001", "Via Roma 1, 20121 Milano (MI)", "alfarobotics@pec.test",
         "2023-05-10", True, "2023-06-01", "MENSILE", ida, p_full, ["AFC_COMPLETO", "PAGHE"], admin, "ATTIVO", "alfa"),
        ("Beta Lab S.r.l.", "BETA", "10000000002", "Corso Italia 22, 10121 Torino (TO)", "betalab@pec.test",
         "2024-01-15", False, None, "TRIMESTRALE", ida, p_int, ["AFC_COMPLETO", "FATTURAZIONE_PER_CONTO"], oper, "ATTIVO", "beta"),
        ("Gamma Flow S.r.l.", "GAMMA", "10000000003", "Piazza Duomo 3, 50122 Firenze (FI)", "gammaflow@pec.test",
         "2024-09-02", True, "2024-10-01", "TRIMESTRALE", None, p_int, ["SOLO_CASH_FLOW"], oper, "ATTIVO", "gamma"),
    ]
    for (den, code, cf, sede, pec, costit, innov, iscr, iva, prov, prof, serv, ref, stato, slug) in samples:
        org = await insert("organizations", {**base_fields(None), "type": "STARTUP", "name": den})
        s = await insert("startups", {
            **base_fields(None), "organization_id": org["id"], "denominazione": den, "codice_breve": code,
            "codice_fiscale": cf, "partita_iva": cf, "sede_legale": sede, "pec": pec, "telefono": None,
            "data_costituzione": costit, "startup_innovativa": innov, "data_iscrizione_sezione_speciale": iscr,
            "data_chiusura_esercizio": "12-31", "regime_iva": iva,
            "provider_organization_id": prov["id"] if prov else None, "service_profile_id": prof["id"],
            "servizi_attivi": serv, "referente_nursery_user_id": ref["id"], "link_impresa_digitale": "https://impresadigitale.eu/" if code == "ALFA" else None,
            "stato_cliente": stato,
        })
        await log_event(None, "STARTUP", s["id"], "STARTUP_CREATED",
                        {"denominazione": den, "codice_breve": code, "stato_cliente": stato, "origine": "dati di esempio"}, "ALL", s["id"])
        await insert("users", user(org, "Admin", code.capitalize(), f"admin@{slug}.test", "ADMIN_STARTUP", demo_pw))
        if code == "ALFA":
            await insert("users", user(org, "Paolo", "Operativo", "operativo@alfa.test", "OPERATIVO_STARTUP", demo_pw))
    await migrate()
