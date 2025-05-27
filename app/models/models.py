from pydantic import BaseModel
from enum import Enum
from typing import List


class DataItem(BaseModel):
    dataType: str | None = ""
    value: str | None = ""


class TokenData(BaseModel):
    google_sub: str
    email: str
    name: str
    picture: str
