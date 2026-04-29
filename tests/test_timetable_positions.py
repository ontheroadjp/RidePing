from __future__ import annotations

from app.timetable import station_sequence_for_destination, validate_timetable_positions


def test_oedo_hikarigaoka_direction_timetable_positions_are_monotonic() -> None:
    stations = station_sequence_for_destination("Toei.Oedo", "光が丘")
    result = validate_timetable_positions("Toei.Oedo", "光が丘", stations, sample_step_minutes=10)

    assert result["checked_samples"] > 0
    assert result["issue_count"] == 0, result["issues"][:5]


def test_oedo_tochomae_direction_timetable_positions_are_monotonic() -> None:
    stations = station_sequence_for_destination("Toei.Oedo", "都庁前")
    result = validate_timetable_positions("Toei.Oedo", "都庁前", stations, sample_step_minutes=10)

    assert result["checked_samples"] > 0
    assert result["issue_count"] == 0, result["issues"][:5]
