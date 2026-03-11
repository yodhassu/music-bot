"""
utils/embeds.py — reusable embed builders for Harmony
"""

from __future__ import annotations
import discord
from typing import Optional
from config import (
    COLOR_PRIMARY, COLOR_SUCCESS,
    COLOR_ERROR, COLOR_WARNING, COLOR_INFO,
)


def _base(color: int) -> discord.Embed:
    return discord.Embed(color=color)


# ── Generic helpers ────────────────────────────────────────────────────────────

def success(title: str, description: str = "") -> discord.Embed:
    e = _base(COLOR_SUCCESS)
    e.title = f"✅  {title}"
    if description:
        e.description = description
    return e


def error(title: str, description: str = "") -> discord.Embed:
    e = _base(COLOR_ERROR)
    e.title = f"❌  {title}"
    if description:
        e.description = description
    return e


def warning(title: str, description: str = "") -> discord.Embed:
    e = _base(COLOR_WARNING)
    e.title = f"⚠️  {title}"
    if description:
        e.description = description
    return e


def info(title: str, description: str = "") -> discord.Embed:
    e = _base(COLOR_INFO)
    e.title = f"ℹ️  {title}"
    if description:
        e.description = description
    return e


# ── Music-specific embeds ──────────────────────────────────────────────────────

def now_playing(track: dict, volume: float, loop_mode: str, queue_len: int) -> discord.Embed:
    """
    Rich "Now Playing" embed.
    track keys: title, url, thumbnail, duration, requester (discord.Member)
    """
    duration_str = _fmt_duration(track.get("duration", 0))
    progress     = _progress_bar(track.get("elapsed", 0), track.get("duration", 1))

    e = _base(COLOR_PRIMARY)
    e.set_author(name="🎵  Now Playing")
    e.title       = track["title"]
    e.url         = track.get("url", "")
    e.description = f"`{progress}` `{duration_str}`"

    if thumb := track.get("thumbnail"):
        e.set_thumbnail(url=thumb)

    e.add_field(name="🔊 Volume",    value=f"{int(volume * 100)}%",     inline=True)
    e.add_field(name="🔁 Loop",      value=loop_mode.capitalize(),       inline=True)
    e.add_field(name="📋 In queue",  value=str(queue_len),               inline=True)

    if req := track.get("requester"):
        e.set_footer(
            text=f"Requested by {req.display_name}",
            icon_url=req.display_avatar.url,
        )
    return e


def track_added(track: dict, position: int) -> discord.Embed:
    e = _base(COLOR_SUCCESS)
    e.set_author(name="➕  Added to Queue")
    e.title       = track["title"]
    e.url         = track.get("url", "")
    e.description = (
        f"⏱ Duration: `{_fmt_duration(track.get('duration', 0))}`\n"
        f"📍 Position: `#{position}`"
    )
    if thumb := track.get("thumbnail"):
        e.set_thumbnail(url=thumb)
    return e


def queue_embed(queue: list[dict], page: int, per_page: int = 10) -> discord.Embed:
    total_pages = max(1, (len(queue) - 1) // per_page + 1)
    start       = page * per_page
    chunk       = queue[start : start + per_page]

    e = _base(COLOR_INFO)
    e.title = "📋  Music Queue"

    lines = []
    for i, t in enumerate(chunk, start=start + 1):
        lines.append(
            f"`{i:02d}.` [{t['title']}]({t.get('url','')})  "
            f"— `{_fmt_duration(t.get('duration',0))}`"
        )

    e.description = "\n".join(lines) or "Queue is empty."
    e.set_footer(text=f"Page {page + 1}/{total_pages}  •  {len(queue)} track(s) total")
    return e


def search_results(tracks: list[dict]) -> discord.Embed:
    e = _base(COLOR_INFO)
    e.set_author(name="🔍  Search Results")
    e.description = "Pick a track by typing its number (1–{n}):".format(n=len(tracks))

    lines = []
    for i, t in enumerate(tracks, 1):
        dur = _fmt_duration(t.get("duration", 0))
        lines.append(f"**{i}.** {t['title']}  `{dur}`")

    e.description += "\n\n" + "\n".join(lines)
    e.set_footer(text="Reply within 30 seconds, or type 'cancel'")
    return e


# ── Internal helpers ───────────────────────────────────────────────────────────

def _fmt_duration(seconds: int) -> str:
    if not seconds:
        return "∞"
    h, remainder = divmod(int(seconds), 3600)
    m, s         = divmod(remainder, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _progress_bar(elapsed: float, total: float, width: int = 15) -> str:
    if total <= 0:
        return "─" * width
    filled = int(width * min(elapsed / total, 1.0))
    bar    = "━" * filled + "●" + "─" * (width - filled)
    return f"{_fmt_duration(elapsed)} {bar} {_fmt_duration(total)}"
