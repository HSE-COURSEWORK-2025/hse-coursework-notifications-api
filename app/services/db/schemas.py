
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    Boolean,
)
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class Notifications(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    for_email = Column(String, nullable=False)
    time = Column(DateTime(timezone=True), nullable=False)
    notification_text = Column(Text, nullable=False)
    checked = Column(Boolean, nullable=False)
