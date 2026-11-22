# Hourglass - WEB APP - CHANGELOG (English)

English version of the changelog, posted with the French one in the patch notes of the official Discord server.
Older versions only exist in French (CHANGELOG.md).

## Version 3.52.0 - Role Tiers Without Condition - 23/11/2026
- **Automatic roles**: a tier can now have no condition at all. Its role goes to every member, as soon as they join the server.
  - Just remove the last condition of the tier; a green line confirms it.
  - For example: @Newcomer for everyone, then 10 h in voice → @Regular. With "highest only", @Regular replaces @Newcomer.
  - A role with moderation rights is still refused in a tier without condition, so that no newcomer gets those rights.
- The member count next to each tier no longer includes bots, like the bot itself.

## Version 3.51.0 - New Help Page in Tabs - 23/11/2026
- **The Help page is rebuilt**, in 8 tabs: Get started, Commands, Progression, Badges, The website, Management, FAQ and Links.
  - The address keeps the open tab (for example `/supports#faq`), so a direct link can be shared. The old `#prestige`, `#titres` and `#badges` links still work.
- **Get started**: invite the bot in 3 steps, what is counted and what is not, and the permissions the bot uses.
- **Commands**: every command with its options, including `/vote` and the server choice of `/versus`.
- **The website**: profiles, customization, rankings, server pages, Versus, Timeline, charts and cards to share.
- **Management** (beta): level-up announcements, reports, automatic roles, private mode, log and managers.
- **FAQ**: 13 frequent questions, such as why voice hours did not move, whether the AFK channel counts, or what to check when a role is not given.
- Less text: the details sit in the "?" on hover. Available in all 12 languages.

## Version 3.50.0 - Server Management Open to Everyone (Beta) - 23/11/2026
- **Server management is open to every server owner**, in beta. Owners can hand it over to members of their choice.
  - The "Manage" button on the server page and the "My servers" menu show up for the owner and their managers.
  - It brings level-up announcements, automatic reports, automatic roles by tiers, private mode and the log.
- **"Beta" label** on the "Manage" and "My servers" pages, with a link to the Hourglass Discord server to report a bug or suggest an idea.

## Version 3.49.1 - Moderation Roles Allowed - 23/11/2026
- **Automatic roles**: roles that give moderation rights (Manage messages, Kick, Ban…) can now be given by a rule.
  - They are flagged in orange in the list.
  - Once chosen, a warning reminds that every member who meets the tier will get them.
  - Only the Administrator role and roles managed by an integration remain impossible.
- **Drop-down lists of the Manage page**: only the remark is colored, the name of the role or channel stays plain. For example "above the bot" and "the bot cannot write there" in red, "moderation rights" in orange, "administrator" in grey.

## Version 3.49.0 - Patch Notes on the Official Server - 22/11/2026
- **Admin, new "Patch notes" section**: the official server and the channel where the bot posts every new version of the website and of the bot, with its changelog in English and in French.
  - Choose what to announce (website and bot, or only one of them) and an optional role to mention.
  - Channels the bot cannot write in are flagged. An announcement channel (📢) lets other servers follow it.
  - The fields are locked while the patch notes are turned off.
  - **Test**: "Post the latest website version" or "… bot version" posts the latest version again, within a minute.
  - **Latest posts**: the versions posted, waiting or failed, with the reason.
- At startup, the website records the entries of its changelog. The bot posts them once the patch notes are turned on, and nothing old is ever posted.

## Version 3.48.1 - Settings Locked While Turned Off - 22/11/2026
- **"Manage" page**: a feature that is turned off (Levels, each Report, Roles) can no longer be changed until its switch is turned on. Its fields are greyed out and locked. The settings already made are kept and come back as soon as it is turned on.
