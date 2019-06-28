from sqlalchemy import Column, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship, backref
from sqlalchemy.dialects.sqlite import INTEGER

from . import Base

class User(Base):
    __tablename__ = "user"
    uid = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    id = Column(INTEGER, nullable=False)
    guild_id = Column(INTEGER, ForeignKey('guild.id'), nullable=False)
    score = relationship("Score",
                          primaryjoin="and_(User.id == Score.user_id, User.guild_id == Score.guild_id)",
                          back_populates="user", uselist=False)
    UniqueConstraint('id', 'guild_id', name='uix_1')