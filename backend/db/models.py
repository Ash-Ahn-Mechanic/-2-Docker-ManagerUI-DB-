from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class CommandLog(Base):
    __tablename__ = 'command_logs'

    command_id     = Column(String(100), primary_key=True)
    mongo_doc_id   = Column(String(24))
    raw_text       = Column(Text)
    status         = Column(String(50))
    action_count   = Column(Integer, default=0)
    current_action = Column(String(100))
    error_count    = Column(Integer, default=0)
    created_at     = Column(DateTime, default=datetime.now)
    started_at     = Column(DateTime)
    finished_at    = Column(DateTime)


class ErrorLog(Base):
    __tablename__ = 'error_logs'

    id         = Column(Integer, primary_key=True, autoincrement=True)
    command_id = Column(String(100))
    level      = Column(String(10))
    node_name  = Column(String(100))
    message    = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
