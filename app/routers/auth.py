from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.auth import current_role
from app.db import get_db, hash_password
from app.view import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> RedirectResponse:
    role = current_role(request)
    if role == "parent":
        return RedirectResponse("/parent", status_code=303)
    if role == "child":
        return RedirectResponse("/trains", status_code=303)
    return RedirectResponse("/login", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "login.html", {"error": ""})


@router.post("/login")
def login(request: Request, role: str = Form(...), login_id: str = Form(...), password: str = Form(...)) -> Response:
    pwd = hash_password(password)
    with get_db() as conn:
        if role == "parent":
            row = conn.execute(
                "SELECT * FROM parent_account WHERE parent_login_id = ? AND password_hash = ?",
                (login_id, pwd),
            ).fetchone()
            if not row:
                return templates.TemplateResponse(request, "login.html", {"error": "IDまたはパスワードが違います"}, status_code=400)
            request.session.clear()
            request.session["role"] = "parent"
            request.session["parent_id"] = row["id"]
            return RedirectResponse("/parent", status_code=303)

        row = conn.execute(
            "SELECT * FROM child_account WHERE child_login_id = ? AND password_hash = ?",
            (login_id, pwd),
        ).fetchone()
        if not row:
            return templates.TemplateResponse(request, "login.html", {"error": "IDまたはパスワードが違います"}, status_code=400)
        request.session.clear()
        request.session["role"] = "child"
        request.session["parent_id"] = row["parent_id"]
        request.session["child_id"] = row["id"]
        return RedirectResponse("/trains", status_code=303)


@router.post("/logout")
def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
