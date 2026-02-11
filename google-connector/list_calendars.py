from googleapiclient.discovery import build
from main import get_credentials


def main():
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)
    cal_list = service.calendarList().list().execute()
    for item in cal_list.get("items", []):
        print(f"{item.get('id')}\t{item.get('summary')}")


if __name__ == "__main__":
    main()
