from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.auth import require_child
from app.db import get_db
from app.notifications import write_notification
from app.timetable import (
    ODPT_KEY,
    first_departure_label_by_station,
    infer_direction_from_destination,
    station_sequence_for_destination,
    timetable_trains,
)
from app.view import templates

router = APIRouter()


@router.get("/trains", response_class=HTMLResponse)
async def trains(request: Request) -> Response:
    role_info = require_child(request)
    if not role_info:
        return RedirectResponse("/login", status_code=303)
    parent_id, child_id = role_info
    with get_db() as conn:
        parent = conn.execute("SELECT * FROM parent_account WHERE id = ?", (parent_id,)).fetchone()
        child = conn.execute("SELECT * FROM child_account WHERE id = ?", (child_id,)).fetchone()
        routes = conn.execute("SELECT * FROM child_route WHERE child_id = ? ORDER BY id", (child_id,)).fetchall()

    selected_route_id = request.query_params.get("route_id")
    selected_route = None
    if selected_route_id:
        selected_route = next((r for r in routes if str(r["id"]) == selected_route_id), None)
    if not selected_route:
        selected_route = routes[0] if routes else None
    if not selected_route:
        return RedirectResponse("/logout", status_code=303)

    railway_id = selected_route["railway_id"] or "Toei.Oedo"
    destination_station = selected_route["destination_station"]
    route_direction = infer_direction_from_destination(railway_id, destination_station)
    stations_for_map = station_sequence_for_destination(railway_id, destination_station)
    train_rows = timetable_trains(
        selected_route["home_station"],
        railway_id,
        destination_station,
        stations_for_map,
    )
    return templates.TemplateResponse(
        request,
        "trains.html",
        {
            "trains": train_rows,
            "setting": {
                "home_station": selected_route["home_station"],
                "child_name": child["child_name"],
                "direction": route_direction,
            },
            "key_enabled": bool(ODPT_KEY),
            "stations": stations_for_map,
            "routes": routes,
            "selected_route_id": selected_route["id"],
            "station_first_departure_labels": first_departure_label_by_station(stations_for_map, route_direction),
        },
    )


@router.post("/report")
def report_ride(
    request: Request,
    train_number: str = Form(...),
    from_station: str = Form(...),
    to_station: str = Form(...),
    eta_home: str = Form(...),
    route_id: int = Form(...),
) -> RedirectResponse:
    role_info = require_child(request)
    if not role_info:
        return RedirectResponse("/login", status_code=303)
    parent_id, child_id = role_info
    with get_db() as conn:
        parent = conn.execute("SELECT * FROM parent_account WHERE id = ?", (parent_id,)).fetchone()
        child = conn.execute("SELECT * FROM child_account WHERE id = ?", (child_id,)).fetchone()
        route = conn.execute("SELECT * FROM child_route WHERE child_id = ? AND id = ?", (child_id, route_id)).fetchone()
        if not route:
            route = conn.execute("SELECT * FROM child_route WHERE child_id = ? ORDER BY id LIMIT 1", (child_id,)).fetchone()
        conn.execute(
            """
            INSERT INTO ride_report (parent_id, child_id, child_name, train_number, from_station, to_station, home_station, eta_home, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                parent_id,
                child_id,
                child["child_name"],
                train_number,
                from_station,
                to_station,
                route["home_station"],
                eta_home,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )

    write_notification(
        parent_email=parent["parent_email"],
        child_name=child["child_name"],
        train_number=train_number,
        from_station=from_station,
        to_station=to_station,
        home_station=route["home_station"],
        eta_home=eta_home,
    )
    return RedirectResponse(f"/trains?route_id={route['id']}", status_code=303)
