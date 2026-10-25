from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import (
    db, alive, base_fields, now_iso, bad_request, not_found, get_user_any, get_current_user,
    require_admin_nursery, log_event, pending_legal,
)

router = APIRouter(prefix="/api/legal")
TIPI = {"TERMINI_USO", "INFORMATIVA_PRIVACY"}


class LegalIn(BaseModel):
    tipo: str = ""
    versione: str = ""
    testo: str = ""


class AcceptIn(BaseModel):
    document_ids: list[str] = []


@router.get("/current")
async def current_documents(user=Depends(get_user_any)):
    return await db.legal_documents.find(alive({"attivo": True, "data_pubblicazione": {"$ne": None}}), {"_id": 0}).sort("tipo", 1).to_list(10)


@router.post("/accept")
async def accept(body: AcceptIn, user=Depends(get_user_any)):
    from routes_users import event_meta
    pending = await pending_legal(user)
    if not pending:
        return {"ok": True}
    if {d["id"] for d in pending} - set(body.document_ids):
        bad_request("Devi accettare tutti i documenti in vigore")
    t = now_iso()
    for d in pending:
        await db.legal_acceptances.insert_one({
            **base_fields(user["id"]), "user_id": user["id"], "legal_document_id": d["id"],
            "tipo": d["tipo"], "versione": d["versione"], "accepted_at": t,
        })
    org = await db.organizations.find_one({"id": user["organization_id"]}, {"_id": 0})
    await log_event(user["id"], "USER", user["id"], "LEGAL_ACCEPTED",
                    {"email": user["email"], "documenti": [f"{d['tipo']} v{d['versione']}" for d in pending]}, **await event_meta(org))
    return {"ok": True}


@router.get("/documents")
async def list_documents(user=Depends(get_current_user)):
    require_admin_nursery(user)
    return await db.legal_documents.find(alive(), {"_id": 0}).sort([("tipo", 1), ("created_at", -1)]).to_list(500)


async def validated(body, current_id=None):
    d = {"tipo": body.tipo, "versione": body.versione.strip(), "testo": body.testo.strip()}
    if d["tipo"] not in TIPI:
        bad_request("Tipo documento non valido")
    if not d["versione"] or not d["testo"]:
        bad_request("Versione e testo sono obbligatori")
    if await db.legal_documents.find_one(alive({"tipo": d["tipo"], "versione": d["versione"], "id": {"$ne": current_id}})):
        raise HTTPException(status_code=409, detail=f"Esiste già la versione {d['versione']} di questo documento")
    return d


async def get_draft(did):
    doc = await db.legal_documents.find_one(alive({"id": did}), {"_id": 0})
    if not doc:
        not_found("Documento non trovato")
    if doc["data_pubblicazione"]:
        raise HTTPException(status_code=409, detail="Un documento pubblicato non è modificabile: crea una nuova versione")
    return doc


@router.post("/documents")
async def create_draft(body: LegalIn, user=Depends(get_current_user)):
    require_admin_nursery(user)
    d = await validated(body)
    doc = {**base_fields(user["id"]), **d, "data_pubblicazione": None, "attivo": False}
    await db.legal_documents.insert_one(dict(doc))
    await log_event(user["id"], "LEGAL_DOCUMENT", doc["id"], "LEGAL_DRAFT_CREATED", {"tipo": d["tipo"], "versione": d["versione"]})
    return doc


@router.put("/documents/{did}")
async def update_draft(did: str, body: LegalIn, user=Depends(get_current_user)):
    require_admin_nursery(user)
    old = await get_draft(did)
    d = await validated(body, did)
    await db.legal_documents.update_one({"id": did}, {"$set": {**d, "updated_at": now_iso()}})
    await log_event(user["id"], "LEGAL_DOCUMENT", did, "LEGAL_DRAFT_UPDATED", {"tipo": d["tipo"], "versione": d["versione"], "versione_precedente": old["versione"]})
    return await db.legal_documents.find_one({"id": did}, {"_id": 0})


@router.post("/documents/{did}/publish")
async def publish(did: str, user=Depends(get_current_user)):
    require_admin_nursery(user)
    doc = await get_draft(did)
    t = now_iso()
    await db.legal_documents.update_many(alive({"tipo": doc["tipo"], "attivo": True}), {"$set": {"attivo": False, "updated_at": t}})
    await db.legal_documents.update_one({"id": did}, {"$set": {"data_pubblicazione": t, "attivo": True, "updated_at": t}})
    await log_event(user["id"], "LEGAL_DOCUMENT", did, "LEGAL_PUBLISHED", {"tipo": doc["tipo"], "versione": doc["versione"]})
    return await db.legal_documents.find_one({"id": did}, {"_id": 0})


@router.delete("/documents/{did}")
async def delete_draft(did: str, user=Depends(get_current_user)):
    require_admin_nursery(user)
    doc = await get_draft(did)
    t = now_iso()
    await db.legal_documents.update_one({"id": did}, {"$set": {"deleted_at": t, "updated_at": t}})
    await log_event(user["id"], "LEGAL_DOCUMENT", did, "LEGAL_DRAFT_DELETED", {"tipo": doc["tipo"], "versione": doc["versione"]})
    return {"ok": True}
