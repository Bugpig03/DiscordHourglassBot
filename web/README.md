# WEB APP

## Description

A web application to easily view statistics from the Discord bot.

## Deployment

To deploy, use the Docker image: `bugpig/hourglass_web`

### Environment Variables

Set the following environment variables before running the application:

- **POSTGRESQL_DBNAME** → Your PostgreSQL database name
- **POSTGRESQL_USER** → Your PostgreSQL username
- **POSTGRESQL_PASSWORD** → Your PostgreSQL password
- **POSTGRESQL_HOST** → Host of your PostgreSQL server
- **POSTGRESQL_PORT** → Port number of your PostgreSQL server
- **SECRET_KEY** → Secret key for Flask