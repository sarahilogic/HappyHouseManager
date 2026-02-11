from datetime import datetime, timedelta

from googleapiclient.discovery import build

from main import get_credentials, FAMILY_CAL_ID, PRIMARY_CAL_ID

# Create a single test event tomorrow from 10:00 to 10:30 local time


def main():
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)

    # Determine "tomorrow" in local time
    now = datetime.now()
    tomorrow = now.date() + timedelta(days=1)

    start_dt = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 10, 0, 0)
    end_dt = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 10, 30, 0)

    # RFC3339 with explicit offset; assume local is Pacific (America/Los_Angeles, -08:00 winter)
    # For a quick test we hardcode -08:00; you can refine to use pytz/zoneinfo later.
    start_str = start_dt.strftime("%Y-%m-%dT%H:%M:%S-08:00")
    end_str = end_dt.strftime("%Y-%m-%dT%H:%M:%S-08:00")

    event_body = {
        "summary": "HHM Test Event",
        "description": "Test event created by Happy Household Manager connector.",
        "start": {"dateTime": start_str},
        "end": {"dateTime": end_str},
    }

    # Prefer Family calendar if available; fall back to primary
    cal_id = FAMILY_CAL_ID or PRIMARY_CAL_ID

    created = service.events().insert(calendarId=cal_id, body=event_body).execute()

    print("[calendar] Created event:")
    print("  id:", created.get("id"))
    print("  summary:", created.get("summary"))
    print("  start:", created.get("start"))
    print("  end:", created.get("end"))


if __name__ == "__main__":
    main()
