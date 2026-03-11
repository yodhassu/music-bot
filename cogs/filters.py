"""
cogs/filters.py — real-time audio filters powered by FFmpeg

/filter <preset>
  Presets: none, bassboost, nightcore, vaporwave, 8d, echo, loud
"""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

import utils.embeds as emb
from utils.player import build_ffmpeg_opts


# ── Filter definitions ─────────────────────────────────────────────────────────
# Each value is an FFmpeg -af filter chain string.
FILTERS: dict[str, tuple[str, str]] = {
    "none":       ("",
                   "Original audio, no processing"),
    "bassboost":  ("bass=g=15,dynaudnorm=f=200",
                   "Heavy low-end boost 🔊"),
    "nightcore":  ("asetrate=44100*1.25,aresample=44100,atempo=1.06",
                   "Sped-up, pitch-raised ⚡"),
    "vaporwave":  ("asetrate=44100*0.8,aresample=44100,atempo=0.9",
                   "Slowed down, lo-fi feel 🌊"),
    "8d":         ("apulsator=hz=0.08",
                   "Panning 360° stereo experience 🎧"),
    "echo":       ("aecho=0.8:0.88:60:0.4",
                   "Reverb / echo effect 🏟"),
    "loud":       ("dynaudnorm=f=150:g=15",
                   "Maximised loudness 📢"),
    "soft":       ("dynaudnorm=f=150:g=5,acompressor=threshold=-12dB:ratio=2",
                   "Gentle compression, easier on the ears 🎵"),
    "karaoke":    ("pan=stereo|c0=c0-c1|c1=c1-c0",
                   "Attempt to remove vocals 🎤"),
}

CHOICES = [
    app_commands.Choice(name=k.capitalize(), value=k)
    for k in FILTERS
]


class Filters(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="filter", description="🎛  Apply an audio filter")
    @app_commands.describe(preset="Choose an audio effect")
    @app_commands.choices(preset=CHOICES)
    async def filter(self, interaction: discord.Interaction, preset: app_commands.Choice[str]):
        music_cog = self.bot.get_cog("Music")
        if music_cog is None:
            await interaction.response.send_message(embed=emb.error("Music cog not loaded"))
            return

        player = music_cog.players.get(interaction.guild.id)
        if not player or not player.voice:
            await interaction.response.send_message(embed=emb.error("Not playing anything"))
            return

        filter_str, description = FILTERS[preset.value]
        player.filter = filter_str

        # Restart the current track with the new filter applied
        if player.voice.is_playing() or player.voice.is_paused():
            player.voice.stop()   # after() hook will call play_next() again

        label = preset.name if preset.value != "none" else "None (removed)"
        await interaction.response.send_message(
            embed=emb.success(
                f"Filter: {label}",
                f"{description}\n\n_Restarting current track with new filter…_",
            )
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Filters(bot))
