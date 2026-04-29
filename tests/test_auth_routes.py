from __future__ import annotations

from fastapi.testclient import TestClient


def test_root_redirects_to_login_when_signed_out(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_parent_login_redirects_to_parent_dashboard(client: TestClient) -> None:
    response = client.post(
        "/login",
        data={"role": "parent", "login_id": "parent1", "password": "parent123"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/parent"


def test_child_login_redirects_to_train_selection(client: TestClient) -> None:
    response = client.post(
        "/login",
        data={"role": "child", "login_id": "child1", "password": "child123"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/trains"


def test_invalid_login_returns_error(client: TestClient) -> None:
    response = client.post(
        "/login",
        data={"role": "parent", "login_id": "parent1", "password": "wrong"},
    )

    assert response.status_code == 400
    assert "IDまたはパスワードが違います" in response.text


def test_logout_clears_session(client: TestClient) -> None:
    client.post("/login", data={"role": "parent", "login_id": "parent1", "password": "parent123"})

    response = client.post("/logout", follow_redirects=False)
    after_logout = client.get("/parent", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    assert after_logout.status_code == 303
    assert after_logout.headers["location"] == "/login"
