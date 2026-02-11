"""Google Connector Service

Local FastAPI service to expose read-only access to:
- Google Calendar
- Gmail
- Google Drive

Auth flow:
- You create OAuth client credentials in Google Cloud Console (Desktop app).
- Save the client_secret file as credentials.json in this folder.
- First run: we open a browser for you to grant access; tokens are stored in token.json.
"""

import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

APP_DIR = Path(__file__).parent
CREDENTIALS_FILE = APP_DIR / "credentials.json"  # downloaded from Google Cloud Console
TOKEN_FILE = APP_DIR / "token.json"             # stored after first auth flow

# Scopes: read/write for Calendar, Gmail (modify), and Drive (file-level)
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive.file",
]

# Calendar IDs
PRIMARY_CAL_ID = "primary"
FAMILY_CAL_ID = "family18346276431992889799@group.calendar.google.com"

app = FastAPI(title="Google Connector", version="0.3.0")


class CalendarEvent(BaseModel):
    start: Optional[str]
    end: Optional[str]
    summary: Optional[str]
    description: Optional[str]
    location: Optional[str]


class GmailMessage(BaseModel):
    id: str
    threadId: Optional[str]
    sender: Optional[str]
    subject: Optional[str]
    snippet: Optional[str]


class DriveFile(BaseModel):
    id: str
    name: Optional[str]
    mimeType: Optional[str]
    modifiedTime: Optional[str]


class DriveFileContent(BaseModel):
    id: str
    name: Optional[str]
    mimeType: Optional[str]
    content: str


def get_credentials() -> Credentials:
    """Load or create OAuth credentials.

    - Requires credentials.json (OAuth client) to exist in APP_DIR.
    - Stores/refreshes token.json.
    """
    if not CREDENTIALS_FILE.exists():
        raise RuntimeError(
            f"Missing {CREDENTIALS_FILE}. Please download your OAuth client file "
            "from Google Cloud Console and save it as credentials.json here."
        )

    creds: Optional[Credentials] = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            # This will open a browser window the first time
            creds = flow.run_local_server(port=0)

        TOKEN_FILE.write_text(creds.to_json())

    return creds


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/calendar/next", response_model=List[CalendarEvent])
async def calendar_next(max_results: int = 10):
    """Return the next upcoming events from primary + Family calendars."""
    try:
        creds = get_credentials()
        service = build("calendar", "v3", credentials=creds)

        now_iso = datetime.now(timezone.utc).isoformat()

        events: List[CalendarEvent] = []

        for cal_id in (PRIMARY_CAL_ID, FAMILY_CAL_ID):
            events_result = (
                service.events()
                .list(
                    calendarId=cal_id,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                    timeMin=now_iso,
                )
                .execute()
            )
            items = events_result.get("items", [])

            for item in items:
                start = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date")
                end = item.get("end", {}).get("dateTime") or item.get("end", {}).get("date")
                events.append(
                    CalendarEvent(
                        start=start,
                        end=end,
                        summary=item.get("summary"),
                        description=item.get("description"),
                        location=item.get("location"),
                    )
                )

        # Sort combined events by start time
        def parse_dt(s: Optional[str]):
            if not s:
                return ""  # push all-day/unknown to the top
            return s

        events.sort(key=lambda e: parse_dt(e.start))
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/gmail/unread", response_model=List[GmailMessage])
async def gmail_unread(max_results: int = 10):
    """Return a list of recent unread emails from the primary inbox."""
    try:
        creds = get_credentials()
        service = build("gmail", "v1", credentials=creds)

        # List unread messages in INBOX
        results = (
            service.users()
            .messages()
            .list(userId="me", labelIds=["INBOX"], q="is:unread", maxResults=max_results)
            .execute()
        )
        messages = results.get("messages", [])

        out: List[GmailMessage] = []

        for msg_meta in messages:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_meta["id"], format="metadata", metadataHeaders=["From", "Subject"])
                .execute()
            )

            headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
            out.append(
                GmailMessage(
                    id=msg.get("id"),
                    threadId=msg.get("threadId"),
                    sender=headers.get("from"),
                    subject=headers.get("subject"),
                    snippet=msg.get("snippet"),
                )
            )

        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/drive/recent", response_model=List[DriveFile])
async def drive_recent(max_results: int = 20):
    """Return a list of recently modified files in Drive."""
    try:
        creds = get_credentials()
        service = build("drive", "v3", credentials=creds)

        results = (
            service.files()
            .list(
                pageSize=max_results,
                fields="files(id, name, mimeType, modifiedTime)",
                orderBy="modifiedTime desc",
                q="trashed = false",
            )
            .execute()
        )
        files = results.get("files", [])

        out: List[DriveFile] = []
        for f in files:
            out.append(
                DriveFile(
                    id=f.get("id"),
                    name=f.get("name"),
                    mimeType=f.get("mimeType"),
                    modifiedTime=f.get("modifiedTime"),
                )
            )

        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/drive/search", response_model=List[DriveFile])
async def drive_search(name: str, max_results: int = 10):
    """Search Drive files by name (simple contains match)."""
    try:
        creds = get_credentials()
        service = build("drive", "v3", credentials=creds)

        # Simple name contains query; case-insensitive behavior depends on Drive
        query = f"name contains '{name}' and trashed = false"

        results = (
            service.files()
            .list(
                pageSize=max_results,
                fields="files(id, name, mimeType, modifiedTime)",
                orderBy="modifiedTime desc",
                q=query,
            )
            .execute()
        )
        files = results.get("files", [])

        out: List[DriveFile] = []
        for f in files:
            out.append(
                DriveFile(
                    id=f.get("id"),
                    name=f.get("name"),
                    mimeType=f.get("mimeType"),
                    modifiedTime=f.get("modifiedTime"),
                )
            )

        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/drive/file/{file_id}", response_model=DriveFileContent)
async def drive_file_content(file_id: str):
    """Return plain-text content for a Drive file when possible.

    - For Google Docs: exports as text/plain.
    - For other file types: returns an error.
    """
    try:
        creds = get_credentials()
        service = build("drive", "v3", credentials=creds)

        meta = service.files().get(fileId=file_id, fields="id, name, mimeType").execute()
        mime = meta.get("mimeType")

        if mime == "application/vnd.google-apps.document":
            # Export Google Docs as plain text
            data = (
                service.files()
                .export(fileId=file_id, mimeType="text/plain")
                .execute()
            )
            # data is bytes
            if isinstance(data, bytes):
                text = data.decode("utf-8", errors="replace")
            else:
                text = str(data)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported mimeType for content export: {mime}",
            )

        return DriveFileContent(
            id=meta.get("id"),
            name=meta.get("name"),
            mimeType=mime,
            content=text,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=9000,
        reload=True,
    )
