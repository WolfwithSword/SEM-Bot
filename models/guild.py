from sqlalchemy import Column
from sqlalchemy.dialects.sqlite import INTEGER, TEXT

from . import Base

class Guild(Base):
    __tablename__ = "guild"
    id = Column(INTEGER, primary_key=True, nullable=False, unique=True)
    gold_value = Column(INTEGER, default=50)
    silver_value = Column(INTEGER, default=25)
    bronze_value = Column(INTEGER, default=15)
    participation_value = Column(INTEGER, default=5)
    timezone = Column(TEXT, default="UTC")
    max_participants = Column(INTEGER, default=100)
    manager_role_id = Column(INTEGER)
    announce_channel_id = Column(INTEGER)