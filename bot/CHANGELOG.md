# Hourglass - Discord BOT - CHANGELOG

## Version 2.4.2 - !stats update avatar - 17/01/2025

    - Fix duplication bug of users in DB

## Version 2.4.1 - !stats update avatar - 16/01/2025

    - command !stats now update avatar of tag user

## Version 2.4.0 - Avatar Update and time format ! - 15/01/2025

- Now saved avatar servers and users on DB
- Update time format to h:min:s
- Security improvement with empty commit in DB
- BDD change with news colums for avatars
- Change name of for table usernames to users and servernames table to servers

## Version 2.3.0 - Serveur Name - 18/10/2024

- Server name are now saved.

## Version 2.2.1 - Creation time - 05/10/2024

- Now retrieve the creation date of each profile.

## Version 2.2.0 - Split discord bot and web app - 05/10/2024

- Split the project into two separate parts for better modularity.
- The web version has its own changelog and starts at version 1.0.0

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
