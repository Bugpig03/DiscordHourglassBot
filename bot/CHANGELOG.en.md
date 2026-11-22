# Hourglass - Discord BOT - CHANGELOG (English)

English version of the changelog, posted with the French one in the patch notes of the official Discord server.
Older versions only exist in French (CHANGELOG.md).

## Version 3.13.0 - Patch Notes on the Official Server - 22/11/2026

- **Automatic patch notes**: every new version of the website and of the bot is posted on the official Discord server, in the channel chosen on the website's admin page.
  - Posted within a minute of the deploy: one message per version, English first, then French.
  - A "🌐 Website" or "🤖 Bot" title with the version number and a link to the full changelog.
  - An optional role to mention (never @everyone or @here).
- **Announcement channel**: the message is also published, so the servers following the channel receive it automatically.
- **Never twice**, even after a restart. Nothing old is posted when they are turned on. A version skipped by a quick deploy is still announced.
- A changelog too long for one Discord message is split between two lines, over several messages.
- The bot's changelogs (English and French) are built into the bot: it knows its own news.
- New tables created automatically (or by `database/migrations/2026-11-22_bot_v3.13.0_patchnotes.sql`).
