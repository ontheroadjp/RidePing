from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.timetable import station_sequence_for_destination, validate_timetable_positions


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate timetable-derived train positions.")
    parser.add_argument("--railway-id", default="Toei.Oedo")
    parser.add_argument("--destination", default="光が丘")
    parser.add_argument("--step-minutes", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    stations = station_sequence_for_destination(args.railway_id, args.destination)

    result = validate_timetable_positions(args.railway_id, args.destination, stations, args.step_minutes)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"railway={result['railway_id']} destination={result['destination_station']} loop={result['target_loop']}")
        print(f"checked_samples={result['checked_samples']} issue_count={result['issue_count']}")
        for issue in result["issues"][:20]:
            print(json.dumps(issue, ensure_ascii=False))

    return 1 if result["issue_count"] else 0


if __name__ == "__main__":
    sys.exit(main())
