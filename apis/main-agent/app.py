from typing import Dict, Any
from pydantic import BaseModel

class EmailPayload(BaseModel):
    gmail_id: str
    subject: str
    from_: str
    to: str
    body: str
    headers: Dict[str, Any] = {}

from fastapi import FastAPI, status

app = FastAPI()

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "ok"}

@app.post("/email", status_code=status.HTTP_202_ACCEPTED)
async def process_email(email: EmailPayload):
    # Example: log, enqueue, or call another internal service.
    # For now, we just echo a small acknowledgment.
    # Replace this with your domain logic (DB insert, queue publish, etc.).
    print(f"Received email {email.gmail_id} from {email.from_} with subject {email.subject}")

    return {"status": "accepted", "gmail_id": email.gmail_id}