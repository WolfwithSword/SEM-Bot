from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.sqlite import INTEGER, TEXT

from . import Base

class Response(Base):
    __tablename__ = "response"
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    event_id = Column(INTEGER, ForeignKey("event.id", ondelete="CASCADE"))
    user_id = Column(INTEGER, ForeignKey('user.id', ondelete="CASCADE"))
    guild_id = Column(INTEGER, ForeignKey('guild.id', ondelete="CASCADE"))
    status = Column(TEXT)