from fastapi import APIRouter
from .notifications import api_v2_get_notifications_router


api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(api_v2_get_notifications_router, tags=["notifications"])
