# 🎵 Harmony — Discord Music Bot

A feature-rich Discord music bot built with **discord.py** and **yt-dlp**.
Streams audio from YouTube with a clean slash-command interface, real-time
audio filters, smart queue management, and skip voting.

---

## ✨ Features

| Feature | Details |
|---------|---------|
| 🎵 **Playback** | YouTube URLs, playlists, or plain search queries |
| 🔍 **Search picker** | Browse top 5 results and choose interactively |
| 📋 **Queue** | Paginated queue with reorder, remove & shuffle |
| 🔁 **Loop modes** | Off · Song · Queue |
| 🎛 **Audio filters** | Bass boost, Nightcore, Vaporwave, 8D, Echo, Karaoke… |
| ⏭ **Skip voting** | Democratic skip — DJs can force-skip |
| 🔊 **Volume control** | 0–200% with live adjustment |
| ⏱ **Inactivity timeout** | Auto-disconnects after 5 minutes of silence |
| 🤖 **Auto-disconnect** | Leaves when the voice channel empties |

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.10+
- [FFmpeg](https://ffmpeg.org/download.html) installed and on your PATH
- A Discord bot token ([guide](https://discordpy.readthedocs.io/en/stable/discord.html))

### 2. Clone & install

```bash
git clone https://github.com/yourname/harmony-bot.git
cd harmony-bot
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env and paste your BOT_TOKEN
```

### 4. Run

```bash
python main.py
```

---

## 📂 Project Structure

```
harmony-bot/
├── main.py              # Bot entry point
├── config.py            # Centralised settings
├── requirements.txt
├── .env.example
├── cogs/
│   ├── music.py         # All playback slash commands
│   ├── filters.py       # Audio filter command
│   └── help.py          # /help command
└── utils/
    ├── player.py         # GuildPlayer class + yt-dlp helpers
    └── embeds.py         # Embed builders (UI layer)
```

---

## 🎛 Commands

| Command | Description |
|---------|-------------|
| `/play <query>` | Play a song, playlist, or search query |
| `/search <query>` | Pick from top 5 YouTube results |
| `/pause` | Pause playback |
| `/resume` | Resume playback |
| `/skip` | Vote to skip (DJs force-skip) |
| `/loop <mode>` | Loop: `off` · `song` · `queue` |
| `/volume <0–200>` | Set volume percentage |
| `/filter <preset>` | Apply an audio effect |
| `/queue [page]` | Browse the queue |
| `/nowplaying` | Show the Now Playing card |
| `/remove <pos>` | Remove a queued track |
| `/move <from> <to>` | Reorder the queue |
| `/shuffle` | Shuffle the queue |
| `/stop` | Stop & clear the queue |
| `/leave` | Disconnect the bot |
| `/help` | List all commands |

---

## 🔐 Permissions

The bot requires the following Discord permissions:

- `Read Messages / View Channels`
- `Send Messages`
- `Embed Links`
- `Connect` + `Speak` (voice)
- `Use Application Commands`

> **Tip:** Create a role called `DJ` to let specific users force-skip
> and perform privileged actions.

---

## 🛠 Configuration

Edit `config.py` (or set environment variables):

| Variable | Default | Description |
|----------|---------|-------------|
| `BOT_TOKEN` | — | Your Discord bot token |
| `PREFIX` | `!` | Legacy text prefix |
| `DEFAULT_VOLUME` | `0.5` | Starting volume (0–2) |
| `MAX_QUEUE_SIZE` | `200` | Max tracks per server |
| `INACTIVITY_TIMEOUT` | `300` | Seconds before auto-disconnect |
| `SKIP_VOTE_RATIO` | `0.5` | Fraction of listeners needed to skip |

---

## 📜 License

MIT — free to use, modify, and distribute.
