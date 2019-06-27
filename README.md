# SEM-Bot

A Simple Event Manager bot for Discord!

Made for Discord Hack Week 2019.

# Team
- WolfwithSword#0001

# Features

This bot has the following features:

- Event Creation and Management
- Event Reminders
- Points and Trophies Rank System

It is a simple bot, but it gets the job done and engages the community.

It is timezone-aware, and a guild can set a specific timezone to use.

# Config

Locate config/config.py and configure as needed.

- TOKEN : Your discord bot token
- PREFIX : Default prefix
- DESCRIPTION : No need to change this really
- MANAGE_ROLE : Default manager role to create on guild join
- ANNOUNCE_CHANNEL : Default announcement channel to create on guild join
- TIMEZONES : Please don't change :) 

# Permissions

The bot needs the following permissions string:
*&permissions=1342565456&scope=bot*

This includes the following permissions. Some may not be needed, but are added as a pre-caution.

- Manage Roles
- Manage Channels
- Manage Emojis
- Send Messages
- Manage Messages
- Embed Links
- Attach Files
- Read Message History
- Add Reactions
- Use External Emojis

# Packages

The following external packages were used:

- discord.py
- sqlalchemy
- sqlalchemy_utils
- arrow
- tabulate

# Commands

- register: Register a user to the bot
- stats: View user stats. Optional: Can mention a user
- leaderboard: View the top 15 users.
- trophy
	- add
	- remove
	- value
	
For each add, remove and set, you can specify a trophy type: **Gold**, **Silver**, **Bronze**.
	
For value, you may also specify **Participation**.

For add/remove, mention one or more users to apply it too. For value, you can set the value of a trophy server-wide.

- event
	- make: Make an event with the following properties:
		- Title
		- Description
		- Channel to host the event
		- Max number of participants
		- Event Start Time (In Server's specified timezone, default to UTC)
	- info: View an event's info before it begins and be able to react again. Requires the event code (4 character code)	
	- remove: Remove/Cancel an event early.
	- participants: Given event code, view all current participants.

When making an event, it will create an announcement message, from which you can react to it to join, leave, or get a ping reminder 15 minutes prior to event start.
	
- guild: Some manager and owner only commands
	- setTimezone: Given a list of timezones, select one as the server timezone
	- setAnnouncementChannel: Give a text channel to be SEM's new announcement channel for the server.
	- seetManagerRole: Give a role to be the new manager role for the server.

- time: View current time information about the server
