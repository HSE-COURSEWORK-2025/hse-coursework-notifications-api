import logging
import asyncio
import json

from prometheus_fastapi_instrumentator import Instrumentator


from fastapi import FastAPI, Request
from fastapi.routing import APIRoute
from fastapi.middleware.cors import CORSMiddleware


from app.settings import settings
from app.api.root import root_router
from app.api.v1.router import api_v1_router

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.settings import (
    notification_user_clients, app_logger
)
from app.services.redisClient import redis_client_async


from sqlalchemy.orm import Session
from app.services.db.db_session import get_session
from app.services.db.schemas import Notifications

from app.services.utils import PrometheusMiddleware, metrics, setting_otlp


logger = logging.getLogger(__name__)



def custom_generate_unique_id(route: APIRoute):
    return f"{route.tags[0]}-{route.name}"


security = HTTPBearer()


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
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
    },
    generate_unique_id_function=custom_generate_unique_id,
    openapi_url=settings.APP_OPENAPI_URL,
    docs_url=settings.APP_DOCS_URL,
    redoc_url=settings.APP_REDOC_URL,
    swagger_ui_oauth2_redirect_url=settings.APP_DOCS_URL + "/oauth2-redirect",
)

# instrumentator = Instrumentator(
#     should_ignore_untemplated=True,
#     excluded_handlers=["/metrics"],
# ).instrument(app)

app.add_middleware(PrometheusMiddleware, app_name=settings.APP_TITLE)
app.add_route("/metrics", metrics)
setting_otlp(app, settings.APP_TITLE, settings.OTLP_GRPC_ENDPOINT)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    status = response.status_code
    app_logger.info(
        f"{request.method} {request.url.path}",
        extra={"status_code": status}
    )
    return response


@app.on_event("startup")
async def startup_event():
    # instrumentator.expose(
    #     app,
    #     endpoint="/metrics",
    #     include_in_schema=False,
    #     tags=["root"],
    # )

    await redis_client_async.connect()


@app.on_event("shutdown")
async def shutdown_event():
    await redis_client_async.disconnect()


if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


app.include_router(api_v1_router)
app.include_router(root_router)


async def broadcast_notification_status():
    """
    Каждую секунду проверяем по пользователю, есть ли у него
    непрочитанные уведомления (checked=False) — и шлём {has_unchecked: bool}.
    Состояние NOTIFICATIONS в БД НЕ меняется.
    """
    while True:
        for email, sockets in list(notification_user_clients.items()):
            try:
                session: Session = await get_session().__anext__()
                exists = (
                    session.query(Notifications)
                    .filter_by(for_email=email, checked=False)
                    .first()
                    is not None
                )

                payload = json.dumps({"has_unchecked": exists})
                for ws in set(sockets):
                    try:
                        await ws.send_text(payload)
                    except Exception:
                        sockets.discard(ws)
            except Exception:
                pass

        await asyncio.sleep(1)


@app.on_event("startup")
async def start_broadcast_tasks():

    asyncio.create_task(broadcast_notification_status())
