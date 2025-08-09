# database.py
from peewee import *
from datetime import datetime
import os

from dotenv import load_dotenv

load_dotenv()

print("DB:", os.getenv("POSTGRESQL_DBNAME"))
print("USER:", os.getenv("POSTGRESQL_USER"))
# --- Configuration de la connexion PostgreSQL ---
db = PostgresqlDatabase(
    os.getenv("POSTGRESQL_DBNAME"),
    user=os.getenv("POSTGRESQL_USER"),
    password=os.getenv("POSTGRESQL_PASSWORD"),
    host=os.getenv("POSTGRESQL_HOST"),
    port=os.getenv("POSTGRESQL_PORT")
)

# --- Base model pour centraliser la DB ---
class BaseModel(Model):
    class Meta:
        database = db

# --- Modèles ---
class Users(BaseModel):
    user_id = BigIntegerField(primary_key=True)
    username = CharField(max_length=255, null=True)
    avatar = CharField(max_length=255, null=True)

    class Meta:
        table_name = 'users'

class Servers(BaseModel):
    server_id = BigIntegerField(primary_key=True)
    servername = CharField(max_length=255, null=True)
    avatar = CharField(max_length=255, null=True)

    class Meta:
        table_name = 'servers'

class HistoricalStats(BaseModel):
    id = AutoField()
    user_id = BigIntegerField(null=True)
    server_id = BigIntegerField(null=True)
    messages = IntegerField(default=0)
    seconds = IntegerField(default=0)
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'historical_stats'

class Stats(BaseModel):
    user_id = BigIntegerField()
    server_id = BigIntegerField()
    messages = IntegerField(default=0)
    seconds = IntegerField(default=0)
    score = IntegerField(default=0)
    date_creation = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'stats'
        primary_key = CompositeKey('user_id', 'server_id')

# --- Fonction pour initialiser la base avec Flask ---
def init_app(app):
    @app.before_request
    def _db_connect():
        if db.is_closed():
            db.connect()

    @app.teardown_request
    def _db_close(exc):
        if not db.is_closed():
            db.close()
