# Regression tests for Modulo 1 collaudo corrections: legal gate, services catalog, StartupService rules,
# provider fields, reset link, visibility, alerts
import os
import uuid
from datetime import date, timedelta

import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
PW = "Prova2026!"
CREDS = {
    "admin": ("admin@imment.it", "Nursery2026!"),
    "operatore": ("operatore@imment.test", PW),
    "prov_op": ("operativo@idaservizi.test", PW),
    "prov_prof": ("professionista@idaservizi.test", PW),
    "alfa_admin": ("admin@alfa.test", PW),
    "alfa_op": ("operativo@alfa.test", PW),
    "beta_admin": ("admin@beta.test", PW),
}
# admin@gamma.test intentionally left without legal acceptance for the UI LegalGate test
TODAY = date.today()
D = lambda n: (TODAY + timedelta(days=n)).isoformat()
CREATED = {"startups": [], "users": [], "services": [], "providers": []}
mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def uniq():
    return uuid.uuid4().hex[:6].upper()


def letters():
    return "".join(chr(65 + (int(c, 16) % 26)) for c in uuid.uuid4().hex[:2])


@pytest.fixture(scope="session")
def raw_tok():
    out = {}
    for k, (e, p) in CREDS.items():
        r = requests.post(f"{API}/auth/login", json={"email": e, "password": p})
        assert r.status_code == 200, f"login {k}: {r.status_code} {r.text}"
        out[k] = {"Authorization": f"Bearer {r.json()['token']}"}
    return out


@pytest.fixture(scope="session")
def tok(raw_tok):
    for k, h in raw_tok.items():
        pend = requests.get(f"{API}/auth/me", headers=h).json()["pending_legal"]
        if pend:
            r = requests.post(f"{API}/legal/accept", headers=h, json={"document_ids": [d["id"] for d in pend]})
            assert r.status_code == 200, r.text
    return raw_tok


@pytest.fixture(scope="session")
def ctx(tok):
    ss = requests.get(f"{API}/startups", headers=tok["admin"]).json()
    by = {s["codice_breve"]: s for s in ss}
    svcs = {s["codice"]: s for s in requests.get(f"{API}/services", headers=tok["admin"]).json()}
    lk = requests.get(f"{API}/lookups", headers=tok["admin"]).json()
    orgs = requests.get(f"{API}/organizations", headers=tok["admin"]).json()
    ida = [o for o in orgs if o["type"] == "PROVIDER" and o["name"].startswith("Ida")][0]
    users = requests.get(f"{API}/users", headers=tok["admin"]).json()
    ue = {u["email"]: u for u in users}
    yield {"ALFA": by["ALFA"], "BETA": by["BETA"], "GAMMA": by["GAMMA"], "svc": svcs, "lk": lk, "ida": ida, "ue": ue}
    for sid in CREATED["startups"]:
        requests.delete(f"{API}/startups/{sid}", headers=tok["admin"])
    for uid in CREATED["users"]:
        requests.post(f"{API}/users/{uid}/deactivate", headers=tok["admin"])
    for sid in CREATED["services"]:
        if requests.delete(f"{API}/services/{sid}", headers=tok["admin"]).status_code != 200:
            mdb.services.update_one({"id": sid}, {"$set": {"deleted_at": "test-cleanup"}})
    for oid in CREATED["providers"]:
        requests.delete(f"{API}/organizations/{oid}", headers=tok["admin"])


def payload(ctx, code=None, provider=True, servizi=None, **kw):
    p = {
        "denominazione": f"TEST Startup {code}", "codice_breve": code or ("TEST" + letters()),
        "codice_fiscale": "12345678901", "partita_iva": "12345678901", "sede_legale": "Via Test 1",
        "pec": "test@pec.test", "data_costituzione": "2024-01-01", "regime_iva": "MENSILE",
        "provider_organization_id": ctx["ida"]["id"] if provider else None,
        "service_profile_id": ctx["lk"]["service_profiles"][0]["id"],
        "servizi": servizi if servizi is not None else [{"service_id": ctx["svc"]["FATTURAZIONE_PER_CONTO"]["id"], "data_attivazione": D(0)}],
        "referente_nursery_user_id": ctx["lk"]["nursery_users"][0]["id"], "stato_cliente": "ONBOARDING",
    }
    p.update(kw)
    return p


def mk_startup(tok, ctx, **kw):
    r = requests.post(f"{API}/startups", headers=tok["admin"], json=payload(ctx, **kw))
    assert r.status_code == 200, r.text
    CREATED["startups"].append(r.json()["id"])
    return r.json()


def svc(ctx, code, att, cess=None):
    return {"service_id": ctx["svc"][code]["id"], "data_attivazione": att, "data_cessazione": cess}


# ---------- Legal gate ----------
class TestLegalGate:
    def test_pending_user_blocked_then_accepts(self, raw_tok):
        h = raw_tok["beta_admin"]
        me = requests.get(f"{API}/auth/me", headers=h)
        assert me.status_code == 200
        pend = me.json()["pending_legal"]
        if not pend:
            pytest.skip("beta_admin already accepted")
        assert {d["tipo"] for d in pend} == {"TERMINI_USO", "INFORMATIVA_PRIVACY"}
        r = requests.get(f"{API}/users", headers=h)
        assert r.status_code == 403 and "termini" in r.json()["detail"].lower()
        assert requests.get(f"{API}/legal/current", headers=h).status_code == 200
        r = requests.post(f"{API}/legal/accept", headers=h, json={"document_ids": [pend[0]["id"]]})
        assert r.status_code == 422
        r = requests.post(f"{API}/legal/accept", headers=h, json={"document_ids": [d["id"] for d in pend]})
        assert r.status_code == 200
        assert requests.get(f"{API}/users", headers=h).status_code == 200
        assert requests.get(f"{API}/auth/me", headers=h).json()["pending_legal"] == []


# ---------- Visibility / permissions ----------
class TestVisibility:
    def test_provider_cannot_see_gamma(self, tok, ctx):
        assert requests.get(f"{API}/startups/{ctx['GAMMA']['id']}", headers=tok["prov_op"]).status_code == 404
        codes = {s["codice_breve"] for s in requests.get(f"{API}/startups", headers=tok["prov_prof"]).json()}
        assert "GAMMA" not in codes and "ALFA" in codes

    def test_startup_user_scope(self, tok, ctx):
        assert requests.get(f"{API}/startups/{ctx['BETA']['id']}", headers=tok["alfa_admin"]).status_code == 404
        assert requests.get(f"{API}/startups/{ctx['ALFA']['id']}", headers=tok["alfa_op"]).status_code == 200

    def test_admin_startup_invite_only_own(self, tok, ctx):
        r = requests.post(f"{API}/users", headers=tok["alfa_admin"], json={
            "organization_id": ctx["BETA"]["organization_id"], "nome": "TEST", "cognome": "X",
            "email": f"test_{uniq()}@x.test", "role": "OPERATIVO_STARTUP"})
        assert r.status_code == 403
        r = requests.post(f"{API}/users", headers=tok["alfa_admin"], json={
            "organization_id": ctx["ALFA"]["organization_id"], "nome": "TEST", "cognome": "Own",
            "email": f"test_{uniq().lower()}@x.test", "role": "OPERATIVO_STARTUP"})
        assert r.status_code == 200, r.text
        CREATED["users"].append(r.json()["user"]["id"])

    def test_codice_breve_validation(self, tok, ctx):
        assert requests.post(f"{API}/startups", headers=tok["admin"], json=payload(ctx, code="AB")).status_code == 422
        r = requests.post(f"{API}/startups", headers=tok["admin"], json=payload(ctx, code="ALFA"))
        assert r.status_code == 409

    def test_service_profile_hidden_and_referente_shown(self, tok, ctx):
        for k in ("alfa_admin", "alfa_op", "prov_op"):
            d = requests.get(f"{API}/startups/{ctx['ALFA']['id']}", headers=tok[k]).json()
            assert "service_profile_id" not in d and "service_profile_name" not in d, k
            assert d["referente"] and d["referente"].get("email"), k
        for s in requests.get(f"{API}/startups", headers=tok["prov_op"]).json():
            assert "service_profile_id" not in s and "service_profile_name" not in s
        assert "service_profile_name" in requests.get(f"{API}/startups/{ctx['ALFA']['id']}", headers=tok["admin"]).json()

    def test_provider_data_visibility(self, tok, ctx):
        d = requests.get(f"{API}/startups/{ctx['ALFA']['id']}", headers=tok["alfa_admin"]).json()
        assert set(d["provider"].keys()) <= {"id", "name", "nome_portale"}
        assert d["provider"]["nome_portale"] == "Impresa Digitale"
        assert d["link_portale_provider"]
        d = requests.get(f"{API}/startups/{ctx['ALFA']['id']}", headers=tok["prov_op"]).json()
        assert "partita_iva" in d["provider"] and "referente_email" in d["provider"]

    def test_servizi_visibility_non_nursery(self, tok, ctx):
        for k in ("alfa_admin", "prov_op"):
            d = requests.get(f"{API}/startups/{ctx['ALFA']['id']}", headers=tok[k]).json()
            assert d["servizi"]
            for s in d["servizi"]:
                assert s["stato"] in ("ATTIVO", "PROGRAMMATO")
                assert "data_cessazione" not in s and "id" not in s
        d = requests.get(f"{API}/startups/{ctx['ALFA']['id']}", headers=tok["admin"]).json()
        assert all("data_cessazione" in s for s in d["servizi"])

    def test_non_nursery_events_only_all(self, tok, ctx):
        for k in ("alfa_admin", "prov_op"):
            ev = requests.get(f"{API}/startups/{ctx['ALFA']['id']}/events", headers=tok[k]).json()
            assert all(e["visibility"] == "ALL" for e in ev)
            assert not any(e["action"].startswith("STARTUP_SERVICE") for e in ev)

    def test_services_api_nursery_only(self, tok):
        assert requests.get(f"{API}/services", headers=tok["alfa_admin"]).status_code == 403
        assert requests.get(f"{API}/services", headers=tok["prov_op"]).status_code == 403
        assert requests.get(f"{API}/services", headers=tok["operatore"]).status_code == 200
        assert requests.post(f"{API}/services", headers=tok["operatore"], json={"codice": "TEST_X", "nome": "x", "categoria": "SERVIZIO_NURSERY"}).status_code == 403


# ---------- Services catalog ----------
class TestServicesCatalog:
    def test_migrated_services(self, ctx):
        s = ctx["svc"]
        assert s["AFC_COMPLETO"]["categoria"] == "SERVIZIO_PROVIDER" and s["AFC_COMPLETO"]["richiede_provider"]
        assert s["PAGHE"]["richiede_provider"]
        assert s["SOLO_CASH_FLOW"]["categoria"] == "SERVIZIO_NURSERY" and not s["SOLO_CASH_FLOW"]["richiede_provider"]
        assert s["AFC_COMPLETO"]["id"] in s["SOLO_CASH_FLOW"]["servizi_incompatibili"]
        assert s["SOLO_CASH_FLOW"]["id"] in s["AFC_COMPLETO"]["servizi_incompatibili"]

    def test_crud_codice_immutable_incompat_reciprocal(self, tok, ctx):
        code = f"test_svc_{uniq()}"
        r = requests.post(f"{API}/services", headers=tok["admin"], json={"codice": code, "nome": f"TEST Svc {code}", "categoria": "SERVIZIO_NURSERY"})
        assert r.status_code == 200, r.text
        a = r.json(); CREATED["services"].append(a["id"])
        assert a["codice"] == code.upper()
        assert requests.post(f"{API}/services", headers=tok["admin"], json={"codice": code, "nome": "dup", "categoria": "SERVIZIO_NURSERY"}).status_code == 409
        r = requests.put(f"{API}/services/{a['id']}", headers=tok["admin"], json={"codice": "TEST_OTHER", "nome": a["nome"], "categoria": "SERVIZIO_NURSERY"})
        assert r.status_code == 422
        code2 = f"TEST_SVC_{uniq()}"
        r = requests.post(f"{API}/services", headers=tok["admin"], json={"codice": code2, "nome": f"TEST Svc {code2}", "categoria": "SERVIZIO_PROVIDER", "servizi_incompatibili": [a["id"]]})
        assert r.status_code == 200, r.text
        b = r.json(); CREATED["services"].append(b["id"])
        lst = {s["id"]: s for s in requests.get(f"{API}/services", headers=tok["admin"]).json()}
        assert b["id"] in lst[a["id"]]["servizi_incompatibili"]
        assert requests.post(f"{API}/services", headers=tok["admin"], json={"codice": "TEST_Y", "nome": "y", "categoria": "BAD"}).status_code == 422
        # delete unlinked
        assert requests.delete(f"{API}/services/{b['id']}", headers=tok["admin"]).status_code == 200
        lst = {s["id"]: s for s in requests.get(f"{API}/services", headers=tok["admin"]).json()}
        assert b["id"] not in lst and b["id"] not in lst[a["id"]]["servizi_incompatibili"]

    def test_linked_delete_409_deactivate_stays(self, tok, ctx):
        code = f"TEST_LNK_{uniq()}"
        s = requests.post(f"{API}/services", headers=tok["admin"], json={"codice": code, "nome": f"TEST Linked {code}", "categoria": "SERVIZIO_NURSERY"}).json()
        CREATED["services"].append(s["id"])
        st = mk_startup(tok, ctx, servizi=[{"service_id": s["id"], "data_attivazione": D(0)}])
        r = requests.delete(f"{API}/services/{s['id']}", headers=tok["admin"])
        assert r.status_code == 409, r.text
        r = requests.put(f"{API}/services/{s['id']}", headers=tok["admin"], json={**{k: s[k] for k in ("codice", "nome", "descrizione", "categoria", "richiede_provider", "ordine")}, "attivo": False})
        assert r.status_code == 200 and r.json()["attivo"] is False
        got = requests.get(f"{API}/startups/{st['id']}", headers=tok["admin"]).json()
        assert any(x["service_id"] == s["id"] for x in got["servizi"])
        r = requests.post(f"{API}/startups", headers=tok["admin"], json=payload(ctx, servizi=[{"service_id": s["id"], "data_attivazione": D(0)}]))
        assert r.status_code == 422
        # existing startup still saves with deactivated service kept
        body = payload(ctx, code=got["codice_breve"], servizi=[{"id": x["id"], "service_id": x["service_id"], "data_attivazione": x["data_attivazione"], "data_cessazione": x["data_cessazione"]} for x in got["servizi"]])
        body["denominazione"] = got["denominazione"]
        assert requests.put(f"{API}/startups/{st['id']}", headers=tok["admin"], json=body).status_code == 200


# ---------- StartupService rules ----------
class TestServiceRules:
    def test_incompatible_overlap(self, tok, ctx):
        r = requests.post(f"{API}/startups", headers=tok["admin"], json=payload(ctx, servizi=[svc(ctx, "SOLO_CASH_FLOW", D(0)), svc(ctx, "AFC_COMPLETO", D(10))]))
        assert r.status_code == 422
        det = r.json()["detail"]
        assert ctx["svc"]["SOLO_CASH_FLOW"]["nome"] in det and ctx["svc"]["AFC_COMPLETO"]["nome"] in det

    def test_incompatible_non_overlap_ok(self, tok, ctx):
        st = mk_startup(tok, ctx, servizi=[svc(ctx, "SOLO_CASH_FLOW", D(-60), D(-1)), svc(ctx, "AFC_COMPLETO", D(0))])
        stati = {x["codice"]: x["stato"] for x in st["servizi"]}
        assert stati == {"SOLO_CASH_FLOW": "CESSATO", "AFC_COMPLETO": "ATTIVO"}

    def test_requires_provider(self, tok, ctx):
        r = requests.post(f"{API}/startups", headers=tok["admin"], json=payload(ctx, provider=False, servizi=[svc(ctx, "PAGHE", D(0))]))
        assert r.status_code == 422 and ctx["svc"]["PAGHE"]["nome"] in r.json()["detail"]

    def test_no_live_service(self, tok, ctx):
        r = requests.post(f"{API}/startups", headers=tok["admin"], json=payload(ctx, servizi=[svc(ctx, "FATTURAZIONE_PER_CONTO", D(-30), D(-2))]))
        assert r.status_code == 422 and "almeno un servizio" in r.json()["detail"]
        r = requests.post(f"{API}/startups", headers=tok["admin"], json=payload(ctx, servizi=[]))
        assert r.status_code == 422

    def test_cessazione_before_attivazione(self, tok, ctx):
        r = requests.post(f"{API}/startups", headers=tok["admin"], json=payload(ctx, servizi=[svc(ctx, "FATTURAZIONE_PER_CONTO", D(0), D(-5))]))
        assert r.status_code == 422 and ctx["svc"]["FATTURAZIONE_PER_CONTO"]["nome"] in r.json()["detail"]

    def test_programmato_and_events_nursery_only(self, tok, ctx):
        st = mk_startup(tok, ctx, servizi=[svc(ctx, "FATTURAZIONE_PER_CONTO", D(0)), svc(ctx, "PAGHE", D(30))])
        stati = {x["codice"]: x["stato"] for x in st["servizi"]}
        assert stati["PAGHE"] == "PROGRAMMATO"
        ev = requests.get(f"{API}/startups/{st['id']}/events", headers=tok["admin"]).json()
        se = [e for e in ev if e["action"].startswith("STARTUP_SERVICE")]
        assert len(se) == 2 and all(e["visibility"] == "NURSERY_ONLY" for e in se)
        # existing record cannot be removed
        body = payload(ctx, code=st["codice_breve"], servizi=[{"id": st["servizi"][0]["id"], "service_id": st["servizi"][0]["service_id"], "data_attivazione": st["servizi"][0]["data_attivazione"]}])
        body["denominazione"] = st["denominazione"]
        assert requests.put(f"{API}/startups/{st['id']}", headers=tok["admin"], json=body).status_code == 422

    def test_cessato_startup_no_live_required(self, tok, ctx):
        st = mk_startup(tok, ctx, servizi=[svc(ctx, "FATTURAZIONE_PER_CONTO", D(-30), D(-2))], stato_cliente="CESSATO")
        assert st["stato_cliente"] == "CESSATO"
        mdb.startups.update_one({"id": st["id"]}, {"$set": {"stato_cliente": "ONBOARDING"}})  # allow cleanup delete


# ---------- Provider fields ----------
class TestProviders:
    def test_create_requires_piva_pec(self, tok):
        r = requests.post(f"{API}/organizations", headers=tok["admin"], json={"name": f"TEST Prov {uniq()}", "pec": "a@pec.it"})
        assert r.status_code == 422
        r = requests.post(f"{API}/organizations", headers=tok["admin"], json={"name": f"TEST Prov {uniq()}", "partita_iva": "12345678901", "pec": "a@pec.it", "nome_portale": "P", "url_portale": "https://p.test"})
        assert r.status_code == 200, r.text
        CREATED["providers"].append(r.json()["id"])
        orgs = {o["id"]: o for o in requests.get(f"{API}/organizations?type=PROVIDER", headers=tok["admin"]).json()}
        assert orgs[r.json()["id"]]["dati_incompleti"] is False
        assert [o for o in orgs.values() if o["name"].startswith("Ida")][0]["dati_incompleti"] is True
        assert requests.put(f"{API}/organizations/{r.json()['id']}", headers=tok["operatore"], json={"name": "x"}).status_code == 403
        r2 = requests.put(f"{API}/organizations/{r.json()['id']}", headers=tok["admin"], json={**r.json(), "url_portale": "ftp://bad"})
        assert r2.status_code == 422


# ---------- Reset link ----------
class TestResetLink:
    def test_permissions(self, tok, ctx):
        ue = ctx["ue"]
        assert requests.post(f"{API}/users/{ue['admin@imment.it']['id']}/reset-link", headers=tok["operatore"]).status_code == 403
        assert requests.post(f"{API}/users/{ue['admin@beta.test']['id']}/reset-link", headers=tok["alfa_admin"]).status_code == 403
        assert requests.post(f"{API}/users/{ue['operativo@alfa.test']['id']}/reset-link", headers=tok["prov_op"]).status_code == 403
        assert requests.post(f"{API}/users/{ue['operativo@alfa.test']['id']}/reset-link", headers=tok["alfa_op"]).status_code == 403

    def test_invited_user_409(self, tok, ctx):
        r = requests.post(f"{API}/users", headers=tok["admin"], json={"organization_id": ctx["ALFA"]["organization_id"], "nome": "TEST", "cognome": "Inv",
                                                                       "email": f"test_{uniq().lower()}@x.test", "role": "OPERATIVO_STARTUP"})
        uid = r.json()["user"]["id"]; CREATED["users"].append(uid)
        assert requests.post(f"{API}/users/{uid}/reset-link", headers=tok["admin"]).status_code == 409

    def test_flow_revoke_use(self, tok, ctx):
        uid = ctx["ue"]["operativo@alfa.test"]["id"]
        t1 = requests.post(f"{API}/users/{uid}/reset-link", headers=tok["alfa_admin"]).json()["invite_token"]
        assert requests.get(f"{API}/auth/reset/{t1}").status_code == 200
        r = requests.post(f"{API}/users/{uid}/reset-link", headers=tok["operatore"])
        assert r.status_code == 200
        t2 = r.json()["invite_token"]
        assert requests.get(f"{API}/auth/reset/{t1}").status_code == 404
        assert requests.post(f"{API}/auth/reset-password", json={"token": t2, "password": "short"}).status_code == 422
        r = requests.post(f"{API}/auth/reset-password", json={"token": t2, "password": PW})
        assert r.status_code == 200 and r.json()["token"]
        assert requests.post(f"{API}/auth/reset-password", json={"token": t2, "password": PW}).status_code == 410
        assert requests.post(f"{API}/auth/login", json={"email": "operativo@alfa.test", "password": PW}).status_code == 200
        ev = requests.get(f"{API}/startups/{ctx['ALFA']['id']}/events", headers=tok["alfa_admin"]).json()
        acts = {e["action"] for e in ev}
        assert "PASSWORD_RESET_LINK_CREATED" in acts and "PASSWORD_RESET_COMPLETED" in acts
        # invite token must not be usable as reset token
        assert requests.get(f"{API}/auth/invitation/{t2}").status_code in (404, 410)


# ---------- Alerts ----------
class TestAlerts:
    def _alert_for(self, tok, ctx, st):
        email = f"test_{uniq().lower()}@x.test"
        r = requests.post(f"{API}/users", headers=tok["admin"], json={"organization_id": st["organization_id"], "nome": "TEST", "cognome": "Alert",
                                                                       "email": email, "role": "ADMIN_STARTUP"})
        assert r.status_code == 200, r.text
        uid = r.json()["user"]["id"]; CREATED["users"].append(uid)
        al = [a for a in requests.get(f"{API}/alerts?stato=DA_GESTIRE", headers=tok["admin"]).json() if a["entity_id"] == uid]
        assert len(al) == 1
        return al[0], uid

    def test_ack_cancel_role(self, tok, ctx):
        st = mk_startup(tok, ctx)
        c0 = requests.get(f"{API}/alerts/count", headers=tok["admin"]).json()["da_gestire"]
        a1, _ = self._alert_for(tok, ctx, st)
        assert requests.get(f"{API}/alerts/count", headers=tok["operatore"]).json()["da_gestire"] == c0 + 1
        assert requests.post(f"{API}/alerts/{a1['id']}/ack", headers=tok["operatore"]).status_code == 200
        assert requests.post(f"{API}/alerts/{a1['id']}/ack", headers=tok["admin"]).status_code == 409
        assert requests.get(f"{API}/alerts/count", headers=tok["admin"]).json()["da_gestire"] == c0
        done = {a["id"]: a for a in requests.get(f"{API}/alerts?stato=GESTITE", headers=tok["admin"]).json()}
        assert done[a1["id"]]["handling"]["handled_by_name"] and done[a1["id"]]["handling"]["azione"] == "PRESA_VISIONE"
        allv = requests.get(f"{API}/alerts", headers=tok["admin"]).json()
        handled_flags = [bool(a["handling"]) for a in allv]
        assert handled_flags == sorted(handled_flags)  # unhandled first
        a2, u2 = self._alert_for(tok, ctx, st)
        assert requests.post(f"{API}/alerts/{a2['id']}/cancel-invite", headers=tok["admin"]).status_code == 200
        assert requests.post(f"{API}/alerts/{a2['id']}/cancel-invite", headers=tok["admin"]).status_code == 409
        a3, u3 = self._alert_for(tok, ctx, st)
        assert requests.post(f"{API}/alerts/{a3['id']}/change-role", headers=tok["admin"], json={"role": "OPERATIVO_STARTUP"}).status_code == 200
        users = {u["id"]: u for u in requests.get(f"{API}/users", headers=tok["admin"]).json()}
        assert users[u2]["status"] == "DISATTIVATO" and users[u3]["role"] == "OPERATIVO_STARTUP"
        done = {a["id"]: a for a in requests.get(f"{API}/alerts?stato=GESTITE", headers=tok["admin"]).json()}
        assert done[a2["id"]]["handling"]["azione"] == "INVITO_ANNULLATO" and done[a3["id"]]["handling"]["azione"] == "RUOLO_CAMBIATO"
        assert requests.get(f"{API}/alerts/count", headers=tok["admin"]).json()["da_gestire"] == c0

    def test_alerts_forbidden_non_nursery(self, tok):
        assert requests.get(f"{API}/alerts", headers=tok["alfa_admin"]).status_code == 403
        assert requests.get(f"{API}/alerts/count", headers=tok["prov_op"]).status_code == 403


# ---------- Legal documents publish (runs last; state restored via DB) ----------
class TestZLegalPublish:
    def test_draft_publish_forces_reaccept(self, tok):
        h = tok["admin"]
        assert requests.get(f"{API}/legal/documents", headers=tok["operatore"]).status_code == 403
        ver = f"TEST-{uniq()}"
        r = requests.post(f"{API}/legal/documents", headers=h, json={"tipo": "TERMINI_USO", "versione": ver, "testo": "TEST testo"})
        assert r.status_code == 200, r.text
        did = r.json()["id"]
        try:
            assert requests.post(f"{API}/legal/documents", headers=h, json={"tipo": "TERMINI_USO", "versione": ver, "testo": "x"}).status_code == 409
            assert requests.put(f"{API}/legal/documents/{did}", headers=h, json={"tipo": "TERMINI_USO", "versione": ver, "testo": "TEST testo 2"}).status_code == 200
            assert requests.get(f"{API}/auth/me", headers=h).json()["pending_legal"] == []
            assert requests.post(f"{API}/legal/documents/{did}/publish", headers=h).status_code == 200
            pend = requests.get(f"{API}/auth/me", headers=h).json()["pending_legal"]
            assert [d["id"] for d in pend] == [did]
            assert requests.get(f"{API}/startups", headers=h).status_code == 403
            assert requests.post(f"{API}/legal/accept", headers=h, json={"document_ids": [did]}).status_code == 200
            assert requests.get(f"{API}/startups", headers=h).status_code == 200
            assert requests.put(f"{API}/legal/documents/{did}", headers=h, json={"tipo": "TERMINI_USO", "versione": ver, "testo": "z"}).status_code == 409
            assert requests.delete(f"{API}/legal/documents/{did}", headers=h).status_code == 409
        finally:
            mdb.legal_documents.delete_one({"id": did})
            mdb.legal_acceptances.delete_many({"legal_document_id": did})
            mdb.legal_documents.update_one({"tipo": "TERMINI_USO", "versione": "1.0"}, {"$set": {"attivo": True}})
