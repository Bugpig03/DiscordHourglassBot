# ==============================================================================
# HOURGLASS BOT v3.0.2 (Go Edition) - Production Dockerfile
# Multi-stage build for minimal image size and maximum performance
# ==============================================================================

# Stage 1: Build binary
FROM golang:1.24-alpine AS builder

WORKDIR /build
ENV GOTOOLCHAIN=auto

# Installer git si nécessaire pour certaines dépendances
RUN apk add --no-cache git ca-certificates

# Cache des dépendances Go
COPY go.mod go.sum ./
RUN go mod download

# Copier l'intégralité du code source
COPY . .

# Compilation binaire statique optimisée pour Linux
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o hourglass-bot main.go

# Stage 2: Runtime image minimale
FROM alpine:3.20

WORKDIR /app

# Installer les certificats SSL, fuseaux horaires et les polices DejaVu
RUN apk add --no-cache ca-certificates tzdata ttf-dejavu

# Copier le binaire compilé depuis l'étape de build
COPY --from=builder /build/hourglass-bot /app/hourglass-bot

# Copier le dossier de polices pour la génération des cartes d'activité
COPY fonts/ /app/fonts/

# Exécution du bot
ENTRYPOINT ["/app/hourglass-bot"]
