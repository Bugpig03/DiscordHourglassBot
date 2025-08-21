import os
import heapq
from collections import defaultdict
from datetime import datetime
from app.database import Users, Stats, HistoricalStats, Servers
from peewee import fn, JOIN
from datetime import datetime, timedelta

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
def format_date_heure_fr(dt):
    mois = [
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre"
    ]
    jour = dt.day
    mois_str = mois[dt.month - 1]
    annee = dt.year
    heure = dt.strftime("%H:%M:%S")
    return f"{jour} {mois_str} {annee} à {heure}"

# CONVERTI LE FORMAT DE DATE BDD EN FORMAT FR
def format_date_fr(dt):
    mois = [
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre"
    ]
    jour = dt.day
    mois_str = mois[dt.month - 1]
    annee = dt.year
    return f"{jour} {mois_str} {annee}"

# RECUPERE LE USER ID DEPUIS LE USERNAME
def get_user_id_by_username(username):
    user = Users.select().where(Users.username == username).first()
    if user:
        return user.user_id
    return None

# RECUPERE LE SERVERNAME DEPUIS LE SERVER ID
def get_servername_by_server_id(server_id):
    server = Servers.select().where(Servers.server_id == server_id).first()
    if server:
        return server.servername
    return None

# RECUPERE LE TOTAL DE SECONDES DEPUIS UN USER ID
def get_total_seconds_by_user_id(user_id):
    result = Stats.select(fn.SUM(Stats.seconds).alias('total_seconds')) \
                  .where(Stats.user_id == user_id) \
                  .scalar()
    return result or 0

# RECUPERE LE TOTAL DE SECONDES DEPUIS UN SERVER ID
def get_total_seconds_by_server_id(server_id):
    result = Stats.select(fn.SUM(Stats.seconds).alias('total_seconds')) \
                  .where(Stats.server_id == server_id) \
                  .scalar()
    return result or 0

# RECUPERE LE TOTAL DE MESSAGE DEPUIS UN USER ID
def get_total_message_by_user_id(user_id):
    result = Stats.select(fn.SUM(Stats.messages).alias('total_messages')) \
                  .where(Stats.user_id == user_id) \
                  .scalar()
    return result or 0

# RECUPERE LE TOTAL DE MESSAGE DEPUIS UN SERVER ID
def get_total_message_by_server_id(server_id):
    result = Stats.select(fn.SUM(Stats.messages).alias('total_messages')) \
                  .where(Stats.server_id == server_id) \
                  .scalar()
    return result or 0

# RECUPERE LE RANG GLBOAL D UN USER DEPUIS UN USER ID
def get_global_rank_by_user_id_seconds(user_id):
    # Total de secondes de cet utilisateur
    user_total = (Stats
                  .select(fn.SUM(Stats.seconds))
                  .where(Stats.user_id == user_id)
                  .scalar() or 0)
    if user_total == 0:
        return None  # Pas d'activité → pas de classement
    # Nombre d'utilisateurs ayant plus de secondes que lui
    rank = (Stats
            .select(Stats.user_id)
            .group_by(Stats.user_id)
            .having(fn.SUM(Stats.seconds) > user_total)
            .count())
    return rank + 1

# RECUPERE LE NB D UTILISATEUR GLOBAL
def get_global_nb_user():
    # Total de secondes de cet utilisateur
    return Users.select(fn.COUNT(Users.user_id)).scalar() or 0

# RECUPERE LE NB SERVER GLOBAL
def get_global_nb_server():
    # Total de secondes de cet utilisateur
    return Servers.select(fn.COUNT(Servers.server_id)).scalar() or 0

# Récupérer l'activité d'un user sur X jours
# Si server_id est donné, ne prendre que ce serveur, sinon tous
def get_activity_sum_last_X_days(user_id, days, server_id=None):
    now = datetime.utcnow()
    since_days = now - timedelta(days=days)

    # Condition commune
    base_condition = (
        (HistoricalStats.user_id == user_id) &
        (HistoricalStats.created_at >= since_days) &
        (HistoricalStats.created_at <= now)
    )
    if server_id is not None:
        base_condition &= (HistoricalStats.server_id == server_id)

    # Trouver la plus ancienne date dans la période
    oldest_record = (HistoricalStats
                     .select(HistoricalStats.created_at)
                     .where(base_condition)
                     .order_by(HistoricalStats.created_at.asc())
                     .first())

    if not oldest_record:
        return {"seconds": 0, "messages": 0}

    oldest_date = oldest_record.created_at.date()

    # Additionner seconds et messages pour CETTE date
    sum_condition = (
        (HistoricalStats.user_id == user_id) &
        (fn.DATE(HistoricalStats.created_at) == oldest_date)
    )
    if server_id is not None:
        sum_condition &= (HistoricalStats.server_id == server_id)

    result = (HistoricalStats
              .select(
                  fn.SUM(HistoricalStats.seconds).alias("total_seconds"),
                  fn.SUM(HistoricalStats.messages).alias("total_messages")
              )
              .where(sum_condition)
              .dicts()
              .first())

    return {
        "seconds": result["total_seconds"] or 0,
        "messages": result["total_messages"] or 0
    }



# RECUPER L AVATAR DEPUIS UN USER ID
def get_user_avatar_url(user_id):
    user = Users.select(Users.avatar).where(Users.user_id == user_id).first()
    return user.avatar if user else None

# RECUPER L AVATAR DEPUIS UN SERVER ID
def get_server_avatar_url(server_id):
    server = Servers.select(Servers.avatar).where(Servers.server_id == server_id).first()
    return server.avatar if server else None

# RECUPER LE SERVER NAME DEPUIS UN SERVER ID
def get_server_name_by_id(server_id):
    server = Servers.select(Servers.servername).where(Servers.server_id == server_id).first()
    return server.servername if server else None

# RÉCUPÈRE LE NB D'UTILISATEURS D'UN SERVEUR VIA STATS
def get_user_count_by_server_id(server_id):
    count = Stats.select(Stats.user_id).where(Stats.server_id == server_id).distinct().count()
    return count

# RÉCUPÈRE LE RANK D UN UTILISATEUR D'UN SERVEUR DEPUIS USER ID ET SERVER ID VIA TABLE STATS
def get_user_rank_in_server(user_id, server_id):
    ranked_stats = (
        Stats
        .select(
            Stats.user_id,
            Stats.server_id,
            fn.RANK().over(
                partition_by=[Stats.server_id],
                order_by=[Stats.seconds.desc()]
            ).alias('rank')
        )
        .where(Stats.server_id == server_id)
        .alias('ranked_stats')
    )
    
    query = (
        Stats
        .select(ranked_stats.c.rank)
        .from_(ranked_stats)
        .where(ranked_stats.c.user_id == user_id)
    )
    
    rank = query.scalar()
    return rank

# RÉCUPÈRE LE RANK D'UN SERVEUR DEPUIS SON SERVER ID
def get_server_rank(server_id):
    query = (
        Stats
        .select(
            Stats.server_id,
            fn.SUM(Stats.seconds).alias('total_seconds')
        )
        .group_by(Stats.server_id)
        .order_by(fn.SUM(Stats.seconds).desc())
    )
    for idx, row in enumerate(query, start=1):
        if int(row.server_id) == int(server_id):
            return idx
    return None


def get_server_activity_sum_last_X_days(server_id, days):
    now = datetime.utcnow()
    since_days = now - timedelta(days=days)

    # Condition commune
    base_condition = (
        (HistoricalStats.server_id == server_id) &
        (HistoricalStats.created_at >= since_days) &
        (HistoricalStats.created_at <= now)
    )

    # Trouver la plus ancienne date dans la période
    oldest_record = (HistoricalStats
                     .select(HistoricalStats.created_at)
                     .where(base_condition)
                     .order_by(HistoricalStats.created_at.asc())
                     .first())

    if not oldest_record:
        return {"seconds": 0, "messages": 0}

    oldest_date = oldest_record.created_at.date()

    # Additionner seconds et messages pour CETTE date
    sum_condition = (
        (HistoricalStats.server_id == server_id) &
        (fn.DATE(HistoricalStats.created_at) == oldest_date)
    )

    result = (HistoricalStats
              .select(
                  fn.SUM(HistoricalStats.seconds).alias("total_seconds"),
                  fn.SUM(HistoricalStats.messages).alias("total_messages")
              )
              .where(sum_condition)
              .dicts()
              .first())

    return {
        "seconds": result["total_seconds"] or 0,
        "messages": result["total_messages"] or 0
    }


def get_user_servers_stats(user_id):
    # On récupère tous les serveurs où l'utilisateur est présent
    ranked_stats = (
        Stats
        .select(
            Stats.server_id,
            Servers.servername,
            Stats.user_id,
            Stats.seconds.alias('time_spent'),
            Stats.messages.alias('messages_count'),
            Stats.date_creation.alias('joined_at'),
            fn.RANK().over(
                partition_by=[Stats.server_id],
                order_by=[Stats.seconds.desc()]
            ).alias('rank')
        )
        .join(Servers, on=(Stats.server_id == Servers.server_id))
    )

    # Maintenant, on ne garde que notre utilisateur
    user_stats = ranked_stats.where(Stats.user_id == user_id)

    # On transforme en liste de dictionnaires
    return [
        {
            "server_id": stat.server_id,
            "server_name": get_server_name_by_id(stat.server_id),
            "avatar": get_server_avatar_url(stat.server_id),
            "rank": stat.rank,
            "nb_user": get_user_count_by_server_id(stat.server_id),
            "time_spent": round(stat.time_spent / 3600, 1),
            "messages_count": stat.messages_count,
            "rank": get_user_rank_in_server(user_id, stat.server_id),
            "joined_at": format_date_fr(stat.joined_at)
        }
        for stat in user_stats
    ]