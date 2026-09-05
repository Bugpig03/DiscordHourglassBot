"""Database configuration and ORM model definitions using Peewee."""

from datetime import datetime
from peewee import (
    Model,
    PostgresqlDatabase,
    BigIntegerField,
    CharField,
    IntegerField,
    DateTimeField,
    AutoField,
    CompositeKey
)
from app.config import Config

# Initialize PostgreSQL database connection instance
db = PostgresqlDatabase(
    Config.DB_NAME,
    user=Config.DB_USER,
    password=Config.DB_PASSWORD,
    host=Config.DB_HOST,
    port=Config.DB_PORT
)


class BaseModel(Model):
    """Base model class tying Peewee models to the shared PostgreSQL database."""

    class Meta:
        database = db


class Users(BaseModel):
    """Discord user metadata."""

    user_id = BigIntegerField(primary_key=True)
    username = CharField(max_length=255, null=True, index=True)
    avatar = CharField(max_length=255, null=True)

    class Meta:
        table_name = "users"


class Servers(BaseModel):
    """Discord server (guild) metadata."""

    server_id = BigIntegerField(primary_key=True)
    servername = CharField(max_length=255, null=True, index=True)
    avatar = CharField(max_length=255, null=True)

    class Meta:
        table_name = "servers"


class HistoricalStats(BaseModel):
    """Daily snapshot of user activity on servers for time-series analysis and rankings."""

    id = AutoField()
    user_id = BigIntegerField(null=True, index=True)
    server_id = BigIntegerField(null=True, index=True)
    messages = IntegerField(default=0)
    seconds = IntegerField(default=0)
    created_at = DateTimeField(default=datetime.now, index=True)

    class Meta:
        table_name = "historical_stats"


class Stats(BaseModel):
    """Current cumulative statistics per user and server pair."""

    user_id = BigIntegerField(index=True)
    server_id = BigIntegerField(index=True)
    messages = IntegerField(default=0)
    seconds = IntegerField(default=0)
    score = IntegerField(default=0)
    date_creation = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "stats"
        primary_key = CompositeKey("user_id", "server_id")


def init_app(app):
    """Register database connection handlers with the Flask application lifecycle."""

    @app.before_request
    def _db_connect():
        if db.is_closed():
            db.connect()

    @app.teardown_request
    def _db_close(exc):
        if not db.is_closed():
            db.close()

