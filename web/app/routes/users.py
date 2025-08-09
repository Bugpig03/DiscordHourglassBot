from flask import Blueprint, render_template, request, flash, redirect, url_for

users_bp = Blueprint("users", __name__)

@users_bp.route("/users", methods=["GET"])
def users():
    return render_template("users.html")