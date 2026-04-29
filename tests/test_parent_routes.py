from __future__ import annotations

from fastapi.testclient import TestClient

from app import db


def login_parent(client: TestClient) -> None:
    client.post("/login", data={"role": "parent", "login_id": "parent1", "password": "parent123"})


def test_parent_pages_require_parent_session(client: TestClient) -> None:
    parent_response = client.get("/parent", follow_redirects=False)
    children_response = client.get("/parent/children", follow_redirects=False)

    assert parent_response.status_code == 303
    assert parent_response.headers["location"] == "/login"
    assert children_response.status_code == 303
    assert children_response.headers["location"] == "/login"


def test_parent_can_view_dashboard_and_children(client: TestClient) -> None:
    login_parent(client)

    dashboard = client.get("/parent")
    children = client.get("/parent/children")

    assert dashboard.status_code == 200
    assert children.status_code == 200
    assert "こども" in children.text


def test_parent_can_add_child_with_default_route(client: TestClient) -> None:
    login_parent(client)

    response = client.post(
        "/parent/children",
        data={"child_name": "テスト子", "child_login_id": "child-test", "child_password": "pass123"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/parent/children"
    with db.get_db() as conn:
        child = conn.execute("SELECT * FROM child_account WHERE child_login_id = ?", ("child-test",)).fetchone()
        route = conn.execute("SELECT * FROM child_route WHERE child_id = ?", (child["id"],)).fetchone()
    assert child["child_name"] == "テスト子"
    assert route["railway_id"] == "Toei.Oedo"
    assert route["home_station"] == "都庁前"


def test_parent_can_open_child_edit_page(client: TestClient) -> None:
    login_parent(client)
    with db.get_db() as conn:
        child_id = conn.execute("SELECT id FROM child_account WHERE child_login_id = ?", ("child1",)).fetchone()["id"]

    response = client.get(f"/parent/children/{child_id}")

    assert response.status_code == 200
    assert "こども" in response.text
    assert "大江戸線" in response.text


def test_child_session_cannot_access_parent_pages(client: TestClient) -> None:
    client.post("/login", data={"role": "child", "login_id": "child1", "password": "child123"})

    response = client.get("/parent", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"
