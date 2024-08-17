FROM python:3.10

# Supervisord installation
RUN apt-get update && apt-get install -y supervisor

WORKDIR /app

COPY . .

RUN mkdir -p data && chmod 777 data

# Requirement for python
RUN pip install discord.py
RUN pip install Flask


EXPOSE 5002

ARG DISCORD_TOKEN

CMD ["/usr/bin/supervisord", "-c", "/app/supervisord.conf"]
