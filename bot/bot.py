# very very ugly code here sry
import discord
from discord import app_commands
from discord.ext import commands
from database import *
import datetime
import os
import io
import aiohttp

try:
    import resvg_py
    HAS_RESVG = True
except ImportError:
    HAS_RESVG = False

BOT_VERSION = "2.6.0"
API_BASE_URL = os.environ.get(
    'HOURGLASS_API_URL',
    os.environ.get('API_URL', 'https://hourglass.mike-server.fr')
).rstrip('/')

async def send_card_or_fallback(ctx, endpoint: str, filename_base: str, fallback_message: str):
    """
    Récupère la carte depuis l'API Hourglass, la convertit en PNG pour un affichage
    graphique natif direct dans Discord (Discord ne rend pas les SVG en images),
    et l'envoie comme fichier joint.
    Si l'API est indisponible ou ne répond pas, envoie le message texte de secours (fallback).
    """
    url = f"{API_BASE_URL}{endpoint}"
    raw_data = None

    try:
        timeout = aiohttp.ClientTimeout(total=8)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                content_type = resp.headers.get("Content-Type", "")
                if (resp.status in (200, 404) and "image/svg+xml" in content_type) or resp.status == 200:
                    raw_data = await resp.read()
                else:
                    print(f"[API ERROR] HTTP {resp.status} from {url}")
    except Exception as e:
        print(f"[API ERROR] Failed to fetch card from {url}: {e}")

    # Si l'API n'a pas renvoyé de données, on bascule vers le message texte de secours
    if not raw_data:
        await ctx.send(fallback_message)
        return

    # Si nous avons les données, on prépare le fichier image (PNG pour affichage Discord)
    file_to_send = None
    if HAS_RESVG:
        try:
            svg_text = raw_data.decode("utf-8", errors="replace")
            png_bytes = resvg_py.svg_to_bytes(svg_text)
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

@bot.hybrid_command(name="stats", description="Affiche les statistiques d'un utilisateur sur ce serveur.")
@app_commands.describe(user="L'utilisateur ciblé (par défaut vous-même)")
async def stats(ctx: commands.Context, user: discord.User = None):
    await ctx.defer()
    if ctx.guild is None:
        await ctx.send("Cette commande doit être exécutée sur un serveur Discord.")
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
        f"__Statistiques de {user.display_name} sur le serveur **{server_name}** :__\n"
        f"Nombre de messages : {nbr_messages}\n"
        f"Temps passé en vocal : {formatted_time}")
    
    safe_name = "".join(c for c in user.name if c.isalnum() or c in ('_', '-')) or str(user_id)
    await send_card_or_fallback(
        ctx,
        f"/api/card/user/{user_id}/server/{server_id}",
        f"stats_{safe_name}_{server_id}",
        message
    )

@bot.hybrid_command(name="allstats", description="Affiche les statistiques globales d'un utilisateur sur tous les serveurs.")
@app_commands.describe(user="L'utilisateur ciblé (par défaut vous-même)")
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
        f"__Statistiques **globales** de {user.display_name} :__\n"
        f"Nombre de messages: {nbr_messages}\n"
        f"Temps passé en vocal: {formatted_time}"
    )
        
    safe_name = "".join(c for c in user.name if c.isalnum() or c in ('_', '-')) or str(user_id)
    await send_card_or_fallback(
        ctx,
        f"/api/card/user/{user_id}",
        f"allstats_{safe_name}",
        message
    )



@bot.hybrid_command(name="top", description="Affiche le Top 10 des utilisateurs les plus actifs en vocal sur ce serveur.")
async def top(ctx: commands.Context):
    await ctx.defer()
    if ctx.guild is None:
        await ctx.send("Cette commande doit être exécutée sur un serveur Discord.")
        return

    top_users = GetTop10UsersBySecondsOnServer(ctx.guild.id)

    message_lines = [f"__Top 10 **{ctx.guild.name}** :__"]

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
        f"/api/card/top/server/{ctx.guild.id}",
        f"top_{ctx.guild.id}",
        message
    )

# Commande Discord !top pour afficher le top 10 des utilisateurs en fonction des secondes accumulées
@bot.hybrid_command(name="alltop", description="Affiche le Top 10 global des utilisateurs les plus actifs en vocal.")
async def alltop(ctx: commands.Context):
    await ctx.defer()
    top_users = GetTop10UsersBySeconds()

    if not top_users:
        message = "Aucun utilisateur trouvé dans les bases de données."
        await send_card_or_fallback(ctx, "/api/card/top", "top_global", message)
        return

    message_lines = ["__Top 10 **global** :__"]

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
        "/api/card/top",
        "top_global",
        message
    )

@bot.hybrid_command(name="server", description="Affiche les statistiques globales de ce serveur.")
async def server(ctx: commands.Context):
    await ctx.defer()
    if ctx.guild is None:
        await ctx.send("Cette commande doit être exécutée sur un serveur Discord.")
        return

    message_count = GetTotalMessagesOnServer(ctx.guild.id)
    seconds_count = GetTotalSecondsOnServer(ctx.guild.id)
    seconds_count = ConvertSecondsToTime(seconds_count)
    message = f"__Statistiques du serveur:__\nNombre de messages au total : {message_count}\nTemps passé en vocal au total : {seconds_count}"
    await send_card_or_fallback(
        ctx,
        f"/api/card/server/{ctx.guild.id}",
        f"server_{ctx.guild.id}",
        message
    )

@bot.hybrid_command(name="help", aliases=["aide"], description="Affiche la liste et l'aide des commandes de Hourglass BOT.")
async def help(ctx: commands.Context):
    await ctx.defer()
    message = (
        f"__**Commandes de Hourglass BOT:**__\n"
        f"**!stats [user]** ou **/stats** - *stats de l'utilisateur sur le serveur*\n"
        f"**!allstats [user]** ou **/allstats** - *stats de l'utilisateurs sur tous les serveur*\n"
        f"**!top** ou **/top** - *top 10 des utilisateurs en vocal sur le serveur*\n"
        f"**!alltop** ou **/alltop** - *top 10 des utilisateurs en vocal sur tous les serveurs*\n"
        f"**!server** ou **/server** - *Informations du serveur*\n"
        f"**!help** ou **/help** - *affiche cette aide*\n"
    )
    await send_card_or_fallback(
        ctx,
        "/api/card/commands",
        "help",
        message
    )

def ConvertSecondsToTime(seconds):
    # Calcul des heures, minutes et secondes
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    # Formatage du temps
    #time_format = "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)
    return f"{hours} h {minutes} min {seconds} s"

def runBot():
    discord_token = os.environ.get('DISCORD_TOKEN')
    bot.run(discord_token)


