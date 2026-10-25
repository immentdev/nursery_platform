import asyncio, re, sys
from playwright.async_api import async_playwright

URL = "https://nursery-fondamenta.preview.emergentagent.com"
OUT = "/app/docs/formazione/screenshots/"
ONLY = sys.argv[1] if len(sys.argv) > 1 else "all"


async def shot(page, name):
    await page.wait_for_timeout(900)
    await page.evaluate("document.querySelectorAll('[data-sonner-toaster]').forEach(e => e.style.display='none')")
    h = await page.evaluate("Math.max(document.documentElement.scrollHeight, document.body.scrollHeight)")
    await page.set_viewport_size({"width": 1440, "height": max(900, h)})
    await page.wait_for_timeout(500)
    await page.screenshot(path=OUT + name)
    await page.set_viewport_size({"width": 1440, "height": 900})
    print("OK", name)


async def login(page, email, pw, cap=None):
    await page.goto(URL + "/login", wait_until="networkidle")
    await page.evaluate("localStorage.clear()")
    await page.goto(URL + "/login", wait_until="networkidle")
    await page.fill('[data-testid="login-email-input"]', email)
    await page.fill('[data-testid="login-password-input"]', pw)
    if cap:
        await shot(page, cap)
    await page.click('[data-testid="login-submit-button"]')
    await page.wait_for_timeout(2500)


async def gate(page, cap=None):
    if await page.locator('[data-testid="legal-accept-button"]').count():
        if cap:
            await shot(page, cap)
        await page.click('[data-testid="legal-accept-checkbox"]')
        await page.click('[data-testid="legal-accept-button"]')
        await page.wait_for_timeout(2000)
        return True
    print("NO GATE")
    return False


async def pick(page, testid, text):
    await page.click(f'[data-testid="{testid}"]')
    await page.wait_for_timeout(300)
    await page.get_by_role("option", name=text).first.click()
    await page.wait_for_timeout(200)


async def nursery(page):
    await login(page, "admin@imment.it", "Nursery2026!", "01-login.png")
    await gate(page, "02-accettazione-documenti.png")
    await page.goto(URL + "/startup", wait_until="networkidle")
    await shot(page, "03-elenco-startup.png")

    await page.goto(URL + "/startup/nuova", wait_until="networkidle")
    f = lambda t, v: page.fill(f'[data-testid="{t}"]', v)
    await f("form-denominazione", "DEMO Formazione S.r.l.")
    await f("form-codice-breve", "DEMO")
    await f("form-codice-fiscale", "09876543210")
    await f("form-partita-iva", "09876543210")
    await f("form-sede", "Via Esempio 1, 00100 Roma (dato dimostrativo)")
    await f("form-pec", "demo.formazione@pec.demo.test")
    await f("form-costituzione", "2026-01-15")
    await pick(page, "form-regime-iva", "Trimestrale")
    await page.click('[data-testid="form-servizi-select"]')
    await page.wait_for_timeout(300)
    for name in ["AFC", "Paghe"]:
        await page.get_by_role("option", name=re.compile(name)).first.click()
        await page.wait_for_timeout(200)
    await page.keyboard.press("Escape")
    await pick(page, "form-provider", "Ida Servizi")
    await page.click('[data-testid="form-profilo"]')
    await page.wait_for_timeout(300)
    await page.get_by_role("option").first.click()
    await pick(page, "form-referente", "Amministratore Nursery")
    await shot(page, "04-nuova-startup.png")
    await page.click('[data-testid="form-submit"]')
    await page.wait_for_url(re.compile(r"/startup/[0-9a-f-]{36}$"), timeout=10000)
    detail = page.url
    await shot(page, "05-scheda-anagrafica.png")
    await page.click('[data-testid="tab-servizi"]')
    await shot(page, "06-scheda-servizi.png")
    await page.goto(detail + "/modifica", wait_until="networkidle")
    await page.locator('[data-testid="form-servizi-list"]').scroll_into_view_if_needed()
    await shot(page, "07-modifica-servizi.png")

    await page.goto(URL + "/utenti", wait_until="networkidle")
    await shot(page, "08-elenco-utenti.png")
    await page.click('[data-testid="invite-user-button"]')
    await page.click('[data-testid="invite-org-select"]')
    await page.fill('[data-testid="invite-org-select-search"]', "DEMO")
    await page.wait_for_timeout(300)
    await page.get_by_role("option", name=re.compile("DEMO Formazione")).first.click()
    await pick(page, "invite-role-select", "Amministratore startup")
    await f("invite-nome-input", "Anna")
    await f("invite-cognome-input", "Demo")
    await f("invite-email-input", "anna@demo.test")
    await page.screenshot(path=OUT + "09-invito-utente.png", full_page=True); print("OK 09")
    await page.click('[data-testid="invite-submit-button"]')
    await page.wait_for_selector('[data-testid="invite-link-dialog"]')
    link = await page.input_value('[data-testid="invite-link-input"]')
    open("/tmp/anna_link.txt", "w").write(link)
    await shot(page, "10-link-invito.png")
    await page.keyboard.press("Escape")

    await page.goto(URL + "/segnalazioni", wait_until="networkidle")
    await shot(page, "11-segnalazioni-da-gestire.png")
    item = page.locator('[data-testid^="alert-"]').filter(has_text="Anna").first
    tid = await item.get_attribute("data-testid")
    await page.click(f'[data-testid="alert-ack-{tid[6:]}"]')
    await page.wait_for_timeout(1500)
    await page.click('[data-testid="alerts-tab-done"]')
    await shot(page, "12-segnalazioni-gestite.png")


async def redo(page):
    await login(page, "operatore@imment.test", "Prova2026!")
    await shot(page, "02-accettazione-documenti.png")
    await login(page, "admin@imment.it", "Nursery2026!", "01-login.png")
    await page.goto(URL + "/startup", wait_until="networkidle")
    await shot(page, "03-elenco-startup.png")
    await page.goto(URL + "/startup/nuova", wait_until="networkidle")
    f = lambda t, v: page.fill(f'[data-testid="{t}"]', v)
    await f("form-denominazione", "DEMO Formazione S.r.l.")
    await f("form-codice-breve", "DEMO")
    await f("form-codice-fiscale", "09876543210")
    await f("form-partita-iva", "09876543210")
    await f("form-sede", "Via Esempio 1, 00100 Roma (dato dimostrativo)")
    await f("form-pec", "demo.formazione@pec.demo.test")
    await f("form-costituzione", "2026-01-15")
    await pick(page, "form-regime-iva", "Trimestrale")
    await page.click('[data-testid="form-servizi-select"]')
    await page.wait_for_timeout(300)
    for name in ["AFC", "Paghe"]:
        await page.get_by_role("option", name=re.compile(name)).first.click()
        await page.wait_for_timeout(200)
    await page.keyboard.press("Escape")
    await pick(page, "form-provider", "Ida Servizi")
    await page.click('[data-testid="form-profilo"]')
    await page.wait_for_timeout(300)
    await page.get_by_role("option").first.click()
    await pick(page, "form-referente", "Amministratore Nursery")
    await shot(page, "04-nuova-startup.png")
    await page.goto(URL + "/startup", wait_until="networkidle")
    await page.click('[data-testid="startup-row-DEMO"]')
    await page.wait_for_timeout(1500)
    detail = page.url
    await shot(page, "05-scheda-anagrafica.png")
    await page.click('[data-testid="tab-servizi"]')
    await shot(page, "06-scheda-servizi.png")
    await page.goto(detail + "/modifica", wait_until="networkidle")
    await shot(page, "07-modifica-servizi.png")
    await page.goto(URL + "/utenti", wait_until="networkidle")
    await shot(page, "08-elenco-utenti.png")
    await page.click('[data-testid="invite-user-button"]')
    await page.click('[data-testid="invite-org-select"]')
    await page.fill('[data-testid="invite-org-select-search"]', "DEMO")
    await page.wait_for_timeout(300)
    await page.get_by_role("option", name=re.compile("DEMO Formazione")).first.click()
    await pick(page, "invite-role-select", "Amministratore startup")
    await f("invite-nome-input", "Anna")
    await f("invite-cognome-input", "Demo")
    await f("invite-email-input", "anna@demo.test")
    await shot(page, "09-invito-utente.png")
    await page.keyboard.press("Escape")
    await page.wait_for_timeout(500)
    row = page.locator('[data-testid^="user-row-"]').filter(has_text="anna@demo.test").first
    uid = (await row.get_attribute("data-testid"))[len("user-row-"):]
    await page.click(f'[data-testid="user-actions-{uid}"]')
    await page.click('[data-testid="user-action-regenerate"]')
    await page.wait_for_selector('[data-testid="invite-link-dialog"]')
    open("/app/memory/anna_link.txt", "w").write(await page.input_value('[data-testid="invite-link-input"]'))
    await shot(page, "10-link-invito.png")
    await page.keyboard.press("Escape")
    await page.goto(URL + "/segnalazioni", wait_until="networkidle")
    await page.click('[data-testid="alerts-tab-done"]')
    await shot(page, "12-segnalazioni-gestite.png")


async def nursery2(page):
    await login(page, "admin@imment.it", "Nursery2026!")
    await gate(page)
    await page.goto(URL + "/provider", wait_until="networkidle")
    row = page.locator('[data-testid^="provider-row-"]').filter(has_text="Ida Servizi").first
    rid = (await row.get_attribute("data-testid"))[len("provider-row-"):]
    await page.click(f'[data-testid="provider-edit-{rid}"]')
    await shot(page, "13-provider.png")
    await page.keyboard.press("Escape")
    await page.goto(URL + "/servizi", wait_until="networkidle")
    await shot(page, "14-catalogo-servizi.png")
    await page.click('[data-testid="service-edit-AFC_COMPLETO"]')
    await shot(page, "15-modifica-servizio.png")
    await page.keyboard.press("Escape")
    await page.goto(URL + "/profili", wait_until="networkidle")
    await shot(page, "16-profili-servizio.png")
    await page.goto(URL + "/documenti-legali", wait_until="networkidle")
    await shot(page, "17-documenti-legali.png")
    await page.goto(URL + "/utenti", wait_until="networkidle")
    await page.fill('[data-testid="users-search-input"]', "anna@demo.test")
    await page.wait_for_timeout(1200)
    row = page.locator('[data-testid^="user-row-"]').filter(has_text="anna@demo.test").first
    uid = (await row.get_attribute("data-testid"))[len("user-row-"):]
    await page.click(f'[data-testid="user-actions-{uid}"]')
    await page.wait_for_timeout(400)
    await page.screenshot(path="/tmp/18a.png")
    await page.click('[data-testid="user-action-reset"]')
    await page.wait_for_selector('[data-testid="invite-link-dialog"]')
    await page.wait_for_timeout(900)
    await page.evaluate("document.querySelectorAll('[data-sonner-toaster]').forEach(e => e.style.display='none')")
    await page.screenshot(path="/tmp/18b.png")
    await page.keyboard.press("Escape")
    await page.goto(URL + "/profilo", wait_until="networkidle")
    await shot(page, "19-area-personale.png")


async def startup(page):
    await login(page, "admin@alfa.test", "Prova2026!")
    await gate(page)
    await page.goto(URL + "/mia-startup", wait_until="networkidle")
    await shot(page, "20-startup-home.png")
    await page.click('[data-testid="tab-servizi"]')
    await shot(page, "21-startup-servizi.png")
    await page.goto(URL + "/utenti", wait_until="networkidle")
    await shot(page, "22-startup-utenti.png")
    await page.goto(URL + "/mia-startup", wait_until="networkidle")
    await page.click('[data-testid="edit-contatti-button"]')
    await shot(page, "23-startup-modifica-contatti.png")


async def provider(page):
    await login(page, "operativo@idaservizi.test", "Prova2026!")
    await gate(page)
    await page.goto(URL + "/startup", wait_until="networkidle")
    await shot(page, "24-provider-elenco.png")
    await page.click('[data-testid="startup-row-ALFA"]')
    await page.wait_for_timeout(1500)
    await shot(page, "25-provider-scheda.png")


async def anon(page):
    await page.goto(URL + "/login", wait_until="networkidle")
    await page.evaluate("localStorage.clear()")
    await page.goto(URL + "/login", wait_until="networkidle")
    await page.click('[data-testid="forgot-password-link"]')
    await shot(page, "26-password-dimenticata.png")


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chromium", args=["--lang=it-IT"])
        for name, fn in [("nursery", nursery), ("redo", redo), ("nursery2", nursery2), ("startup", startup), ("provider", provider), ("anon", anon)]:
            if ONLY not in ("all", name):
                continue
            ctx = await b.new_context(viewport={"width": 1440, "height": 900}, locale="it-IT", timezone_id="Europe/Rome")
            page = await ctx.new_page()
            try:
                await fn(page)
            except Exception as e:
                print("FAIL", name, e)
                await page.screenshot(path=f"/tmp/fail-{name}.png", full_page=True)
            await ctx.close()
        await b.close()

asyncio.run(main())
