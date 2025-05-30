import logging
import asyncio
import json
import random

from prometheus_fastapi_instrumentator import Instrumentator


from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi


from app.settings import settings, setup_logging
from app.api.root import root_router
from app.api.v1.router import api_v1_router
from app.services.db.schemas import Base
from app.services.db.engine import db_engine

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security import OAuth2PasswordBearer

from app.settings import google_fitness_api_user_clients, google_health_api_user_clients, notification_user_clients
from app.services.redisClient import redis_client_async

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY

from sqlalchemy.orm import Session
from app.services.db.db_session import get_session
from app.services.db.schemas import Notifications


import logging


logger = logging.getLogger(__name__)
setup_logging()


# кастомизация для генератора openapi клиента
def custom_generate_unique_id(route: APIRoute):
    return f"{route.tags[0]}-{route.name}"

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    # Здесь выполните валидацию токена (например, с помощью JWT библиотеки)
    if token != "expected_token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return token


app = FastAPI(
    root_path=settings.ROOT_PATH,
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    contact={
        "name": settings.APP_CONTACT_NAME,
        "email": str(settings.APP_CONTACT_EMAIL),
        # "url": str(settings.APP_CONTACT_URL),
    },
    generate_unique_id_function=custom_generate_unique_id,
    openapi_url=settings.APP_OPENAPI_URL,
    docs_url=settings.APP_DOCS_URL,
    redoc_url=settings.APP_REDOC_URL,
    swagger_ui_oauth2_redirect_url=settings.APP_DOCS_URL + "/oauth2-redirect",
)

instrumentator = Instrumentator(
    should_ignore_untemplated=True,
    excluded_handlers=["/metrics"],
).instrument(app)


@app.on_event("startup")
async def startup_event():
    instrumentator.expose(
        app,
        endpoint="/metrics",
        include_in_schema=False,
        tags=["root"],
    )
    # try:
    #     Base.metadata.create_all(bind=db_engine.engine)
    # except Exception:
    #     pass

    await redis_client_async.connect()


@app.on_event("shutdown")
async def shutdown_event():
    # await cmdb_client_stop()
    # await FastAPILimiter.close()
    ...

    # await kafka_client.disconnect()
    await redis_client_async.disconnect()


if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# @app.exception_handler(RequestValidationError)
# async def validation_exception_handler(request: Request, exc: RequestValidationError):
#     # Читаем «сырое» тело (bytes)
#     body = await request.body()
#     logging.error(f"🔴 422 validation error: {exc.errors()}\nRequest body: {body!r}")
#     return JSONResponse(
#         status_code=HTTP_422_UNPROCESSABLE_ENTITY,
#         content={"detail": exc.errors()},
#     )   


app.include_router(api_v1_router)
app.include_router(root_router)




async def broadcast_notification_status():
    """
    Каждую секунду проверяем по пользователю, есть ли у него 
    непрочитанные уведомления (checked=False) — и шлём {has_unchecked: bool}.
    Состояние NOTIFICATIONS в БД НЕ меняется.
    """
    while True:
        # Для каждого подключённого email
        for email, sockets in list(notification_user_clients.items()):
            try:
                session: Session = await get_session().__anext__()
                # Открываем сессию
                # Проверяем наличие хотя бы одного непрочитанного
                exists = session.query(Notifications).filter_by(
                    for_email=email,
                    checked=False
                ).first() is not None

                payload = json.dumps({"has_unchecked": exists})
                # Рассылаем всем WS-клиентам этого email
                for ws in set(sockets):
                    try:
                        await ws.send_text(payload)
                    except Exception:
                        # если отвалился — убираем
                        sockets.discard(ws)
            except Exception:
                # гасим любые ошибки, чтобы таска не умирала
                pass

        await asyncio.sleep(1)


@app.on_event("startup")
async def start_broadcast_tasks():
    
    asyncio.create_task(broadcast_notification_status())