from __future__ import annotations

import os

from fastapi.templating import Jinja2Templates

from app.paths import BASE_DIR

DEV_UI_ENABLED = os.getenv("DEV_UI_ENABLED", "1") == "1"

templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
templates.env.globals["dev_ui_enabled"] = DEV_UI_ENABLED
