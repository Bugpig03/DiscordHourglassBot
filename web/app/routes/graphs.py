from flask import Blueprint, render_template, request, flash, redirect, url_for
from peewee import fn
from datetime import datetime
from app.functions import get_first_of_month_hours_sum, get_monthly_hours_diff
import json
from app.database import Stats,Servers

graphs_bp = Blueprint("graphs", __name__)

FR_MONTH_ABBR = {
    1: "Janv", 2: "Fév", 3: "Mars", 4: "Avr",
    5: "Mai", 6: "Juin", 7: "Juil", 8: "Août",
    9: "Sept", 10: "Oct", 11: "Nov", 12: "Déc"
}

@graphs_bp.route("/graphs", methods=["GET"])
def graphs():

    # Graphiques des heures total
    data = get_first_of_month_hours_sum()

    chart_data_json = json.dumps({
    "labels": [row["month"] for row in data],
    "hours": [row["total_hours"] for row in data]
    })

    # Graphiqes en barres des heures par mois 
    monthly_diff_data = get_monthly_hours_diff()
    monthly_chart_data_json = json.dumps({
        "labels": [
            f"{FR_MONTH_ABBR[datetime.strptime(row['month'], '%Y-%m-%d').month]} "
            f"{datetime.strptime(row['month'], '%Y-%m-%d').year}"
            for row in monthly_diff_data
        ],
        "hours": [row["hours_this_month"] for row in monthly_diff_data]
    })

    # Graphiques camember des heures total par serveur

    
    query = (Stats # Somme des secondes pour chaque serveur (tous les utilisateurs)
             .select(Stats.server_id, fn.SUM(Stats.seconds).alias('total_seconds'))
             .group_by(Stats.server_id)
             .order_by(Stats.server_id))

    labels = []
    hours = []

    for row in query:
        # Récupérer le nom du serveur
        server = Servers.get_or_none(Servers.server_id == row.server_id)
        server_name = server.servername if server else str(row.server_id)
        labels.append(server_name)
        hours.append(round(row.total_seconds / 3600, 1))  # conversion en heures

    chart_data_json_pie_server = json.dumps({
        "labels": labels,
        "hours": hours
    })

    return render_template("graphs.html", chart_data_json=chart_data_json,monthly_chart_data_json=monthly_chart_data_json,chart_data_json_pie_server=chart_data_json_pie_server)
