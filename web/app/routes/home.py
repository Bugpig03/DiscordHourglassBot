from flask import Blueprint, render_template, request, flash, redirect, url_for

home_bp = Blueprint("home", __name__)

@home_bp.route("/", methods=["GET"])
def home():
    return render_template("home.html")

@home_bp.route("/commands", methods=["GET"])
def commands():
    return render_template("commands.html")