"""Former members directory (/users), merged into the members page in v3."""

from flask import Blueprint, redirect, request, url_for

users_bp = Blueprint("users", __name__)


@users_bp.route("/users", methods=["GET"])
def users():
    """Permanent redirect to /members, keeping the search and the former alphabetical order."""
    args = request.args.to_dict()
    args.setdefault("sort_by", "name")
    return redirect(url_for("top.top_users", **args), code=301)
