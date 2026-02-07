import json
from pathlib import Path

import requests

BASE = "http://127.0.0.1:9000"
DOC_NAME = "Happy House Manager"

WORKSPACE_OUT = Path(r"C:\Users\sarah\.openclaw\workspace\HHM_SPEC.txt")


def main():
    print(f"[fetch] Searching Drive for name contains: {DOC_NAME!r}")
    r = requests.get(f"{BASE}/drive/search", params={"name": DOC_NAME, "max_results": 5})
    print("[fetch] search status:", r.status_code)
    if not r.ok:
        print("[fetch] search error:", r.text)
        return

    items = r.json()
    if not items:
        print("[fetch] no files found matching that name")
        return

    file = items[0]
    file_id = file.get("id")
    file_name = file.get("name")
    print(f"[fetch] using file id={file_id}, name={file_name!r}")

    r2 = requests.get(f"{BASE}/drive/file/{file_id}")
    print("[fetch] file status:", r2.status_code)
    if not r2.ok:
        print("[fetch] file error:", r2.text)
        return

    data = r2.json()
    content = data.get("content", "")

    WORKSPACE_OUT.parent.mkdir(parents=True, exist_ok=True)
    WORKSPACE_OUT.write_text(content, encoding="utf-8")
    print(f"[fetch] wrote {len(content)} chars to {WORKSPACE_OUT}")


if __name__ == "__main__":
    main()
