"""
cogs/music.py — core music commands for Harmony

Slash commands:
  /play <query>       — play a song or playlist
  /search <query>     — pick from top 5 results
  /pause              — pause playback
  /resume             — resume playback
  /skip               — vote to skip (or force skip if DJ)
  /queue [page]       — show the queue
  /nowplaying         — refresh the Now Playing embed
  /remove <position>  — remove a track from the queue
  /move <from> <to>   — reorder the queue
  /shuffle            — shuffle the queue
  /loop <mode>        — set loop mode: off / song / queue
  /volume <0–200>     — set volume
  /stop               — stop playback and clear queue
  /leave              — disconnect the bot
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from config import MAX_SEARCH_RESULTS, SKIP_VOTE_RATIO
from utils.player import GuildPlayer, LoopMode, fetch_track, fetch_search
import utils.embeds as emb

log = logging.getLogger("harmony.music")


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot     = bot
        self.players: dict[int, GuildPlayer] = {}   # guild_id → player

    # ── Internal helpers ───────────────────────────────────────────────────────

    def get_player(self, guild: discord.Guild, channel: discord.TextChannel) -> GuildPlayer:
        if guild.id not in self.players:
            self.players[guild.id] = GuildPlayer(guild, channel)
        return self.players[guild.id]

    async def ensure_voice(self, interaction: discord.Interaction) -> Optional[GuildPlayer]:
        """Ensure user is in a VC and bot has joined it. Returns the player or None."""
        if not interaction.user.voice:
            await interaction.followup.send(embed=emb.error("Not in a voice channel",
                "Join a voice channel first, then try again."))
            return None

        vc = interaction.user.voice.channel
        player = self.get_player(interaction.guild, interaction.channel)

        if player.voice is None or not player.voice.is_connected():
            player.voice = await vc.connect()
        elif player.voice.channel != vc:
            await player.voice.move_to(vc)

        return player

    def is_dj(self, member: discord.Member) -> bool:
        """DJ = has 'Manage Channels' permission or a role named 'DJ'."""
        if member.guild_permissions.manage_channels:
            return True
        return any(r.name.lower() == "dj" for r in member.roles)

    # ── /play ──────────────────────────────────────────────────────────────────

    @app_commands.command(name="play", description="▶️  Play a song or playlist (URL or search query)")
    @app_commands.describe(query="YouTube URL, Spotify URL, or search terms")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        player = await self.ensure_voice(interaction)
        if player is None:
            return

        await interaction.followup.send(embed=emb.info("Searching…", f"🔍 `{query}`"))

        try:
            tracks = await fetch_track(query, interaction.user)
        except Exception as e:
            log.error(f"fetch_track error: {e}")
            await interaction.followup.send(embed=emb.error("Couldn't find that track",
                "Try a different search term or URL."))
            return

        if not tracks:
            await interaction.followup.send(embed=emb.error("No results found"))
            return

        pos = player.enqueue(tracks)

        if len(tracks) > 1:
            await interaction.followup.send(embed=emb.success(
                f"Playlist added — {len(tracks)} tracks",
                f"Starting at position `#{pos}`",
            ))
        else:
            await interaction.followup.send(embed=emb.track_added(tracks[0], pos))

        if not player.voice.is_playing() and not player.voice.is_paused():
            await player.play_next()
            if player.current:
                player.current["elapsed"] = 0
                await interaction.followup.send(
                    embed=emb.now_playing(
                        player.current, player.volume,
                        player.loop.value, len(player.queue),
                    )
                )

    # ── /search ────────────────────────────────────────────────────────────────

    @app_commands.command(name="search", description="🔍  Search YouTube and pick a result")
    @app_commands.describe(query="Search terms")
    async def search(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        player = await self.ensure_voice(interaction)
        if player is None:
            return

        results = await fetch_search(query, MAX_SEARCH_RESULTS)
        if not results:
            await interaction.followup.send(embed=emb.error("No results found"))
            return

        msg = await interaction.followup.send(embed=emb.search_results(results))

        def check(m: discord.Message) -> bool:
            return (
                m.author.id == interaction.user.id
                and m.channel.id == interaction.channel.id
                and (m.content.isdigit() or m.content.lower() == "cancel")
            )

        try:
            reply = await self.bot.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await msg.edit(embed=emb.warning("Search timed out"))
            return

        if reply.content.lower() == "cancel":
            await msg.edit(embed=emb.info("Search cancelled"))
            return

        choice = int(reply.content) - 1
        if not (0 <= choice < len(results)):
            await msg.edit(embed=emb.error("Invalid choice"))
            return

        picked = results[choice]
        picked["requester"] = interaction.user

        # Re-fetch full info so we have the stream URL
        full = await fetch_track(picked["url"], interaction.user)
        if not full:
            await interaction.followup.send(embed=emb.error("Failed to load track"))
            return

        pos = player.enqueue(full)
        await interaction.followup.send(embed=emb.track_added(full[0], pos))

        if not player.voice.is_playing() and not player.voice.is_paused():
            await player.play_next()

    # ── /pause ─────────────────────────────────────────────────────────────────

    @app_commands.command(name="pause", description="⏸  Pause playback")
    async def pause(self, interaction: discord.Interaction):
        player = self.players.get(interaction.guild.id)
        if not player or not player.voice:
            await interaction.response.send_message(embed=emb.error("Not playing anything"))
            return
        player.pause()
        await interaction.response.send_message(embed=emb.success("Paused"))

    # ── /resume ────────────────────────────────────────────────────────────────

    @app_commands.command(name="resume", description="▶️  Resume paused playback")
    async def resume(self, interaction: discord.Interaction):
        player = self.players.get(interaction.guild.id)
        if not player or not player.voice:
            await interaction.response.send_message(embed=emb.error("Nothing is paused"))
            return
        player.resume()
        await interaction.response.send_message(embed=emb.success("Resumed"))

    # ── /skip ──────────────────────────────────────────────────────────────────

    @app_commands.command(name="skip", description="⏭  Vote to skip the current track")
    async def skip(self, interaction: discord.Interaction):
        player = self.players.get(interaction.guild.id)
        if not player or not player.voice or not player.voice.is_playing():
            await interaction.response.send_message(embed=emb.error("Nothing is playing"))
            return

        # DJs can force-skip
        if self.is_dj(interaction.user):
            player.skip()
            await interaction.response.send_message(embed=emb.success("Skipped (DJ)"))
            return

        player.skip_votes.add(interaction.user.id)
        listeners = [
            m for m in player.voice.channel.members
            if not m.bot and not m.voice.deaf
        ]
        needed  = max(1, int(len(listeners) * SKIP_VOTE_RATIO))
        current = len(player.skip_votes)

        if current >= needed:
            player.skip()
            await interaction.response.send_message(
                embed=emb.success("Skipped", f"Vote passed ({current}/{needed})"))
        else:
            await interaction.response.send_message(
                embed=emb.info("Skip voted",
                    f"**{current}/{needed}** votes — need {needed - current} more."))

    # ── /queue ─────────────────────────────────────────────────────────────────

    @app_commands.command(name="queue", description="📋  View the music queue")
    @app_commands.describe(page="Page number (default 1)")
    async def queue(self, interaction: discord.Interaction, page: int = 1):
        player = self.players.get(interaction.guild.id)
        if not player or not player.queue:
            await interaction.response.send_message(embed=emb.info("Queue is empty"))
            return
        await interaction.response.send_message(
            embed=emb.queue_embed(player.queue, page=max(0, page - 1)))

    # ── /nowplaying ────────────────────────────────────────────────────────────

    @app_commands.command(name="nowplaying", description="🎶  Show what's currently playing")
    async def nowplaying(self, interaction: discord.Interaction):
        player = self.players.get(interaction.guild.id)
        if not player or not player.current:
            await interaction.response.send_message(embed=emb.error("Nothing is playing"))
            return
        player.current["elapsed"] = player.elapsed
        await interaction.response.send_message(
            embed=emb.now_playing(
                player.current, player.volume,
                player.loop.value, len(player.queue),
            ))

    # ── /remove ────────────────────────────────────────────────────────────────

    @app_commands.command(name="remove", description="🗑  Remove a track from the queue")
    @app_commands.describe(position="Queue position to remove")
    async def remove(self, interaction: discord.Interaction, position: int):
        player = self.players.get(interaction.guild.id)
        if not player:
            await interaction.response.send_message(embed=emb.error("No active player"))
            return
        try:
            removed = player.remove(position)
            await interaction.response.send_message(
                embed=emb.success("Removed", f"**{removed['title']}** removed from queue."))
        except IndexError:
            await interaction.response.send_message(
                embed=emb.error("Invalid position", "Check `/queue` for valid positions."))

    # ── /move ──────────────────────────────────────────────────────────────────

    @app_commands.command(name="move", description="🔀  Move a track to a different queue position")
    @app_commands.describe(from_pos="Current position", to_pos="New position")
    async def move(self, interaction: discord.Interaction, from_pos: int, to_pos: int):
        player = self.players.get(interaction.guild.id)
        if not player:
            await interaction.response.send_message(embed=emb.error("No active player"))
            return
        try:
            player.move(from_pos, to_pos)
            await interaction.response.send_message(
                embed=emb.success("Moved", f"Track moved from `#{from_pos}` → `#{to_pos}`"))
        except IndexError as e:
            await interaction.response.send_message(embed=emb.error("Invalid position", str(e)))

    # ── /shuffle ───────────────────────────────────────────────────────────────

    @app_commands.command(name="shuffle", description="🔀  Shuffle the queue")
    async def shuffle(self, interaction: discord.Interaction):
        player = self.players.get(interaction.guild.id)
        if not player or not player.queue:
            await interaction.response.send_message(embed=emb.error("Queue is empty"))
            return
        player.shuffle()
        await interaction.response.send_message(embed=emb.success("Shuffled the queue 🎲"))

    # ── /loop ──────────────────────────────────────────────────────────────────

    LOOP_CHOICES = [
        app_commands.Choice(name="Off",   value="off"),
        app_commands.Choice(name="Song",  value="song"),
        app_commands.Choice(name="Queue", value="queue"),
    ]

    @app_commands.command(name="loop", description="🔁  Set the loop mode")
    @app_commands.describe(mode="off — Song — queue")
    @app_commands.choices(mode=LOOP_CHOICES)
    async def loop(self, interaction: discord.Interaction, mode: app_commands.Choice[str]):
        player = self.players.get(interaction.guild.id)
        if not player:
            await interaction.response.send_message(embed=emb.error("No active player"))
            return
        player.loop = LoopMode(mode.value)
        icons = {"off": "➡️", "song": "🔂", "queue": "🔁"}
        await interaction.response.send_message(
            embed=emb.success(f"Loop: {mode.name}",
                f"{icons[mode.value]} Loop mode set to **{mode.name}**"))

    # ── /volume ────────────────────────────────────────────────────────────────

    @app_commands.command(name="volume", description="🔊  Set the playback volume (0–200)")
    @app_commands.describe(level="Volume percentage (0–200, default 50)")
    async def volume(self, interaction: discord.Interaction, level: int):
        player = self.players.get(interaction.guild.id)
        if not player:
            await interaction.response.send_message(embed=emb.error("No active player"))
            return
        if not (0 <= level <= 200):
            await interaction.response.send_message(
                embed=emb.error("Out of range", "Volume must be between 0 and 200."))
            return
        player.set_volume(level / 100.0)
        bar = "▓" * (level // 10) + "░" * (20 - level // 10)
        await interaction.response.send_message(
            embed=emb.success(f"Volume: {level}%", f"`{bar}`"))

    # ── /stop ──────────────────────────────────────────────────────────────────

    @app_commands.command(name="stop", description="⏹  Stop playback and clear the queue")
    async def stop(self, interaction: discord.Interaction):
        player = self.players.get(interaction.guild.id)
        if not player:
            await interaction.response.send_message(embed=emb.error("No active player"))
            return
        player.clear()
        if player.voice and player.voice.is_playing():
            player.voice.stop()
        await interaction.response.send_message(embed=emb.success("Stopped & queue cleared"))

    # ── /leave ─────────────────────────────────────────────────────────────────

    @app_commands.command(name="leave", description="👋  Disconnect the bot from voice")
    async def leave(self, interaction: discord.Interaction):
        player = self.players.pop(interaction.guild.id, None)
        if player:
            await player.destroy()
        await interaction.response.send_message(embed=emb.success("Disconnected 👋"))

    # ── Event listeners ────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        """Auto-disconnect if everyone leaves the voice channel."""
        if member.bot:
            return
        player = self.players.get(member.guild.id)
        if not player or not player.voice:
            return

        channel = player.voice.channel
        humans  = [m for m in channel.members if not m.bot]
        if len(humans) == 0:
            await player.text_channel.send(
                "👋  Everyone left — disconnecting.", delete_after=15)
            await player.destroy()
            self.players.pop(member.guild.id, None)


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
