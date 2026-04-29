from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import init_db
from app.paths import DB_PATH, NOTIFICATION_DIR


def main() -> int:
    init_db()
    print(f"initialized db: {DB_PATH}")
    print(f"notification dir: {NOTIFICATION_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
