from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import (
    TZ, db, alive, now_iso, bad_request, get_current_user, hash_password,
    verify_password, validate_password_strength, hash_token, create_access_token, log_event, is_startup_user,
)
from routes_users import event_meta, check_personal

router = APIRouter(prefix="/api/auth")
MAX_ATTEMPTS = 5
LOCK_MINUTES = 15


class LoginIn(BaseModel):
    email: str
    password: str


class AcceptIn(BaseModel):
    token: str
    password: str


class PasswordIn(BaseModel):
    current_password: str
    new_password: str


class MeIn(BaseModel):
    nome: str = ""
    cognome: str = ""
    telefono: Optional[str] = None


async def me_payload(user):
    org = await db.organizations.find_one({"id": user["organization_id"]}, {"_id": 0})
    startup = None
    if is_startup_user(user):
        startup = await db.startups.find_one(alive({"organization_id": user["organization_id"]}), {"_id": 0})
    return {**user, "organization": org, "startup_id": startup["id"] if startup else None}


async def valid_invitation(token):
    inv = await db.invitations.find_one({"token_hash": hash_token(token), "deleted_at": None}, {"_id": 0})
    if not inv or inv["revoked_at"]:
        raise HTTPException(status_code=404, detail="Link di invito non valido o annullato")
    if inv["used_at"]:
        raise HTTPException(status_code=410, detail="Questo invito è già stato utilizzato")
    if datetime.fromisoformat(inv["expires_at"]) < datetime.now(TZ):
        raise HTTPException(status_code=410, detail="Il link di invito è scaduto: chiedi un nuovo invito")
    user = await db.users.find_one(alive({"id": inv["user_id"], "status": "INVITATO"}), {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Link di invito non valido o annullato")
    return inv, user


@router.post("/login")
async def login(body: LoginIn):
    email = body.email.strip().lower()
    att = await db.login_attempts.find_one({"identifier": email}, {"_id": 0})
    if att and att.get("locked_until") and datetime.fromisoformat(att["locked_until"]) > datetime.now(TZ):
        raise HTTPException(status_code=429, detail="Troppi tentativi falliti. Riprova tra qualche minuto.")
    user = await db.users.find_one(alive({"email": email}), {"_id": 0})
    if not user or not verify_password(body.password, user.get("password_hash")):
        count = (att or {}).get("count", 0) + 1
        locked = (datetime.now(TZ) + timedelta(minutes=LOCK_MINUTES)).isoformat() if count >= MAX_ATTEMPTS else None
        await db.login_attempts.update_one({"identifier": email},
                                           {"$set": {"count": 0 if locked else count, "locked_until": locked}}, upsert=True)
        raise HTTPException(status_code=401, detail="Email o password non corretti")
    if user["status"] != "ATTIVO":
        raise HTTPException(status_code=403, detail="Account non attivo. Contatta Nursery.")
    await db.login_attempts.delete_one({"identifier": email})
    user.pop("password_hash", None)
    return {"token": create_access_token(user["id"]), "user": await me_payload(user)}


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return await me_payload(user)


@router.patch("/me")
async def update_me(body: MeIn, user=Depends(get_current_user)):
    d = body.model_dump()
    check_personal(d)
    new = {"nome": d["nome"].strip(), "cognome": d["cognome"].strip(), "telefono": (d["telefono"] or "").strip() or None}
    changes = {k: {"from": user.get(k), "to": v} for k, v in new.items() if user.get(k) != v}
    if changes:
        await db.users.update_one({"id": user["id"]}, {"$set": {**new, "updated_at": now_iso()}})
        org = await db.organizations.find_one({"id": user["organization_id"]}, {"_id": 0})
        await log_event(user["id"], "USER", user["id"], "USER_UPDATED", {"email": user["email"], "changes": changes}, **await event_meta(org))
    return await me_payload(await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0}))


@router.post("/change-password")
async def change_password(body: PasswordIn, user=Depends(get_current_user)):
    full = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    if not verify_password(body.current_password, full.get("password_hash")):
        bad_request("La password attuale non è corretta")
    validate_password_strength(body.new_password)
    await db.users.update_one({"id": user["id"]}, {"$set": {"password_hash": hash_password(body.new_password), "updated_at": now_iso()}})
    org = await db.organizations.find_one({"id": user["organization_id"]}, {"_id": 0})
    await log_event(user["id"], "USER", user["id"], "PASSWORD_CHANGED", {"email": user["email"]}, **await event_meta(org))
    return {"ok": True}


@router.get("/invitation/{token}")
async def get_invitation(token: str):
    inv, user = await valid_invitation(token)
    org = await db.organizations.find_one({"id": user["organization_id"]}, {"_id": 0})
    return {"email": user["email"], "nome": user["nome"], "cognome": user["cognome"],
            "organization_name": org["name"] if org else None, "expires_at": inv["expires_at"]}


@router.post("/accept-invite")
async def accept_invite(body: AcceptIn):
    inv, user = await valid_invitation(body.token)
    validate_password_strength(body.password)
    t = now_iso()
    await db.users.update_one({"id": user["id"]}, {"$set": {"password_hash": hash_password(body.password), "status": "ATTIVO", "updated_at": t}})
    await db.invitations.update_one({"id": inv["id"]}, {"$set": {"used_at": t, "updated_at": t}})
    org = await db.organizations.find_one({"id": user["organization_id"]}, {"_id": 0})
    await log_event(user["id"], "USER", user["id"], "INVITE_ACCEPTED", {"email": user["email"]}, **await event_meta(org))
    user["status"] = "ATTIVO"
    return {"token": create_access_token(user["id"]), "user": await me_payload(user)}

