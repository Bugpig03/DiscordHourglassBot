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

    await ctx.send(f"Stats de {user.mention} :\nNombre de messages : {message_count}\nTemps passé en vocal : {seconds_count}")


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


