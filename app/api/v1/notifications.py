import json
import pandas as pd
import isodate
import datetime
from typing import List
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Depends
from app.services.auth import get_current_user
from app.services.redisClient import redis_client_async
from app.settings import settings, security
from app.models.models import NotificationsModel
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.services.db.db_session import get_session
from dateutil.parser import parse
from app.services.emailSender import mailer
from app.services.db.schemas import Notifications
from app.models.models import TokenData, EmailNotificationRequest


api_v2_get_notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])


@api_v2_get_notifications_router.post("/send_email", status_code=status.HTTP_200_OK)
async def send_email_notification(
    data: EmailNotificationRequest,
):
    try:
        session: Session = await get_session().__anext__()
        await mailer.send(
            to_email=data.to_email,
            subject=data.subject,
            html_content=f"<p>{data.message}</p>"
        )

        new_notification = Notifications(
            for_email = data.to_email,
            time = str(datetime.datetime.now()),
            notification_text = data.message,
            checked = False
        )
        session.add(new_notification)
        session.commit()

        return {"status": "Email sent"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {e}"
        )


@api_v2_get_notifications_router.get(
    "/get_unchecked_notifications",
    status_code=status.HTTP_200_OK,
    response_model=List[NotificationsModel],
)
async def get_unchecked_notifications(
    token=Depends(security),
    user_data: TokenData=Depends(get_current_user)
):
    try:
        # Получаем сессию
        session: Session = await get_session().__anext__()

        # Запрашиваем только непрочитанные уведомления
        records = (
            session.query(Notifications)
            .filter_by(for_email=user_data.email, checked=False)
            .all()
        )

        # Конвертим ORM-модели в Pydantic-модели
        processed_records = [
            NotificationsModel.model_validate(rec)
            for rec in records
        ]

        for rec in records:
            rec.checked = True
        session.commit()

        return processed_records

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get unchecked notifications: {e}"
        )


@api_v2_get_notifications_router.get("/get_all_notifications", status_code=status.HTTP_200_OK, response_model=List[NotificationsModel])
async def get_all_notifications(
    token=Depends(security),
    user_data: TokenData=Depends(get_current_user)
):
    try:
        session: Session = await get_session().__anext__()
        records = (
            session.query(Notifications)
            .filter_by(for_email=user_data.email)
            .all()
        )
        
        processed_records = [
            NotificationsModel.model_validate(rec)
            for rec in records
        ]

        return processed_records
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get all notifications: {e}"
        )
