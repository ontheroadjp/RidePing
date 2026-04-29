from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx
import jpholiday

ODPT_KEY = os.getenv("ODPT_CONSUMER_KEY", "")

MINI_TOKYO_BASE = "https://raw.githubusercontent.com/nagix/mini-tokyo-3d/master/data"
MINI_TOKYO_OEDO_TIMETABLE = f"{MINI_TOKYO_BASE}/train-timetables/toei-oedo.json"
MINI_TOKYO_CACHE_TTL_SEC = 60 * 30

STATIONS = [
    "都庁前", "新宿西口", "東新宿", "若松河田", "牛込柳町", "牛込神楽坂", "飯田橋", "春日", "本郷三丁目",
    "上野御徒町", "新御徒町", "蔵前", "両国", "森下", "清澄白河", "門前仲町", "月島", "勝どき", "築地市場",
    "汐留", "大門", "赤羽橋", "麻布十番", "六本木", "青山一丁目", "国立競技場", "代々木", "新宿", "都庁前",
]

_MT3D_CACHE: dict[str, object] = {
    "loaded_at": 0.0,
    "stations": {},
    "railway_stations": [],
    "timetables": [],
    "color": "#CE045B",
    "railway_master": [],
    "railway_station_names": {},
}


@dataclass
class TrainCandidate:
    train_id: str
    train_number: str
    from_station: str
    to_station: str
    delay_sec: int
    eta_home: str
    state: str = "running"
    from_index: float = 0.0
    to_index: float = 0.0
    position_index: float = 0.0
    departed_at_sec: int = 0
    arrives_at_sec: int = 0
    current_time_sec: int = 0
    departure_label: str = ""


def normalize_station_id(station_id: str) -> str:
    parts = station_id.split(".")
    if parts and parts[-1].isdigit():
        return ".".join(parts[:-1])
    return station_id


def hhmm_to_minutes(value: str) -> int:
    hh, mm = value.split(":")
    return int(hh) * 60 + int(mm)


def hhmm_to_service_seconds(value: str) -> int:
    minutes = hhmm_to_minutes(value)
    if minutes < 180:
        minutes += 24 * 60
    return minutes * 60


def current_service_datetime(now: datetime | None = None) -> tuple[datetime, int]:
    current = now or datetime.now()
    minutes = current.hour * 60 + current.minute
    service_seconds = (minutes + (24 * 60 if minutes < 180 else 0)) * 60 + current.second
    service_date = current - timedelta(days=1) if minutes < 180 else current
    return service_date, service_seconds


def timetable_day_type(service_date: datetime) -> str:
    if service_date.weekday() >= 5 or jpholiday.is_holiday(service_date.date()):
        return "SaturdayHoliday"
    return "Weekday"


def format_service_seconds(seconds: int) -> str:
    minutes = (seconds // 60) % (24 * 60)
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def station_name(urn: str | None) -> str:
    if not urn:
        return "不明"
    if ":" not in urn:
        return urn
    tail = urn.split(":", 1)[1]
    return tail.split(".")[-1] if "." in tail else tail


def load_minitokyo_oedo_data(force: bool = False) -> None:
    now = time.time()
    if not force and now - float(_MT3D_CACHE.get("loaded_at", 0.0)) < MINI_TOKYO_CACHE_TTL_SEC and _MT3D_CACHE.get("railway_stations"):
        return
    try:
        with httpx.Client(timeout=8.0) as client:
            railways = client.get(f"{MINI_TOKYO_BASE}/railways.json").json()
            stations = client.get(f"{MINI_TOKYO_BASE}/stations.json").json()
            timetables = client.get(MINI_TOKYO_OEDO_TIMETABLE).json()
    except Exception:
        return

    station_title_map: dict[str, str] = {}
    for s in stations:
        sid = s.get("id", "")
        title = s.get("title", {}).get("ja")
        if sid and title:
            station_title_map[sid] = title

    railway_stations: list[str] = []
    railway_master: list[dict[str, object]] = []
    railway_station_names: dict[str, list[str]] = {}
    color = "#CE045B"
    for r in railways:
        rid = r.get("id")
        title = r.get("title", {}).get("ja")
        station_names: list[str] = []
        for sid in r.get("stations", []):
            normalized = normalize_station_id(sid)
            name = station_title_map.get(normalized)
            if name and (not station_names or station_names[-1] != name):
                station_names.append(name)
        if rid and title and station_names:
            railway_master.append({"id": rid, "title_ja": title})
            railway_station_names[rid] = station_names

    for r in railways:
        if r.get("id") == "Toei.Oedo":
            color = r.get("color") or color
            for sid in r.get("stations", []):
                normalized = normalize_station_id(sid)
                name = station_title_map.get(normalized)
                if name and (not railway_stations or railway_stations[-1] != name):
                    railway_stations.append(name)
            break

    if railway_stations:
        _MT3D_CACHE["loaded_at"] = now
        _MT3D_CACHE["stations"] = station_title_map
        _MT3D_CACHE["railway_stations"] = railway_stations
        _MT3D_CACHE["timetables"] = timetables
        _MT3D_CACHE["color"] = color
        _MT3D_CACHE["railway_master"] = railway_master
        _MT3D_CACHE["railway_station_names"] = railway_station_names


def get_route_station_map() -> dict[str, list[str]]:
    load_minitokyo_oedo_data()
    rows = _MT3D_CACHE.get("railway_station_names") or {}
    return dict(rows)


def get_railway_master() -> list[dict[str, object]]:
    load_minitokyo_oedo_data()
    rows = _MT3D_CACHE.get("railway_master") or []
    return sorted(rows, key=lambda x: str(x.get("title_ja", "")))


def get_railway_stations(railway_id: str) -> list[str]:
    load_minitokyo_oedo_data()
    names = _MT3D_CACHE.get("railway_station_names") or {}
    return list(names.get(railway_id, []))


def get_terminal_destinations(railway_id: str) -> list[str]:
    stations = get_railway_stations(railway_id)
    if len(stations) < 2:
        return []
    return [stations[0], stations[-1]]


def infer_direction_from_destination(railway_id: str, destination_station: str) -> str:
    terminals = get_terminal_destinations(railway_id)
    if len(terminals) < 2:
        return "down"
    if destination_station == terminals[1]:
        return "down"
    return "up"


def timetable_loop_for_destination(railway_id: str, destination_station: str) -> str:
    terminals = get_terminal_destinations(railway_id)
    if len(terminals) < 2:
        return "OuterLoop"
    return "InnerLoop" if destination_station == terminals[0] else "OuterLoop"


def get_station_options(railway_id: str = "Toei.Oedo") -> list[str]:
    load_minitokyo_oedo_data()
    dynamic = get_railway_stations(railway_id)
    if dynamic:
        return list(dynamic)
    return STATIONS[:-1]


def first_departure_by_station(stations_for_map: list[str], route_direction: str) -> dict[str, str]:
    load_minitokyo_oedo_data()
    timetables = _MT3D_CACHE.get("timetables") or []
    station_map = _MT3D_CACHE.get("stations") or {}
    target_loop = "OuterLoop" if route_direction == "down" else "InnerLoop"
    result: dict[str, int] = {}

    for t in timetables:
        if t.get("d") != target_loop:
            continue
        for stop in t.get("tt", []):
            dep = stop.get("d")
            sid = normalize_station_id(stop.get("s", ""))
            name = station_map.get(sid, station_name(sid))
            if not dep or not name:
                continue
            m = hhmm_to_minutes(dep)
            if m < 180:
                continue
            if name not in result or m < result[name]:
                result[name] = m

    out: dict[str, str] = {}
    for s in stations_for_map:
        m = result.get(s)
        out[s] = f"{m // 60:02d}:{m % 60:02d}" if m is not None else "--:--"
    return out


def first_departure_label_by_station(stations_for_map: list[str], route_direction: str) -> dict[str, str]:
    times = first_departure_by_station(stations_for_map, route_direction)
    now = datetime.now()
    now_min = now.hour * 60 + now.minute
    labels: dict[str, str] = {}
    for station, hhmm in times.items():
        if hhmm == "--:--":
            labels[station] = ""
            continue
        dep_min = hhmm_to_minutes(hhmm)
        labels[station] = f"始発: {hhmm}" if now_min < dep_min else ""
    return labels


def eta_from_timetable(home_station: str, stops: list[dict[str, str]], station_map: dict[str, str], now_sec: int) -> str:
    for stop in stops:
        sid = normalize_station_id(stop.get("s", ""))
        name = station_map.get(sid, station_name(sid))
        if name != home_station:
            continue
        value = stop.get("a") or stop.get("d")
        if not value:
            continue
        sec = hhmm_to_service_seconds(value)
        if sec >= now_sec:
            return format_service_seconds(sec)
    return "--:--"


def timetable_trains(
    home_station: str,
    railway_id: str,
    destination_station: str,
    stations_for_map: list[str],
    now: datetime | None = None,
) -> list[TrainCandidate]:
    load_minitokyo_oedo_data()
    timetables = _MT3D_CACHE.get("timetables") or []
    station_map = _MT3D_CACHE.get("stations") or {}
    service_date, now_sec = current_service_datetime(now)
    day_type = timetable_day_type(service_date)
    target_loop = timetable_loop_for_destination(railway_id, destination_station)
    station_positions: dict[str, list[int]] = {}
    for idx, name in enumerate(stations_for_map):
        station_positions.setdefault(name, []).append(idx)
    rows: list[TrainCandidate] = []

    for t in timetables:
        if t.get("r") != railway_id or t.get("d") != target_loop:
            continue
        if not str(t.get("id", "")).endswith(f".{day_type}"):
            continue

        stops = t.get("tt", [])
        train_number = t.get("n", "列車番号不明")
        for i, current_stop in enumerate(stops):
            sid = normalize_station_id(current_stop.get("s", ""))
            station = station_map.get(sid, station_name(sid))
            arr_here = current_stop.get("a")
            dep_here = current_stop.get("d")

            if arr_here and dep_here:
                arr_sec = hhmm_to_service_seconds(arr_here)
                dep_sec = hhmm_to_service_seconds(dep_here)
                if arr_sec <= now_sec <= dep_sec and station in station_positions:
                    idx = float(station_positions[station][0])
                    rows.append(
                        TrainCandidate(
                            train_id=f"mt3d-{t.get('id', train_number)}-{i}-stop",
                            train_number=train_number,
                            from_station=station,
                            to_station=station,
                            delay_sec=0,
                            eta_home=eta_from_timetable(home_station, stops, station_map, now_sec),
                            state="stopped",
                            from_index=idx,
                            to_index=idx,
                            position_index=idx,
                            departed_at_sec=dep_sec,
                            arrives_at_sec=arr_sec,
                            current_time_sec=now_sec,
                            departure_label=format_service_seconds(dep_sec),
                        )
                    )
                    break

            if i >= len(stops) - 1 or not dep_here:
                continue
            next_stop = stops[i + 1]
            next_sid = normalize_station_id(next_stop.get("s", ""))
            next_station = station_map.get(next_sid, station_name(next_sid))
            arr_next = next_stop.get("a")
            if not arr_next:
                continue
            dep_sec = hhmm_to_service_seconds(dep_here)
            arr_sec = hhmm_to_service_seconds(arr_next)
            if dep_sec <= now_sec <= arr_sec and station in station_positions and next_station in station_positions:
                pairs = [
                    (from_pos, to_pos)
                    for from_pos in station_positions[station]
                    for to_pos in station_positions[next_station]
                    if to_pos > from_pos
                ]
                if not pairs:
                    continue
                from_idx_int, to_idx_int = min(pairs, key=lambda p: p[1] - p[0])
                from_idx = float(from_idx_int)
                to_idx = float(to_idx_int)
                progress = 1.0 if arr_sec == dep_sec else (now_sec - dep_sec) / (arr_sec - dep_sec)
                position = from_idx + ((to_idx - from_idx) * max(0.0, min(1.0, progress)))
                rows.append(
                    TrainCandidate(
                        train_id=f"mt3d-{t.get('id', train_number)}-{i}",
                        train_number=train_number,
                        from_station=station,
                        to_station=next_station,
                        delay_sec=0,
                        eta_home=eta_from_timetable(home_station, stops, station_map, now_sec),
                        state="running",
                        from_index=from_idx,
                        to_index=to_idx,
                        position_index=position,
                        departed_at_sec=dep_sec,
                        arrives_at_sec=arr_sec,
                        current_time_sec=now_sec,
                        departure_label=format_service_seconds(dep_sec),
                    )
                )
                break

    rows.sort(key=lambda x: x.position_index)
    return rows


def train_to_dict(train: TrainCandidate) -> dict[str, object]:
    return {
        "train_id": train.train_id,
        "train_number": train.train_number,
        "from_station": train.from_station,
        "to_station": train.to_station,
        "delay_sec": train.delay_sec,
        "eta_home": train.eta_home,
        "state": train.state,
        "from_index": train.from_index,
        "to_index": train.to_index,
        "position_index": train.position_index,
        "departed_at_sec": train.departed_at_sec,
        "arrives_at_sec": train.arrives_at_sec,
        "current_time_sec": train.current_time_sec,
        "departure_label": train.departure_label,
    }


def validate_timetable_positions(
    railway_id: str,
    destination_station: str,
    stations_for_map: list[str],
    sample_step_minutes: int = 5,
) -> dict[str, object]:
    load_minitokyo_oedo_data()
    timetables = _MT3D_CACHE.get("timetables") or []
    station_map = _MT3D_CACHE.get("stations") or {}
    target_loop = timetable_loop_for_destination(railway_id, destination_station)
    station_positions: dict[str, list[int]] = {}
    for idx, name in enumerate(stations_for_map):
        station_positions.setdefault(name, []).append(idx)
    issues: list[dict[str, object]] = []
    checked = 0

    for day_type in ("Weekday", "SaturdayHoliday"):
        for t in timetables:
            if t.get("r") != railway_id or t.get("d") != target_loop:
                continue
            if not str(t.get("id", "")).endswith(f".{day_type}"):
                continue
            stops = t.get("tt", [])
            for i in range(len(stops) - 1):
                current_stop = stops[i]
                next_stop = stops[i + 1]
                dep = current_stop.get("d")
                arr = next_stop.get("a")
                if not dep or not arr:
                    continue
                from_name = station_map.get(normalize_station_id(current_stop.get("s", "")), "")
                to_name = station_map.get(normalize_station_id(next_stop.get("s", "")), "")
                dep_sec = hhmm_to_service_seconds(dep)
                arr_sec = hhmm_to_service_seconds(arr)
                if from_name not in station_positions or to_name not in station_positions:
                    issues.append({"type": "station_not_on_map", "train": t.get("id"), "from": from_name, "to": to_name})
                    continue
                pairs = [
                    (from_idx, to_idx)
                    for from_idx in station_positions[from_name]
                    for to_idx in station_positions[to_name]
                    if to_idx > from_idx
                ]
                if not pairs:
                    issues.append(
                        {
                            "type": "non_increasing_index",
                            "train": t.get("id"),
                            "from": from_name,
                            "to": to_name,
                            "from_indexes": station_positions[from_name],
                            "to_indexes": station_positions[to_name],
                        }
                    )
                    continue
                from_index, to_index = min(pairs, key=lambda p: p[1] - p[0])
                if arr_sec < dep_sec:
                    issues.append({"type": "arrival_before_departure", "train": t.get("id"), "from": from_name, "to": to_name, "dep": dep, "arr": arr})

                span = max(1, arr_sec - dep_sec)
                step = max(1, sample_step_minutes * 60)
                for offset in range(0, span + 1, step):
                    now_sec = min(arr_sec, dep_sec + offset)
                    progress = 1.0 if arr_sec == dep_sec else (now_sec - dep_sec) / (arr_sec - dep_sec)
                    expected = from_index + ((to_index - from_index) * progress)
                    if expected < from_index - 0.0001 or expected > to_index + 0.0001:
                        issues.append({"type": "position_out_of_segment", "train": t.get("id"), "position": expected, "from": from_name, "to": to_name})
                    checked += 1

    return {
        "railway_id": railway_id,
        "destination_station": destination_station,
        "target_loop": target_loop,
        "checked_samples": checked,
        "issue_count": len(issues),
        "issues": issues[:200],
    }


def station_sequence_for_destination(railway_id: str, destination_station: str) -> list[str]:
    load_minitokyo_oedo_data()
    timetables = _MT3D_CACHE.get("timetables") or []
    station_map = _MT3D_CACHE.get("stations") or {}
    target_loop = timetable_loop_for_destination(railway_id, destination_station)
    best: list[str] = []
    for t in timetables:
        if t.get("r") != railway_id or t.get("d") != target_loop:
            continue
        names = [
            station_map.get(normalize_station_id(stop.get("s", "")), station_name(stop.get("s", "")))
            for stop in t.get("tt", [])
        ]
        if destination_station not in names:
            continue
        if len(names) > len(best):
            best = names
    if best:
        return best
    stations = get_station_options(railway_id)
    if destination_station and stations and destination_station == stations[0]:
        return list(reversed(stations))
    return stations
