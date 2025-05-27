import json
import pandas as pd
import isodate
from typing import List
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Depends
from app.services.auth import get_current_user
from app.services.redisClient import redis_client_async
from app.settings import settings, security
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.services.db.db_session import get_session
from dateutil.parser import parse
from app.services.emailSender import mailer


api_v2_send_email_router = APIRouter(prefix="/send_email", tags=["get_data"])



class EmailNotificationRequest(BaseModel):
    to_email: str
    subject: str
    message: str


@api_v2_send_email_router.post("/send", status_code=status.HTTP_200_OK)
async def send_email_notification(
    data: EmailNotificationRequest,
    # user=Depends(get_current_user)  # Только авторизованные могут отправлять
):
    try:
        await mailer.send(
            to_email=data.to_email,
            subject=data.subject,
            html_content=f"<p>{data.message}</p>"
        )
        return {"status": "Email sent"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {e}"
        )
