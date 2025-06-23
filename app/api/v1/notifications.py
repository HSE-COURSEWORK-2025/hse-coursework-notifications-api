import datetime
import aiohttp
from typing import List
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session

import logging
from app.services.auth import get_current_user
from app.settings import security
from app.services.db.db_session import get_session
from app.services.emailSender import mailer
from app.models.models import NotificationsModel, TokenData, EmailNotificationRequest
from app.services.db.schemas import Notifications
from fastapi import (
    WebSocket,
    WebSocketDisconnect,
)
from app.settings import notification_user_clients

api_v2_get_notifications_router = APIRouter(
    prefix="/notifications", tags=["notifications"]
)


async def send_email_async(to_email: str, subject: str, message: str):
    url = "http://192.168.1.15:8080/notifications-api/api/v1/notifications/send_email"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {
        "to_email": str(to_email),   # Замените на реальный email
        "subject": str(subject),    # Замените на тему письма
        "message": str(message)     # Замените на текст письма
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                # Проверка статуса ответа
                if response.status == 200:
                    logging.info("Email успешно отправлен!")
                    data = await response.json()
                    logging.info("Ответ сервера:", data)
                else:
                    logging.error(f"Ошибка! Статус код: {response.status}")
                    error_text = await response.text()
                    logging.error("Ответ сервера:", error_text)
    
    except Exception as e:
        logging.error(f"Неожиданная ошибка: {e}")


@api_v2_get_notifications_router.post("/send_email", status_code=status.HTTP_200_OK)
async def send_email_notification(
    data: EmailNotificationRequest,
):
    try:
        session: Session = await get_session().__anext__()
        new_notification = Notifications(
            for_email=data.to_email,
            time=datetime.datetime.now(),
            notification_text=data.message,
            checked=False,
        )
        session.add(new_notification)
        session.commit()

        # await mailer.send(
        #     to_email=data.to_email,
        #     subject=data.subject,
        #     html_content=f"<p>{data.message}</p>",
        # )

        await send_email_async(to_email=data.to_email, subject=data.subject, message=data.message)

        return {"status": "Email sent"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {e}",
        )


@api_v2_get_notifications_router.get(
    "/get_unchecked_notifications",
    status_code=status.HTTP_200_OK,
    response_model=List[NotificationsModel],
)
async def get_unchecked_notifications(
    token=Depends(security), user_data: TokenData = Depends(get_current_user)
):
    try:
        session: Session = await get_session().__anext__()

        records = (
            session.query(Notifications)
            .filter_by(for_email=user_data.email, checked=False)
            .order_by(Notifications.time.desc())
            .all()
        )

        processed_records = [NotificationsModel.model_validate(rec) for rec in records]

        for rec in records:
            rec.checked = True
        session.commit()

        return processed_records

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get unchecked notifications: {e}",
        )


@api_v2_get_notifications_router.get(
    "/get_all_notifications",
    status_code=status.HTTP_200_OK,
    response_model=List[NotificationsModel],
)
async def get_all_notifications(
    token=Depends(security), user_data: TokenData = Depends(get_current_user)
):
    try:
        session: Session = await get_session().__anext__()

        records = (
            session.query(Notifications)
            .filter_by(for_email=user_data.email)
            .order_by(Notifications.time.desc())
            .all()
        )

        processed_records = [NotificationsModel.model_validate(rec) for rec in records]

        return processed_records
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get all notifications: {e}",
        )


@api_v2_get_notifications_router.websocket("/has_unchecked")
async def has_unchecked_notifications_ws(websocket: WebSocket):

    await websocket.accept()

    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        user_data: TokenData = await get_current_user(token)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    email = user_data.email

    clients = notification_user_clients.setdefault(email, set())
    clients.add(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        clients.discard(websocket)
    except Exception:
        clients.discard(websocket)
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
