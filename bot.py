import discord
from discord.ext import commands

from sqlalchemy import engine, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import any_

import arrow
import asyncio
from tabulate import tabulate

import random, string

from models import *
import config

REACTIONS = ['✅', '❌', '⏲']

engine = create_engine('sqlite:///SEM.db', echo=False)
Session = sessionmaker(bind=engine)
session = Session()

if not engine.dialect.has_table(engine, 'guild'):
    Base.metadata.create_all(engine)

bot = commands.Bot(command_prefix=config.PREFIX, description=config.DESCRIPTION)


@bot.event
async def on_guild_join(guild):
    g = session.query(Guild).filter(int(guild.id) == Guild.id).one_or_none()
    if g is None:
        g = Guild(id = guild.id)
        session.add(g)
    session.commit()
    server_roles = []

    if len(guild.roles) > 0:
        server_roles = [r.name for r in guild.roles]

    if config.MANAGER_ROLE not in server_roles:
        await guild.create_role(name=config.MANAGER_ROLE, hoist=False, mentionable=False, reason="SEM Manager Roles")

    if config.ANNOUNCE_CHANNEL not in [c.name for c in guild.text_channels]:
        await guild.create_text_channel(name=config.ANNOUNCE_CHANNEL,
                                        topic="SEM Event Announcements",
                                        reason="SEM Bot Default Channel")

    guild = bot.get_guild(g.id)
    if not g.manager_role_id:
        for role in guild.roles:
            if role.name == config.MANAGER_ROLE:
                g.manager_role_id = role.id
    if not g.announce_channel_id:
        for channel in guild.text_channels:
            if channel.name == config.ANNOUNCE_CHANNEL:
                g.announce_channel_id = channel.id
    session.commit()

@bot.event
async def on_ready():
    print("---SEM Started---")
    print(bot.user.name)
    print(bot.user.id)
    print("-----------------")
    for guild in bot.guilds:
        g = session.query(Guild).filter(guild.id == Guild.id).one_or_none()
        if g is None:
            g = Guild(id = guild.id)
            session.add(g)
            session.commit()
            server_roles = []

            if len(guild.roles) > 0:
                server_roles = [r.name for r in guild.roles]

            if config.MANAGER_ROLE not in server_roles:
                await guild.create_role(name=config.MANAGER_ROLE, hoist=False, mentionable=False, reason="SEM Manager Roles")

            if config.ANNOUNCE_CHANNEL not in [c.name for c in guild.text_channels]:
                await guild.create_text_channel(name=config.ANNOUNCE_CHANNEL,
                                                topic="SEM Event Announcements",
                                                reason="SEM Bot Default Channel")
            if not g.manager_role_id:
                for role in guild.roles:
                    if role.name == config.MANAGER_ROLE:
                        g.manager_role_id = role.id
            if not g.announce_channel_id:
                for channel in guild.text_channels:
                    if channel.name == config.ANNOUNCE_CHANNEL:
                        g.announce_channel_id = channel.id
            session.commit()
    bot.loop.create_task(scan_reminders())
    bot.loop.create_task(scan_events())



@bot.command(brief="Register as a User", aliases=['signup', 'join'],
             description="Register as a new user on the server")
@commands.guild_only()
async def register(ctx):
    discordID = ctx.author.id
    username = ctx.author.name
    guild = ctx.message.guild
    try:
        result = registerUser(discordID, username, guild)
        await ctx.send(result)
    except Exception as e:
        await ctx.send('Could not complete your command')
        print(e)

def registerUser(discordID, username, guild):
    msg = ""
    user = session.query(User).filter(User.id == discordID, User.guild_id == guild.id).one_or_none()
    if user is not None:
        msg = "{} is already registered in server {}!".format(username, guild.name)
    else:
        user = User(id=discordID, guild_id=guild.id);
        score = Score(user_id=user.id, guild_id=user.guild_id)
        session.add_all([user, score])

        msg = "Registering new user {} for server {}".format(username, guild.name)

    session.commit()
    return msg

@bot.command(brief="View user stats", aliases=['info', 'rank', 'points','score'],
             description="View statistics on a user. Defaults to yourself, but you may ping another user to know their stats")
@commands.guild_only()
async def stats(ctx):
    try:
        msg_user = ctx.message.author
        if len(ctx.message.mentions) > 0:
            msg_user = ctx.message.mentions[0]

        user = session.query(User).filter(User.id == msg_user.id, User.guild_id == ctx.message.guild.id).one_or_none()
        if user is None:
            await ctx.send("User {} has not registered in this server! Type {}register to start!".format(msg_user.name, bot.command_prefix))
            return

        guild = session.query(Guild).filter(Guild.id == ctx.message.guild.id).one_or_none()

        headers = ["Rank", "User", "Events Done", "Gold/Silver/Bronze/Participation", "Score"]
        all_ranks = session.query(Score.user_id).filter(Score.guild_id == ctx.message.guild.id).order_by(calcScore(guild, Score).desc()).all()
        all_ranks = [x[0] for x in all_ranks]
        rank = (all_ranks).index(user.id) +1
        rows = [[rank, msg_user.name, user.score.event_count,
                 "{}/{}/{}/{}".format(user.score.gold, user.score.silver, user.score.bronze, user.score.participation),
                    calcScore(guild, user.score)]]
        table = tabulate(rows, headers)
        await ctx.send("User Info for {} in server: {}\n```\n{}\n```\n".format(msg_user.name, ctx.message.guild.name,table))
    except Exception as e:
        await ctx.send('Could not complete your command')
        print(e)

def calcScore(guild, score):
    points = 0
    points += (score.gold * guild.gold_value)
    points += (score.silver * guild.silver_value)
    points += (score.bronze * guild.bronze_value)
    points += (score.participation * guild.participation_value)
    return points


@bot.command(brief="View Top 15", aliases=['top'],
             description="View the top 15 users by score value!")
@commands.guild_only()
async def leaderboard(ctx):
    try:
        guildID = ctx.message.guild.id
        guild = session.query(Guild).filter(Guild.id == guildID).one_or_none()

        scores = session.query(Score).filter(Score.guild_id == guildID)\
            .order_by(calcScore(guild, Score).desc()).limit(15).all()

        headers = ["Rank", "User", "Events Done", "Gold/Silver/Bronze/Participation", "Score"]
        rows = [("{}.".format(scores.index(s) + 1), (bot.get_user(s.user_id)).name,
                  s.event_count, "{}/{}/{}/{}".format(s.gold, s.silver, s.bronze, s.participation),
                 calcScore(guild, s)) for s in scores]
        table = tabulate(rows, headers)
        await ctx.send("Leaderboard (T15) for {}\n```\n{}\n```\n".format(ctx.message.guild.name, table))
    except Exception as e:
        await ctx.send('Could not complete your command')
        print(e)

@bot.group()
async def trophy(ctx):
    """Add or Remove Trophies from Users"""
    if ctx.invoked_subcommand is None:
        await ctx.send("Please specify an action and trophy rank, followed by user mention(s)")

@trophy.group()
async def add(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send("Please specify a trophy rank, followed by user mention(s)")
@trophy.group()
async def remove(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send("Please specify a trophy rank, followed by user mention(s)")
@trophy.group()
async def value(ctx):
    author = ctx.author
    _guild = ctx.message.guild
    guild = session.query(Guild).filter(Guild.id == _guild.id).one_or_none()

    if not (author.id == _guild.owner.id or guild.manager_role_id in [r.id for r in author.roles]):
        await ctx.send("You do not have permission to use this command")
        return
    if ctx.invoked_subcommand is None:
        await ctx.send("Please specify a trophy type (or participation) to set the points of, followed by a positive value. This action is retroactive.")

@value.command(brief="Set value for Gold trophies", aliases=['Gold'], description="Set value for Gold trophies")
@commands.guild_only()
async def gold(ctx, val:int):
    _guild = ctx.message.guild
    guild = session.query(Guild).filter(Guild.id == _guild.id).one_or_none()
    if val < 0:
        await ctx.send("Cannot set negative value. Please try again.")
        return
    guild.gold_value = val
    session.commit()
    await ctx.send("Success!")

@value.command(brief="Set value for Silver trophies", aliases=['Silver'], description="Set value for Silver trophies")
@commands.guild_only()
async def silver(ctx, val:int):
    _guild = ctx.message.guild
    guild = session.query(Guild).filter(Guild.id == _guild.id).one_or_none()
    if val < 0:
        await ctx.send("Cannot set negative value. Please try again.")
        return
    guild.silver_value = val
    session.commit()
    await ctx.send("Success!")

@value.command(brief="Set value for Bronze trophies", aliases=['Bronze'], description="Set value for Bronze trophies")
@commands.guild_only()
async def bronze(ctx, val:int):
    _guild = ctx.message.guild
    guild = session.query(Guild).filter(Guild.id == _guild.id).one_or_none()
    if val < 0:
        await ctx.send("Cannot set negative value. Please try again.")
        return
    guild.bronze_value = val
    session.commit()
    await ctx.send("Success!")

@value.command(brief="Set value for participation points", aliases=['Participation'], description="Set value for Participation points")
@commands.guild_only()
async def participation(ctx, val:int):
    _guild = ctx.message.guild
    guild = session.query(Guild).filter(Guild.id == _guild.id).one_or_none()
    if val < 0:
        await ctx.send("Cannot set negative value. Please try again.")
        return
    guild.participation_value = val
    session.commit()
    await ctx.send("Success!")


@add.command(brief="Add a gold trophy", aliases=['Gold'],
             description="Add a gold trophy to all mentioned users")
@commands.guild_only()
async def gold(ctx):
    await modifyTrophy('Gold', 1, ctx)


@add.command(brief="Add a silver trophy", aliases=['Silver'],
             description="Add a silver trophy to all mentioned users")
@commands.guild_only()
async def silver(ctx):
    await modifyTrophy('Silver', 1, ctx)


@add.command(brief="Add a bronze trophy", aliases=['Bronze'],
             description="Add a bronze trophy to all mentioned users")
@commands.guild_only()
async def bronze(ctx):
    await modifyTrophy('Bronze', 1, ctx)


@remove.command(brief="Remove a gold trophy", aliases=['Gold'],
                description="Remove a gold trophy from all mentioned users")
@commands.guild_only()
async def gold(ctx):
    await modifyTrophy('Gold', -1, ctx)


@remove.command(brief="Remove a silver trophy", aliases=['Silver'],
                description="Remove a silver trophy from all mentioned users")
@commands.guild_only()
async def silver(ctx):
    await modifyTrophy('Silver', -1, ctx)


@remove.command(brief="Remove a bronze trophy", aliases=['Bronze'],
                description="Remove a bronze trophy from all mentioned users")
@commands.guild_only()
async def bronze(ctx):
    await modifyTrophy('Bronze', -1, ctx)


async def modifyTrophy(type, add, ctx):
    guildID = ctx.message.guild.id
    guild = session.query(Guild).filter(Guild.id == guildID).one_or_none()
    caller_roles = [r.id for r in ctx.author.roles]
    allowed = guild.manager_role_id in caller_roles
    if not allowed:
        await ctx.send("You do not have permission for this command")
        return

    try:
        unregistered = []
        if len(ctx.message.mentions) < 1:
            await ctx.send("You must mention one or more users to add a trophy to. Format: {}add{} @User".format(bot.command_prefix, type))
            return
        users_mentioned = list(set([u.id for u in ctx.message.mentions]))
        users = session.query(User).filter(User.guild_id == guildID, User.id.in_(users_mentioned)).all()
        for u in users_mentioned:
            if u not in [user.id for user in users]:
                unregistered.append(bot.get_user(u).name)
        for user in users:
            if type == "Gold":
                user.score.gold += add
            elif type == "Silver":
                user.score.silver += add
            elif type == "Bronze":
                user.score.bronze += add
        session.commit()
        names = ", ".join([bot.get_user(user.id).name for user in users])

        action = "added"
        action2 = "to"
        if add < 0:
            action = "removed"
            action2="from"
        msg = "Successfully {} a {} trophy {} {}!\n".format(action, type, action2, names)
        if len(unregistered) > 0:
            unreg_names = ", ".join(unregistered)
            msg += "Could not add trophies to: {}. They have not registered".format(unreg_names)
        await ctx.send(msg)
    except Exception as e:
        await ctx.send("Could not complete your command")
        print(e)


async def checkEventExists(code, guild_id, ctx):
    event = session.query(Event).filter(Event.guild_id == guild_id, Event.active == True,
                                        Event.code == code).one_or_none()

    if event is None:
        await ctx.send("There is no active event in this server for code {}".format(code))
        return None

    return event

@bot.group()
async def event(ctx):
    """Event commands"""
    if ctx.invoked_subcommand is None:
        await ctx.send("Please specify a valid subcommand with correct parameters.\n{}help event for more information".format(bot.command_prefix))

@event.command(brief="Create an Event",
             description="Make a new Event! Any text in command will be used as event title.",
             aliases=['new', 'create'])
@commands.guild_only()
async def make(ctx):
    creator = ctx.author
    _guild = ctx.message.guild
    guild = session.query(Guild).filter(Guild.id == _guild.id).one_or_none()
    roles = [r.id for r in creator.roles]
    if guild.manager_role_id not in roles:
        await ctx.send("You do not have permission to create a new event!")
        return

    await ctx.send("We will now begin the process of creating a new event")

    current_codes = session.query(Event.code).filter(Event.guild_id == guild.id, Event.active == True).all()
    curreent_codes = [c[0] for c in current_codes]
    code = "".join([random.choice(string.ascii_letters) for n in range(4)]).upper()
    while code in current_codes:
        code = "".join([random.choice(string.ascii_letters) for n in range(4)]).upper()

    titleSplit = ctx.message.clean_content.split(" ",2)
    title = ""
    if len(titleSplit) < 3 or titleSplit[2] == "":
        await ctx.send("Please state a title for the event")
        try:
            msg = await bot.wait_for('message', check=lambda message: message.author.id == creator.id and message.channel.id == ctx.message.channel.id, timeout=60)
            title = msg.clean_content
        except asyncio.TimeoutError:
            await ctx.send("Event Creation Cancelled. Type faster next time!")
            return
    else:
        title = titleSplit[2]
    if len(title) > 30:
        title = title[:30]
    event = Event(code = code, title = title, guild_id = guild.id, creator_id = creator.id)

    description = ""
    while description == "":
        try:
            await ctx.send("Please provide a description for the event")
            msg = await bot.wait_for('message', check=lambda message: message.author.id == creator.id
                                                                  and message.channel.id == ctx.message.channel.id,
                                     timeout=120)
            description = msg.clean_content
        except asyncio.TimeoutError:
            await ctx.send("Event Creation Cancelled. Type faster next time!")
            return

    if len(description) > 150:
        description = description[:150]
    event.description = description

    event.create_time = arrow.utcnow()

    event_channel = None
    while event_channel is None:
        await ctx.send("Please mention a host channel for the event.")
        try:
            msg = await bot.wait_for('message',
                                 check=lambda message: message.author.id == creator.id
                                                       and len(message.channel_mentions) > 0,
                                 timeout=60
                                 )
            event_channel = msg.channel_mentions[0]
        except asyncio.TimeoutError:
            await ctx.send("Event Creation Cancelled. Type faster next time!")
            return
    event.channel_id = event_channel.id

    participants = 0
    while participants < 1:
        try:
            await ctx.send("Please specify the number of participants. **Min**:{} **Max**:{}".format(1, guild.max_participants))
            msg = await bot.wait_for('message', check=lambda message: message.author.id == creator.id
                                                                  and message.channel.id == ctx.message.channel.id,
                                     timeout=60)
            try:
                participants = int(msg.content)
                if participants < 1 or participants > guild.max_participants:
                    participants = 0
            except:
                pass
        except asyncio.TimeoutError:
            await ctx.send("Event Creation Cancelled. Type faster next time!")
            return
    event.num_participants = participants

    event_time = arrow.get(0)
    while event_time <= arrow.utcnow():
        prompt = "Please enter the event time in the following format: {}\n**Server Timezone** is set to {} ({})"
        tzformat = "YYYY-MM-DD HH:mm"
        offset = arrow.utcnow().to(guild.timezone).format('ZZ')
        prompt = prompt.format(tzformat, guild.timezone, offset)
        await ctx.send(prompt)
        try:
            msg = await bot.wait_for('message', check=lambda message: message.author.id == creator.id
                                                                  and message.channel.id == ctx.message.channel.id,
                                     timeout=180)
            try:
                time = arrow.get(msg.content + " " + guild.timezone, tzformat + " ZZZ")
                if time > arrow.utcnow():
                    event_time = time
                else:
                    await ctx.send("Please specify an event time in the future. My time machine command is a WIP.")
            except:
                await ctx.send("Please specify a valid time in the given format!")
        except asyncio.TimeoutError:
            await ctx.send("Event Creation Cancelled. Type faster next time!")
            return
    event.event_time = event_time.to('UTC')
    reminder = Reminder(guild_id=guild.id, event_time=event.event_time)
    event.reminder = reminder
    event.timezone = guild.timezone
    session.add_all([event, reminder])
    session.commit()
    msg = "Event successfully created! View it with `{prefix}event info {code}`. Delete with `{prefix}event remove {code}`.\n"
    msg += "Participants can join by reacting to the Event Announcement embed from the announce "
    msg += " or from the info embed using `{prefix}event view {code}`! They can also opt-in to a 15 minute reminder!"
    msg = msg.format(prefix=bot.command_prefix, code=code)
    await ctx.send(msg)

    session.refresh(event)
    embed = event.as_embed
    embed.add_field(name="Creator: ", value=creator.name)

    try:
        announce_channel = bot.get_channel(guild.announce_channel_id)
        announcement = await announce_channel.send(embed=embed)
        for reaction in REACTIONS:
            await announcement.add_reaction(reaction)

        await watchReactions(announcement, event, guild, ctx)
    except:
        await ctx.send("Could not send in announcement channel. Try having an organizer reset the announcement channel?")

@event.command(aliases=['view'], brief="View event info",
               description="Repost event in the announcement channel to view information, join, leave, or make a reminder!\nSpecify the event code.")
@commands.guild_only()
async def info(ctx, code: str):
    code = code.upper()
    _guild = ctx.message.guild
    guild = session.query(Guild).filter(Guild.id == _guild.id).one_or_none()

    event = await checkEventExists(code, guild.id, ctx)
    if event is None:
        return

    embed = event.as_embed
    embed.add_field(name="Creator: ", value=bot.get_user(event.creator_id))
    try:
        announce_channel = bot.get_channel(guild.announce_channel_id)
        announcement = await announce_channel.send(embed=embed)
        for reaction in REACTIONS:
            await announcement.add_reaction(reaction)

        await watchReactions(announcement, event, guild, ctx)
    except Exception as e :
        print(e)
        await ctx.send("Could not send in announcement channel. Try having an organizer reset the announcement channel?")

@event.command(aliases=['delete', 'cancel'], brief="Cancel an event",
               description="Cancel an active event. Specify the event code")
@commands.guild_only()
async def remove(ctx, code: str):
    code = code.upper()
    _guild = ctx.message.guild
    guild = session.query(Guild).filter(Guild.id == _guild.id).one_or_none()

    event = await checkEventExists(code, guild.id, ctx)
    if event is None:
        return

    event.active = False
    session.delete(event.reminder)
    session.commit()
    await ctx.send("Success!")

@event.command(brief="View participants",
               description="View the participants to a given event. Please provide the event code.")
@commands.guild_only()
async def participants(ctx, code: str):
    code = code.upper()
    _guild = ctx.message.guild
    guild = session.query(Guild).filter(Guild.id == _guild.id).one_or_none()

    event = await checkEventExists(code, guild.id, ctx)
    if event is None:
        return

    # tabulate users
    headers = ['No.', 'Name']
    users = [bot.get_user(u.user_id) for u in event.responses if u.status == "Yes"]
    rows = [(users.index(user)+1, user.name) for user in users]
    table = tabulate(rows, headers)
    msg = "Current participants for Event {code}: {title} ({num}/{max})\n```\n{table}\n```\n"
    msg = msg.format(code=event.code, title=event.title,
                     num=len(users),
                     max=event.num_participants, table=table)
    await ctx.send(msg)


async def watchReactions(msg, event, guild, ctx):
    try:
        session.refresh(event)
        if not event.active:
            return

        user_ids = [p.user_id for p in event.responses if p.status == "Yes"]
        reaction, user = await bot.wait_for('reaction_add',
                                               check=lambda reaction, user: str(
                                                   reaction.emoji) in REACTIONS and user.id != bot.user.id and reaction.message.id == msg.id,
                                               timeout=300)

        _user = session.query(User).filter(User.id == user.id, User.guild_id == guild.id).one_or_none()
        if _user is None:
            await user.send("You have not registered in server `{}` yet! Please {}register and try reacting again!".format(ctx.message.guild.name, bot.command_prefix))
        else:
            emoji = str(reaction.emoji)

            if emoji == '✅' and len(user_ids) < event.num_participants and user.id not in user_ids:
                response = Response(event_id = event.id, user_id = user.id, guild_id = guild.id, status="Yes")
                session.add(response)

            elif emoji == '✅' and len(user_ids) == event.num_participants and user.id not in user_ids:
                await user.send("This event is full, please wait for someone to leave or join another!")

            elif emoji == '❌' and user.id in user_ids:
                response = [r for r in event.responses if r.status == "Yes" and r.user_id == user.id][0]
                session.delete(response)
            if emoji == '⏲':
                if event.reminder is None:
                    reminder = Reminder(event_id = event.id, event_time = event.event_time, guild_id = event.guild_id)
                    session.add(reminder)
                    session.commit()
                    session.refresh(event)
                reminded_users = [u.id for u in event.reminder.users]
                if user.id not in reminded_users:
                    event.reminder.users.append(_user)

            session.commit()

            embed = event.as_embed
            embed.add_field(name="Creator: ", value=bot.get_user(event.creator_id))
            await msg.edit(embed = embed)

        await watchReactions(reaction.message, event, guild, ctx)
    except asyncio.TimeoutError:
        await msg.edit(content="Time's up! Please use `{}event info {}` again to join, leave or set a reminder!".format(bot.command_prefix, event.code))
        return

@bot.group()
async def guild(ctx):
    """Manager and Server Owner level commands (Settings)"""
    if ctx.invoked_subcommand is None:
        await ctx.send("Please specify a valid subcommand. `{}help` to view commands.".format(bot.command_prefix))

def chunkifyList(li, num):
    for i in range(0, len(li), num):
        yield li[i:i+num]

@guild.command(brief="Change server timezone", description="Change server timezone",
               aliases=['updateTimezone', 'setTimeZone', 'updateTimeZone'])
@commands.guild_only()
async def setTimezone(ctx):
    author = ctx.author
    _guild = ctx.message.guild
    guild = session.query(Guild).filter(Guild.id == _guild.id).one_or_none()

    if not (author.id == _guild.owner.id or guild.manager_role_id in [r.id for r in author.roles]):
        await ctx.send("You do not have permission to use this command")
        return

    headers = ['#', 'Offset', 'Location']
    rowsX = list(chunkifyList(config.TIMEZONES, len(config.TIMEZONES)//3))
    for row in rowsX:
        rows = [(config.TIMEZONES.index(t)+1, t[0], t[1]) for t in row]

        table = tabulate(rows, headers)
        await ctx.send('```\n{}\n```'.format(table))

    message = "Please select a timezone from the list above. Respond with the number. EX To pick UTC, respond with {}\nCurrent timezone is: {}".format(len(config.TIMEZONES), guild.timezone)
    message += "\nOr type in a valid GMT offset as this list is not DST aware. Format: GMT+##:## or GMT-##:##"
    message += "\n**Note:** Timezone changes are not retroactive to events or reminders. They are always in UTC."

    await ctx.send(message)

    try:
        msg = await bot.wait_for('message', check=lambda message: message.author.id == author.id
                                              and message.channel.id == ctx.message.channel.id,
             timeout=180)
        try:
            if str(msg.content).upper().startswith("GMT"):
                try:
                    arrow.utcnow().to(str(msg.content).upper())
                    guild.timezone = str(msg.content).upper()
                    session.commit()
                    await ctx.send("Timezone successfully changed to {}".format(guild.timezone))
                    return
                except:
                    await ctx.send("Non valid timezone sent. Please try again")
                    return
            num = int(msg.content)
            if num < 1 or num > len(config.TIMEZONES):
                await ctx.send("Non valid timezone sent. Please try again")
                return
            timezone = config.TIMEZONES[num-1][0]
            guild.timezone = timezone
            session.commit()
            await ctx.send("Timezone successfully changed to {}".format(timezone))
        except:
            await ctx.send("Non valid timezone sent. Please try again")
    except asyncio.TimeoutError:
        await ctx.send("Time's up! Guild timezone was not changed.")


@guild.command(brief="Change announcement channel", description="Change announcement channel")
@commands.guild_only()
async def setAnnouncementChannel(ctx, channel: discord.TextChannel):
    author = ctx.author
    _guild = ctx.message.guild
    guild = session.query(Guild).filter(Guild.id == _guild.id).one_or_none()

    if not (author.id == _guild.owner.id or guild.manager_role_id in [r.id for r in author.roles]):
        await ctx.send("You do not have permission to use this command")
        return

    guild.announce_channel_id = channel.id
    session.commit()
    await ctx.send("Success!")

@guild.command(brief="Change Management Role (owner only)",
               description="Change the event manager role. Only the owner can do this")
@commands.guild_only()
async def setManagerRole(ctx, role:discord.Role):
    author = ctx.author
    _guild = ctx.message.guild
    guild = session.query(Guild).filter(Guild.id == _guild.id).one_or_none()

    if not (author.id == _guild.owner.id):
        await ctx.send("You do not have permission to use this command")
        return

    guild.manager_role_id = role.id
    session.commit()
    await ctx.send("Success!")

async def scan_reminders():
    await bot.wait_until_ready()

    while not bot.is_closed():
        utc = arrow.utcnow()
        utc15 = (arrow.utcnow()).replace(minutes=+15)
        reminders = session.query(Reminder).filter(Reminder.event_time > utc, Reminder.event_time <= utc15).all()
        if len(reminders) > 0:
            for reminder in reminders:
                users = [bot.get_user(user.id) for user in reminder.users]
                msg = "Reminder for Event: `{}` with code {} starts in around 15 minutes!\n".format(reminder.event.title, reminder.event.code)
                msg += " ".join(list(set([user.mention for user in users])))
                msg += "\nView information about the event with `{}event info {}`\n".format(bot.command_prefix, reminder.event.code)

                guild = session.query(Guild).filter(Guild.id == reminder.guild_id).one_or_none()

                try:
                    channel = bot.get_channel(guild.announce_channel_id)
                    await channel.send(msg)
                except:
                    await ctx.send("Could not send in announcement channel. Try having an organizer reset the announcement channel?")

            q = Reminder.__table__.delete().where(Reminder.event_time <= utc15)
            session.execute(q)
            session.commit()

        await asyncio.sleep(60)

async def scan_events():
    await bot.wait_until_ready()

    while not bot.is_closed():
        utc = arrow.utcnow()
        utcP1 = (arrow.utcnow()).replace(minutes=+1)
        events = session.query(Event).filter(Event.event_time > utc, Event.event_time <= utcP1, Event.active == True).all()

        if len(events) > 0:
            for event in events:
                users = [bot.get_user(response.user_id) for response in event.responses if response.status == "Yes"]

                msg = "Event: `{}` ({}) is starting!!!\n".format(event.title, event.code)
                msg += " ".join(list(set([user.mention for user in users])))

                guild = session.query(Guild).filter(Guild.id == event.guild_id).one_or_none()

                embed = event.as_embed
                embed.add_field(name="Creator: ", value=bot.get_user(event.creator_id))

                try:
                    announce_channel = bot.get_channel(guild.announce_channel_id)
                    announcement = await announce_channel.send("Event is starting!",embed=embed)
                except:
                    await ctx.send("Could not send in announcement channel. Try having an organizer reset the announcement channel?")

                channel = bot.get_channel(event.channel_id)
                if channel is None:
                    _guild = bot.get_guild(guild.id)
                    channel = await _guild.create_text_channel(name="Event - {}".format(event.code),
                                                    topic="SEM Event {}".format(event.code),
                                                    reason="SEM Bot Event Channel. Specified did not exist!")
                announcement = await channel.send("Event is starting!", embed=embed)
                await channel.send(msg)

                event.active = False
                user_ids = [u.id for u in users]
                scores = session.query(Score).filter(Score.guild_id == guild.id, Score.user_id.in_(user_ids)).all()
                for score in scores:
                    score.participation+=1
                    score.event_count+=1

                session.commit()

        await asyncio.sleep(60)

@bot.command(brief="View current times", description="View current times")
@commands.guild_only()
async def time(ctx):
    _guild = ctx.message.guild
    guild = session.query(Guild).filter(Guild.id == _guild.id).one_or_none()

    current_time_utc = arrow.utcnow()
    server_time = current_time_utc.to(guild.timezone)
    gmt_time = current_time_utc.to("GMT+00:00")

    embed = discord.Embed(title="Time", description="Current Server Times", colour=5111790)
    embed.add_field(name="UTC", value=current_time_utc, inline = False)
    embed.add_field(name="Server", value=server_time, inline = True)
    embed.add_field(name="Server TZ", value=guild.timezone, inline = True)
    embed.add_field(name="GMT", value=gmt_time, inline = False)
    await ctx.send(embed=embed)

if __name__ == '__main__':
    try:
        bot.run(config.TOKEN)
    except Exception as e:
        print('Could Not Start Bot')
        print(e)
    finally:
        print('Closing Session')
        session.close()