# ==============================================================================
# HOURGLASS BOT (Go Edition) - Production Dockerfile
# Multi-stage build for minimal image size and maximum performance
# ==============================================================================

# Stage 1: Build binary
FROM golang:1.26-alpine AS builder

WORKDIR /build
ENV GOTOOLCHAIN=auto

# Installer git si nécessaire pour certaines dépendances
RUN apk add --no-cache git ca-certificates

# Cache des dépendances Go
COPY go.mod go.sum ./
RUN go mod download

# Copier l'intégralité du code source
COPY . .

# Version, date de build et commit affichés par /version (passés par GitHub Actions ; build local : valeurs du code)
ARG BOT_VERSION=""
ARG BUILD_DATE=""
ARG GIT_COMMIT=""

# Compilation binaire statique optimisée pour Linux
RUN LDFLAGS="-s -w" &&     if [ -n "$BOT_VERSION" ]; then LDFLAGS="$LDFLAGS -X hourglass-bot/handlers.Version=$BOT_VERSION"; fi &&     if [ -n "$BUILD_DATE" ]; then LDFLAGS="$LDFLAGS -X hourglass-bot/handlers.BuildDate=$BUILD_DATE"; fi &&     if [ -n "$GIT_COMMIT" ]; then LDFLAGS="$LDFLAGS -X hourglass-bot/handlers.Commit=$GIT_COMMIT"; fi &&     CGO_ENABLED=0 GOOS=linux go build -ldflags="$LDFLAGS" -o hourglass-bot main.go

# Stage 2: Runtime image minimale
FROM alpine:3.20

WORKDIR /app

# Installer les certificats SSL et les fuseaux horaires (les cartes sont dessinées par le site web)
RUN apk add --no-cache ca-certificates tzdata

# Copier le binaire compilé depuis l'étape de build
COPY --from=builder /build/hourglass-bot /app/hourglass-bot

# Exécution du bot
ENTRYPOINT ["/app/hourglass-bot"]
