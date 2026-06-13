import discord
from discord import app_commands

intents = discord.Intents.default()
# Needed by the AFK tracker to see members and manage their roles. Must also be
# enabled in the Developer Portal → Bot → "Server Members Intent".
intents.members = True
client: discord.Client = discord.Client(intents=intents)
tree: app_commands.CommandTree = app_commands.CommandTree(client)
