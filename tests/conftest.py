from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from app import db
from app.routers import api, auth, child, parent
from app.timetable import TrainCandidate


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    db_path = tmp_path / "app.db"
    notification_dir = tmp_path / "notifications"

    monkeypatch.setattr(db, "DB_PATH", db_path)
    monkeypatch.setattr(db, "NOTIFICATION_DIR", notification_dir)

    import app.notifications as notifications

    monkeypatch.setattr(notifications, "NOTIFICATION_DIR", notification_dir)

    stations = ["都庁前", "新宿西口", "東新宿"]
    monkeypatch.setattr(parent, "get_station_options", lambda railway_id="Toei.Oedo": stations)
    monkeypatch.setattr(parent, "get_railway_master", lambda: [{"id": "Toei.Oedo", "title_ja": "都営大江戸線"}])
    monkeypatch.setattr(parent, "get_route_station_map", lambda: {"Toei.Oedo": stations})
    monkeypatch.setattr(parent, "get_terminal_destinations", lambda railway_id: ["都庁前", "光が丘"])
    monkeypatch.setattr(parent, "get_railway_stations", lambda railway_id: ["都庁前", "新宿西口", "光が丘"])
    monkeypatch.setattr(parent, "infer_direction_from_destination", lambda railway_id, destination_station: "down")

    monkeypatch.setattr(child, "station_sequence_for_destination", lambda railway_id, destination_station: stations)
    monkeypatch.setattr(child, "infer_direction_from_destination", lambda railway_id, destination_station: "down")
    monkeypatch.setattr(child, "first_departure_label_by_station", lambda station_names, route_direction: {s: "" for s in station_names})
    monkeypatch.setattr(child, "timetable_trains", lambda home_station, railway_id, destination_station, station_names: [])

    train = TrainCandidate(
        train_id="test-train",
        train_number="A123",
        from_station="都庁前",
        to_station="新宿西口",
        delay_sec=0,
        eta_home="08:12",
        from_index=0.0,
        to_index=1.0,
        position_index=0.5,
    )
    monkeypatch.setattr(api, "station_sequence_for_destination", lambda railway_id, destination_station: stations)
    monkeypatch.setattr(api, "timetable_trains", lambda home_station, railway_id, destination_station, station_names: [train])
    monkeypatch.setattr(
        api,
        "validate_timetable_positions",
        lambda railway_id, destination_station, station_names, step_minutes: {
            "railway_id": railway_id,
            "destination_station": destination_station,
            "target_loop": "OuterLoop",
            "checked_samples": 1,
            "issue_count": 0,
            "issues": [],
        },
    )

    db.init_db()

    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key="test-secret")
    app.include_router(auth.router)
    app.include_router(parent.router)
    app.include_router(child.router)
    app.include_router(api.router)

    with TestClient(app) as test_client:
        yield test_client
