from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.database import db, Users, Servers, HistoricalStats, Stats
from peewee import fn

graphs_bp = Blueprint("graphs", __name__)

@graphs_bp.route("/graphs", methods=["GET"])
def graphs():
    return render_template("graphs.html")
