from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.auth import require_parent
from app.db import get_db, hash_password
from app.timetable import (
    get_railway_master,
    get_railway_stations,
    get_route_station_map,
    get_station_options,
    get_terminal_destinations,
    infer_direction_from_destination,
)
from app.view import templates

router = APIRouter()


@router.get("/parent", response_class=HTMLResponse)
def parent_dashboard(request: Request) -> Response:
    parent_id = require_parent(request)
    if not parent_id:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        parent = conn.execute("SELECT * FROM parent_account WHERE id = ?", (parent_id,)).fetchone()
        reports = conn.execute("SELECT * FROM ride_report WHERE parent_id = ? ORDER BY id DESC LIMIT 10", (parent_id,)).fetchall()
    return templates.TemplateResponse(
        request,
        "parent.html",
        {"parent": parent, "reports": reports},
    )


@router.post("/parent/settings")
def save_parent_settings(request: Request, parent_email: str = Form(...)) -> RedirectResponse:
    parent_id = require_parent(request)
    if not parent_id:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        conn.execute(
            "UPDATE parent_account SET parent_email = ? WHERE id = ?",
            (parent_email, parent_id),
        )
    return RedirectResponse("/parent", status_code=303)


@router.get("/parent/children", response_class=HTMLResponse)
def parent_children(request: Request) -> Response:
    parent_id = require_parent(request)
    if not parent_id:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        children = conn.execute("SELECT * FROM child_account WHERE parent_id = ? ORDER BY id", (parent_id,)).fetchall()
    return templates.TemplateResponse(request, "children.html", {"children": children})


@router.post("/parent/children")
def add_child(
    request: Request,
    child_name: str = Form(...),
    child_login_id: str = Form(...),
    child_password: str = Form(...),
) -> RedirectResponse:
    parent_id = require_parent(request)
    if not parent_id:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO child_account (parent_id, child_login_id, password_hash, child_name) VALUES (?, ?, ?, ?)",
            (parent_id, child_login_id, hash_password(child_password), child_name),
        )
        child_id = conn.execute("SELECT id FROM child_account WHERE child_login_id = ?", (child_login_id,)).fetchone()["id"]
        conn.execute(
            "INSERT INTO child_route (child_id, route_name, railway_id, home_station, destination_station, direction) VALUES (?, ?, ?, ?, ?, ?)",
            (child_id, "大江戸線", "Toei.Oedo", "都庁前", "都庁前", "down"),
        )
    return RedirectResponse("/parent/children", status_code=303)


@router.get("/parent/children/{child_id}", response_class=HTMLResponse)
def edit_child(request: Request, child_id: int) -> Response:
    parent_id = require_parent(request)
    if not parent_id:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        child = conn.execute(
            "SELECT * FROM child_account WHERE id = ? AND parent_id = ?",
            (child_id, parent_id),
        ).fetchone()
        if not child:
            return RedirectResponse("/parent/children", status_code=303)
        routes = conn.execute("SELECT * FROM child_route WHERE child_id = ? ORDER BY id", (child_id,)).fetchall()
    return templates.TemplateResponse(
        request,
        "child_edit.html",
        {
            "child": child,
            "routes": routes,
            "stations": get_station_options(),
            "route_master": get_railway_master(),
            "route_station_map": get_route_station_map(),
        },
    )


@router.post("/parent/children/{child_id}/update")
def update_child(
    request: Request,
    child_id: int,
    child_name: str = Form(...),
    child_login_id: str = Form(...),
    child_password: str = Form(""),
) -> RedirectResponse:
    parent_id = require_parent(request)
    if not parent_id:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        if child_password:
            conn.execute(
                "UPDATE child_account SET child_name = ?, child_login_id = ?, password_hash = ? WHERE id = ? AND parent_id = ?",
                (child_name, child_login_id, hash_password(child_password), child_id, parent_id),
            )
        else:
            conn.execute(
                "UPDATE child_account SET child_name = ?, child_login_id = ? WHERE id = ? AND parent_id = ?",
                (child_name, child_login_id, child_id, parent_id),
            )
    return RedirectResponse(f"/parent/children/{child_id}", status_code=303)


@router.post("/parent/children/{child_id}/delete")
def delete_child(request: Request, child_id: int) -> RedirectResponse:
    parent_id = require_parent(request)
    if not parent_id:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        conn.execute("DELETE FROM child_route WHERE child_id = ?", (child_id,))
        conn.execute("DELETE FROM ride_report WHERE child_id = ? AND parent_id = ?", (child_id, parent_id))
        conn.execute("DELETE FROM child_account WHERE id = ? AND parent_id = ?", (child_id, parent_id))
    return RedirectResponse("/parent/children", status_code=303)


@router.post("/parent/children/{child_id}/routes")
def add_child_route(
    request: Request,
    child_id: int,
    railway_id: str = Form(...),
    route_name: str = Form(...),
    home_station: str = Form(...),
    destination_station: str = Form(...),
) -> RedirectResponse:
    parent_id = require_parent(request)
    if not parent_id:
        return RedirectResponse("/login", status_code=303)
    terminals = get_terminal_destinations(railway_id)
    if len(terminals) < 2:
        return RedirectResponse(f"/parent/children/{child_id}", status_code=303)
    if destination_station not in terminals:
        destination_station = terminals[1]
    direction = infer_direction_from_destination(railway_id, destination_station)
    stations = get_railway_stations(railway_id)
    if home_station not in stations:
        home_station = stations[0]
    with get_db() as conn:
        owns = conn.execute("SELECT id FROM child_account WHERE id = ? AND parent_id = ?", (child_id, parent_id)).fetchone()
        if owns:
            conn.execute(
                "INSERT INTO child_route (child_id, route_name, railway_id, home_station, destination_station, direction) VALUES (?, ?, ?, ?, ?, ?)",
                (child_id, route_name, railway_id, home_station, destination_station, direction),
            )
    return RedirectResponse(f"/parent/children/{child_id}", status_code=303)


@router.post("/parent/children/{child_id}/routes/{route_id}/delete")
def delete_child_route(request: Request, child_id: int, route_id: int) -> RedirectResponse:
    parent_id = require_parent(request)
    if not parent_id:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        owns = conn.execute("SELECT id FROM child_account WHERE id = ? AND parent_id = ?", (child_id, parent_id)).fetchone()
        if owns:
            conn.execute("DELETE FROM child_route WHERE id = ? AND child_id = ?", (route_id, child_id))
            cnt = conn.execute("SELECT COUNT(*) AS c FROM child_route WHERE child_id = ?", (child_id,)).fetchone()["c"]
            if cnt == 0:
                conn.execute(
                    "INSERT INTO child_route (child_id, route_name, railway_id, home_station, destination_station, direction) VALUES (?, ?, ?, ?, ?, ?)",
                    (child_id, "大江戸線", "Toei.Oedo", "都庁前", "都庁前", "down"),
                )
    return RedirectResponse(f"/parent/children/{child_id}", status_code=303)
