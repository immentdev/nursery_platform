import re
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import (
    db, EMAIL_RE, NURSERY_ROLES, STATI_CLIENTE, REGIMI_IVA, today_iso, check_date, is_provider,
    alive, base_fields, now_iso, bad_request, forbidden, not_found, get_current_user,
    is_nursery, require_nursery, require_admin_nursery, startup_scope, get_visible_startup,
    log_event, user_label, revoke_invitations,
)
from routes_services import ServizioIn, record_status, validate_service_records

router = APIRouter(prefix="/api/startups")


class StartupIn(BaseModel):
    denominazione: str = ""
    codice_breve: str = ""
    codice_fiscale: str = ""
    partita_iva: str = ""
    sede_legale: str = ""
    pec: str = ""
    telefono: Optional[str] = None
    data_costituzione: str = ""
    startup_innovativa: bool = False
    data_iscrizione_sezione_speciale: Optional[str] = None
    data_chiusura_esercizio: str = "12-31"
    regime_iva: str = ""
    provider_organization_id: Optional[str] = None
    service_profile_id: str = ""
    servizi: List[ServizioIn] = []
    referente_nursery_user_id: str = ""
    link_portale_provider: Optional[str] = None
    stato_cliente: str = "ONBOARDING"


class ContattiIn(BaseModel):
    pec: str = ""
    sede_legale: str = ""
    telefono: Optional[str] = None


FIELDS = [f for f in StartupIn.model_fields if f != "servizi"]
SENSITIVE = {"referente_nursery_user_id", "service_profile_id"}
PROVIDER_FULL = ("id", "name", "partita_iva", "pec", "nome_portale", "url_portale", "referente_nome", "referente_email", "referente_telefono")
REQUIRED = {
    "denominazione": "Denominazione", "codice_fiscale": "Codice fiscale", "partita_iva": "Partita IVA",
    "data_costituzione": "Data di costituzione", "regime_iva": "Regime IVA",
    "service_profile_id": "Profilo di servizio", "referente_nursery_user_id": "Referente Nursery",
}


def validate_contacts(d):
    if not d["sede_legale"]:
        bad_request("La sede legale è obbligatoria")
    if not EMAIL_RE.match(d["pec"]):
        bad_request("La PEC non è un indirizzo email valido")
    if d.get("telefono") and not re.match(r"^\+?[0-9 .\-/]{6,20}$", d["telefono"]):
        bad_request("Il numero di telefono non è valido")


async def prepare_services(sid, entries, provider_id, stato):
    existing = {r["id"]: r async for r in db.startup_services.find(alive({"startup_id": sid}), {"_id": 0})} if sid else {}
    sent = {e["id"] for e in entries if e.get("id")}
    if set(existing) - sent:
        bad_request("Un servizio già registrato non si può rimuovere: imposta la data di cessazione")
    if sent - set(existing):
        bad_request("Servizio della startup non trovato")
    new_ids = [e["service_id"] for e in entries if not e.get("id")]
    active = {s["id"] async for s in db.services.find(alive({"id": {"$in": new_ids}, "attivo": True}), {"_id": 0})}
    if set(new_ids) - active:
        bad_request("Si possono assegnare solo servizi attivi del catalogo")
    merged = [{
        "id": e.get("id"),
        "service_id": existing[e["id"]]["service_id"] if e.get("id") else e["service_id"],
        "data_attivazione": (e.get("data_attivazione") or "").strip(),
        "data_cessazione": (e.get("data_cessazione") or "").strip() or None,
    } for e in entries]
    await validate_service_records(merged, provider_id, stato)
    return merged, existing


async def persist_services(actor_id, sid, merged, existing):
    names = {s["id"]: s["nome"] async for s in db.services.find({"id": {"$in": [r["service_id"] for r in merged]}}, {"_id": 0})}
    for r in merged:
        name = names.get(r["service_id"])
        if r["id"]:
            old = existing[r["id"]]
            ch = {k: {"from": old.get(k), "to": r[k]} for k in ("data_attivazione", "data_cessazione") if old.get(k) != r[k]}
            if ch:
                await db.startup_services.update_one({"id": r["id"]}, {"$set": {"data_attivazione": r["data_attivazione"], "data_cessazione": r["data_cessazione"], "updated_at": now_iso()}})
                await log_event(actor_id, "STARTUP_SERVICE", r["id"], "STARTUP_SERVICE_UPDATED", {"servizio": name, "changes": ch}, "NURSERY_ONLY", sid)
        else:
            rec = {**base_fields(actor_id), "startup_id": sid, "service_id": r["service_id"],
                   "data_attivazione": r["data_attivazione"], "data_cessazione": r["data_cessazione"]}
            await db.startup_services.insert_one(dict(rec))
            await log_event(actor_id, "STARTUP_SERVICE", rec["id"], "STARTUP_SERVICE_ADDED",
                            {"servizio": name, "data_attivazione": r["data_attivazione"], "data_cessazione": r["data_cessazione"]}, "NURSERY_ONLY", sid)


def clean(d):
    out = {}
    for k, v in d.items():
        if isinstance(v, str):
            v = v.strip()
            if v == "" and k in ("telefono", "data_iscrizione_sezione_speciale", "provider_organization_id", "link_portale_provider"):
                v = None
        out[k] = v
    out["codice_breve"] = (out.get("codice_breve") or "").upper()
    return out


async def validate_startup(raw, current_id=None):
    d = clean(raw)
    for f, label in REQUIRED.items():
        if not d[f]:
            bad_request(f"Il campo {label} è obbligatorio")
    if not re.fullmatch(r"[A-Z]{3,6}", d["codice_breve"]):
        bad_request("Il codice breve deve contenere da 3 a 6 lettere maiuscole (A-Z)")
    dup = await db.startups.find_one(alive({"codice_breve": d["codice_breve"], "id": {"$ne": current_id}}), {"_id": 0})
    if dup:
        raise HTTPException(status_code=409, detail=f"Il codice breve {d['codice_breve']} è già usato da {dup['denominazione']}")
    if not re.fullmatch(r"\d{11}", d["codice_fiscale"]):
        bad_request("Il codice fiscale di una SRL deve essere composto da 11 cifre")
    if not re.fullmatch(r"\d{11}", d["partita_iva"]):
        bad_request("La partita IVA deve essere composta da 11 cifre")
    validate_contacts(d)
    check_date(d["data_costituzione"], "Data di costituzione")
    if d["startup_innovativa"]:
        if not d["data_iscrizione_sezione_speciale"]:
            bad_request("Per una startup innovativa la data di iscrizione alla sezione speciale è obbligatoria")
        check_date(d["data_iscrizione_sezione_speciale"], "Data iscrizione sezione speciale")
    else:
        d["data_iscrizione_sezione_speciale"] = None
    try:
        date.fromisoformat(f"2024-{d['data_chiusura_esercizio']}")
    except ValueError:
        bad_request("Data di chiusura esercizio non valida (giorno/mese inesistente)")
    if d["regime_iva"] not in REGIMI_IVA:
        bad_request("Regime IVA non valido")
    if d["stato_cliente"] not in STATI_CLIENTE:
        bad_request("Stato cliente non valido")
    if d["provider_organization_id"] and not await db.organizations.find_one(
            alive({"id": d["provider_organization_id"], "type": "PROVIDER"})):
        bad_request("Il provider selezionato non esiste")
    if not await db.service_profiles.find_one(alive({"id": d["service_profile_id"]})):
        bad_request("Il profilo di servizio selezionato non esiste")
    if not await db.users.find_one(alive({"id": d["referente_nursery_user_id"], "role": {"$in": list(NURSERY_ROLES)},
                                          "status": {"$ne": "DISATTIVATO"}})):
        bad_request("Il referente Nursery deve essere un utente Nursery non disattivato")
    if d["link_portale_provider"] and not re.match(r"^https?://\S+$", d["link_portale_provider"]):
        bad_request("Il link al portale del provider deve essere un URL che inizia con http:// o https://")
    return d


async def display(field, value):
    if not value:
        return value
    if field == "provider_organization_id":
        o = await db.organizations.find_one({"id": value}, {"_id": 0})
        return o["name"] if o else value
    if field == "service_profile_id":
        p = await db.service_profiles.find_one({"id": value}, {"_id": 0})
        return p["nome"] if p else value
    if field == "referente_nursery_user_id":
        return user_label(await db.users.find_one({"id": value}, {"_id": 0, "password_hash": 0})) or value
    return value


async def log_changes(actor_id, sid, changes):
    groups = {"other": {}, "sensitive": {}, "status": {}}
    for f, (a, b) in changes.items():
        key = "sensitive" if f in SENSITIVE else "status" if f == "stato_cliente" else "other"
        groups[key][f] = {"from": await display(f, a), "to": await display(f, b)}
    if groups["other"]:
        await log_event(actor_id, "STARTUP", sid, "STARTUP_UPDATED", {"changes": groups["other"]}, "ALL", sid)
    if groups["sensitive"]:
        await log_event(actor_id, "STARTUP", sid, "STARTUP_UPDATED", {"changes": groups["sensitive"]}, "NURSERY_ONLY", sid)
    if groups["status"]:
        await log_event(actor_id, "STARTUP", sid, "STARTUP_STATUS_CHANGED", {"changes": groups["status"]}, "ALL", sid)


async def enrich(docs, user):
    nursery = is_nursery(user)
    full_provider = nursery or is_provider(user)

    async def by_id(coll, ids):
        return {x["id"]: x async for x in db[coll].find({"id": {"$in": list(ids)}}, {"_id": 0, "password_hash": 0})}
    provs = await by_id("organizations", {d["provider_organization_id"] for d in docs if d.get("provider_organization_id")})
    profs = await by_id("service_profiles", {d["service_profile_id"] for d in docs})
    refs = await by_id("users", {d["referente_nursery_user_id"] for d in docs})
    recs = await db.startup_services.find(alive({"startup_id": {"$in": [d["id"] for d in docs]}}), {"_id": 0}).sort("data_attivazione", 1).to_list(10000)
    svcs = await by_id("services", {r["service_id"] for r in recs})
    t = today_iso()
    for d in docs:
        servizi = []
        for r in (x for x in recs if x["startup_id"] == d["id"]):
            st = record_status(r, t)
            s = svcs.get(r["service_id"], {})
            if not nursery and st == "CESSATO":
                continue
            item = {"service_id": r["service_id"], "codice": s.get("codice"), "nome": s.get("nome"), "stato": st,
                    "data_attivazione": r["data_attivazione"], "ordine": s.get("ordine", 0)}
            if nursery:
                item.update(id=r["id"], data_cessazione=r["data_cessazione"], categoria=s.get("categoria"), service_attivo=s.get("attivo"))
            servizi.append(item)
        d["servizi"] = servizi
        p = provs.get(d.get("provider_organization_id"))
        d["provider_name"] = p["name"] if p else None
        d["provider"] = {k: p.get(k) for k in (PROVIDER_FULL if full_provider else ("id", "name", "nome_portale"))} if p else None
        r = refs.get(d["referente_nursery_user_id"])
        d["referente_name"] = user_label(r)
        if nursery:
            d["service_profile_name"] = (profs.get(d["service_profile_id"]) or {}).get("nome")
        else:
            d.pop("service_profile_id", None)
            d["referente"] = {k: r.get(k) for k in ("nome", "cognome", "email", "telefono")} if r else None
    return docs


@router.get("")
async def list_startups(q: Optional[str] = None, stato_cliente: Optional[str] = None,
                        provider_organization_id: Optional[str] = None, servizio: Optional[str] = None,
                        referente_nursery_user_id: Optional[str] = None, user=Depends(get_current_user)):
    if not is_nursery(user) and user["role"] not in ("OPERATIVO_PROVIDER", "PROFESSIONISTA_PROVIDER"):
        forbidden()
    query = startup_scope(user)
    if q:
        rx = {"$regex": re.escape(q.strip()), "$options": "i"}
        query["$or"] = [{"denominazione": rx}, {"codice_breve": rx}]
    if stato_cliente:
        query["stato_cliente"] = stato_cliente
    if provider_organization_id and is_nursery(user):
        query["provider_organization_id"] = None if provider_organization_id == "NONE" else provider_organization_id
    if servizio:
        t = today_iso()
        query["id"] = {"$in": await db.startup_services.distinct("startup_id", alive({
            "service_id": servizio, "data_attivazione": {"$lte": t},
            "$or": [{"data_cessazione": None}, {"data_cessazione": {"$gte": t}}]}))}
    if referente_nursery_user_id:
        query["referente_nursery_user_id"] = referente_nursery_user_id
    docs = await db.startups.find(query, {"_id": 0}).sort("denominazione", 1).to_list(1000)
    return await enrich(docs, user)


@router.post("")
async def create_startup(body: StartupIn, user=Depends(get_current_user)):
    require_nursery(user)
    d = await validate_startup(body.model_dump(exclude={"servizi"}))
    merged, _ = await prepare_services(None, [s.model_dump() for s in body.servizi], d["provider_organization_id"], d["stato_cliente"])
    org = {**base_fields(user["id"]), "type": "STARTUP", "name": d["denominazione"]}
    await db.organizations.insert_one(dict(org))
    doc = {**base_fields(user["id"]), "organization_id": org["id"], **d}
    await db.startups.insert_one(dict(doc))
    await log_event(user["id"], "STARTUP", doc["id"], "STARTUP_CREATED",
                    {"denominazione": d["denominazione"], "codice_breve": d["codice_breve"], "stato_cliente": d["stato_cliente"]},
                    "ALL", doc["id"])
    await persist_services(user["id"], doc["id"], merged, {})
    return (await enrich([doc], user))[0]


@router.get("/{sid}")
async def get_startup(sid: str, user=Depends(get_current_user)):
    return (await enrich([await get_visible_startup(user, sid)], user))[0]


@router.put("/{sid}")
async def update_startup(sid: str, body: StartupIn, user=Depends(get_current_user)):
    require_nursery(user)
    old = await db.startups.find_one(alive({"id": sid}), {"_id": 0})
    if not old:
        not_found("Startup non trovata")
    d = await validate_startup(body.model_dump(exclude={"servizi"}), sid)
    merged, existing = await prepare_services(sid, [s.model_dump() for s in body.servizi], d["provider_organization_id"], d["stato_cliente"])
    await persist_services(user["id"], sid, merged, existing)
    changes = {f: (old.get(f), d[f]) for f in FIELDS if old.get(f) != d[f]}
    if changes:
        await db.startups.update_one({"id": sid}, {"$set": {**d, "updated_at": now_iso()}})
        if "denominazione" in changes:
            await db.organizations.update_one({"id": old["organization_id"]},
                                              {"$set": {"name": d["denominazione"], "updated_at": now_iso()}})
        await log_changes(user["id"], sid, changes)
    return await get_startup(sid, user)


@router.patch("/{sid}/contatti")
async def update_contatti(sid: str, body: ContattiIn, user=Depends(get_current_user)):
    old = await get_visible_startup(user, sid)
    if not (is_nursery(user) or user["role"] == "ADMIN_STARTUP"):
        forbidden("Solo l'amministratore della startup o Nursery possono modificare i contatti")
    d = clean(body.model_dump())
    validate_contacts(d)
    d = {k: d[k] for k in ("pec", "sede_legale", "telefono")}
    changes = {f: (old.get(f), d[f]) for f in d if old.get(f) != d[f]}
    if changes:
        await db.startups.update_one({"id": sid}, {"$set": {**d, "updated_at": now_iso()}})
        await log_changes(user["id"], sid, changes)
    return await get_startup(sid, user)


@router.delete("/{sid}")
async def delete_startup(sid: str, user=Depends(get_current_user)):
    require_admin_nursery(user)
    doc = await db.startups.find_one(alive({"id": sid}), {"_id": 0})
    if not doc:
        not_found("Startup non trovata")
    if doc["stato_cliente"] != "ONBOARDING":
        raise HTTPException(status_code=409, detail="Si possono eliminare solo startup in stato ONBOARDING. Le altre si chiudono impostando lo stato CESSATO.")
    t = now_iso()
    await db.startups.update_one({"id": sid}, {"$set": {"deleted_at": t, "updated_at": t}})
    await db.organizations.update_one({"id": doc["organization_id"]}, {"$set": {"deleted_at": t, "updated_at": t}})
    async for u in db.users.find(alive({"organization_id": doc["organization_id"]}), {"_id": 0, "password_hash": 0}):
        await revoke_invitations(u["id"])
        await db.users.update_one({"id": u["id"]}, {"$set": {"status": "DISATTIVATO", "updated_at": t}})
        await log_event(user["id"], "USER", u["id"], "USER_DEACTIVATED", {"motivo": "Startup eliminata", "email": u["email"]}, "ALL", sid)
    await log_event(user["id"], "STARTUP", sid, "STARTUP_DELETED",
                    {"denominazione": doc["denominazione"], "codice_breve": doc["codice_breve"]}, "NURSERY_ONLY", sid)
    return {"ok": True}


@router.get("/{sid}/users")
async def startup_users(sid: str, user=Depends(get_current_user)):
    s = await get_visible_startup(user, sid)
    return await db.users.find(alive({"organization_id": s["organization_id"]}), {"_id": 0, "password_hash": 0}).sort("cognome", 1).to_list(500)


@router.get("/{sid}/events")
async def startup_events(sid: str, user=Depends(get_current_user)):
    await get_visible_startup(user, sid)
    query = {"startup_id": sid}
    if not is_nursery(user):
        query["visibility"] = "ALL"
    events = await db.event_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(1000)
    ids = {e["actor_user_id"] for e in events if e.get("actor_user_id")}
    actors = {u["id"]: user_label(u) async for u in db.users.find({"id": {"$in": list(ids)}}, {"_id": 0, "password_hash": 0})}
    for e in events:
        e["actor_name"] = actors.get(e.get("actor_user_id")) or "Sistema"
    return events
