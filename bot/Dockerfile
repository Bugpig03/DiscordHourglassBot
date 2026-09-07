#Docker file - DISCORD BOT APP

FROM python:3.12.4

WORKDIR /app

# Installer les dépendances
RUN pip install --no-cache-dir discord.py psycopg2 aiohttp

COPY . /app

CMD ["python", "main.py"]
