"""Gamification system for Hourglass Web: XP, Levels, and Real-time Badges computed purely in memory."""

from datetime import datetime, timezone
from typing import Any


def calculate_user_xp_and_level(total_seconds: int, total_messages: int) -> dict[str, Any]:
    """Calculate user XP, level, title, and progress percentage based on voice time and messages.
    
    Formula:
      - 1 minute in voice = 1 XP
      - 1 text message = 5 XP
      - Level curve: quadratic progression where Level = int((XP / 100) ** 0.5) + 1
    """
    total_seconds = max(0, total_seconds or 0)
    total_messages = max(0, total_messages or 0)

    voice_minutes = total_seconds // 60
    total_xp = voice_minutes + (total_messages * 5)

    level = int((total_xp / 100) ** 0.5) + 1
    current_level_base_xp = ((level - 1) ** 2) * 100
    next_level_target_xp = (level ** 2) * 100
    xp_needed_for_level = next_level_target_xp - current_level_base_xp
    xp_progress_in_level = total_xp - current_level_base_xp

    if xp_needed_for_level > 0:
        progress_percent = min(100.0, max(0.0, round((xp_progress_in_level / xp_needed_for_level) * 100, 1)))
    else:
        progress_percent = 100.0

    # Dynamic honor titles depending on level
    titles = {
        "fr": [
            (50, "Légende Hourglass"),
            (40, "Grand Maître"),
            (30, "Vétéran de l'Éther"),
            (20, "Expert des Ondes"),
            (10, "Membre Confirmé"),
            (5, "Initié Actif"),
            (1, "Novice Curieux"),
        ],
        "en": [
            (50, "Hourglass Legend"),
            (40, "Grandmaster"),
            (30, "Aether Veteran"),
            (20, "Voice Expert"),
            (10, "Senior Member"),
            (5, "Active Initiate"),
            (1, "Curious Novice"),
        ]
    }

    def get_title(lang: str = "fr") -> str:
        lang_titles = titles.get(lang, titles["fr"])
        for min_lvl, title_name in lang_titles:
            if level >= min_lvl:
                return title_name
        return "Membre" if lang == "fr" else "Member"

    return {
        "total_xp": total_xp,
        "level": level,
        "title_fr": get_title("fr"),
        "title_en": get_title("en"),
        "current_level_base_xp": current_level_base_xp,
        "next_level_target_xp": next_level_target_xp,
        "xp_progress_in_level": xp_progress_in_level,
        "xp_needed_for_level": xp_needed_for_level,
        "progress_percent": progress_percent,
    }


def _make_badge_svg(inner_svg: str) -> str:
    """Wrap inner SVG paths into a normalized SVG icon string."""
    return f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{inner_svg}</svg>'


def calculate_user_badges(stats: dict[str, Any], lang: str = "fr") -> list[dict[str, Any]]:
    """Compute live user badges based on current statistics without modifying the database.
    
    Each badge contains:
      - id: unique slug
      - svg_path: inner SVG elements (paths, circles, polylines)
      - icon: full standalone SVG string for HTML rendering
      - name: localized name
      - description: localized criteria
      - rarity: 'common', 'rare', 'epic', 'legendary'
      - unlocked: boolean
      - current: current progression value
      - target: required threshold
      - progress_percent: completion percentage (0 to 100)
    """
    total_seconds = stats.get("total_seconds") or 0
    total_hours = total_seconds / 3600.0
    total_messages = stats.get("total_message") or 0
    rank = stats.get("rank")
    servers = stats.get("user_servers_stats") or []
    server_count = len(servers)
    last_30d_seconds = stats.get("total_time_last_30d") or 0
    last_30d_hours = last_30d_seconds / 3600.0
    join_source = stats.get("raw_join_date") or stats.get("join_date")

    # Real-time level calculation from gamification engine
    user_xp_info = calculate_user_xp_and_level(total_seconds, total_messages)
    user_level = user_xp_info["level"]

    # Calculate days since earliest recorded activity
    days_since_join = 0
    if join_source:
        now_utc = datetime.now(timezone.utc)
        if isinstance(join_source, datetime):
            dt = join_source if join_source.tzinfo else join_source.replace(tzinfo=timezone.utc)
            days_since_join = max(0, (now_utc - dt).days)
        elif isinstance(join_source, str):
            try:
                dt = datetime.fromisoformat(join_source)
                dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
                days_since_join = max(0, (now_utc - dt).days)
            except Exception:
                days_since_join = 0

    is_fr = (lang == "fr")

    raw_badges = [
        # ===================================================================
        # 1. Progression Vocale
        # ===================================================================
        {
            "id": "voice_bronze",
            "svg_path": '<path d="M3 18v-6a9 9 0 0 1 18 0v6"/><path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"/>',
            "rarity": "common",
            "name": "Premiers Échos" if is_fr else "First Echoes",
            "description": "Passer au moins 1 heure en vocal" if is_fr else "Spend at least 1 hour in voice",
            "unlocked": total_hours >= 1.0,
            "current": round(total_hours, 1),
            "target": 1.0,
            "unit": "h",
        },
        {
            "id": "voice_silver",
            "svg_path": '<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/>',
            "rarity": "common",
            "name": "Habitué du Micro" if is_fr else "Mic Regular",
            "description": "Passer au moins 10 heures en vocal" if is_fr else "Spend at least 10 hours in voice",
            "unlocked": total_hours >= 10.0,
            "current": round(total_hours, 1),
            "target": 10.0,
            "unit": "h",
        },
        {
            "id": "voice_gold",
            "svg_path": '<path d="M4.9 19.1C1 15.2 1 8.8 4.9 4.9"/><path d="M7.8 16.2c-2.3-2.3-2.3-6.1 0-8.5"/><circle cx="12" cy="12" r="2"/><path d="M16.2 7.8c2.3 2.3 2.3 6.1 0 8.5"/><path d="M19.1 4.9C23 8.8 23 15.1 19.1 19.1"/>',
            "rarity": "rare",
            "name": "Voix d'Or" if is_fr else "Golden Voice",
            "description": "Passer au moins 50 heures en vocal" if is_fr else "Spend at least 50 hours in voice",
            "unlocked": total_hours >= 50.0,
            "current": round(total_hours, 1),
            "target": 50.0,
            "unit": "h",
        },
        {
            "id": "voice_centurion",
            "svg_path": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 11v2"/><path d="M12 9v6"/><path d="M15 11v2"/>',
            "rarity": "rare",
            "name": "Centurion Vocal" if is_fr else "Vocal Centurion",
            "description": "Atteindre 100 heures cumulées en salon vocal" if is_fr else "Accumulate 100 hours in voice channels",
            "unlocked": total_hours >= 100.0,
            "current": round(total_hours, 1),
            "target": 100.0,
            "unit": "h",
        },
        {
            "id": "voice_diamond",
            "svg_path": '<path d="M6 3h12l4 6-10 12L2 9z"/><path d="M11 3 8 9l4 12 4-12-3-6"/><path d="M2 9h20"/>',
            "rarity": "epic",
            "name": "Pilier Vocal" if is_fr else "Vocal Pillar",
            "description": "Accumuler plus de 200 heures en vocal" if is_fr else "Accumulate over 200 hours in voice",
            "unlocked": total_hours >= 200.0,
            "current": round(total_hours, 1),
            "target": 200.0,
            "unit": "h",
        },
        {
            "id": "voice_titan",
            "svg_path": '<path d="m8 3 4 8 5-5 5 15H2L8 3z"/><path d="m4.14 15 .76-1.55L8 10l3.86 7.72"/>',
            "rarity": "epic",
            "name": "Titan Vocal" if is_fr else "Voice Titan",
            "description": "Dépasser le seuil titanesque des 500 heures en vocal" if is_fr else "Exceed 500 hours in voice channels",
            "unlocked": total_hours >= 500.0,
            "current": round(total_hours, 1),
            "target": 500.0,
            "unit": "h",
        },
        {
            "id": "voice_legend",
            "svg_path": '<path d="m2 4 3 12h14l3-12-6 7-4-7-4 7-6-7zm3 16h14"/>',
            "rarity": "legendary",
            "name": "Maître de la Voix" if is_fr else "Voice Master",
            "description": "Atteindre 1 000 heures en vocal" if is_fr else "Reach 1,000 hours in voice",
            "unlocked": total_hours >= 1000.0,
            "current": round(total_hours, 1),
            "target": 1000.0,
            "unit": "h",
        },

        # ===================================================================
        # 2. Progression Messages & Textes
        # ===================================================================
        {
            "id": "msg_novice",
            "svg_path": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
            "rarity": "common",
            "name": "Premiers Mots" if is_fr else "First Words",
            "description": "Envoyer au moins 25 messages" if is_fr else "Send at least 25 messages",
            "unlocked": total_messages >= 25,
            "current": total_messages,
            "target": 25,
            "unit": "msgs",
        },
        {
            "id": "msg_talkative",
            "svg_path": '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>',
            "rarity": "common",
            "name": "Bavard" if is_fr else "Chatterbox",
            "description": "Envoyer au moins 250 messages" if is_fr else "Send at least 250 messages",
            "unlocked": total_messages >= 250,
            "current": total_messages,
            "target": 250,
            "unit": "msgs",
        },
        {
            "id": "msg_chronicler",
            "svg_path": '<path d="M12 19l7-7 3 3-7 7-3-3z"/><path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z"/><circle cx="11" cy="11" r="2"/>',
            "rarity": "common",
            "name": "Chroniqueur" if is_fr else "Chronicler",
            "description": "Partager au moins 500 messages écrits" if is_fr else "Share at least 500 text messages",
            "unlocked": total_messages >= 500,
            "current": total_messages,
            "target": 500,
            "unit": "msgs",
        },
        {
            "id": "msg_eloquent",
            "svg_path": '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/><line x1="8" y1="7" x2="16" y2="7"/><line x1="8" y1="11" x2="14" y2="11"/>',
            "rarity": "rare",
            "name": "Éloquent" if is_fr else "Eloquent",
            "description": "Envoyer au moins 1 000 messages" if is_fr else "Send at least 1,000 messages",
            "unlocked": total_messages >= 1000,
            "current": total_messages,
            "target": 1000,
            "unit": "msgs",
        },
        {
            "id": "msg_typist",
            "svg_path": '<rect width="20" height="16" x="2" y="4" rx="2"/><path d="M6 8h.01M10 8h.01M14 8h.01M18 8h.01M6 12h.01M10 12h.01M14 12h.01M18 12h.01M7 16h10"/>',
            "rarity": "rare",
            "name": "Dactylo d'Élite" if is_fr else "Elite Typist",
            "description": "Écrire plus de 2 500 messages sur Discord" if is_fr else "Write over 2,500 messages on Discord",
            "unlocked": total_messages >= 2500,
            "current": total_messages,
            "target": 2500,
            "unit": "msgs",
        },
        {
            "id": "msg_legend",
            "svg_path": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="m13 7-3 4h4l-2 4"/>',
            "rarity": "epic",
            "name": "Légende du Clavier" if is_fr else "Keyboard Legend",
            "description": "Envoyer au moins 5 000 messages" if is_fr else "Send at least 5,000 messages",
            "unlocked": total_messages >= 5000,
            "current": total_messages,
            "target": 5000,
            "unit": "msgs",
        },
        {
            "id": "msg_overlord",
            "svg_path": '<path d="M14.5 17.5 3 6V3h3l11.5 11.5"/><path d="m13 19 6-6"/><path d="m16 16 4 4"/><path d="m19 21 2-2"/>',
            "rarity": "legendary",
            "name": "Seigneur des Textes" if is_fr else "Text Overlord",
            "description": "Franchir le cap titanesque des 10 000 messages" if is_fr else "Surpass the colossal mark of 10,000 messages",
            "unlocked": total_messages >= 10000,
            "current": total_messages,
            "target": 10000,
            "unit": "msgs",
        },

        # ===================================================================
        # 3. Paliers de Niveau & Expérience (XP)
        # ===================================================================
        {
            "id": "level_5",
            "svg_path": '<path d="M12 2v8"/><path d="m4.93 10.93 5.66-5.66"/><path d="M2 18h8"/><path d="M20 18c0-4.4-3.6-8-8-8s-8 3.6-8 8h16Z"/>',
            "rarity": "common",
            "name": "Initié" if is_fr else "Initiate",
            "description": "Atteindre le niveau 5 Hourglass" if is_fr else "Reach Hourglass Level 5",
            "unlocked": user_level >= 5,
            "current": user_level,
            "target": 5,
            "unit": "lvl",
        },
        {
            "id": "level_10",
            "svg_path": '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
            "rarity": "rare",
            "name": "Explorateur Émérite" if is_fr else "Proven Explorer",
            "description": "Atteindre le niveau 10 Hourglass" if is_fr else "Reach Hourglass Level 10",
            "unlocked": user_level >= 10,
            "current": user_level,
            "target": 10,
            "unit": "lvl",
        },
        {
            "id": "level_15",
            "svg_path": '<circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/>',
            "rarity": "rare",
            "name": "Aventurier Confirmé" if is_fr else "Seasoned Adventurer",
            "description": "Atteindre le niveau 15 Hourglass" if is_fr else "Reach Hourglass Level 15",
            "unlocked": user_level >= 15,
            "current": user_level,
            "target": 15,
            "unit": "lvl",
        },
        {
            "id": "level_20",
            "svg_path": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><circle cx="12" cy="11" r="3"/>',
            "rarity": "epic",
            "name": "Vétéran Aguerri" if is_fr else "Seasoned Veteran",
            "description": "Atteindre le niveau 20 Hourglass" if is_fr else "Reach Hourglass Level 20",
            "unlocked": user_level >= 20,
            "current": user_level,
            "target": 20,
            "unit": "lvl",
        },
        {
            "id": "level_30",
            "svg_path": '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
            "rarity": "epic",
            "name": "Grand Maître" if is_fr else "Grandmaster",
            "description": "Atteindre le niveau 30 Hourglass" if is_fr else "Reach Hourglass Level 30",
            "unlocked": user_level >= 30,
            "current": user_level,
            "target": 30,
            "unit": "lvl",
        },
        {
            "id": "level_50",
            "svg_path": '<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3z"/><path d="M5 3v4"/><path d="M3 5h4"/><path d="M19 17v4"/><path d="M17 19h4"/>',
            "rarity": "legendary",
            "name": "Divinité d'Hourglass" if is_fr else "Hourglass Divinity",
            "description": "Atteindre le niveau légendaire 50" if is_fr else "Reach the legendary Level 50",
            "unlocked": user_level >= 50,
            "current": user_level,
            "target": 50,
            "unit": "lvl",
        },

        # ===================================================================
        # 4. Classement & Compétitivité
        # ===================================================================
        {
            "id": "rank_podium",
            "svg_path": '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.45 1-1 1H8v4h8v-4h-1c-.55 0-1-.45-1-1v-2.34"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>',
            "rarity": "legendary",
            "name": "Sur le Podium" if is_fr else "On the Podium",
            "description": "Faire partie du Top 3 global Hourglass" if is_fr else "Rank in the global Top 3 of Hourglass",
            "unlocked": (rank is not None and 1 <= rank <= 3),
            "current": f"#{rank}" if rank else "-",
            "target": "Top 3",
            "unit": "",
        },
        {
            "id": "rank_top10",
            "svg_path": '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
            "rarity": "epic",
            "name": "Élite du Top 10" if is_fr else "Top 10 Elite",
            "description": "Atteindre le Top 10 des membres les plus actifs" if is_fr else "Reach the Top 10 of most active members",
            "unlocked": (rank is not None and 1 <= rank <= 10),
            "current": f"#{rank}" if rank else "-",
            "target": "Top 10",
            "unit": "",
        },
        {
            "id": "rank_top50",
            "svg_path": '<path d="M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z"/><path d="m9 12 2 2 4-4"/>',
            "rarity": "rare",
            "name": "Membre d'Élite" if is_fr else "Elite Member",
            "description": "Faire partie du Top 50 global" if is_fr else "Rank in the global Top 50",
            "unlocked": (rank is not None and 1 <= rank <= 50),
            "current": f"#{rank}" if rank else "-",
            "target": "Top 50",
            "unit": "",
        },

        # ===================================================================
        # 5. Serveurs & Exploration Sociale
        # ===================================================================
        {
            "id": "social_explorer",
            "svg_path": '<circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>',
            "rarity": "common",
            "name": "Explorateur" if is_fr else "Explorer",
            "description": "Être actif sur au moins 2 serveurs différents" if is_fr else "Be active on at least 2 different servers",
            "unlocked": server_count >= 2,
            "current": server_count,
            "target": 2,
            "unit": "serveurs" if is_fr else "servers",
        },
        {
            "id": "social_nomad",
            "svg_path": '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
            "rarity": "rare",
            "name": "Nomade Discord" if is_fr else "Discord Nomad",
            "description": "Voyager et participer sur au moins 3 serveurs" if is_fr else "Travel and participate on at least 3 servers",
            "unlocked": server_count >= 3,
            "current": server_count,
            "target": 3,
            "unit": "serveurs" if is_fr else "servers",
        },
        {
            "id": "social_globetrotter",
            "svg_path": '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/>',
            "rarity": "rare",
            "name": "Citoyen du Monde" if is_fr else "Globetrotter",
            "description": "Être présent et actif sur 4 serveurs ou plus" if is_fr else "Be active on 4 or more servers",
            "unlocked": server_count >= 4,
            "current": server_count,
            "target": 4,
            "unit": "serveurs" if is_fr else "servers",
        },
        {
            "id": "social_ambassador",
            "svg_path": '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" x2="15.42" y1="13.51" y2="17.49"/><line x1="15.41" x2="8.59" y1="6.51" y2="10.49"/>',
            "rarity": "epic",
            "name": "Ambassadeur" if is_fr else "Ambassador",
            "description": "Tisser des liens sur 6 serveurs différents ou plus" if is_fr else "Connect across 6 or more different servers",
            "unlocked": server_count >= 6,
            "current": server_count,
            "target": 6,
            "unit": "serveurs" if is_fr else "servers",
        },

        # ===================================================================
        # 6. Attachement & Fidélité
        # ===================================================================
        {
            "id": "loyalty_member",
            "svg_path": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
            "rarity": "common",
            "name": "Membre Titulaire" if is_fr else "Established Member",
            "description": "Inscrit et suivi par Hourglass depuis plus de 30 jours" if is_fr else "Tracked by Hourglass for more than 30 days",
            "unlocked": days_since_join >= 30,
            "current": days_since_join,
            "target": 30,
            "unit": "j" if is_fr else "d",
        },
        {
            "id": "loyalty_veteran",
            "svg_path": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/>',
            "rarity": "rare",
            "name": "Fidèle Compagnon" if is_fr else "Faithful Companion",
            "description": "Inscrit et suivi par Hourglass depuis plus de 60 jours" if is_fr else "Tracked by Hourglass for more than 60 days",
            "unlocked": days_since_join >= 60,
            "current": days_since_join,
            "target": 60,
            "unit": "j" if is_fr else "d",
        },
        {
            "id": "loyalty_pioneer",
            "svg_path": '<path d="M5 22h14"/><path d="M5 2h14"/><path d="M17 22v-4.172a2 2 0 0 0-.586-1.414L12 12l-4.414 4.414A2 2 0 0 0 7 17.828V22"/><path d="M7 2v4.172a2 2 0 0 0 .586 1.414L12 12l4.414-4.414A2 2 0 0 0 17 6.172V2"/>',
            "rarity": "epic",
            "name": "Pionnier Hourglass" if is_fr else "Hourglass Pioneer",
            "description": "Présent aux côtés d'Hourglass depuis plus de 120 jours" if is_fr else "Standing with Hourglass for over 120 days",
            "unlocked": days_since_join >= 120,
            "current": days_since_join,
            "target": 120,
            "unit": "j" if is_fr else "d",
        },
        {
            "id": "loyalty_ancestor",
            "svg_path": '<path d="M12 2a10 10 0 0 0-7.07 17.07l2.83-2.83a6 6 0 0 1 0-8.48l1.41-1.42"/><path d="M12 2a10 10 0 0 1 7.07 17.07l-2.83-2.83a6 6 0 0 0 0-8.48l-1.41-1.42"/><path d="M12 8v8"/><path d="m9 13 3 3 3-3"/>',
            "rarity": "legendary",
            "name": "Doyen de la Communauté" if is_fr else "Community Elder",
            "description": "Membre légendaire suivi depuis plus de 250 jours" if is_fr else "Legendary member tracked for over 250 days",
            "unlocked": days_since_join >= 250,
            "current": days_since_join,
            "target": 250,
            "unit": "j" if is_fr else "d",
        },

        # ===================================================================
        # 7. Dynamisme, Régularité & Polyvalence
        # ===================================================================
        {
            "id": "activity_warmup",
            "svg_path": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
            "rarity": "common",
            "name": "En Plein Échauffement" if is_fr else "Warming Up",
            "description": "Passer au moins 5 heures en vocal ce mois-ci" if is_fr else "Spend at least 5 voice hours in the last 30 days",
            "unlocked": last_30d_hours >= 5.0,
            "current": round(last_30d_hours, 1),
            "target": 5.0,
            "unit": "h",
        },
        {
            "id": "activity_hyperactive",
            "svg_path": '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
            "rarity": "rare",
            "name": "Hyperactif" if is_fr else "Hyperactive",
            "description": "Cumuler plus de 15 heures en vocal ce mois-ci" if is_fr else "Over 15 voice hours in the last 30 days",
            "unlocked": last_30d_hours >= 15.0,
            "current": round(last_30d_hours, 1),
            "target": 15.0,
            "unit": "h",
        },
        {
            "id": "activity_monthly_champ",
            "svg_path": '<circle cx="12" cy="8" r="6"/><path d="m15.477 12.89 1.515 8.526a.5.5 0 0 1-.81.47l-4.182-3.137-4.182 3.137a.5.5 0 0 1-.81-.47l1.515-8.526"/>',
            "rarity": "epic",
            "name": "Champion du Mois" if is_fr else "Monthly Champion",
            "description": "Totaliser plus de 40 heures de vocal au cours des 30 derniers jours" if is_fr else "Over 40 voice hours accumulated in the last 30 days",
            "unlocked": last_30d_hours >= 40.0,
            "current": round(last_30d_hours, 1),
            "target": 40.0,
            "unit": "h",
        },
        {
            "id": "versatile",
            "svg_path": '<path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>',
            "rarity": "rare",
            "name": "Polyvalent" if is_fr else "Versatile",
            "description": "Au moins 10 heures en vocal ET 100 messages" if is_fr else "At least 10 hours in voice AND 100 messages",
            "unlocked": (total_hours >= 10.0 and total_messages >= 100),
            "current": f"{round(total_hours, 1)}h / {total_messages}m",
            "target": "10h / 100m",
            "unit": "",
        },
        {
            "id": "hybrid_master",
            "svg_path": '<path d="M18.178 8c5.096 0 5.096 8 0 8-5.095 0-7.133-8-12.739-8-4.585 0-4.585 8 0 8 5.606 0 7.644-8 12.74-8z"/>',
            "rarity": "epic",
            "name": "Maître Hybride" if is_fr else "Hybrid Master",
            "description": "Cumuler plus de 50 heures en vocal ET plus de 500 messages" if is_fr else "Accumulate over 50 voice hours AND over 500 messages",
            "unlocked": (total_hours >= 50.0 and total_messages >= 500),
            "current": f"{round(total_hours, 1)}h / {total_messages}m",
            "target": "50h / 500m",
            "unit": "",
        },
        {
            "id": "all_rounder",
            "svg_path": '<circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/>',
            "rarity": "legendary",
            "name": "Virtuose Global" if is_fr else "All-Round Virtuoso",
            "description": "Cumuler au total plus de 100 heures en vocal ET plus de 1 000 messages" if is_fr else "Accumulate over 100 voice hours AND over 1,000 messages",
            "unlocked": (total_hours >= 100.0 and total_messages >= 1000),
            "current": f"{round(total_hours, 1)}h / {total_messages}m",
            "target": "100h / 1000m",
            "unit": "",
        },
    ]

    # Calculate completion percentage for progress bars and build SVG icons
    for b in raw_badges:
        b["icon"] = _make_badge_svg(b.get("svg_path", ""))
        if b["unlocked"]:
            b["progress_percent"] = 100.0
        elif isinstance(b["current"], (int, float)) and isinstance(b["target"], (int, float)) and b["target"] > 0:
            b["progress_percent"] = min(99.0, max(0.0, round((b["current"] / b["target"]) * 100, 1)))
        else:
            b["progress_percent"] = 0.0

    return raw_badges
