from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from app.auth import require_child
from app.db import get_db
from app.timetable import station_sequence_for_destination, timetable_trains, train_to_dict, validate_timetable_positions
from app.view import DEV_UI_ENABLED

router = APIRouter()


@router.get("/api/trains")
def api_trains(request: Request, route_id: int | None = None) -> Response:
    role_info = require_child(request)
    if not role_info:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    _parent_id, child_id = role_info
    with get_db() as conn:
        routes = conn.execute("SELECT * FROM child_route WHERE child_id = ? ORDER BY id", (child_id,)).fetchall()

    selected_route = None
    if route_id is not None:
        selected_route = next((r for r in routes if r["id"] == route_id), None)
    if not selected_route:
        selected_route = routes[0] if routes else None
    if not selected_route:
        return JSONResponse({"trains": [], "generated_at": datetime.now().isoformat(timespec="seconds")})

    railway_id = selected_route["railway_id"] or "Toei.Oedo"
    destination_station = selected_route["destination_station"]
    stations_for_map = station_sequence_for_destination(railway_id, destination_station)
    trains_now = timetable_trains(selected_route["home_station"], railway_id, destination_station, stations_for_map)
    return JSONResponse(
        {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "trains": [train_to_dict(t) for t in trains_now],
        }
    )


@router.get("/api/debug/timetable")
def api_debug_timetable(request: Request, route_id: int | None = None, step_minutes: int = 5) -> Response:
    if not DEV_UI_ENABLED:
        return JSONResponse({"error": "debug api disabled"}, status_code=404)
    role_info = require_child(request)
    if not role_info:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    _parent_id, child_id = role_info
    with get_db() as conn:
        routes = conn.execute("SELECT * FROM child_route WHERE child_id = ? ORDER BY id", (child_id,)).fetchall()
    selected_route = None
    if route_id is not None:
        selected_route = next((r for r in routes if r["id"] == route_id), None)
    if not selected_route:
        selected_route = routes[0] if routes else None
    if not selected_route:
        return JSONResponse({"error": "route not found"}, status_code=404)

    railway_id = selected_route["railway_id"] or "Toei.Oedo"
    destination_station = selected_route["destination_station"]
    stations_for_map = station_sequence_for_destination(railway_id, destination_station)
    return JSONResponse(validate_timetable_positions(railway_id, destination_station, stations_for_map, step_minutes))
