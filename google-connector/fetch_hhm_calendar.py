import json
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = "http://127.0.0.1:9000"
OUT_PATH = Path(r"C:\Users\sarah\.openclaw\workspace\HHM_CALENDAR.json")


def main():
    resp = requests.get(f"{BASE}/calendar/next", params={"max_results": 50})
    print("[calendar] status:", resp.status_code)
    if not resp.ok:
        print("[calendar] error:", resp.text)
        return

    events = resp.json()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(events, indent=2), encoding="utf-8")
    print(f"[calendar] wrote {len(events)} events to {OUT_PATH}")


if __name__ == "__main__":
    main()
