import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import (
    db, EMAIL_RE, COMPETENCE_AREAS, ROLES_BY_ORG_TYPE,
    alive, base_fields, now_iso, bad_request, forbidden, not_found, get_current_user,
    is_nursery, can_manage, log_event, create_invitation, revoke_invitations,
)

router = APIRouter(prefix="/api/users")


class InviteIn(BaseModel):
    organization_id: str
    nome: str = ""
    cognome: str = ""
    email: str = ""
    telefono: Optional[str] = None
    role: str
    competence_areas: List[str] = []


class UserUpdateIn(BaseModel):
    nome: str = ""
    cognome: str = ""
    telefono: Optional[str] = None
    competence_areas: List[str] = []


class RoleIn(BaseModel):
    role: str


async def get_org(oid):
    org = await db.organizations.find_one(alive({"id": oid}), {"_id": 0})
    if not org:
        not_found("Organizzazione non trovata")
    return org


async def event_meta(org):
    sid = None
    if org["type"] == "STARTUP":
        s = await db.startups.find_one({"organization_id": org["id"]}, {"_id": 0})
        sid = s["id"] if s else None
    return {"visibility": "NURSERY_ONLY" if org["type"] == "NURSERY" else "ALL", "startup_id": sid}


async def load_target(uid):
    target = await db.users.find_one(alive({"id": uid}), {"_id": 0, "password_hash": 0})
    if not target:
        not_found("Utente non trovato")
    return target, await get_org(target["organization_id"])


def assert_manage(actor, org, role):
    if not can_manage(actor, org, role):
        forbidden("Non hai i permessi per gestire questo utente o assegnare questo ruolo")


def not_self(actor, target):
    if actor["id"] == target["id"]:
        forbidden("Non puoi eseguire questa operazione sul tuo stesso utente")


def check_personal(d):
    if not d["nome"].strip() or not d["cognome"].strip():
        bad_request("Nome e cognome sono obbligatori")
    if d.get("telefono") and not re.match(r"^\+?[0-9 .\-/]{6,20}$", d["telefono"].strip()):
        bad_request("Il numero di telefono non è valido")


def check_competences(org, areas):
    if org["type"] == "PROVIDER":
        if set(areas) - COMPETENCE_AREAS:
            bad_request("Area di competenza non valida (ammesse: CONTABILITA, PAGHE)")
    elif areas:
        bad_request("Le aree di competenza si applicano solo agli utenti provider")


async def assert_not_last_admin(actor, target):
    if actor["role"] != "ADMIN_STARTUP" or target["role"] != "ADMIN_STARTUP" or target["status"] != "ATTIVO":
        return
    others = await db.users.count_documents(alive({
        "organization_id": target["organization_id"], "role": "ADMIN_STARTUP",
        "status": "ATTIVO", "id": {"$ne": target["id"]},
    }))
    if others == 0:
        raise HTTPException(status_code=409, detail="Non puoi disattivare o declassare l'ultimo ADMIN_STARTUP attivo della startup")


@router.get("")
async def list_users(organization_id: Optional[str] = None, org_type: Optional[str] = None,
                     role: Optional[str] = None, status: Optional[str] = None, q: Optional[str] = None,
                     user=Depends(get_current_user)):
    query = alive()
    if is_nursery(user):
        if organization_id:
            query["organization_id"] = organization_id
    elif user["role"] == "ADMIN_STARTUP":
        query["organization_id"] = user["organization_id"]
    else:
        forbidden()
    orgs = {o["id"]: o async for o in db.organizations.find({}, {"_id": 0})}
    if org_type:
        ids = [oid for oid, o in orgs.items() if o["type"] == org_type]
        query["organization_id"] = {"$in": ids} if "organization_id" not in query else query["organization_id"]
    if role:
        query["role"] = role
    if status:
        query["status"] = status
    if q:
        rx = {"$regex": re.escape(q.strip()), "$options": "i"}
        query["$or"] = [{"nome": rx}, {"cognome": rx}, {"email": rx}]
    users = await db.users.find(query, {"_id": 0, "password_hash": 0}).sort("cognome", 1).to_list(2000)
    for u in users:
        o = orgs.get(u["organization_id"], {})
        u["organization_name"] = o.get("name")
        u["organization_type"] = o.get("type")
    return users


@router.post("")
async def invite_user(body: InviteIn, user=Depends(get_current_user)):
    org = await get_org(body.organization_id)
    if body.role not in ROLES_BY_ORG_TYPE[org["type"]]:
        bad_request("Il ruolo non è compatibile con il tipo di organizzazione")
    assert_manage(user, org, body.role)
    d = body.model_dump()
    check_personal(d)
    email = d["email"].strip().lower()
    if not EMAIL_RE.match(email):
        bad_request("Indirizzo email non valido")
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Esiste già un utente con questa email")
    areas = list(dict.fromkeys(d["competence_areas"]))
    check_competences(org, areas)
    doc = {
        **base_fields(user["id"]), "organization_id": org["id"], "nome": d["nome"].strip(),
        "cognome": d["cognome"].strip(), "email": email, "telefono": (d["telefono"] or "").strip() or None,
        "role": body.role, "competence_areas": areas, "status": "INVITATO", "password_hash": None,
    }
    await db.users.insert_one(dict(doc))
    token, expires = await create_invitation(doc["id"], user["id"])
    await log_event(user["id"], "USER", doc["id"], "USER_INVITED",
                    {"email": email, "nome": doc["nome"], "cognome": doc["cognome"], "role": body.role, "organization": org["name"]},
                    nursery_alert=body.role == "ADMIN_STARTUP", **await event_meta(org))
    doc.pop("password_hash")
    return {"user": doc, "invite_token": token, "expires_at": expires}


@router.patch("/{uid}")
async def update_user(uid: str, body: UserUpdateIn, user=Depends(get_current_user)):
    target, org = await load_target(uid)
    assert_manage(user, org, target["role"])
    d = body.model_dump()
    check_personal(d)
    areas = list(dict.fromkeys(d["competence_areas"]))
    check_competences(org, areas)
    new = {"nome": d["nome"].strip(), "cognome": d["cognome"].strip(),
           "telefono": (d["telefono"] or "").strip() or None, "competence_areas": areas}
    changes = {k: {"from": target.get(k), "to": v} for k, v in new.items() if target.get(k) != v}
    if changes:
        await db.users.update_one({"id": uid}, {"$set": {**new, "updated_at": now_iso()}})
        await log_event(user["id"], "USER", uid, "USER_UPDATED", {"email": target["email"], "changes": changes}, **await event_meta(org))
    return await db.users.find_one({"id": uid}, {"_id": 0, "password_hash": 0})


@router.post("/{uid}/role")
async def change_role(uid: str, body: RoleIn, user=Depends(get_current_user)):
    target, org = await load_target(uid)
    not_self(user, target)
    assert_manage(user, org, target["role"])
    assert_manage(user, org, body.role)
    if body.role == target["role"]:
        return target
    if body.role != "ADMIN_STARTUP":
        await assert_not_last_admin(user, target)
    await db.users.update_one({"id": uid}, {"$set": {"role": body.role, "updated_at": now_iso()}})
    await log_event(user["id"], "USER", uid, "ROLE_CHANGED",
                    {"email": target["email"], "from": target["role"], "to": body.role},
                    nursery_alert=body.role == "ADMIN_STARTUP", **await event_meta(org))
    return await db.users.find_one({"id": uid}, {"_id": 0, "password_hash": 0})


@router.post("/{uid}/deactivate")
async def deactivate_user(uid: str, user=Depends(get_current_user)):
    target, org = await load_target(uid)
    not_self(user, target)
    assert_manage(user, org, target["role"])
    if target["status"] == "DISATTIVATO":
        raise HTTPException(status_code=409, detail="L'utente è già disattivato")
    await assert_not_last_admin(user, target)
    await revoke_invitations(uid)
    await db.users.update_one({"id": uid}, {"$set": {"status": "DISATTIVATO", "updated_at": now_iso()}})
    action = "INVITE_CANCELLED" if target["status"] == "INVITATO" else "USER_DEACTIVATED"
    await log_event(user["id"], "USER", uid, action, {"email": target["email"], "role": target["role"]}, **await event_meta(org))
    return await db.users.find_one({"id": uid}, {"_id": 0, "password_hash": 0})


@router.post("/{uid}/reactivate")
async def reactivate_user(uid: str, user=Depends(get_current_user)):
    target, org = await load_target(uid)
    assert_manage(user, org, target["role"])
    if target["status"] != "DISATTIVATO":
        raise HTTPException(status_code=409, detail="L'utente non è disattivato")
    full = await db.users.find_one({"id": uid}, {"_id": 0})
    status = "ATTIVO" if full.get("password_hash") else "INVITATO"
    await db.users.update_one({"id": uid}, {"$set": {"status": status, "updated_at": now_iso()}})
    await log_event(user["id"], "USER", uid, "USER_REACTIVATED", {"email": target["email"], "status": status}, **await event_meta(org))
    return await db.users.find_one({"id": uid}, {"_id": 0, "password_hash": 0})


@router.post("/{uid}/regenerate-invite")
async def regenerate_invite(uid: str, user=Depends(get_current_user)):
    target, org = await load_target(uid)
    assert_manage(user, org, target["role"])
    if target["status"] != "INVITATO":
        raise HTTPException(status_code=409, detail="Si può rigenerare il link solo per utenti in stato INVITATO")
    token, expires = await create_invitation(uid, user["id"])
    await log_event(user["id"], "USER", uid, "INVITE_REGENERATED", {"email": target["email"]}, **await event_meta(org))
    return {"user": target, "invite_token": token, "expires_at": expires}
