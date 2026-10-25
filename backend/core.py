import os
import re
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import bcrypt
import jwt
from fastapi import HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorClient

TZ = ZoneInfo("Europe/Rome")
client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_HOURS = 8
INVITE_DAYS = 7

NURSERY_ROLES = {"ADMIN_NURSERY", "OPERATORE_NURSERY"}
PROVIDER_ROLES = {"OPERATIVO_PROVIDER", "PROFESSIONISTA_PROVIDER"}
STARTUP_ROLES = {"ADMIN_STARTUP", "OPERATIVO_STARTUP"}
ROLES_BY_ORG_TYPE = {"NURSERY": NURSERY_ROLES, "PROVIDER": PROVIDER_ROLES, "STARTUP": STARTUP_ROLES}
COMPETENCE_AREAS = {"CONTABILITA", "PAGHE"}
SERVIZI = {"AFC_COMPLETO", "SOLO_CASH_FLOW", "FATTURAZIONE_PER_CONTO", "PAGHE"}
STATI_CLIENTE = {"ONBOARDING", "ATTIVO", "SOSPESO", "CESSATO"}
REGIMI_IVA = {"MENSILE", "TRIMESTRALE"}

NO_ID = {"_id": 0}
PUBLIC_USER = {"_id": 0, "password_hash": 0}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def now_iso() -> str:
    return datetime.now(TZ).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


def base_fields(actor_id):
    t = now_iso()
    return {"id": new_id(), "created_at": t, "updated_at": t, "created_by": actor_id, "deleted_at": None}


def alive(extra=None):
    q = {"deleted_at": None}
    q.update(extra or {})
    return q


def bad_request(msg):
    raise HTTPException(status_code=422, detail=msg)


def forbidden(msg="Operazione non consentita per il tuo ruolo"):
    raise HTTPException(status_code=403, detail=msg)


def not_found(msg="Risorsa non trovata"):
    raise HTTPException(status_code=404, detail=msg)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bool(hashed) and bcrypt.checkpw(plain.encode(), hashed.encode())


def validate_password_strength(pw: str):
    if len(pw) < 8 or not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw):
        bad_request("La password deve avere almeno 8 caratteri e contenere lettere e numeri")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(user_id: str) -> str:
    payload = {"sub": user_id, "type": "access", "exp": datetime.now(TZ) + timedelta(hours=ACCESS_TOKEN_HOURS)}
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=JWT_ALGORITHM)


async def get_current_user(request: Request) -> dict:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Autenticazione richiesta")
    try:
        payload = jwt.decode(header[7:], os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Sessione scaduta, accedi di nuovo")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token non valido")
    user = await db.users.find_one(alive({"id": payload.get("sub")}), PUBLIC_USER)
    if not user or user["status"] != "ATTIVO":
        raise HTTPException(status_code=401, detail="Utente non attivo")
    return user


def is_nursery(u):
    return u["role"] in NURSERY_ROLES


def is_provider(u):
    return u["role"] in PROVIDER_ROLES


def is_startup_user(u):
    return u["role"] in STARTUP_ROLES


def require_nursery(u):
    if not is_nursery(u):
        forbidden()


def require_admin_nursery(u):
    if u["role"] != "ADMIN_NURSERY":
        forbidden("Operazione riservata all'amministratore Nursery")


def startup_scope(u) -> dict:
    if is_nursery(u):
        return alive()
    if is_provider(u):
        return alive({"provider_organization_id": u["organization_id"]})
    return alive({"organization_id": u["organization_id"]})


async def get_visible_startup(u, startup_id) -> dict:
    doc = await db.startups.find_one({**startup_scope(u), "id": startup_id}, NO_ID)
    if not doc:
        not_found("Startup non trovata o non accessibile")
    return doc


def can_manage(actor, org, role) -> bool:
    if role not in ROLES_BY_ORG_TYPE[org["type"]]:
        return False
    r = actor["role"]
    if r == "ADMIN_NURSERY":
        return True
    if r == "OPERATORE_NURSERY":
        return org["type"] != "NURSERY"
    if r == "ADMIN_STARTUP":
        return org["id"] == actor["organization_id"]
    return False


def user_label(u):
    return f"{u['nome']} {u['cognome']}" if u else None


async def log_event(actor_id, entity_type, entity_id, action, details=None, visibility="ALL",
                    startup_id=None, nursery_alert=False):
    t = now_iso()
    await db.event_logs.insert_one({
        **base_fields(actor_id),
        "actor_user_id": actor_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "startup_id": startup_id,
        "action": action,
        "details": details or {},
        "visibility": visibility,
        "nursery_alert": nursery_alert,
        "timestamp": t,
    })


async def create_invitation(user_id, actor_id):
    t = now_iso()
    await db.invitations.update_many(
        {"user_id": user_id, "used_at": None, "revoked_at": None},
        {"$set": {"revoked_at": t, "updated_at": t}},
    )
    token = secrets.token_urlsafe(32)
    expires = (datetime.now(TZ) + timedelta(days=INVITE_DAYS)).isoformat()
    await db.invitations.insert_one({
        **base_fields(actor_id),
        "user_id": user_id,
        "token_hash": hash_token(token),
        "expires_at": expires,
        "used_at": None,
        "revoked_at": None,
    })
    return token, expires


async def revoke_invitations(user_id):
    t = now_iso()
    await db.invitations.update_many(
        {"user_id": user_id, "used_at": None, "revoked_at": None},
        {"$set": {"revoked_at": t, "updated_at": t}},
    )
