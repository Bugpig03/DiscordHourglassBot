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
    # Vérifie si le message est envoyé dans un serveur
    if message.guild:
        server_id = message.guild.id
        user_id = message.author.id
        AddMessagesToUser(user_id,server_id)
        

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


    if before.channel is None and after.channel is not None:
        # L'utilisateur a rejoint un salon vocal

        users_activity[member.id] = now.strftime("%Y-%m-%d %H:%M:%S")
        print(f'{member} has joined a voice channel: {after.channel.name}')

@bot.command()
async def stats(ctx, user: discord.User = None):
    if user is None:
        user = ctx.author
    
    # Obtient le nombre de messages de l'utilisateur
    message_count = GetMessagesOfUser(user.id, ctx.guild.id)
    
    # Obtient le nombre de secondes passées sur le serveur par l'utilisateur
    seconds_count = GetSecondsOfUser(user.id, ctx.guild.id)
    seconds_count = ConvertSecondsToTime(seconds_count)

    await ctx.send(f"__Statistiques **locale** de {user.display_name}:__\nNombre de messages : {message_count}\nTemps passé en vocal : {seconds_count}")

@bot.command()
async def allstats(ctx, user: discord.User = None):

    if user is None:
        user = ctx.author

    user_id = user.id

    try:
        all_user_stats = GetUserStatsFromAllDBs(user_id)

        if not all_user_stats:
            await ctx.send(f"Aucune statistique trouvée pour l'utilisateur {user.display_name}.")
            return
        
        await ctx.send(f"__Statistiques **globale** de {user.display_name} :__")
        user_global_msg = 0
        user_global_seconds = 0
        for stats in all_user_stats:
            user_global_msg = user_global_msg  + stats[1]
            user_global_seconds = user_global_seconds + stats[2]
        await ctx.send(f"Nombre de messages: {user_global_msg}\n Temps passé en vocal: {ConvertSecondsToTime(user_global_seconds)}")
    
    except Exception as e:
        await ctx.send(f"Une erreur est survenue lors de la récupération des statistiques : {e}")



@bot.command()
async def top(ctx):

    top_users = GetTop10UsersBySeconds(ctx.guild.id)

    await ctx.send(f"__Top 10 **{ctx.guild.name}**:__")
    top_count = 0

    for user in top_users:
        top_count+=1

        user_id = user[0]
        user_seconds = user[2]
        member = ctx.guild.get_member(user_id)
        seconds_count = ConvertSecondsToTime(user_seconds)

        if member:
            await ctx.send(f"**{top_count}** - {member} - {seconds_count}")
        else:
            await ctx.send(f"**{top_count}** - {user_id} - {seconds_count}")

# Commande Discord !top pour afficher le top 10 des utilisateurs en fonction des secondes accumulées
@bot.command()
async def alltop(ctx):
    try:
        top_users = AggregateUserSeconds()

        if not top_users:
            await ctx.send("Aucun utilisateur trouvé dans les bases de données.")
            return

        await ctx.send("__Top 10 **global**:__")
        for index, (user_id, total_seconds) in enumerate(top_users, start=1):
            user = ctx.guild.get_member(user_id)
            user_name = user.display_name if user else f"Utilisateur inconnu ({user_id})"
            await ctx.send(f"**{index}.** {user_name} - {ConvertSecondsToTime(total_seconds)}")

    except Exception as e:
        await ctx.send(f"Une erreur est survenue lors de la récupération du top 10 : {e}")

@bot.command()
async def server(ctx):
    message_count = get_total_messages_on_server(ctx.guild.id)
    seconds_count = get_total_seconds_on_server(ctx.guild.id)
    seconds_count = ConvertSecondsToTime(seconds_count)
    await ctx.send(f"__Statistiques du serveur:__\nNombre de messages au total : {message_count}\nTemps passé en vocal au total : {seconds_count}")

@bot.command()
async def aide(ctx):
    await ctx.send("__**Commandes de Hourglass BOT:**__\n**!stats [user]** - *stats de l'utilisateur sur le serveur*\n**!allstats [user]** - *stats de l'utilisateurs sur tous les serveur*\n**!top** - *top 10 des utilisateurs en fonction du temps passé sur le serveur*\n**!alltop** - *top 10 des utilisateurs en fonction du temps passé sur tous les serveurs*")


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


