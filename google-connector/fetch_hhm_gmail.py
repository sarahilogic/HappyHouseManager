import json
from pathlib import Path

import requests

BASE = "http://127.0.0.1:9000"
OUT_PATH = Path(r"C:\Users\sarah\.openclaw\workspace\HHM_GMAIL_UNREAD.json")


def main():
    resp = requests.get(f"{BASE}/gmail/unread", params={"max_results": 20})
    print("[gmail] status:", resp.status_code)
    if not resp.ok:
        print("[gmail] error:", resp.text)
        return

    msgs = resp.json()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(msgs, indent=2), encoding="utf-8")
    print(f"[gmail] wrote {len(msgs)} messages to {OUT_PATH}")


if __name__ == "__main__":
    main()
