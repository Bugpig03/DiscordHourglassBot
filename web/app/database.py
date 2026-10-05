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
    CompositeKey,
    BooleanField
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
    is_bot_present = BooleanField(default=True)
    first_tracked_at = DateTimeField(default=datetime.now)
    left_at = DateTimeField(null=True)

    class Meta:
        table_name = "servers"


class PresenceHistory(BaseModel):
    """Hourly/periodic snapshot of server and global presence status over time."""

    id = AutoField()
    server_id = BigIntegerField(null=True, index=True)
    online_count = IntegerField(default=0)
    idle_count = IntegerField(default=0)
    dnd_count = IntegerField(default=0)
    offline_count = IntegerField(default=0)
    recorded_at = DateTimeField(default=datetime.now, index=True)

    class Meta:
        table_name = "presence_history"


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


class Channels(BaseModel):
    """Discord channels metadata (voice and text)."""

    channel_id = BigIntegerField(primary_key=True)
    server_id = BigIntegerField(index=True)
    name = CharField(max_length=255)
    type = CharField(max_length=50)
    last_updated = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "channels"


class VoiceSessions(BaseModel):
    """Individual voice sessions with live tracking support."""

    session_id = AutoField()
    user_id = BigIntegerField(index=True)
    server_id = BigIntegerField(index=True)
    channel_id = BigIntegerField(null=True, index=True)
    joined_at = DateTimeField(index=True)
    left_at = DateTimeField(null=True, index=True)
    duration_seconds = IntegerField(default=0)
    last_heartbeat = DateTimeField(null=True)
    is_legacy = BooleanField(default=False)
    is_streaming = BooleanField(default=False)
    is_camera_on = BooleanField(default=False)

    class Meta:
        table_name = "voice_sessions"


class MessageEvents(BaseModel):
    """Individual or batched timestamped message occurrences."""

    event_id = AutoField()
    user_id = BigIntegerField(index=True)
    server_id = BigIntegerField(index=True)
    channel_id = BigIntegerField(null=True, index=True)
    created_at = DateTimeField(default=datetime.now, index=True)
    count = IntegerField(default=1)
    is_legacy = BooleanField(default=False)

    class Meta:
        table_name = "message_events"


class LiveServerStatus(BaseModel):
    """Real-time presence snapshot per guild."""

    server_id = BigIntegerField(primary_key=True)
    online_count = IntegerField(default=0)
    idle_count = IntegerField(default=0)
    dnd_count = IntegerField(default=0)
    offline_count = IntegerField(default=0)
    voice_count = IntegerField(default=0)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "live_server_status"


class UserPresence(BaseModel):
    """Real-time presence status per user."""

    user_id = BigIntegerField(primary_key=True)
    status = CharField(max_length=50, default="offline")
    last_updated = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "user_presence"



def init_app(app):
    """Register database connection handlers with the Flask application lifecycle."""

    @app.before_request
    def _db_connect():
        if db.is_closed():
            db.connect()
            try:
                db.execute_sql("SET TIME ZONE 'UTC'")
            except Exception:
                pass

    @app.teardown_request
    def _db_close(exc):
        if not db.is_closed():
            db.close()

