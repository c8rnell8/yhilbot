import os

import discord
from discord import app_commands

intents = discord.Intents.default()
# Needed by the AFK tracker to see members and manage their roles. Must also be
# enabled in the Developer Portal → Bot → "Server Members Intent". If that
# toggle is off the gateway rejects the connection, so bot.py re-launches once
# with YHIL_NO_MEMBERS=1 to keep the bot online (AFK scan stays dormant until
# the toggle is enabled and the bot restarts).
intents.members = os.environ.get("YHIL_NO_MEMBERS") != "1"
client: discord.Client = discord.Client(intents=intents)
tree: app_commands.CommandTree = app_commands.CommandTree(client)
