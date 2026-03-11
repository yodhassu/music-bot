"""
utils/player.py — GuildPlayer: one instance per Discord server
Manages queue, playback state, loop modes, and volume.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from enum import Enum
from typing import Optional

import discord
import yt_dlp

from config import DEFAULT_VOLUME, MAX_QUEUE_SIZE, INACTIVITY_TIMEOUT


# ── Loop modes ─────────────────────────────────────────────────────────────────
class LoopMode(str, Enum):
    OFF   = "off"
    SONG  = "song"
    QUEUE = "queue"


# ── yt-dlp options ─────────────────────────────────────────────────────────────
YTDL_OPTS = {
    "format":             "bestaudio/best",
    "noplaylist":         False,          # allow playlists
    "quiet":              True,
    "no_warnings":        True,
    "default_search":     "ytsearch",     # search by name if no URL
    "source_address":     "0.0.0.0",      # bind to IPv4 (avoids some errors)
    "extract_flat":       "in_playlist",
    "skip_download":      True,
    "postprocessors": [{
        "key":            "FFmpegExtractAudio",
        "preferredcodec": "opus",
    }],
}

FFMPEG_BASE_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options":        "-vn",
}


def build_ffmpeg_opts(extra_filter: str = "") -> dict:
    opts = dict(FFMPEG_BASE_OPTS)
    if extra_filter:
        opts["options"] += f" -af {extra_filter}"
    return opts


# ── Track extraction ───────────────────────────────────────────────────────────

async def fetch_track(query: str, requester: discord.Member) -> list[dict]:
    """
    Resolve a URL or search query into one or more track dicts.
    Returns a list so playlists work too.
    """
    loop = asyncio.get_event_loop()

    with yt_dlp.YoutubeDL(YTDL_OPTS) as ydl:
        raw = await loop.run_in_executor(
            None,
            lambda: ydl.extract_info(query, download=False),
        )

    if raw is None:
        return []

    # Playlist
    if "entries" in raw:
        entries = [e for e in raw["entries"] if e]
        return [_build_track(e, requester) for e in entries]

    return [_build_track(raw, requester)]


async def fetch_search(query: str, n: int = 5) -> list[dict]:
    """Return up to n search results without a requester (for the picker UI)."""
    loop = asyncio.get_event_loop()
    opts = dict(YTDL_OPTS)
    opts["default_search"] = f"ytsearch{n}"

    with yt_dlp.YoutubeDL(opts) as ydl:
        raw = await loop.run_in_executor(
            None,
            lambda: ydl.extract_info(query, download=False),
        )

    if raw is None or "entries" not in raw:
        return []

    return [_build_track(e, None) for e in raw["entries"] if e]


def _build_track(data: dict, requester) -> dict:
    return {
        "title":     data.get("title", "Unknown Title"),
        "url":       data.get("webpage_url") or data.get("url", ""),
        "stream":    data.get("url", ""),          # direct audio stream URL
        "thumbnail": data.get("thumbnail"),
        "duration":  data.get("duration", 0),
        "requester": requester,
        "elapsed":   0.0,
        "started_at": None,
    }


# ── Guild Player ───────────────────────────────────────────────────────────────

class GuildPlayer:
    """
    One GuildPlayer lives for the lifetime of the bot's presence in a voice channel.
    Handles: queue, playback, volume, loop, skip votes, inactivity.
    """

    def __init__(self, guild: discord.Guild, channel: discord.TextChannel):
        self.guild        = guild
        self.text_channel = channel
        self.voice:  Optional[discord.VoiceClient] = None

        self._queue:  deque[dict] = deque()
        self.current: Optional[dict]  = None
        self.loop:    LoopMode        = LoopMode.OFF
        self.volume:  float           = DEFAULT_VOLUME
        self.filter:  str             = ""            # FFmpeg audio filter string
        self.skip_votes: set[int]     = set()         # user IDs who voted to skip

        self._np_message: Optional[discord.Message] = None
        self._idle_task:  Optional[asyncio.Task]    = None
        self._play_next_event = asyncio.Event()

    # ── Queue helpers ──────────────────────────────────────────────────────────

    def enqueue(self, tracks: list[dict]) -> int:
        """Add tracks to the queue. Returns the position of the first track."""
        if len(self._queue) >= MAX_QUEUE_SIZE:
            raise OverflowError(f"Queue is full ({MAX_QUEUE_SIZE} tracks max).")
        pos = len(self._queue) + 1
        for t in tracks:
            self._queue.append(t)
        return pos

    @property
    def queue(self) -> list[dict]:
        return list(self._queue)

    def shuffle(self):
        import random
        lst = list(self._queue)
        random.shuffle(lst)
        self._queue = deque(lst)

    def remove(self, index: int) -> dict:
        """Remove track at 1-based index."""
        lst = list(self._queue)
        if not (1 <= index <= len(lst)):
            raise IndexError("No track at that position.")
        removed = lst.pop(index - 1)
        self._queue = deque(lst)
        return removed

    def move(self, from_idx: int, to_idx: int):
        lst = list(self._queue)
        n   = len(lst)
        if not (1 <= from_idx <= n and 1 <= to_idx <= n):
            raise IndexError("Index out of range.")
        track = lst.pop(from_idx - 1)
        lst.insert(to_idx - 1, track)
        self._queue = deque(lst)

    def clear(self):
        self._queue.clear()
        self.skip_votes.clear()

    # ── Playback ───────────────────────────────────────────────────────────────

    async def play_next(self):
        """Pull the next track from the queue and start streaming."""
        self.skip_votes.clear()
        self._cancel_idle()

        if self.loop == LoopMode.SONG and self.current:
            track = self.current
        elif self._queue:
            track = self._queue.popleft()
            if self.loop == LoopMode.QUEUE and self.current:
                self._queue.append(self.current)
        else:
            self.current = None
            self._start_idle()
            return

        self.current = track
        track["started_at"] = time.monotonic()

        # Re-fetch stream URL because YouTube URLs expire
        fresh = await _refresh_stream(track["url"])
        if fresh:
            track["stream"] = fresh

        source = discord.FFmpegPCMAudio(
            track["stream"],
            **build_ffmpeg_opts(self.filter),
        )
        source = discord.PCMVolumeTransformer(source, volume=self.volume)

        def after(err):
            if err:
                import logging
                logging.getLogger("harmony").error(f"Playback error: {err}")
            asyncio.run_coroutine_threadsafe(self.play_next(), self.guild._state.loop)

        self.voice.play(source, after=after)

    def skip(self):
        if self.voice and self.voice.is_playing():
            self.voice.stop()   # triggers after() → play_next()

    def pause(self):
        if self.voice and self.voice.is_playing():
            self.voice.pause()

    def resume(self):
        if self.voice and self.voice.is_paused():
            self.voice.resume()

    def set_volume(self, vol: float):
        self.volume = max(0.0, min(2.0, vol))
        if self.voice and self.voice.source:
            self.voice.source.volume = self.volume

    @property
    def elapsed(self) -> float:
        if self.current and self.current.get("started_at"):
            return time.monotonic() - self.current["started_at"]
        return 0.0

    # ── Inactivity ─────────────────────────────────────────────────────────────

    def _start_idle(self):
        self._idle_task = asyncio.ensure_future(self._idle_timeout())

    def _cancel_idle(self):
        if self._idle_task and not self._idle_task.done():
            self._idle_task.cancel()
        self._idle_task = None

    async def _idle_timeout(self):
        await asyncio.sleep(INACTIVITY_TIMEOUT)
        if self.voice and self.voice.is_connected():
            await self.text_channel.send(
                "⏹  Left voice channel due to inactivity.",
                delete_after=30,
            )
            await self.voice.disconnect()

    # ── Cleanup ────────────────────────────────────────────────────────────────

    async def destroy(self):
        self._cancel_idle()
        self.clear()
        self.current = None
        if self.voice:
            await self.voice.disconnect(force=True)


# ── Stream refresh ─────────────────────────────────────────────────────────────

async def _refresh_stream(url: str) -> Optional[str]:
    """Re-extract the direct audio URL (needed because YT links expire ~6 h)."""
    try:
        loop = asyncio.get_event_loop()
        opts = {**YTDL_OPTS, "extract_flat": False}
        with yt_dlp.YoutubeDL(opts) as ydl:
            data = await loop.run_in_executor(
                None, lambda: ydl.extract_info(url, download=False)
            )
        return data.get("url") if data else None
    except Exception:
        return None
