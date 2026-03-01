import os
import asyncio
import base64
from email import message_from_bytes
from typing import List

import aiohttp
from googleapiclient.discovery import build, Resource
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

MAIN_AGENT_API_EMAIL_URL = os.getenv("MAIN_AGENT_API_EMAIL_URL")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "10"))

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def get_gmail_service() -> Resource:
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    service = build("gmail", "v1", credentials=creds)
    return service

async def send_to_api(session: aiohttp.ClientSession, payload: dict):
    async with session.post(MAIN_AGENT_API_EMAIL_URL, json=payload) as resp:
        if resp.status >= 400:
            text = await resp.text()
            print(f"Error posting to API: {resp.status} {text}")

def decode_message(raw: str) -> dict:
    msg_bytes = base64.urlsafe_b64decode(raw.encode("utf-8"))
    msg = message_from_bytes(msg_bytes)

    subject = msg.get("Subject", "")
    from_ = msg.get("From", "")
    to_ = msg.get("To", "")
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="ignore")
                break
    else:
        body = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="ignore")

    return {
        "subject": subject,
        "from": from_,
        "to": to_,
        "body": body,
        "headers": dict(msg.items()),
    }

async def process_new_messages(service, last_history_id: str | None):
    # List messages in INBOX, newest first.[web:4][web:6]
    results = service.users().messages().list(
        userId="me",
        labelIds=["INBOX"],
        q="is:unread",
        maxResults=50,
    ).execute()
    messages: List[dict] = results.get("messages", [])

    if not messages:
        return last_history_id

    async with aiohttp.ClientSession() as session:
        tasks = []
        for m in messages:
            msg = service.users().messages().get(userId="me", id=m["id"], format="raw").execute()
            payload = decode_message(msg["raw"])
            payload["gmail_id"] = m["id"]
            tasks.append(send_to_api(session, payload))
        if tasks:
            await asyncio.gather(*tasks)

    # Track last processed message id (simple approach).
    return messages[0]["id"]

async def main():
    service = get_gmail_service()
    last_history_id = None

    while True:
        try:
            last_history_id = await process_new_messages(service, last_history_id)
        except Exception as e:
            print(f"Error in poll loop: {e}")
        await asyncio.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
