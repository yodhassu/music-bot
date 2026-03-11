"""
config.py — centralised settings for Harmony
Copy this file to .env and fill in your values,
OR just edit the defaults below for quick local testing.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Core ───────────────────────────────────────────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "YOUR_TOKEN_HERE")
PREFIX:    str = os.getenv("PREFIX", "!")

# ── Music defaults ─────────────────────────────────────────────────────────────
DEFAULT_VOLUME:      float = 0.5          # 50 %
MAX_QUEUE_SIZE:      int   = 200          # tracks per server
INACTIVITY_TIMEOUT:  int   = 300          # seconds before auto-disconnect
SKIP_VOTE_RATIO:     float = 0.5          # 50 % of listeners needed to skip
MAX_SEARCH_RESULTS:  int   = 5            # results shown on /search

# ── Embed colours (hex) ────────────────────────────────────────────────────────
COLOR_PRIMARY  = 0x7C3AED   # violet — main brand colour
COLOR_SUCCESS  = 0x22C55E   # green
COLOR_ERROR    = 0xEF4444   # red
COLOR_WARNING  = 0xF59E0B   # amber
COLOR_INFO     = 0x3B82F6   # blue
