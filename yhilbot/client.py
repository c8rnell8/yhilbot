import discord
from discord import app_commands

intents = discord.Intents.default()
client: discord.Client = discord.Client(intents=intents)
tree: app_commands.CommandTree = app_commands.CommandTree(client)
