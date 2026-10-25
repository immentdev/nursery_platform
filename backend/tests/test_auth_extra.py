# Auth extras: bcrypt format, brute-force lock, expired invite
import os
import uuid
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
API = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/") + "/api"
mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def test_bcrypt_hash():
    u = mdb.users.find_one({"email": "admin@imment.it"})
    assert u["password_hash"].startswith("$2b$")


def test_lockout_unknown_email():
    email = f"test_lock_{uuid.uuid4().hex[:6]}@example.test"
    codes = [requests.post(f"{API}/auth/login", json={"email": email, "password": "x"}).status_code for _ in range(6)]
    assert codes[:5] == [401] * 5 and codes[5] == 429
    mdb.login_attempts.delete_one({"identifier": email})


def test_expired_invite():
    r = requests.post(f"{API}/auth/login", json={"email": "admin@imment.it", "password": "Nursery2026!"})
    h = {"Authorization": f"Bearer {r.json()['token']}"}
    orgs = requests.get(f"{API}/organizations", headers=h, params={"type": "PROVIDER"}).json()
    ida = [o for o in orgs if o["name"].startswith("Ida")][0]
    inv = requests.post(f"{API}/users", headers=h, json={"organization_id": ida["id"], "nome": "T", "cognome": "Exp",
                                                         "email": f"test_exp_{uuid.uuid4().hex[:6]}@example.test",
                                                         "role": "OPERATIVO_PROVIDER", "competence_areas": ["PAGHE"]})
    assert inv.status_code == 200
    uid = inv.json()["user"]["id"]
    mdb.invitations.update_one({"user_id": uid, "used_at": None, "revoked_at": None},
                               {"$set": {"expires_at": "2020-01-01T00:00:00+01:00"}})
    g = requests.get(f"{API}/auth/invitation/{inv.json()['invite_token']}")
    assert g.status_code == 410 and "scaduto" in g.json()["detail"]
    requests.post(f"{API}/users/{uid}/deactivate", headers=h)
