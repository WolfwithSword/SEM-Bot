from sqlalchemy.dialects.sqlite import INTEGER, TEXT, BOOLEAN, DATETIME
from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy_utils import ArrowType
from sqlalchemy.orm import relationship, backref


from . import Base

user_association_table = Table('user_association', Base.metadata,
    Column('reminder_id', INTEGER, ForeignKey('reminder.id')),
    Column('user_id', INTEGER, ForeignKey('user.id'))
)

class Reminder(Base):
    __tablename__ = 'reminder'
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    event_id = Column(INTEGER, ForeignKey('event.id'))
    event_time = Column(ArrowType, ForeignKey("event.event_time"))
    event =  relationship('Event', uselist=False, back_populates="reminder",
                          primaryjoin="and_(Reminder.event_id == Event.id, Reminder.guild_id == Event.guild_id)")
    users = relationship("User", collection_class=list, secondary=user_association_table, backref="reminders" )

    guild_id = Column(INTEGER, ForeignKey('guild.id'))