from __future__ import annotations

from fastapi import Request


def current_role(request: Request) -> str | None:
    return request.session.get("role")


def require_parent(request: Request) -> int | None:
    if request.session.get("role") != "parent":
        return None
    return request.session.get("parent_id")


def require_child(request: Request) -> tuple[int, int] | None:
    if request.session.get("role") != "child":
        return None
    pid = request.session.get("parent_id")
    cid = request.session.get("child_id")
    if not pid or not cid:
        return None
    return pid, cid
