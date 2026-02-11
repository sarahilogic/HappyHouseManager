from googleapiclient.discovery import build

from main import get_credentials, FAMILY_CAL_ID, PRIMARY_CAL_ID

# Deletes the previously created HHM Test Event by id.
# If you ever recreate it with a different id, update EVENT_ID below.

EVENT_ID = "13uqc1kgql6aef44oghbe18kd4"


def main():
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)

    cal_id = FAMILY_CAL_ID or PRIMARY_CAL_ID

    print(f"[calendar] Deleting event {EVENT_ID} from calendar {cal_id}...")
    service.events().delete(calendarId=cal_id, eventId=EVENT_ID).execute()
    print("[calendar] Deletion request sent (no content on success).")


if __name__ == "__main__":
    main()
