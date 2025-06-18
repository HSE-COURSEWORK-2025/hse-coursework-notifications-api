import datetime
from typing import List
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.services.auth import get_current_user
from app.settings import security
from app.services.db.db_session import get_session
from app.services.emailSender import mailer
from app.models.models import NotificationsModel, TokenData, EmailNotificationRequest
from app.services.db.schemas import Notifications
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status, HTTPException
from app.services.auth import get_current_user
from app.models.models import TokenData
from app.settings import security, notification_user_clients

api_v2_get_notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])


@api_v2_get_notifications_router.post(
    "/send_email", 
    status_code=status.HTTP_200_OK
)
async def send_email_notification(
    data: EmailNotificationRequest,
):
    try:
        session: Session = await get_session().__anext__()
        # Отправка письма
        

        # Запись уведомления в БД
        new_notification = Notifications(
            for_email=data.to_email,
            time=datetime.datetime.now(),    # лучше хранить как datetime
            notification_text=data.message,
            checked=False
        )
        session.add(new_notification)
        session.commit()

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


@api_v2_get_notifications_router.get(
    "/get_unchecked_notifications",
    status_code=status.HTTP_200_OK,
    response_model=List[NotificationsModel],
)
async def get_unchecked_notifications(
    token=Depends(security),
    user_data: TokenData = Depends(get_current_user)
):
    try:
        session: Session = await get_session().__anext__()

        # Выбираем только непрочитанные и сортируем по убыванию времени
        records = (
            session.query(Notifications)
            .filter_by(for_email=user_data.email, checked=False)
            .order_by(Notifications.time.desc())
            .all()
        )

        # Преобразуем в Pydantic-модели
        processed_records = [
            NotificationsModel.model_validate(rec)
            for rec in records
        ]

        # Отмечаем как прочитанные
        for rec in records:
            rec.checked = True
        session.commit()

        return processed_records

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get unchecked notifications: {e}"
        )


@api_v2_get_notifications_router.get(
    "/get_all_notifications",
    status_code=status.HTTP_200_OK,
    response_model=List[NotificationsModel]
)
async def get_all_notifications(
    token=Depends(security),
    user_data: TokenData = Depends(get_current_user)
):
    try:
        session: Session = await get_session().__anext__()

        # Все уведомления пользователя, сортировка по убыванию времени
        records = (
            session.query(Notifications)
            .filter_by(for_email=user_data.email)
            .order_by(Notifications.time.desc())
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


@api_v2_get_notifications_router.websocket("/has_unchecked")
async def has_unchecked_notifications_ws(websocket: WebSocket):
    # 1) Примем WS
    await websocket.accept()

    # 2) Забираем токен из query-параметров: /has_unchecked?token=...
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 3) Верифицируем и получаем user_data
    try:
        user_data: TokenData = await get_current_user(token)
    except HTTPException as e:
        # невалидный токен — закрываем WS
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    email = user_data.email

    # 4) Регистрируем WS в глобальном словаре
    clients = notification_user_clients.setdefault(email, set())
    clients.add(websocket)

    try:
        # 5) Держим соединение живым — пинги от клиента не ждём, 
        #    а просто читаем, чтобы NAT/прокси не убили сокет:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        # клиент уходит — чистим
        clients.discard(websocket)
    except Exception:
        # на любую ошибку — тоже чистим и закрываем
        clients.discard(websocket)
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
