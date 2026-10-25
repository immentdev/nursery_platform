import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import (
    db, NURSERY_ROLES, EMAIL_RE, alive, base_fields, now_iso, bad_request, not_found,
    get_current_user, is_nursery, require_nursery, require_admin_nursery, log_event, user_label,
    revoke_invitations,
)

router = APIRouter(prefix="/api")


class OrgIn(BaseModel):
    name: str = ""
    partita_iva: Optional[str] = None
    pec: Optional[str] = None
    nome_portale: Optional[str] = None
    url_portale: Optional[str] = None
    referente_nome: Optional[str] = None
    referente_email: Optional[str] = None
    referente_telefono: Optional[str] = None


PROVIDER_FIELDS = ("partita_iva", "pec", "nome_portale", "url_portale", "referente_nome", "referente_email", "referente_telefono")


def provider_data(body, creating):
    d = {k: ((getattr(body, k) or "").strip() or None) for k in ("name",) + PROVIDER_FIELDS}
    if not d["name"]:
        bad_request("La ragione sociale è obbligatoria")
    if creating and (not d["partita_iva"] or not d["pec"]):
        bad_request("Ragione sociale, partita IVA e PEC sono obbligatorie per un nuovo provider")
    if d["partita_iva"] and not re.fullmatch(r"\d{11}", d["partita_iva"]):
        bad_request("La partita IVA deve essere composta da 11 cifre")
    for k, label in (("pec", "La PEC"), ("referente_email", "L'email del referente")):
        if d[k] and not EMAIL_RE.match(d[k]):
            bad_request(f"{label} non è un indirizzo email valido")
    if d["url_portale"] and not re.match(r"^https?://\S+$", d["url_portale"]):
        bad_request("L'URL del portale deve iniziare con http:// o https://")
    if d["referente_telefono"] and not re.match(r"^\+?[0-9 .\-/]{6,20}$", d["referente_telefono"]):
        bad_request("Il telefono del referente non è valido")
    return d


class ProfileIn(BaseModel):
    nome: str = ""
    descrizione: str = ""


async def linked_startups(field, value):
    docs = await db.startups.find(alive({field: value, "stato_cliente": {"$ne": "CESSATO"}}), {"_id": 0}).to_list(500)
    return [{"id": s["id"], "denominazione": s["denominazione"], "codice_breve": s["codice_breve"]} for s in docs]


def blocked(what, startups, extra=""):
    names = ", ".join(f"{s['denominazione']} ({s['codice_breve']})" for s in startups)
    raise HTTPException(status_code=409, detail={
        "message": f"Impossibile eliminare: {what} è collegato a startup non cessate: {names}. {extra}".strip(),
        "startups": startups,
    })


# Organizations
@router.get("/organizations")
async def list_orgs(type: str = None, user=Depends(get_current_user)):
    if not is_nursery(user):
        return await db.organizations.find(alive({"id": user["organization_id"]}), {"_id": 0}).to_list(1)
    query = alive({"type": type} if type else {})
    orgs = await db.organizations.find(query, {"_id": 0}).sort("name", 1).to_list(1000)
    for o in orgs:
        if o["type"] == "PROVIDER":
            o["dati_incompleti"] = not (o.get("name") and o.get("partita_iva") and o.get("pec"))
            o["startup_count"] = await db.startups.count_documents(alive({"provider_organization_id": o["id"]}))
        o["user_count"] = await db.users.count_documents(alive({"organization_id": o["id"]}))
    return orgs


@router.post("/organizations")
async def create_provider(body: OrgIn, user=Depends(get_current_user)):
    require_admin_nursery(user)
    d = provider_data(body, True)
    if await db.organizations.find_one(alive({"type": "PROVIDER", "name": d["name"]})):
        raise HTTPException(status_code=409, detail="Esiste già un provider con questo nome")
    org = {**base_fields(user["id"]), "type": "PROVIDER", **d}
    await db.organizations.insert_one(dict(org))
    await log_event(user["id"], "ORGANIZATION", org["id"], "ORGANIZATION_CREATED", {"name": d["name"], "type": "PROVIDER"})
    return org


@router.put("/organizations/{oid}")
async def update_provider(oid: str, body: OrgIn, user=Depends(get_current_user)):
    require_admin_nursery(user)
    org = await db.organizations.find_one(alive({"id": oid, "type": "PROVIDER"}), {"_id": 0})
    if not org:
        not_found("Provider non trovato")
    d = provider_data(body, False)
    if await db.organizations.find_one(alive({"type": "PROVIDER", "name": d["name"], "id": {"$ne": oid}})):
        raise HTTPException(status_code=409, detail="Esiste già un provider con questo nome")
    changes = {k: {"from": org.get(k), "to": v} for k, v in d.items() if org.get(k) != v}
    if changes:
        await db.organizations.update_one({"id": oid}, {"$set": {**d, "updated_at": now_iso()}})
        await log_event(user["id"], "ORGANIZATION", oid, "ORGANIZATION_UPDATED", {"name": d["name"], "changes": changes})
    return await db.organizations.find_one({"id": oid}, {"_id": 0})


@router.delete("/organizations/{oid}")
async def delete_provider(oid: str, user=Depends(get_current_user)):
    require_admin_nursery(user)
    org = await db.organizations.find_one(alive({"id": oid, "type": "PROVIDER"}), {"_id": 0})
    if not org:
        not_found("Provider non trovato")
    linked = await linked_startups("provider_organization_id", oid)
    if linked:
        blocked(f"il provider {org['name']}", linked)
    t = now_iso()
    await db.organizations.update_one({"id": oid}, {"$set": {"deleted_at": t, "updated_at": t}})
    async for u in db.users.find(alive({"organization_id": oid, "status": {"$ne": "DISATTIVATO"}}), {"_id": 0, "password_hash": 0}):
        await revoke_invitations(u["id"])
        await db.users.update_one({"id": u["id"]}, {"$set": {"status": "DISATTIVATO", "updated_at": t}})
        await log_event(user["id"], "USER", u["id"], "USER_DEACTIVATED", {"email": u["email"], "motivo": "Provider eliminato"})
    await log_event(user["id"], "ORGANIZATION", oid, "ORGANIZATION_DELETED", {"name": org["name"]})
    return {"ok": True}


# Service profiles
@router.get("/service-profiles")
async def list_profiles(user=Depends(get_current_user)):
    require_nursery(user)
    profiles = await db.service_profiles.find(alive(), {"_id": 0}).sort("nome", 1).to_list(500)
    for p in profiles:
        p["startup_count"] = await db.startups.count_documents(alive({"service_profile_id": p["id"]}))
    return profiles


async def validated_profile(body, current_id=None):
    nome = body.nome.strip()
    if not nome:
        bad_request("Il nome del profilo è obbligatorio")
    if await db.service_profiles.find_one(alive({"nome": nome, "id": {"$ne": current_id}})):
        raise HTTPException(status_code=409, detail="Esiste già un profilo con questo nome")
    return {"nome": nome, "descrizione": body.descrizione.strip()}


@router.post("/service-profiles")
async def create_profile(body: ProfileIn, user=Depends(get_current_user)):
    require_admin_nursery(user)
    d = await validated_profile(body)
    doc = {**base_fields(user["id"]), **d}
    await db.service_profiles.insert_one(dict(doc))
    await log_event(user["id"], "SERVICE_PROFILE", doc["id"], "SERVICE_PROFILE_CREATED", d, "NURSERY_ONLY")
    return doc


@router.put("/service-profiles/{pid}")
async def update_profile(pid: str, body: ProfileIn, user=Depends(get_current_user)):
    require_admin_nursery(user)
    old = await db.service_profiles.find_one(alive({"id": pid}), {"_id": 0})
    if not old:
        not_found("Profilo non trovato")
    d = await validated_profile(body, pid)
    changes = {k: {"from": old[k], "to": v} for k, v in d.items() if old[k] != v}
    if changes:
        await db.service_profiles.update_one({"id": pid}, {"$set": {**d, "updated_at": now_iso()}})
        await log_event(user["id"], "SERVICE_PROFILE", pid, "SERVICE_PROFILE_UPDATED", {"changes": changes}, "NURSERY_ONLY")
    return await db.service_profiles.find_one({"id": pid}, {"_id": 0})


@router.delete("/service-profiles/{pid}")
async def delete_profile(pid: str, user=Depends(get_current_user)):
    require_admin_nursery(user)
    p = await db.service_profiles.find_one(alive({"id": pid}), {"_id": 0})
    if not p:
        not_found("Profilo non trovato")
    linked = await linked_startups("service_profile_id", pid)
    if linked:
        blocked(f"il profilo {p['nome']}", linked)
    t = now_iso()
    await db.service_profiles.update_one({"id": pid}, {"$set": {"deleted_at": t, "updated_at": t}})
    await log_event(user["id"], "SERVICE_PROFILE", pid, "SERVICE_PROFILE_DELETED", {"nome": p["nome"]}, "NURSERY_ONLY")
    return {"ok": True}


# Lookups and alerts
@router.get("/lookups")
async def lookups(user=Depends(get_current_user)):
    require_nursery(user)
    providers = await db.organizations.find(alive({"type": "PROVIDER"}), {"_id": 0}).sort("name", 1).to_list(500)
    profiles = await db.service_profiles.find(alive(), {"_id": 0}).sort("nome", 1).to_list(500)
    refs = await db.users.find(alive({"role": {"$in": list(NURSERY_ROLES)}, "status": {"$ne": "DISATTIVATO"}}), {"_id": 0, "password_hash": 0}).sort("cognome", 1).to_list(500)
    return {
        "providers": [{"id": o["id"], "name": o["name"]} for o in providers],
        "service_profiles": [{"id": p["id"], "nome": p["nome"]} for p in profiles],
        "nursery_users": [{"id": u["id"], "name": user_label(u)} for u in refs],
    }


class AlertRoleIn(BaseModel):
    role: str


@router.get("/alerts/count")
async def alerts_count(user=Depends(get_current_user)):
    require_nursery(user)
    handled = await db.alert_handlings.distinct("event_log_id", alive())
    return {"da_gestire": await db.event_logs.count_documents({"nursery_alert": True, "id": {"$nin": handled}})}


async def get_alert(eid):
    ev = await db.event_logs.find_one({"id": eid, "nursery_alert": True}, {"_id": 0})
    if not ev:
        not_found("Segnalazione non trovata")
    return ev


async def handle(user, ev, azione):
    if await db.alert_handlings.find_one(alive({"event_log_id": ev["id"]})):
        return False
    await db.alert_handlings.insert_one({**base_fields(user["id"]), "event_log_id": ev["id"], "handled_by_user_id": user["id"],
                                        "handled_at": now_iso(), "azione": azione})
    await log_event(user["id"], "ALERT", ev["id"], "ALERT_HANDLED",
                    {"azione": azione, "segnalazione": ev["action"], "email": ev["details"].get("email")}, "NURSERY_ONLY", ev.get("startup_id"))
    return True


@router.post("/alerts/{eid}/ack")
async def ack_alert(eid: str, user=Depends(get_current_user)):
    require_nursery(user)
    if not await handle(user, await get_alert(eid), "PRESA_VISIONE"):
        raise HTTPException(status_code=409, detail="Segnalazione già gestita")
    return {"ok": True}


@router.post("/alerts/{eid}/cancel-invite")
async def alert_cancel_invite(eid: str, user=Depends(get_current_user)):
    from routes_users import deactivate_user
    require_nursery(user)
    ev = await get_alert(eid)
    target = await db.users.find_one(alive({"id": ev["entity_id"]}), {"_id": 0, "password_hash": 0})
    if not target or target["status"] != "INVITATO":
        raise HTTPException(status_code=409, detail="L'invito non è più in attesa")
    await deactivate_user(ev["entity_id"], user=user)
    await handle(user, ev, "INVITO_ANNULLATO")
    return {"ok": True}


@router.post("/alerts/{eid}/change-role")
async def alert_change_role(eid: str, body: AlertRoleIn, user=Depends(get_current_user)):
    from routes_users import change_role, RoleIn
    require_nursery(user)
    ev = await get_alert(eid)
    await change_role(ev["entity_id"], RoleIn(role=body.role), user=user)
    await handle(user, ev, "RUOLO_CAMBIATO")
    return {"ok": True}


@router.get("/alerts")
async def alerts(stato: Optional[str] = None, user=Depends(get_current_user)):
    require_nursery(user)
    hm = {h["event_log_id"]: h async for h in db.alert_handlings.find(alive(), {"_id": 0})}
    events = await db.event_logs.find({"nursery_alert": True}, {"_id": 0}).sort("timestamp", -1).to_list(500)
    if stato == "DA_GESTIRE":
        events = [e for e in events if e["id"] not in hm]
    elif stato == "GESTITE":
        events = [e for e in events if e["id"] in hm]
    events.sort(key=lambda e: e["id"] in hm)
    uids = {e["actor_user_id"] for e in events if e.get("actor_user_id")} | {e["entity_id"] for e in events} | {h["handled_by_user_id"] for h in hm.values()}
    users = {u["id"]: u async for u in db.users.find({"id": {"$in": list(uids)}}, {"_id": 0, "password_hash": 0})}
    sids = {e["startup_id"] for e in events if e.get("startup_id")}
    startups = {s["id"]: s async for s in db.startups.find({"id": {"$in": list(sids)}}, {"_id": 0})}
    for e in events:
        e["actor_name"] = user_label(users.get(e.get("actor_user_id"))) or "Sistema"
        e["target_name"] = user_label(users.get(e["entity_id"]))
        s = startups.get(e.get("startup_id"))
        e["startup_name"] = s["denominazione"] if s else None
        e["startup_deleted"] = bool(s and s.get("deleted_at"))
        target = users.get(e["entity_id"]) or {}
        e["target_status"] = target.get("status")
        e["target_role"] = target.get("role")
        h = hm.get(e["id"])
        e["handling"] = {**h, "handled_by_name": user_label(users.get(h["handled_by_user_id"]))} if h else None
    return events
