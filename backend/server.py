from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import os  # noqa: E402
import logging  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402

from core import client  # noqa: E402
from routes_auth import router as auth_router  # noqa: E402
from routes_users import router as users_router  # noqa: E402
from routes_startups import router as startups_router  # noqa: E402
from routes_admin import router as admin_router  # noqa: E402
from routes_services import router as services_router  # noqa: E402
from routes_legal import router as legal_router  # noqa: E402
from seed import seed  # noqa: E402

app = FastAPI(title="Piattaforma Nursery - Modulo 1")
for r in (auth_router, users_router, startups_router, admin_router, services_router, legal_router):
    app.include_router(r)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ["CORS_ORIGINS"].split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


@app.get("/api/")
async def root():
    return {"message": "Piattaforma Nursery API"}


@app.on_event("startup")
async def on_startup():
    await seed()


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
