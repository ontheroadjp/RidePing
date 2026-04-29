from __future__ import annotations

import hashlib
import sqlite3

from app.paths import DB_PATH, NOTIFICATION_DIR


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTIFICATION_DIR.mkdir(parents=True, exist_ok=True)
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS parent_account (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              parent_login_id TEXT NOT NULL UNIQUE,
              password_hash TEXT NOT NULL,
              parent_email TEXT NOT NULL,
              home_station TEXT NOT NULL,
              direction TEXT NOT NULL DEFAULT 'down'
            );

            CREATE TABLE IF NOT EXISTS child_account (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              parent_id INTEGER NOT NULL,
              child_login_id TEXT NOT NULL UNIQUE,
              password_hash TEXT NOT NULL,
              child_name TEXT NOT NULL,
              FOREIGN KEY(parent_id) REFERENCES parent_account(id)
            );

            CREATE TABLE IF NOT EXISTS child_route (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              child_id INTEGER NOT NULL,
              route_name TEXT NOT NULL,
              railway_id TEXT NOT NULL DEFAULT 'Toei.Oedo',
              home_station TEXT NOT NULL,
              destination_station TEXT NOT NULL DEFAULT '都庁前',
              direction TEXT NOT NULL DEFAULT 'down',
              FOREIGN KEY(child_id) REFERENCES child_account(id)
            );

            CREATE TABLE IF NOT EXISTS ride_report (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              parent_id INTEGER NOT NULL,
              child_id INTEGER NOT NULL,
              child_name TEXT NOT NULL,
              train_number TEXT,
              from_station TEXT,
              to_station TEXT,
              home_station TEXT NOT NULL,
              eta_home TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(parent_id) REFERENCES parent_account(id),
              FOREIGN KEY(child_id) REFERENCES child_account(id)
            );
            """
        )
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(ride_report)").fetchall()}
        if cols and "parent_id" not in cols:
            conn.executescript(
                """
                ALTER TABLE ride_report RENAME TO ride_report_legacy;
                CREATE TABLE ride_report (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  parent_id INTEGER NOT NULL,
                  child_id INTEGER NOT NULL,
                  child_name TEXT NOT NULL,
                  train_number TEXT,
                  from_station TEXT,
                  to_station TEXT,
                  home_station TEXT NOT NULL,
                  eta_home TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  FOREIGN KEY(parent_id) REFERENCES parent_account(id),
                  FOREIGN KEY(child_id) REFERENCES child_account(id)
                );
                """
            )

        cur = conn.execute("SELECT COUNT(*) AS c FROM parent_account")
        if cur.fetchone()["c"] == 0:
            conn.execute(
                "INSERT INTO parent_account (parent_login_id, password_hash, parent_email, home_station, direction) VALUES (?, ?, ?, ?, ?)",
                ("parent1", hash_password("parent123"), "parent@example.com", "都庁前", "down"),
            )
            parent_id = conn.execute("SELECT id FROM parent_account WHERE parent_login_id = ?", ("parent1",)).fetchone()["id"]
            conn.execute(
                "INSERT INTO child_account (parent_id, child_login_id, password_hash, child_name) VALUES (?, ?, ?, ?)",
                (parent_id, "child1", hash_password("child123"), "こども"),
            )
            child_id = conn.execute("SELECT id FROM child_account WHERE child_login_id = ?", ("child1",)).fetchone()["id"]
            conn.execute(
                "INSERT INTO child_route (child_id, route_name, railway_id, home_station, destination_station, direction) VALUES (?, ?, ?, ?, ?, ?)",
                (child_id, "大江戸線", "Toei.Oedo", "都庁前", "都庁前", "down"),
            )

        legacy_exists = conn.execute(
            "SELECT COUNT(*) AS c FROM sqlite_master WHERE type='table' AND name='ride_report_legacy'"
        ).fetchone()["c"]
        if legacy_exists:
            parent = conn.execute("SELECT id FROM parent_account ORDER BY id LIMIT 1").fetchone()
            child = conn.execute("SELECT id, child_name FROM child_account WHERE parent_id = ? ORDER BY id LIMIT 1", (parent["id"],)).fetchone()
            conn.execute(
                """
                INSERT INTO ride_report (parent_id, child_id, child_name, train_number, from_station, to_station, home_station, eta_home, created_at)
                SELECT ?, ?, ?, train_number, from_station, to_station, home_station, eta_home, created_at
                FROM ride_report_legacy
                """,
                (parent["id"], child["id"], child["child_name"]),
            )
            conn.execute("DROP TABLE ride_report_legacy")

        child_rows = conn.execute("SELECT id FROM child_account").fetchall()
        route_cols = {row["name"] for row in conn.execute("PRAGMA table_info(child_route)").fetchall()}
        if "railway_id" not in route_cols:
            conn.execute("ALTER TABLE child_route ADD COLUMN railway_id TEXT NOT NULL DEFAULT 'Toei.Oedo'")
        if "destination_station" not in route_cols:
            conn.execute("ALTER TABLE child_route ADD COLUMN destination_station TEXT NOT NULL DEFAULT '都庁前'")
        for child in child_rows:
            rc = conn.execute("SELECT COUNT(*) AS c FROM child_route WHERE child_id = ?", (child["id"],)).fetchone()["c"]
            if rc == 0:
                conn.execute(
                    "INSERT INTO child_route (child_id, route_name, railway_id, home_station, destination_station, direction) VALUES (?, ?, ?, ?, ?, ?)",
                    (child["id"], "大江戸線", "Toei.Oedo", "都庁前", "都庁前", "down"),
                )
