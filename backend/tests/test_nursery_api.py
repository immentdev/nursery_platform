# Regression tests for Piattaforma Nursery Modulo 1: permission matrix, visibility, invites, rules
import os
import uuid
import pytest
import requests

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
    "gamma_admin": ("admin@gamma.test", PW),
}
CREATED_STARTUPS = []
CREATED_USERS = []


def uniq():
    return uuid.uuid4().hex[:8]


def letters():
    return "".join(chr(65 + (int(c, 16) % 26)) for c in uuid.uuid4().hex[:2])


@pytest.fixture(scope="session")
def tok():
    out = {}
    for k, (e, p) in CREDS.items():
        r = requests.post(f"{API}/auth/login", json={"email": e, "password": p})
        assert r.status_code == 200, f"login {k}: {r.status_code} {r.text}"
        out[k] = {"Authorization": f"Bearer {r.json()['token']}"}
    return out


@pytest.fixture(scope="session")
def ctx(tok):
    ss = requests.get(f"{API}/startups", headers=tok["admin"]).json()
    by = {s["codice_breve"]: s for s in ss}
    lk = requests.get(f"{API}/lookups", headers=tok["admin"]).json()
    orgs = requests.get(f"{API}/organizations", headers=tok["admin"]).json()
    nursery = [o for o in orgs if o["type"] == "NURSERY"][0]
    ida = [o for o in orgs if o["type"] == "PROVIDER" and o["name"].startswith("Ida")][0]
    yield {"ALFA": by["ALFA"], "BETA": by["BETA"], "GAMMA": by["GAMMA"], "lk": lk, "nursery": nursery, "ida": ida}
    # cleanup
    for sid in CREATED_STARTUPS:
        requests.delete(f"{API}/startups/{sid}", headers=tok["admin"])
    for uid in CREATED_USERS:
        requests.post(f"{API}/users/{uid}/deactivate", headers=tok["admin"])


def startup_payload(ctx, code, provider=True, servizi=None, **kw):
    p = {
        "denominazione": f"TEST Startup {code}", "codice_breve": code, "codice_fiscale": "12345678901",
        "partita_iva": "12345678901", "sede_legale": "Via Test 1", "pec": "test@pec.test",
        "data_costituzione": "2024-01-01", "regime_iva": "MENSILE",
        "provider_organization_id": ctx["ida"]["id"] if provider else None,
        "service_profile_id": ctx["lk"]["service_profiles"][0]["id"],
        "servizi_attivi": servizi if servizi is not None else ["FATTURAZIONE_PER_CONTO"],
        "referente_nursery_user_id": ctx["lk"]["nursery_users"][0]["id"], "stato_cliente": "ONBOARDING",
    }
    p.update(kw)
    return p


def create_startup(tok, ctx, **kw):
    code = "TEST" + letters()
    r = requests.post(f"{API}/startups", headers=tok["admin"], json=startup_payload(ctx, code, **kw))
    assert r.status_code == 200, r.text
    CREATED_STARTUPS.append(r.json()["id"])
    return r.json()


def invite(tok_h, org_id, role, accept=True):
    email = f"test_{uniq()}@example.test"
    r = requests.post(f"{API}/users", headers=tok_h, json={"organization_id": org_id, "nome": "Test", "cognome": "User",
                                                           "email": email, "role": role})
    if r.status_code != 200:
        return r, None
    CREATED_USERS.append(r.json()["user"]["id"])
    headers = None
    if accept:
        a = requests.post(f"{API}/auth/accept-invite", json={"token": r.json()["invite_token"], "password": "TestPass123"})
        assert a.status_code == 200, a.text
        headers = {"Authorization": f"Bearer {a.json()['token']}"}
    return r, headers


# --- Acceptance 1: permission matrix ---
class TestMatrix:
    def test_list_startups(self, tok, ctx):
        for k in ("admin", "operatore"):
            r = requests.get(f"{API}/startups", headers=tok[k])
            assert r.status_code == 200 and {"ALFA", "BETA", "GAMMA"} <= {s["codice_breve"] for s in r.json()}
        for k in ("prov_op", "prov_prof"):
            codes = {s["codice_breve"] for s in requests.get(f"{API}/startups", headers=tok[k]).json()}
            assert {"ALFA", "BETA"} <= codes and "GAMMA" not in codes
            assert all(s["provider_organization_id"] == ctx["ida"]["id"] for s in requests.get(f"{API}/startups", headers=tok[k]).json())
        for k in ("alfa_admin", "alfa_op", "beta_admin"):
            assert requests.get(f"{API}/startups", headers=tok[k]).status_code == 403

    def test_get_startup_scoping(self, tok, ctx):
        a, b = ctx["ALFA"]["id"], ctx["BETA"]["id"]
        assert requests.get(f"{API}/startups/{a}", headers=tok["alfa_admin"]).status_code == 200
        assert requests.get(f"{API}/startups/{a}", headers=tok["alfa_op"]).status_code == 200
        assert requests.get(f"{API}/startups/{b}", headers=tok["alfa_admin"]).status_code == 404
        assert requests.get(f"{API}/startups/{b}/users", headers=tok["alfa_op"]).status_code == 404
        assert requests.get(f"{API}/startups/{a}", headers=tok["beta_admin"]).status_code == 404
        assert requests.get(f"{API}/startups/{a}/users", headers=tok["prov_prof"]).status_code == 200

    def test_write_startup_forbidden(self, tok, ctx):
        a = ctx["ALFA"]
        for k in ("prov_op", "prov_prof", "alfa_admin", "alfa_op"):
            assert requests.post(f"{API}/startups", headers=tok[k], json=startup_payload(ctx, "TESTZZ")).status_code == 403
            assert requests.put(f"{API}/startups/{a['id']}", headers=tok[k], json=a).status_code in (403, 404)
            assert requests.delete(f"{API}/startups/{a['id']}", headers=tok[k]).status_code == 403
        assert requests.delete(f"{API}/startups/{a['id']}", headers=tok["operatore"]).status_code == 403

    def test_contatti(self, tok, ctx):
        a = ctx["ALFA"]
        body = {"pec": a["pec"], "sede_legale": a["sede_legale"], "telefono": "+39 02 1234567"}
        r = requests.patch(f"{API}/startups/{a['id']}/contatti", headers=tok["alfa_admin"], json=body)
        assert r.status_code == 200 and r.json()["telefono"] == "+39 02 1234567"
        assert requests.patch(f"{API}/startups/{a['id']}/contatti", headers=tok["alfa_op"], json=body).status_code == 403
        assert requests.patch(f"{API}/startups/{a['id']}/contatti", headers=tok["prov_op"], json=body).status_code == 403
        assert requests.patch(f"{API}/startups/{ctx['BETA']['id']}/contatti", headers=tok["alfa_admin"], json=body).status_code == 404
        bad = requests.patch(f"{API}/startups/{a['id']}/contatti", headers=tok["alfa_admin"], json={**body, "pec": "nope"})
        assert bad.status_code == 422
        # revert
        r = requests.patch(f"{API}/startups/{a['id']}/contatti", headers=tok["alfa_admin"], json={**body, "telefono": ""})
        assert r.status_code == 200 and r.json()["telefono"] is None

    def test_users_list(self, tok, ctx):
        assert requests.get(f"{API}/users", headers=tok["admin"]).status_code == 200
        assert requests.get(f"{API}/users", headers=tok["operatore"]).status_code == 200
        for k in ("prov_op", "prov_prof", "alfa_op"):
            assert requests.get(f"{API}/users", headers=tok[k]).status_code == 403
        r = requests.get(f"{API}/users", headers=tok["alfa_admin"])
        assert r.status_code == 200
        assert {u["organization_id"] for u in r.json()} == {ctx["ALFA"]["organization_id"]}
        # filter cannot escape scope
        r = requests.get(f"{API}/users", headers=tok["alfa_admin"], params={"organization_id": ctx["BETA"]["organization_id"]})
        assert all(u["organization_id"] == ctx["ALFA"]["organization_id"] for u in r.json())
        r = requests.get(f"{API}/users", headers=tok["alfa_admin"], params={"org_type": "NURSERY"})
        assert all(u["organization_id"] == ctx["ALFA"]["organization_id"] for u in r.json())

    def test_orgs_profiles_lookups_alerts(self, tok, ctx):
        for k in ("admin", "operatore"):
            assert len(requests.get(f"{API}/organizations", headers=tok[k]).json()) >= 5
            for ep in ("service-profiles", "lookups", "alerts"):
                assert requests.get(f"{API}/{ep}", headers=tok[k]).status_code == 200
        for k in ("prov_op", "prov_prof", "alfa_admin", "alfa_op"):
            orgs = requests.get(f"{API}/organizations", headers=tok[k]).json()
            assert len(orgs) == 1
            for ep in ("service-profiles", "lookups", "alerts"):
                assert requests.get(f"{API}/{ep}", headers=tok[k]).status_code == 403
        for k in ("operatore", "prov_op", "alfa_admin"):
            assert requests.post(f"{API}/organizations", headers=tok[k], json={"name": "TEST X"}).status_code == 403
            assert requests.post(f"{API}/service-profiles", headers=tok[k], json={"nome": "TEST X"}).status_code == 403
            assert requests.delete(f"{API}/organizations/{ctx['ida']['id']}", headers=tok[k]).status_code == 403

    def test_unauthenticated(self):
        assert requests.get(f"{API}/startups").status_code == 401
        assert requests.get(f"{API}/auth/me", headers={"Authorization": "Bearer xxx"}).status_code == 401


# --- Acceptance 2: provider isolation ---
class TestProviderIsolation:
    def test_gamma_hidden(self, tok, ctx):
        g = ctx["GAMMA"]["id"]
        for k in ("prov_op", "prov_prof"):
            for suffix in ("", "/users", "/events"):
                assert requests.get(f"{API}/startups/{g}{suffix}", headers=tok[k]).status_code == 404

    def test_second_provider_hidden(self, tok, ctx):
        r = requests.post(f"{API}/organizations", headers=tok["admin"], json={"name": f"TEST Provider {uniq()}"})
        assert r.status_code == 200
        pid = r.json()["id"]
        s = create_startup(tok, ctx, provider_organization_id=pid)
        assert s["provider_organization_id"] == pid
        for k in ("prov_op", "prov_prof"):
            assert s["id"] not in {x["id"] for x in requests.get(f"{API}/startups", headers=tok[k]).json()}
            assert requests.get(f"{API}/startups/{s['id']}", headers=tok[k]).status_code == 404
            assert requests.get(f"{API}/startups/{s['id']}/events", headers=tok[k]).status_code == 404
        # provider delete blocked while linked
        d = requests.delete(f"{API}/organizations/{pid}", headers=tok["admin"])
        assert d.status_code == 409 and s["id"] in [x["id"] for x in d.json()["detail"]["startups"]]
        assert requests.delete(f"{API}/startups/{s['id']}", headers=tok["admin"]).status_code == 200
        assert requests.get(f"{API}/startups/{s['id']}", headers=tok["admin"]).status_code == 404
        assert requests.delete(f"{API}/organizations/{pid}", headers=tok["admin"]).status_code == 200


# --- Acceptance 3: ADMIN_STARTUP invites ---
class TestStartupAdminInvite:
    def test_invites(self, tok, ctx):
        alfa_org = ctx["ALFA"]["organization_id"]
        r, _ = invite(tok["alfa_admin"], alfa_org, "OPERATIVO_STARTUP", accept=False)
        assert r.status_code == 200 and r.json()["invite_token"] and r.json()["user"]["status"] == "INVITATO"
        r, _ = invite(tok["alfa_admin"], alfa_org, "ADMIN_STARTUP", accept=False)
        assert r.status_code == 200
        uid = r.json()["user"]["id"]
        alerts = requests.get(f"{API}/alerts", headers=tok["admin"]).json()
        assert any(e["entity_id"] == uid and e["action"] == "USER_INVITED" for e in alerts)
        r, _ = invite(tok["alfa_admin"], ctx["BETA"]["organization_id"], "OPERATIVO_STARTUP")
        assert r.status_code == 403
        r, _ = invite(tok["alfa_admin"], ctx["ida"]["id"], "OPERATIVO_PROVIDER")
        assert r.status_code == 403
        r, _ = invite(tok["alfa_admin"], ctx["nursery"]["id"], "OPERATORE_NURSERY")
        assert r.status_code == 403
        r, _ = invite(tok["alfa_op"], alfa_org, "OPERATIVO_STARTUP")
        assert r.status_code == 403
        r, _ = invite(tok["prov_op"], alfa_org, "OPERATIVO_STARTUP")
        assert r.status_code == 403
        r, _ = invite(tok["operatore"], ctx["nursery"]["id"], "OPERATORE_NURSERY")
        assert r.status_code == 403
        r, _ = invite(tok["admin"], alfa_org, "OPERATIVO_PROVIDER")
        assert r.status_code == 422  # role incompatible with org type

    def test_alfa_admin_cannot_touch_nursery_or_provider_users(self, tok, ctx):
        users = requests.get(f"{API}/users", headers=tok["admin"]).json()
        prov = [u for u in users if u["email"] == "operativo@idaservizi.test"][0]
        nurs = [u for u in users if u["email"] == "operatore@imment.test"][0]
        for t in (prov, nurs):
            assert requests.post(f"{API}/users/{t['id']}/deactivate", headers=tok["alfa_admin"]).status_code == 403
            assert requests.patch(f"{API}/users/{t['id']}", headers=tok["alfa_admin"], json={"nome": "X", "cognome": "Y"}).status_code == 403
        # operatore cannot touch nursery users
        adm = [u for u in users if u["email"] == "admin@imment.it"][0]
        assert requests.post(f"{API}/users/{adm['id']}/deactivate", headers=tok["operatore"]).status_code == 403


# --- Acceptance 4: codice_breve ---
class TestCodiceBreve:
    def test_lowercase_normalized(self, tok, ctx):
        code = "test" + letters().lower()
        r = requests.post(f"{API}/startups", headers=tok["admin"], json=startup_payload(ctx, code))
        assert r.status_code == 200 and r.json()["codice_breve"] == code.upper()
        CREATED_STARTUPS.append(r.json()["id"])

    @pytest.mark.parametrize("code", ["TES1", "AB", "ABCDEFG", "AB-C", "ÀBCD"])
    def test_invalid(self, tok, ctx, code):
        r = requests.post(f"{API}/startups", headers=tok["admin"], json=startup_payload(ctx, code))
        assert r.status_code == 422 and "codice breve" in r.json()["detail"].lower()

    def test_duplicate(self, tok, ctx):
        r = requests.post(f"{API}/startups", headers=tok["admin"], json=startup_payload(ctx, "alfa"))
        assert r.status_code in (409, 422) and "già usato" in r.json()["detail"]


# --- Servizi rules ---
class TestServizi:
    @pytest.mark.parametrize("serv,prov", [([], True), (["SOLO_CASH_FLOW", "AFC_COMPLETO"], True),
                                           (["AFC_COMPLETO"], False), (["PAGHE"], False), (["FOO"], True)])
    def test_rules(self, tok, ctx, serv, prov):
        r = requests.post(f"{API}/startups", headers=tok["admin"], json=startup_payload(ctx, "TESTQQ", provider=prov, servizi=serv))
        assert r.status_code == 422 and r.json()["detail"].startswith("Regola servizi")

    def test_ok_without_provider(self, tok, ctx):
        s = create_startup(tok, ctx, provider=False, servizi=["SOLO_CASH_FLOW", "FATTURAZIONE_PER_CONTO"])
        assert s["provider_organization_id"] is None


# --- Delete rules ---
class TestDeleteRules:
    def test_delete_non_onboarding(self, tok, ctx):
        r = requests.delete(f"{API}/startups/{ctx['ALFA']['id']}", headers=tok["admin"])
        assert r.status_code == 409

    def test_delete_ida_and_profile_blocked(self, tok, ctx):
        r = requests.delete(f"{API}/organizations/{ctx['ida']['id']}", headers=tok["admin"])
        assert r.status_code == 409 and len(r.json()["detail"]["startups"]) >= 2
        pid = ctx["ALFA"]["service_profile_id"]
        r = requests.delete(f"{API}/service-profiles/{pid}", headers=tok["admin"])
        assert r.status_code == 409 and "ALFA" in r.json()["detail"]["message"]


# --- Acceptance 5: events & visibility; invite flow; last admin ---
class TestEventsAndInvites:
    def test_events_visibility(self, tok, ctx):
        s = create_startup(tok, ctx)
        sid = s["id"]
        refs = ctx["lk"]["nursery_users"]
        new_ref = [u for u in refs if u["id"] != s["referente_nursery_user_id"]][0]["id"]
        body = {k: s[k] for k in startup_payload(ctx, "X")}
        body.update({"referente_nursery_user_id": new_ref, "sede_legale": "Via Nuova 2"})
        r = requests.put(f"{API}/startups/{sid}", headers=tok["admin"], json=body)
        assert r.status_code == 200 and r.json()["sede_legale"] == "Via Nuova 2"
        ev_n = requests.get(f"{API}/startups/{sid}/events", headers=tok["admin"]).json()
        assert any(e["visibility"] == "NURSERY_ONLY" and "referente_nursery_user_id" in e["details"].get("changes", {}) for e in ev_n)
        assert any(e["visibility"] == "ALL" and "sede_legale" in e["details"].get("changes", {}) for e in ev_n)
        ev_p = requests.get(f"{API}/startups/{sid}/events", headers=tok["prov_op"]).json()
        assert all(e["visibility"] == "ALL" for e in ev_p)
        assert any("sede_legale" in e["details"].get("changes", {}) for e in ev_p)
        assert not any("referente_nursery_user_id" in e["details"].get("changes", {}) for e in ev_p)
        # user invite event appears
        r, h = invite(tok["admin"], s["organization_id"], "ADMIN_STARTUP")
        ev = requests.get(f"{API}/startups/{sid}/events", headers=h).json()
        acts = {e["action"] for e in ev}
        assert {"USER_INVITED", "INVITE_ACCEPTED", "STARTUP_CREATED"} <= acts
        assert all(e["visibility"] == "ALL" for e in ev)

    def test_invite_flow_regenerate(self, tok, ctx):
        r, _ = invite(tok["alfa_admin"], ctx["ALFA"]["organization_id"], "OPERATIVO_STARTUP", accept=False)
        old, uid = r.json()["invite_token"], r.json()["user"]["id"]
        assert requests.get(f"{API}/auth/invitation/{old}").status_code == 200
        g = requests.post(f"{API}/users/{uid}/regenerate-invite", headers=tok["alfa_admin"])
        assert g.status_code == 200
        new = g.json()["invite_token"]
        assert new != old
        assert requests.get(f"{API}/auth/invitation/{old}").status_code == 404
        assert requests.post(f"{API}/auth/accept-invite", json={"token": new, "password": "short"}).status_code == 422
        a = requests.post(f"{API}/auth/accept-invite", json={"token": new, "password": "TestPass123"})
        assert a.status_code == 200 and a.json()["user"]["status"] == "ATTIVO"
        me = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {a.json()['token']}"})
        assert me.status_code == 200 and me.json()["startup_id"] == ctx["ALFA"]["id"]
        assert requests.post(f"{API}/auth/accept-invite", json={"token": new, "password": "TestPass123"}).status_code == 410
        assert requests.post(f"{API}/users/{uid}/regenerate-invite", headers=tok["alfa_admin"]).status_code == 409

    def test_cancel_invite(self, tok, ctx):
        r, _ = invite(tok["alfa_admin"], ctx["ALFA"]["organization_id"], "OPERATIVO_STARTUP", accept=False)
        t, uid = r.json()["invite_token"], r.json()["user"]["id"]
        d = requests.post(f"{API}/users/{uid}/deactivate", headers=tok["alfa_admin"])
        assert d.status_code == 200 and d.json()["status"] == "DISATTIVATO"
        assert requests.get(f"{API}/auth/invitation/{t}").status_code == 404

    def test_last_admin_and_self(self, tok, ctx):
        users = requests.get(f"{API}/users", headers=tok["gamma_admin"]).json()
        me = [u for u in users if u["email"] == "admin@gamma.test"][0]
        assert requests.post(f"{API}/users/{me['id']}/role", headers=tok["gamma_admin"], json={"role": "OPERATIVO_STARTUP"}).status_code == 403
        assert requests.post(f"{API}/users/{me['id']}/deactivate", headers=tok["gamma_admin"]).status_code == 403
        # two-admin scenario in a TEST startup
        s = create_startup(tok, ctx)
        r1, h1 = invite(tok["admin"], s["organization_id"], "ADMIN_STARTUP")
        r2, h2 = invite(h1, s["organization_id"], "ADMIN_STARTUP")
        u2 = r2.json()["user"]["id"]
        u1 = r1.json()["user"]["id"]
        d = requests.post(f"{API}/users/{u2}/role", headers=h1, json={"role": "OPERATIVO_STARTUP"})
        assert d.status_code == 200 and d.json()["role"] == "OPERATIVO_STARTUP"
        # u2 now OPERATIVO cannot act
        assert requests.post(f"{API}/users/{u1}/deactivate", headers=h2).status_code == 403
        # role change to ADMIN_STARTUP generates alert
        p = requests.post(f"{API}/users/{u2}/role", headers=h1, json={"role": "ADMIN_STARTUP"})
        assert p.status_code == 200
        alerts = requests.get(f"{API}/alerts", headers=tok["operatore"]).json()
        assert any(e["entity_id"] == u2 and e["action"] == "ROLE_CHANGED" for e in alerts)
        # nursery admin can demote last admin (no constraint for nursery)
        assert requests.post(f"{API}/users/{u2}/deactivate", headers=tok["admin"]).status_code == 200
        assert requests.post(f"{API}/users/{u1}/role", headers=tok["admin"], json={"role": "OPERATIVO_STARTUP"}).status_code == 200

    def test_profile_and_password(self, tok, ctx):
        s = create_startup(tok, ctx)
        _, h = invite(tok["admin"], s["organization_id"], "OPERATIVO_STARTUP")
        r = requests.patch(f"{API}/auth/me", headers=h, json={"nome": "Nuovo", "cognome": "Nome", "telefono": "333 1234567"})
        assert r.status_code == 200 and r.json()["nome"] == "Nuovo"
        assert requests.get(f"{API}/auth/me", headers=h).json()["telefono"] == "333 1234567"
        assert requests.post(f"{API}/auth/change-password", headers=h, json={"current_password": "wrong", "new_password": "Abcdef123"}).status_code == 422
        assert requests.post(f"{API}/auth/change-password", headers=h, json={"current_password": "TestPass123", "new_password": "abc"}).status_code == 422
        assert requests.post(f"{API}/auth/change-password", headers=h, json={"current_password": "TestPass123", "new_password": "Abcdef123"}).status_code == 200
        email = requests.get(f"{API}/auth/me", headers=h).json()["email"]
        assert requests.post(f"{API}/auth/login", json={"email": email, "password": "Abcdef123"}).status_code == 200
