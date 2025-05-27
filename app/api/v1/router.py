from fastapi import APIRouter
from .send_email import api_v2_send_email_router


api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(api_v2_send_email_router, tags=["get_data"])
