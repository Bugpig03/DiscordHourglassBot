FROM python:3.10

WORKDIR /app

RUN pip install discord.py

RUN mkdir -p data && chmod 777 data

COPY . .

ARG DISCORD_TOKEN

CMD ["python", "bot/main.py"]
