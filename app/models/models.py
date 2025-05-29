from pydantic import BaseModel, ConfigDict
from enum import Enum
from typing import List
from datetime import  datetime


class TokenData(BaseModel):
    google_sub: str
    email: str
    name: str
    picture: str


class NotificationsModel(BaseModel):
    for_email: str
    time: datetime
    notification_text: str
    checked: bool

    model_config = ConfigDict(from_attributes=True)


class EmailNotificationRequest(BaseModel):
    to_email: str
    subject: str
    message: str
