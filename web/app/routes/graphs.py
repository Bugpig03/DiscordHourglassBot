from flask import Blueprint, render_template, request, flash, redirect, url_for
from peewee import fn
from app.functions import get_first_of_month_hours_sum
import json

graphs_bp = Blueprint("graphs", __name__)

@graphs_bp.route("/graphs", methods=["GET"])
def graphs():
    data = get_first_of_month_hours_sum()

    chart_data_json = json.dumps({
    "labels": [row["month"] for row in data],
    "hours": [row["total_hours"] for row in data]
    })
    print(chart_data_json)
    return render_template("graphs.html", chart_data_json=chart_data_json)
