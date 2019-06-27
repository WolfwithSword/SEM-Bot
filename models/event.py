from sqlalchemy.dialects.sqlite import INTEGER, TEXT, BOOLEAN, DATETIME
from sqlalchemy_utils import ArrowType
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from discord import Embed

import arrow

from . import Base

class Event(Base):
    __tablename__ = "event"
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    code = Column(INTEGER, nullable=False)
    active = Column(BOOLEAN, default=True)
    title = Column(TEXT, default="Event")
    description = Column(TEXT, default="")
    event_time = Column(ArrowType)
    create_time = Column(ArrowType)
    num_participants = Column(INTEGER)
    creator_id = Column(INTEGER, ForeignKey("user.id"))
    channel_id = Column(INTEGER)
    timezone = Column(TEXT)
    guild_id = Column(INTEGER, ForeignKey('guild.id'))
    responses = relationship("Response", passive_deletes=True)
    reminder = relationship("Reminder", uselist=False, back_populates="event",
                            primaryjoin="and_(Event.id == Reminder.event_id, Event.guild_id == Reminder.guild_id)")

    @property
    def details(self):
        info = {
            "title": self.title,
            "description": self.description,
            "colour": 5111790
        }
        return info

    @property
    def as_embed(self):
        embed = Embed(**self.details)
        embed.add_field(name="Code", value=self.code, inline=True)
        time = str(self.event_time.to(str(self.timezone)).format("YYYY-MM-DD HH:mm")) + " " + str(self.timezone)
        embed.add_field(name="Time", value=time, inline = True)
        participants = [p for p in self.responses if p.status == "Yes"]
        embed.add_field(name="Participants", value="{}/{}".format(len(participants), self.num_participants), inline=False)

        embed.add_field(name="Join/Leave", value="React to Join ✅ or Leave ❌", inline = False)
        embed.add_field(name="Remind Me!", value="React ⏲️for a 15m reminder!", inline=False)

        return embed
