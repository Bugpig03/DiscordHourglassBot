# DESCRIPTION
Gimme the time and stats.... I need to know how much time I've wasted on this Discord server.

# DOCKER INSTALLATION
Configuration setup for Docker deployment

### Docker Arguments to Define

- **DISCORD_TOKEN**: → Your Discord token
- **POSTGRESQL_DBNAME**: → Your PostgreSQL database name
- **POSTGRESQL_USER**: → Your PostgreSQL user
- **POSTGRESQL_PASSWORD**: → Your PostgreSQL password
- **POSTGRESQL_HOST**: → Host of your PostgreSQL server
- **POSTGRESQL_PORT**: → Port number of your PostgreSQL server


# Hourglass - Version History

## Version 2.1.1 - Fix alltop command - 15/09/2024
- The display of seconds for the "alltop" command was incorrect

## Version 2.1.0 - Bot Page and More Stats! - 09/09/2024
- Added a new bot page on the website to display all bot statistics.
- Introduced new user count and profile count statistics.
- Made minor improvements to the website.
- Database stats (size and transactions)

## Version 2.0.0 - Database System and Username Display - 03/09/2024
- Migrated the database system to PostgreSQL.
- Implemented a TOP 25 leaderboard on the website with username display.
- Fixed the SPAM message issue.

## Version 1.2.0 - Web Interface - 18/08/2024
- Launched the website to view bot statistics.
- Added the `server` command to get server stats.
- Implemented a parallel processing system for the Discord bot and web.

## Version 1.1.0 - Cross-Server Stats - 20/06/2024
- Added the `allstats` command for cross-server statistics.
- Added the `top` command to get the top 10 users.
- Added the `alltop` command for cross-server top statistics.
- Added the `aide` command for help.
- Fixed message formatting issues in Hourglass responses.

## Version 1.0.0 - Initial Release - 28/04/2024
- Basic `stats` command for displaying user statistics.

## MADE BY
ChatGPT, Mike and BugPig
