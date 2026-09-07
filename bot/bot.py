# very very ugly code here sry
import discord
from discord import app_commands
from discord.ext import commands
from database import *
import datetime
import os
import io
import aiohttp

import re
import base64

try:
    import resvg_py
    HAS_RESVG = True
except ImportError:
    HAS_RESVG = False

BOT_VERSION = "2.6.2"
API_BASE_URL = os.environ.get(
    'HOURGLASS_API_URL',
    os.environ.get('API_URL', 'https://hourglass.mike-server.fr')
).rstrip('/')

FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")
FONTS_DIRS = [
    d for d in [
        FONTS_DIR,
        "/usr/share/fonts",
        "/usr/local/share/fonts",
        "/usr/share/fonts/truetype",
        "/usr/share/fonts/truetype/dejavu",
        "C:/Windows/Fonts",
        os.path.expanduser("~/AppData/Local/Microsoft/Windows/Fonts"),
        "/System/Library/Fonts",
        "/Library/Fonts",
    ] if os.path.exists(d)
]

_AVATAR_CACHE = {}
DEFAULT_AVATAR_URL = "https://cdn.discordapp.com/embed/avatars/0.png"

async def _get_default_avatar_data_uri(session: aiohttp.ClientSession) -> str:
    """Récupère et met en cache l'avatar Discord par défaut en Base64."""
    if DEFAULT_AVATAR_URL in _AVATAR_CACHE:
        return _AVATAR_CACHE[DEFAULT_AVATAR_URL]
    try:
        async with session.get(DEFAULT_AVATAR_URL, timeout=aiohttp.ClientTimeout(total=2)) as resp:
            if resp.status == 200:
                raw = await resp.read()
                mime = resp.headers.get("Content-Type", "image/png").split(";")[0].strip()
                b64 = base64.b64encode(raw).decode("ascii")
                data_uri = f"data:{mime};base64,{b64}"
                _AVATAR_CACHE[DEFAULT_AVATAR_URL] = data_uri
                return data_uri
    except Exception as e:
        print(f"[IMAGE INLINE] Failed to fetch default avatar: {e}")
    return ""

async def _inline_remote_images(session: aiohttp.ClientSession, svg: str) -> str:
    """Remplace les URLs (distantes ou relatives) des images par des Data URIs base64 pour resvg."""
    urls = list(set(re.findall(r'href=["\']([^"\']+)["\']', svg)))
    if not urls:
        return svg
    for u in urls:
        if u.startswith("data:"):
            continue
        if u in _AVATAR_CACHE:
            svg = svg.replace(u, _AVATAR_CACHE[u])
            continue
        fetch_url = u if u.startswith("http") else f"{API_BASE_URL}{u}"
        try:
            async with session.get(fetch_url, timeout=aiohttp.ClientTimeout(total=2)) as resp:
                if resp.status == 200:
                    raw = await resp.read()
                    mime = resp.headers.get("Content-Type", "image/png").split(";")[0].strip()
                    b64 = base64.b64encode(raw).decode("ascii")
                    data_uri = f"data:{mime};base64,{b64}"
                    _AVATAR_CACHE[u] = data_uri
                    svg = svg.replace(u, data_uri)
                else:
                    fallback_uri = await _get_default_avatar_data_uri(session)
                    if fallback_uri:
                        _AVATAR_CACHE[u] = fallback_uri
                        svg = svg.replace(u, fallback_uri)
        except Exception as e:
            print(f"[IMAGE INLINE] Could not fetch avatar {u}: {e}")
            fallback_uri = await _get_default_avatar_data_uri(session)
            if fallback_uri:
                _AVATAR_CACHE[u] = fallback_uri
                svg = svg.replace(u, fallback_uri)
    return svg

async def send_card_or_fallback(ctx, endpoint: str, filename_base: str, fallback_message: str):
    """
    Récupère la carte depuis l'API Hourglass, la convertit en PNG pour un affichage
    graphique natif direct dans Discord (Discord ne rend pas les SVG en images),
    et l'envoie comme fichier joint.
    Si l'API est indisponible ou ne répond pas, envoie le message texte de secours (fallback).
    """
    url = f"{API_BASE_URL}{endpoint}"
    raw_data = None
    svg_text = None

    try:
        timeout = aiohttp.ClientTimeout(total=8)
        headers = {"User-Agent": "Mozilla/5.0 (compatible; DiscordHourglassBot/2.6.2)"}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url) as resp:
                content_type = resp.headers.get("Content-Type", "")
                if (resp.status in (200, 404) and "image/svg+xml" in content_type) or resp.status == 200:
                    raw_data = await resp.read()
                else:
                    print(f"[API ERROR] HTTP {resp.status} from {url}")

            if raw_data:
                svg_text = raw_data.decode("utf-8", errors="replace")
                # Intégrer les images d'avatars distants en base64 pour que resvg les dessine
                svg_text = await _inline_remote_images(session, svg_text)
    except Exception as e:
        print(f"[API ERROR] Failed to fetch card from {url}: {e}")

    # Si l'API n'a pas renvoyé de données, on bascule vers le message texte de secours
    if not raw_data or not svg_text:
        await ctx.send(fallback_message)
        return

    # Si nous avons les données, on prépare le fichier image (PNG pour affichage Discord)
    file_to_send = None
    if HAS_RESVG:
        try:
            png_bytes = resvg_py.svg_to_bytes(
                svg_text,
                font_dirs=FONTS_DIRS if FONTS_DIRS else None,
                font_family="DejaVu Sans",
                sans_serif_family="DejaVu Sans",
                monospace_family="DejaVu Sans Mono",
                serif_family="DejaVu Serif",
            )
            file_to_send = discord.File(fp=io.BytesIO(png_bytes), filename=f"{filename_base}.png")
        except Exception as conv_err:
            print(f"[CONVERT ERROR] Could not convert SVG to PNG: {conv_err}")

    # Si resvg_py n'est pas installé ou en cas d'erreur de conversion, on envoie le SVG brut
    if not file_to_send:
        file_to_send = discord.File(fp=io.BytesIO(raw_data), filename=f"{filename_base}.svg")

    try:
        await ctx.send(file=file_to_send)
    except Exception as send_err:
        print(f"[DISCORD ERROR] Failed to send file attachment: {send_err}")
        # En dernier recours si Discord refuse l'envoi de fichier (ex: permissions du salon)
        await ctx.send(fallback_message)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

users_activity = {}

@bot.event
async def on_ready():
    print(f'Connected as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} slash command(s)')
    except Exception as e:
        print(f'Failed to sync slash commands: {e}')

@bot.event
async def on_message(message):
    if message.guild:
        server_id = message.guild.id
        user_id = message.author.id
        username = message.author.name
        servername = message.guild.name
        AddMessagesToUser(user_id,server_id)
        SetUsername(user_id, username)
        SetServerName(server_id, servername)
        if message.author.avatar:
            SetUserAvatar(message.author.id, message.author.avatar.url)
        if message.guild.icon:
            SetServerAvatar(message.guild.id, message.guild.icon.url)
        
    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):

    now = datetime.datetime.now()

    if before.channel is not None and after.channel is None:
        guild_id = member.guild.id
        # L'utilisateur a quitté un salon vocal
        print(f'{member} has left a voice channel: {before.channel.name}')

        join_time = users_activity.pop(member.id, None)
        join_time = datetime.datetime.strptime(join_time, "%Y-%m-%d %H:%M:%S")
        if join_time is not None:
            time_spent = now - join_time
            time_spent = int((now - join_time).total_seconds())
            print(f'{member} spent {time_spent} seconds in the voice channel')
            AddSecondsToUser(member.id, member.guild.id, time_spent)
            SetUsername(member.id, member.name)
            SetServerName(member.guild.id, member.guild.name)
            if member.avatar:
                SetUserAvatar(member.id, member.avatar.url)
            if member.guild.icon:
                SetServerAvatar(member.guild.id, member.guild.icon.url)


    if before.channel is None and after.channel is not None:
        # L'utilisateur a rejoint un salon vocal

        users_activity[member.id] = now.strftime("%Y-%m-%d %H:%M:%S")
        print(f'{member} has joined a voice channel: {after.channel.name}')

@bot.hybrid_command(name="stats", description="Displays a user's statistics on this server.")
@app_commands.describe(user="Target member (defaults to yourself)")
async def stats(ctx: commands.Context, user: discord.User = None):
    await ctx.defer()
    if ctx.guild is None:
        await ctx.send("This command must be executed within a Discord server.")
        return

    if user is None:
        user = ctx.author
    
    user_id = user.id
    server_id = ctx.guild.id

    server_name = ctx.guild.name

    if user.avatar:
        SetUserAvatar(user.id, user.avatar.url)

    formatted_time = ConvertSecondsToTime(GetSecondsOfUserOnServer(user_id,server_id))
    nbr_messages = GetMessagesOfUserOnServer(user_id,server_id)

    message = (
        f"__Statistics for {user.display_name} on server **{server_name}**:__\n"
        f"Messages sent: {nbr_messages}\n"
        f"Time spent in voice: {formatted_time}"
    )
    
    safe_name = "".join(c for c in user.name if c.isalnum() or c in ('_', '-')) or str(user_id)
    await send_card_or_fallback(
        ctx,
        f"/api/card/user/{user_id}/server/{server_id}?lang=en",
        f"stats_{safe_name}_{server_id}",
        message
    )

@bot.hybrid_command(name="allstats", description="Displays global statistics for a user across all servers.")
@app_commands.describe(user="Target member (defaults to yourself)")
async def allstats(ctx: commands.Context, user: discord.User = None):
    await ctx.defer()
    if user is None:
        user = ctx.author

    user_id = user.id

    if user.avatar:
        SetUserAvatar(user.id, user.avatar.url)

    formatted_time = ConvertSecondsToTime(GetSecondsOfUser(user_id))
    nbr_messages = GetMessagesOfUser(user_id)

    message = (
        f"__**Global** statistics for {user.display_name}:__\n"
        f"Total messages: {nbr_messages}\n"
        f"Time spent in voice: {formatted_time}"
    )
        
    safe_name = "".join(c for c in user.name if c.isalnum() or c in ('_', '-')) or str(user_id)
    await send_card_or_fallback(
        ctx,
        f"/api/card/user/{user_id}?lang=en",
        f"allstats_{safe_name}",
        message
    )


@bot.hybrid_command(name="top", description="Displays the Top 10 most active voice users on this server.")
async def top(ctx: commands.Context):
    await ctx.defer()
    if ctx.guild is None:
        await ctx.send("This command must be executed within a Discord server.")
        return

    top_users = GetTop10UsersBySecondsOnServer(ctx.guild.id)

    message_lines = [f"__Top 10 Voice Members on **{ctx.guild.name}**:__"]

    top_count = 1

    for user in top_users:
        user_id = user[0]
        user_seconds = user[2]
        member = ctx.guild.get_member(user_id)
        seconds_count = ConvertSecondsToTime(user_seconds)

        if member:
            line = f"**{top_count}** - {member} - {seconds_count}"
        else:
            line = f"**{top_count}** - {user_id} - {seconds_count}"
        
        top_count = top_count + 1
        message_lines.append(line)

    message = "\n".join(message_lines)
    await send_card_or_fallback(
        ctx,
        f"/api/card/top/server/{ctx.guild.id}?lang=en",
        f"top_{ctx.guild.id}",
        message
    )

# Commande Discord !top pour afficher le top 10 des utilisateurs en fonction des secondes accumulées
@bot.hybrid_command(name="alltop", description="Displays the global Top 10 most active voice users across all servers.")
async def alltop(ctx: commands.Context):
    await ctx.defer()
    top_users = GetTop10UsersBySeconds()

    if not top_users:
        message = "No voice users found in database."
        await send_card_or_fallback(ctx, "/api/card/top?lang=en", "top_global", message)
        return

    message_lines = ["__Global Top 10 Voice Members:__"]

    top_count = 1

    for user in top_users:
        user_id = user[0]
        user_seconds = user[1]
        member = ctx.guild.get_member(user_id) if ctx.guild else None
        seconds_count = ConvertSecondsToTime(user_seconds)

        if member:
            line = f"**{top_count}** - {member} - {seconds_count}"
        else:
            line = f"**{top_count}** - {user_id} - {seconds_count}"

        top_count = top_count + 1
        message_lines.append(line)
    message = "\n".join(message_lines)
    await send_card_or_fallback(
        ctx,
        "/api/card/top?lang=en",
        "top_global",
        message
    )

@bot.hybrid_command(name="server", description="Displays global statistics for this server.")
async def server(ctx: commands.Context):
    await ctx.defer()
    if ctx.guild is None:
        await ctx.send("This command must be executed within a Discord server.")
        return

    message_count = GetTotalMessagesOnServer(ctx.guild.id)
    seconds_count = GetTotalSecondsOnServer(ctx.guild.id)
    seconds_count = ConvertSecondsToTime(seconds_count)
    message = f"__Server Statistics:__\nTotal messages: {message_count}\nTotal voice time: {seconds_count}"
    await send_card_or_fallback(
        ctx,
        f"/api/card/server/{ctx.guild.id}?lang=en",
        f"server_{ctx.guild.id}",
        message
    )

@bot.hybrid_command(name="help", aliases=["aide"], description="Displays the command list and help guide for Hourglass BOT.")
async def help(ctx: commands.Context):
    await ctx.defer()
    message = (
        f"__**Hourglass BOT Commands:**__\n"
        f"**/stats [user]** or **!stats** - *User stats on this server*\n"
        f"**/allstats [user]** or **!allstats** - *Global user stats across all servers*\n"
        f"**/top** or **!top** - *Top 10 voice users on this server*\n"
        f"**/alltop** or **!alltop** - *Global Top 10 voice users across all servers*\n"
        f"**/server** or **!server** - *Server statistics and voice metrics*\n"
        f"**/help** or **!help** - *Display this command guide*\n"
    )
    await send_card_or_fallback(
        ctx,
        "/api/card/commands?lang=en",
        "help",
        message
    )

def ConvertSecondsToTime(seconds):
    # Calcul des heures, minutes et secondes
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    return f"{hours}h {minutes}m {seconds}s"

def runBot():
    discord_token = os.environ.get('DISCORD_TOKEN')
    bot.run(discord_token)


