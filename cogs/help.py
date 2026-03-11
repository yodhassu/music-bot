"""
cogs/help.py — custom /help command
"""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from config import COLOR_PRIMARY


COMMANDS = [
    ("▶️  /play <query>",       "Play a song or playlist by URL or search terms."),
    ("🔍  /search <query>",     "Search YouTube and pick from the top 5 results."),
    ("⏸  /pause",              "Pause the current track."),
    ("▶️  /resume",             "Resume a paused track."),
    ("⏭  /skip",               "Vote to skip — DJs can force-skip instantly."),
    ("🔂  /loop <mode>",        "Set loop mode: `off` · `song` · `queue`."),
    ("🔊  /volume <0–200>",     "Adjust playback volume."),
    ("🎛  /filter <preset>",    "Apply audio effects: bass boost, nightcore, 8D, echo…"),
    ("📋  /queue [page]",       "Browse the track queue."),
    ("🎶  /nowplaying",         "Show the Now Playing card."),
    ("🗑  /remove <pos>",       "Remove a track from the queue."),
    ("↕️  /move <from> <to>",   "Reorder a track in the queue."),
    ("🔀  /shuffle",            "Shuffle the entire queue."),
    ("⏹  /stop",               "Stop playback and clear the queue."),
    ("👋  /leave",              "Disconnect the bot from voice."),
]


class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="📖  Show all Harmony commands")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎵  Harmony — Command Reference",
            description=(
                "All commands use Discord slash syntax.\n"
                "**DJ** = role named `DJ` or Manage Channels permission."
            ),
            color=COLOR_PRIMARY,
        )

        for name, desc in COMMANDS:
            embed.add_field(name=name, value=desc, inline=False)

        embed.set_footer(text="Harmony • github.com/yourname/harmony-bot")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))
