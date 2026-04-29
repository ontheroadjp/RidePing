from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.db import init_db
from app.paths import BASE_DIR
from app.routers import api, auth, child, parent

app = FastAPI(title="乗ったよ / RidePing MVP")
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "dev-secret-change-me"))
app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")

init_db()

app.include_router(auth.router)
app.include_router(parent.router)
app.include_router(child.router)
app.include_router(api.router)
