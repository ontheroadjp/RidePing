from __future__ import annotations

from datetime import datetime

from app.paths import NOTIFICATION_DIR


def write_notification(
    parent_email: str,
    child_name: str,
    train_number: str,
    from_station: str,
    to_station: str,
    home_station: str,
    eta_home: str,
) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    body = (
        f"To: {parent_email}\n"
        f"Subject: 【この電車に乗ってるよ】乗車連絡\n\n"
        f"{child_name}さんが大江戸線に乗車しました。\n"
        f"列車番号: {train_number}\n"
        f"現在区間: {from_station} -> {to_station}\n"
        f"最寄駅: {home_station}\n"
        f"到着予定: {eta_home}\n"
        f"通知時刻: {ts}\n"
    )
    out = NOTIFICATION_DIR / f"notification-{datetime.now().strftime('%Y%m%d')}.txt"
    with out.open("a", encoding="utf-8") as f:
        f.write(body)
        f.write("\n" + "-" * 40 + "\n\n")
