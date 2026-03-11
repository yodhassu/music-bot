"""
╔══════════════════════════════════════════════╗
║         🎵  Harmony — Discord Music Bot       ║
║         Built with discord.py + yt-dlp        ║
╚══════════════════════════════════════════════╝
"""

import discord
from discord.ext import commands
import asyncio
import logging
from config import BOT_TOKEN, PREFIX

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("harmony")


# ── Bot setup ──────────────────────────────────────────────────────────────────
class Harmony(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True

        super().__init__(
            command_prefix=PREFIX,
            intents=intents,
            help_command=None,           # we have a custom one
            case_insensitive=True,
            strip_after_prefix=True,
        )

    async def setup_hook(self):
        """Load all cogs and sync slash commands."""
        cogs = ["cogs.music", "cogs.filters", "cogs.help"]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                log.info(f"✅  Loaded cog: {cog}")
            except Exception as e:
                log.error(f"❌  Failed to load {cog}: {e}")

        synced = await self.tree.sync()
        log.info(f"🔄  Synced {len(synced)} slash command(s)")

    async def on_ready(self):
        log.info(f"🎵  Harmony is online as {self.user} (ID: {self.user.id})")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/play • Harmony",
            )
        )

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("🚫 You don't have permission to do that.", ephemeral=True)
            return
        log.error(f"Unhandled error in command '{ctx.command}': {error}")


# ── Entry point ────────────────────────────────────────────────────────────────
async def main():
    async with Harmony() as bot:
        await bot.start(BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
