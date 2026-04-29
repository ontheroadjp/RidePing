from __future__ import annotations

from fastapi.testclient import TestClient

from app import db


def login_child(client: TestClient) -> None:
    client.post("/login", data={"role": "child", "login_id": "child1", "password": "child123"})


def test_child_pages_require_child_session(client: TestClient) -> None:
    trains_response = client.get("/trains", follow_redirects=False)
    api_response = client.get("/api/trains")

    assert trains_response.status_code == 303
    assert trains_response.headers["location"] == "/login"
    assert api_response.status_code == 401
    assert api_response.json()["error"] == "unauthorized"


def test_child_can_view_train_selection(client: TestClient) -> None:
    login_child(client)

    response = client.get("/trains")

    assert response.status_code == 200
    assert "こども" in response.text
    assert "都庁前" in response.text


def test_api_trains_returns_train_candidates_for_child(client: TestClient) -> None:
    login_child(client)

    response = client.get("/api/trains")
    payload = response.json()

    assert response.status_code == 200
    assert "generated_at" in payload
    assert payload["trains"][0]["train_number"] == "A123"
    assert payload["trains"][0]["from_station"] == "都庁前"


def test_debug_timetable_api_returns_validation_payload_for_child(client: TestClient) -> None:
    login_child(client)

    response = client.get("/api/debug/timetable?step_minutes=10")
    payload = response.json()

    assert response.status_code == 200
    assert payload["railway_id"] == "Toei.Oedo"
    assert payload["issue_count"] == 0


def test_report_ride_persists_report_and_writes_notification(client: TestClient) -> None:
    login_child(client)
    with db.get_db() as conn:
        route_id = conn.execute("SELECT id FROM child_route ORDER BY id LIMIT 1").fetchone()["id"]

    response = client.post(
        "/report",
        data={
            "train_number": "A123",
            "from_station": "都庁前",
            "to_station": "新宿西口",
            "eta_home": "08:12",
            "route_id": route_id,
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == f"/trains?route_id={route_id}"
    with db.get_db() as conn:
        report = conn.execute("SELECT * FROM ride_report ORDER BY id DESC LIMIT 1").fetchone()
    assert report["train_number"] == "A123"
    assert report["from_station"] == "都庁前"
    assert report["eta_home"] == "08:12"

    notification_files = list(db.NOTIFICATION_DIR.glob("notification-*.txt"))
    assert len(notification_files) == 1
    body = notification_files[0].read_text(encoding="utf-8")
    assert "列車番号: A123" in body
    assert "現在区間: 都庁前 -> 新宿西口" in body
