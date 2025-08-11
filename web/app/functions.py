import os
import heapq
from collections import defaultdict
from datetime import datetime
from app.database import Users, Stats
from peewee import fn

# CONVERTI LES SECONDES EN HEURES, MINUTES, SECONDES
def ConvertSecondsToTime(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    # Formatage du temps
    #time_format = "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)
    return f"{hours} h {minutes} min {seconds} s"

# CONVERTI LES SECONDES EN HEURES
def ConvertSecondsToHours(seconds): # Transforme les secondes en heures
    hours = round(seconds / 3600,1)

    return f"{hours} h"

# CONVERTI LE FORMAT DE DATE BDD EN FORMAT FR
def format_date_fr(dt):
    mois = [
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre"
    ]
    jour = dt.day
    mois_str = mois[dt.month - 1]
    annee = dt.year
    heure = dt.strftime("%H:%M:%S")
    return f"{jour} {mois_str} {annee} à {heure}"

# RECUPERE LE USER ID DEPUIS LE USERNAME
def get_user_id_by_username(username):
    user = Users.select().where(Users.username == username).first()
    if user:
        return user.user_id
    return None

# RECUPERE LE TOTAL DE SECONDES DEPUIS UN USER ID
def get_total_seconds_by_user_id(user_id):
    result = Stats.select(fn.SUM(Stats.seconds).alias('total_seconds')) \
                  .where(Stats.user_id == user_id) \
                  .scalar()
    return result or 0
