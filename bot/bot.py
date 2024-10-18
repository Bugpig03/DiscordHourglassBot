# very very ugly code here sry
import discord
from discord.ext import commands
from database import *
import datetime
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

users_activity = {}

@bot.event
async def on_ready():
    print(f'Connected as {bot.user}')

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


    if before.channel is None and after.channel is not None:
        # L'utilisateur a rejoint un salon vocal

        users_activity[member.id] = now.strftime("%Y-%m-%d %H:%M:%S")
        print(f'{member} has joined a voice channel: {after.channel.name}')

@bot.command()
async def stats(ctx, user: discord.User = None):

    if user is None:
        user = ctx.author
    
    user_id = user.id
    server_id = ctx.guild.id

    server_name = ctx.guild.name

    formatted_time = ConvertSecondsToTime(GetSecondsOfUserOnServer(user_id,server_id))
    nbr_messages = GetMessagesOfUserOnServer(user_id,server_id)
    

    message = (
        f"__Statistiques de {user.display_name} sur le serveur **{server_name}** :__\n"
        f"Nombre de messages : {nbr_messages}\n"
        f"Temps passé en vocal : {formatted_time}")
    
    await ctx.send(message)

@bot.command()
async def allstats(ctx, user: discord.User = None):

    if user is None:
        user = ctx.author

    user_id = user.id

    formatted_time = ConvertSecondsToTime(GetSecondsOfUser(user_id))
    nbr_messages = GetMessagesOfUser(user_id)

    message = (
        f"__Statistiques **globales** de {user.display_name} :__\n"
        f"Nombre de messages: {nbr_messages}\n"
        f"Temps passé en vocal: {formatted_time}"
    )
        
    await ctx.send(message)



@bot.command()
async def top(ctx):

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
            print(line)
        else:
            line = f"**{top_count}** - {user_id} - {seconds_count}"
            print(line)
        
        top_count = top_count + 1
        message_lines.append(line)

    message = "\n".join(message_lines)
    await ctx.send(message)

# Commande Discord !top pour afficher le top 10 des utilisateurs en fonction des secondes accumulées
@bot.command()
async def alltop(ctx):
        
    top_users = GetTop10UsersBySeconds()

    if not top_users:
        await ctx.send("Aucun utilisateur trouvé dans les bases de données.")
        return

    message_lines = ["__Top 10 **global** :__"]

    top_count = 1

    for user in top_users:
        user_id = user[0]
        user_seconds = user[1]
        member = ctx.guild.get_member(user_id)
        seconds_count = ConvertSecondsToTime(user_seconds)

        if member:
            line = f"**{top_count}** - {member} - {seconds_count}"
        else:
            line = f"**{top_count}** - {user_id} - {seconds_count}"

        top_count = top_count + 1
        message_lines.append(line)
    message = "\n".join(message_lines)
    await ctx.send(message)

@bot.command()
async def server(ctx):
    message_count = GetTotalMessagesOnServer(ctx.guild.id)
    seconds_count = GetTotalSecondsOnServer(ctx.guild.id)
    seconds_count = ConvertSecondsToTime(seconds_count)
    await ctx.send(f"__Statistiques du serveur:__\nNombre de messages au total : {message_count}\nTemps passé en vocal au total : {seconds_count}")

@bot.command()
async def aide(ctx):
    message = (
        f"__**Commandes de Hourglass BOT:**__\n"
        f"**!stats [user]** - *stats de l'utilisateur sur le serveur*\n"
        f"**!allstats [user]** - *stats de l'utilisateurs sur tous les serveur*\n"
        f"**!top** - *top 10 des utilisateurs en fonction du temps passé sur le serveur*\n"
        f"**!allstats [user]** - *stats de l'utilisateurs sur tous les serveur*\n"
        f"**!alltop** - *top 10 des utilisateurs en fonction du temps passé sur tous les serveurs*\n"
        f"**!server** - *Informations du serveur*\n"
    )
    await ctx.send(message)


def ConvertSecondsToTime(seconds):
    # Calcul des heures, minutes et secondes
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    # Formatage du temps
    time_format = "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)
    
    return time_format

def runBot():
    discord_token = os.environ.get('DISCORD_TOKEN')
    bot.run(discord_token)


