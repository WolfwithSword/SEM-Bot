from sqlalchemy import Column, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship, backref
from sqlalchemy.dialects.sqlite import INTEGER, TEXT, BOOLEAN

from . import Base

class Score(Base):
    __tablename__ = 'score'
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    user_id = Column(INTEGER, ForeignKey("user.id"), nullable=False)
    guild_id = Column(INTEGER, ForeignKey("user.guild_id"), nullable=False)
    user = relationship("User", back_populates="score",
                         primaryjoin="and_(User.id == Score.user_id, User.guild_id == Score.guild_id)")
    gold = Column(INTEGER, default=0)
    silver = Column(INTEGER, default=0)
    bronze = Column(INTEGER, default=0)
    participation = Column(INTEGER, default=0)
    event_count = Column(INTEGER, default=0)