import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import (
    db, alive, base_fields, now_iso, today_iso, check_date, bad_request, not_found,
    get_current_user, require_nursery, require_admin_nursery, log_event,
)

router = APIRouter(prefix="/api/services")
CATEGORIE = {"SERVIZIO_PROVIDER", "SERVIZIO_NURSERY"}
END = "9999-12-31"


class ServiceIn(BaseModel):
    codice: str = ""
    nome: str = ""
    descrizione: str = ""
    categoria: str = ""
    richiede_provider: bool = False
    servizi_incompatibili: List[str] = []
    attivo: bool = True
    ordine: int = 0


class ServizioIn(BaseModel):
    id: Optional[str] = None
    service_id: str = ""
    data_attivazione: str = ""
    data_cessazione: Optional[str] = None


def record_status(r, t=None):
    t = t or today_iso()
    if r.get("data_cessazione") and r["data_cessazione"] < t:
        return "CESSATO"
    if r["data_attivazione"] > t:
        return "PROGRAMMATO"
    return "ATTIVO"


async def incompat_map():
    m = {}
    async for p in db.service_incompatibilities.find(alive(), {"_id": 0}):
        m.setdefault(p["service_a_id"], set()).add(p["service_b_id"])
        m.setdefault(p["service_b_id"], set()).add(p["service_a_id"])
    return m


async def linked_startups_for_service(service_id):
    sids = await db.startup_services.distinct("startup_id", alive({"service_id": service_id}))
    docs = await db.startups.find(alive({"id": {"$in": sids}, "stato_cliente": {"$ne": "CESSATO"}}), {"_id": 0}).to_list(1000)
    return [{"id": s["id"], "denominazione": s["denominazione"], "codice_breve": s["codice_breve"]} for s in docs]


async def validate_service_records(records, provider_id, stato_cliente):
    ids = list({r["service_id"] for r in records})
    services = {s["id"]: s async for s in db.services.find(alive({"id": {"$in": ids}}), {"_id": 0})}
    for r in records:
        s = services.get(r["service_id"])
        if not s:
            bad_request("Servizio non trovato")
        check_date(r["data_attivazione"], f"Data di attivazione di «{s['nome']}»")
        if r.get("data_cessazione"):
            check_date(r["data_cessazione"], f"Data di cessazione di «{s['nome']}»")
            if r["data_cessazione"] < r["data_attivazione"]:
                bad_request(f"Servizio «{s['nome']}»: la data di cessazione non può precedere quella di attivazione")
    live = [r for r in records if record_status(r) != "CESSATO"]
    if stato_cliente != "CESSATO" and not live:
        bad_request("Regola servizi: la startup deve avere almeno un servizio attivo o programmato")
    for r in live:
        s = services[r["service_id"]]
        if s["richiede_provider"] and not provider_id:
            bad_request(f"Regola servizi: il servizio «{s['nome']}» richiede un provider assegnato")
    inc = await incompat_map()
    for i, a in enumerate(records):
        for b in records[i + 1:]:
            if a["data_attivazione"] <= (b.get("data_cessazione") or END) and b["data_attivazione"] <= (a.get("data_cessazione") or END):
                na, nb = services[a["service_id"]]["nome"], services[b["service_id"]]["nome"]
                if a["service_id"] == b["service_id"]:
                    bad_request(f"Il servizio «{na}» ha due periodi che si sovrappongono")
                if b["service_id"] in inc.get(a["service_id"], set()):
                    bad_request(f"Regola servizi: «{na}» e «{nb}» sono incompatibili e i loro periodi si sovrappongono")


async def sync_incompat(sid, new_ids, actor_id):
    cur = (await incompat_map()).get(sid, set())
    new = set(new_ids)
    t = now_iso()
    for other in cur - new:
        a, b = sorted([sid, other])
        await db.service_incompatibilities.update_many(alive({"service_a_id": a, "service_b_id": b}), {"$set": {"deleted_at": t, "updated_at": t}})
    for other in new - cur:
        a, b = sorted([sid, other])
        await db.service_incompatibilities.insert_one({**base_fields(actor_id), "service_a_id": a, "service_b_id": b})


async def validated(body, current=None):
    d = body.model_dump()
    d["codice"] = d["codice"].strip().upper()
    d["nome"] = d["nome"].strip()
    d["descrizione"] = d["descrizione"].strip()
    d["servizi_incompatibili"] = list(dict.fromkeys(d["servizi_incompatibili"]))
    if current:
        if d["codice"] and d["codice"] != current["codice"]:
            bad_request("Il codice del servizio non è modificabile dopo la creazione")
        d["codice"] = current["codice"]
    else:
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{1,29}", d["codice"]):
            bad_request("Il codice deve contenere da 2 a 30 caratteri maiuscoli (A-Z, 0-9, _) e iniziare con una lettera")
        if await db.services.find_one({"codice": d["codice"]}):
            raise HTTPException(status_code=409, detail=f"Esiste già un servizio con codice {d['codice']}")
    if not d["nome"]:
        bad_request("Il nome del servizio è obbligatorio")
    if d["categoria"] not in CATEGORIE:
        bad_request("Categoria non valida (SERVIZIO_PROVIDER o SERVIZIO_NURSERY)")
    others = d["servizi_incompatibili"]
    if current and current["id"] in others:
        bad_request("Un servizio non può essere incompatibile con se stesso")
    if len(others) != await db.services.count_documents(alive({"id": {"$in": others}})):
        bad_request("Uno dei servizi incompatibili indicati non esiste")
    return d


@router.get("")
async def list_services(user=Depends(get_current_user)):
    require_nursery(user)
    inc = await incompat_map()
    items = await db.services.find(alive(), {"_id": 0}).sort([("ordine", 1), ("nome", 1)]).to_list(500)
    for s in items:
        s["servizi_incompatibili"] = sorted(inc.get(s["id"], set()))
        s["startup_count"] = len(await linked_startups_for_service(s["id"]))
    return items


@router.post("")
async def create_service(body: ServiceIn, user=Depends(get_current_user)):
    require_admin_nursery(user)
    d = await validated(body)
    others = d.pop("servizi_incompatibili")
    doc = {**base_fields(user["id"]), **d}
    await db.services.insert_one(dict(doc))
    await sync_incompat(doc["id"], others, user["id"])
    await log_event(user["id"], "SERVICE", doc["id"], "SERVICE_CREATED", {"codice": d["codice"], "nome": d["nome"]}, "NURSERY_ONLY")
    return {**doc, "servizi_incompatibili": others}


@router.put("/{sid}")
async def update_service(sid: str, body: ServiceIn, user=Depends(get_current_user)):
    require_admin_nursery(user)
    old = await db.services.find_one(alive({"id": sid}), {"_id": 0})
    if not old:
        not_found("Servizio non trovato")
    d = await validated(body, old)
    others = d.pop("servizi_incompatibili")
    old_inc = sorted((await incompat_map()).get(sid, set()))
    changes = {k: {"from": old.get(k), "to": v} for k, v in d.items() if old.get(k) != v}
    if sorted(others) != old_inc:
        names = {s["id"]: s["nome"] async for s in db.services.find({"id": {"$in": others + old_inc}}, {"_id": 0})}
        changes["servizi_incompatibili"] = {"from": [names.get(i) for i in old_inc], "to": [names.get(i) for i in others]}
    if changes:
        await db.services.update_one({"id": sid}, {"$set": {**d, "updated_at": now_iso()}})
        await sync_incompat(sid, others, user["id"])
        action = "SERVICE_DEACTIVATED" if old["attivo"] and not d["attivo"] else "SERVICE_UPDATED"
        await log_event(user["id"], "SERVICE", sid, action, {"codice": old["codice"], "changes": changes}, "NURSERY_ONLY")
    return {**(await db.services.find_one({"id": sid}, {"_id": 0})), "servizi_incompatibili": others}


@router.delete("/{sid}")
async def delete_service(sid: str, user=Depends(get_current_user)):
    from routes_admin import blocked
    require_admin_nursery(user)
    s = await db.services.find_one(alive({"id": sid}), {"_id": 0})
    if not s:
        not_found("Servizio non trovato")
    linked = await linked_startups_for_service(sid)
    if linked:
        blocked(f"il servizio {s['nome']}", linked, "Puoi solo disattivarlo.")
    t = now_iso()
    await db.services.update_one({"id": sid}, {"$set": {"deleted_at": t, "updated_at": t}})
    await sync_incompat(sid, [], user["id"])
    await log_event(user["id"], "SERVICE", sid, "SERVICE_DELETED", {"codice": s["codice"], "nome": s["nome"]}, "NURSERY_ONLY")
    return {"ok": True}
