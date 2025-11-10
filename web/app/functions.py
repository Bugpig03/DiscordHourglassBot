import os
import heapq
from collections import defaultdict
from datetime import datetime
from app.database import Users, Stats, HistoricalStats, Servers
from peewee import fn, JOIN, SQL
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
    if isinstance(server_id, str):
        if not server_id.isdigit():
            return None
        server_id = int(server_id)
    elif not isinstance(server_id, int):
        return None
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
        return "Non classé"  # Pas d'activité → pas de classement
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

    sum_condition_now = (
        (Stats.user_id == user_id)
    )

    if server_id is not None:
        sum_condition &= (HistoricalStats.server_id == server_id)
        sum_condition_now &= (Stats.server_id == server_id)

    result = (HistoricalStats
              .select(
                  fn.SUM(HistoricalStats.seconds).alias("total_seconds"),
                  fn.SUM(HistoricalStats.messages).alias("total_messages")
              )
              .where(sum_condition)
              .dicts()
              .first())

    result_now = (Stats
        .select(
            fn.SUM(Stats.seconds).alias("total_seconds"),
            fn.SUM(Stats.messages).alias("total_messages")
        )
        .where(sum_condition_now)
        .dicts()
        .first()
    )

    seconds = result_now["total_seconds"] - result["total_seconds"]
    messages = result_now["total_messages"] - result["total_messages"]

    return {
        "seconds": seconds or 0,
        "messages": messages or 0
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

    sum_condition_now = (
        (Stats.server_id == server_id)
    )

    result = (HistoricalStats
              .select(
                  fn.SUM(HistoricalStats.seconds).alias("total_seconds"),
                  fn.SUM(HistoricalStats.messages).alias("total_messages")
              )
              .where(sum_condition)
              .dicts()
              .first())

    result_now = (Stats
        .select(
            fn.SUM(Stats.seconds).alias("total_seconds"),
            fn.SUM(Stats.messages).alias("total_messages")
        )
        .where(sum_condition_now)
        .dicts()
        .first()
    )

    seconds = result_now["total_seconds"] - result["total_seconds"]
    messages = result_now["total_messages"] - result["total_messages"]

    return {
        "seconds": seconds or 0,
        "messages": messages or 0
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


def get_first_of_month_hours_sum(server_id=None, user_id=None):
    """
    Somme des heures pour tous les utilisateurs,
    uniquement le premier jour de chaque mois.
    """
    # Grouper par mois directement, filtrer les 1ers jours
    query = (HistoricalStats
        .select(
            fn.DATE_TRUNC('month', HistoricalStats.created_at).alias('month_start'),
            fn.SUM(HistoricalStats.seconds).alias('total_seconds')
        )
        .where(SQL("EXTRACT(DAY FROM created_at) = 1"))
    )

    if server_id:
        query = query.where(HistoricalStats.server_id == server_id)
    if user_id:
        query = query.where(HistoricalStats.user_id == user_id)

    query = query.group_by(fn.DATE_TRUNC('month', HistoricalStats.created_at)) \
                 .order_by(fn.DATE_TRUNC('month', HistoricalStats.created_at))

    result = []
    for row in query:
        hours = row.total_seconds / 3600
        result.append({
            "month": row.month_start.strftime("%Y-%m-%d"),
            "total_hours": round(hours, 1)
        })

    # ajout du debut du bot ici
    result.append({
            "month": "2024-04-28",
            "total_hours": 0.0
        })
    
    # ajout last value
    result.append({
            "month": datetime.now().strftime("%Y-%m-%d"),
            "total_hours": round ((Stats.select(fn.SUM(Stats.seconds)).scalar() or 0) / 3600 ,1)
        })

    #TRIE
    result = sorted(result, key=lambda x: x["month"])

    return result


def get_monthly_hours_diff(server_id=None, user_id=None):
    """
    Calcule le nombre d'heures passées chaque mois,
    en prenant la différence entre les totaux du 1er de chaque mois.
    La différence est associée au mois de départ.
    Exemple : (valeur du 01/02) - (valeur du 01/01) => heures de janvier
    """
    # Étape 1 : Récupérer les totaux au 1er de chaque mois
    query = (HistoricalStats
        .select(
            fn.DATE_TRUNC('month', HistoricalStats.created_at).alias('month_start'),
            fn.SUM(HistoricalStats.seconds).alias('total_seconds')
        )
        .where(SQL("EXTRACT(DAY FROM created_at) = 1"))
    )

    if server_id:
        query = query.where(HistoricalStats.server_id == server_id)
    if user_id:
        query = query.where(HistoricalStats.user_id == user_id)

    query = query.group_by(fn.DATE_TRUNC('month', HistoricalStats.created_at)) \
                 .order_by(fn.DATE_TRUNC('month', HistoricalStats.created_at))

    # Étape 2 : Transformer les résultats en liste triée
    monthly_data = []
    for row in query:
        monthly_data.append({
            "month": row.month_start.strftime("%Y-%m-%d"),
            "total_hours": round(row.total_seconds / 3600, 1)
        })

    # Ajouter la valeur actuelle (aujourd’hui)
    current_total = (Stats
        .select(fn.SUM(Stats.seconds))
        .scalar() or 0)

    monthly_data.append({
        "month": datetime.now().strftime("%Y-%m-%d"),
        "total_hours": round(current_total / 3600, 1)
    })

    # Étape 3 : Trier chronologiquement
    monthly_data = sorted(monthly_data, key=lambda x: x["month"])

    # Étape 4 : Calculer les différences entre mois consécutifs
    monthly_differences = []
    for i in range(1, len(monthly_data)):
        prev = monthly_data[i - 1]
        curr = monthly_data[i]
        diff = round(curr["total_hours"] - prev["total_hours"], 1)

        # On associe la différence au mois de départ
        monthly_differences.append({
            "month": prev["month"],
            "hours_this_month": max(diff, 0)
        })

    return monthly_differences