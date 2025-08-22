#Docker file - WEB APP

FROM python:3.12.4

WORKDIR /app

# Installer les dépendances en premier pour profiter du cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 5002

CMD ["python", "run.py"]
