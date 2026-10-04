#!/usr/bin/env python3
"""
HOURGLASS v3.0 - Script de Migration des Données Historiques
============================================================
Ce script lit la table `stats` et l'ensemble des snapshots journaliers de
`historical_stats`, reconstitue fidèlement les sessions vocales et l'activité
de messages jour par jour dans le passé, et peuple les nouvelles tables
`voice_sessions` et `message_events` avec le flag `is_legacy = TRUE`.

Il garantit mathématiquement une parité à 100% (à la seconde près) avec les
totaux actuels de `stats`.

Usage :
    python migrate_v3.py --dry-run   # Simule et vérifie la parité sans écrire
    python migrate_v3.py --execute   # Applique la migration dans la base de données
"""

import os
import sys
import argparse
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_values

# Assurer l'encodage UTF-8 sous Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from dotenv import load_dotenv
    # Chercher le .env dans le dossier courant ou le dossier parent
    load_dotenv()
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass


def get_db_connection():
    db_name = os.environ.get("POSTGRESQL_DBNAME", "devhourglass")
    user = os.environ.get("POSTGRESQL_USER", "postgres")
    password = os.environ.get("POSTGRESQL_PASSWORD", "admin")
    host = os.environ.get("POSTGRESQL_HOST", "localhost")
    port = int(os.environ.get("POSTGRESQL_PORT", "5432"))

    return psycopg2.connect(
        dbname=db_name,
        user=user,
        password=password,
        host=host,
        port=port
    )


def apply_schema(conn):
    schema_path = os.path.join(os.path.dirname(__file__), "schema_v3.sql")
    if os.path.exists(schema_path):
        with open(schema_path, "r", encoding="utf-8") as f:
            sql = f.read()
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        print("✅ Schéma SQL v3.0 appliqué avec succès (tables et index créés).")
    else:
        print(f"⚠️ Fichier schema_v3.sql introuvable à {schema_path}.")


def run_migration(dry_run=True):
    print("=" * 70)
    mode_label = "SIMULATION (DRY-RUN - Aucune écriture)" if dry_run else "EXÉCUTION RÉELLE EN BDD"
    print(f"🚀 HOURGLASS v3.0 - Démarrage de la Migration : {mode_label}")
    print("=" * 70)

    conn = get_db_connection()
    try:
        if not dry_run:
            apply_schema(conn)

        with conn.cursor() as cur:
            # 1. Récupération de l'ensemble des paires (user_id, server_id) dans stats
            cur.execute("""
                SELECT user_id, server_id, messages, seconds, date_creation
                FROM stats
                ORDER BY user_id, server_id
            """)
            stats_rows = cur.fetchall()
            total_pairs = len(stats_rows)
            print(f"📊 {total_pairs} paires utilisateur-serveur trouvées dans la table 'stats'.")

            # 2. Récupération optimisée de tous les snapshots de historical_stats
            print("⏳ Chargement des snapshots historiques...")
            cur.execute("""
                SELECT user_id, server_id, created_at, messages, seconds
                FROM historical_stats
                ORDER BY user_id, server_id, created_at ASC
            """)
            hist_rows = cur.fetchall()
            print(f"📦 {len(hist_rows)} snapshots historiques chargés en mémoire.")

            # Grouper l'historique par (user_id, server_id)
            history_map = {}
            for u_id, s_id, c_at, m, s in hist_rows:
                key = (u_id, s_id)
                if key not in history_map:
                    history_map[key] = []
                history_map[key].append((c_at, m, s))

            voice_sessions_to_insert = []
            message_events_to_insert = []

            total_target_seconds = 0
            total_target_messages = 0
            total_reconstructed_seconds = 0
            total_reconstructed_messages = 0

            # 3. Calcul des sessions journalières par paire
            for idx, (user_id, server_id, target_msgs, target_secs, date_creation) in enumerate(stats_rows):
                total_target_seconds += target_secs
                total_target_messages += target_msgs

                hist = history_map.get((user_id, server_id), [])

                # --- Reconstruction Vocale ---
                if target_secs > 0:
                    raw_voice_deltas = []
                    prev_s = 0
                    prev_t = date_creation

                    for t, m, s in hist:
                        delta_s = max(0, s - prev_s)
                        if delta_s > 0:
                            raw_voice_deltas.append({
                                'joined_at': prev_t,
                                'left_at': t,
                                'raw_s': delta_s
                            })
                        prev_s = s
                        prev_t = t

                    sum_raw_s = sum(d['raw_s'] for d in raw_voice_deltas)

                    if sum_raw_s == 0:
                        voice_sessions_to_insert.append((
                            user_id, server_id, None, date_creation, date_creation, target_secs, date_creation, True
                        ))
                        total_reconstructed_seconds += target_secs
                    else:
                        # Méthode du plus fort reste (garantie mathématique de somme exacte = target_secs)
                        items = []
                        total_base = 0
                        for idx_d, d in enumerate(raw_voice_deltas):
                            exact = (d['raw_s'] * target_secs) / sum_raw_s
                            base = int(exact)
                            total_base += base
                            rem = exact - base
                            items.append({'idx': idx_d, 'delta': d, 'val': base, 'rem': rem})

                        deficit = target_secs - total_base
                        if deficit > 0:
                            items.sort(key=lambda x: x['rem'], reverse=True)
                            for i in range(min(deficit, len(items))):
                                items[i]['val'] += 1

                        # Réordonner chronologiquement
                        items.sort(key=lambda x: x['idx'])
                        for it in items:
                            val = it['val']
                            if val > 0:
                                d = it['delta']
                                voice_sessions_to_insert.append((
                                    user_id, server_id, None, d['joined_at'], d['left_at'], val, d['left_at'], True
                                ))
                                total_reconstructed_seconds += val

                # --- Reconstruction Messages ---
                if target_msgs > 0:
                    raw_msg_deltas = []
                    prev_m = 0

                    for t, m, s in hist:
                        delta_m = max(0, m - prev_m)
                        if delta_m > 0:
                            raw_msg_deltas.append({
                                'created_at': t,
                                'raw_m': delta_m
                            })
                        prev_m = m

                    sum_raw_m = sum(d['raw_m'] for d in raw_msg_deltas)

                    if sum_raw_m == 0:
                        message_events_to_insert.append((
                            user_id, server_id, None, date_creation, target_msgs, True
                        ))
                        total_reconstructed_messages += target_msgs
                    else:
                        # Méthode du plus fort reste (somme exacte = target_msgs)
                        items = []
                        total_base = 0
                        for idx_m, d in enumerate(raw_msg_deltas):
                            exact = (d['raw_m'] * target_msgs) / sum_raw_m
                            base = int(exact)
                            total_base += base
                            rem = exact - base
                            items.append({'idx': idx_m, 'delta': d, 'val': base, 'rem': rem})

                        deficit = target_msgs - total_base
                        if deficit > 0:
                            items.sort(key=lambda x: x['rem'], reverse=True)
                            for i in range(min(deficit, len(items))):
                                items[i]['val'] += 1

                        items.sort(key=lambda x: x['idx'])
                        for it in items:
                            val = it['val']
                            if val > 0:
                                d = it['delta']
                                message_events_to_insert.append((
                                    user_id, server_id, None, d['created_at'], val, True
                                ))
                                total_reconstructed_messages += val

            # 4. Rapport de contrôle de parité
            print("-" * 70)
            print("🔍 RAPPORT DE CONTRÔLE DE PARITÉ DES DONNÉES :")
            print(f"  • Secondes Cible (stats)        : {total_target_seconds:,} s ({total_target_seconds/3600:,.1f} h)")
            print(f"  • Secondes Reconstituées        : {total_reconstructed_seconds:,} s ({total_reconstructed_seconds/3600:,.1f} h)")
            print(f"  • Écart Secondes                : {total_reconstructed_seconds - total_target_seconds} s")
            print(f"  • Messages Cible (stats)        : {total_target_messages:,}")
            print(f"  • Messages Reconstitués         : {total_reconstructed_messages:,}")
            print(f"  • Écart Messages                : {total_reconstructed_messages - total_target_messages}")
            print(f"  • Total Sessions Vocales Créées : {len(voice_sessions_to_insert):,}")
            print(f"  • Total Lots de Messages Créés  : {len(message_events_to_insert):,}")
            print("-" * 70)

            parity_ok = (total_reconstructed_seconds == total_target_seconds) and (total_reconstructed_messages == total_target_messages)
            if parity_ok:
                print("✨ PARITÉ 100% PARFAITE ! Aucune seconde ni aucun message perdu.")
            else:
                print("⚠️ ATTENTION : Discordance détectée dans les totaux !")

            # 5. Écriture par lots si mode --execute
            if not dry_run and parity_ok:
                print("📥 Insertion par lots dans 'voice_sessions'...")
                # Nettoyage préalable des archives existantes si relancé
                cur.execute("DELETE FROM voice_sessions WHERE is_legacy = TRUE")
                execute_values(
                    cur,
                    """
                    INSERT INTO voice_sessions 
                    (user_id, server_id, channel_id, joined_at, left_at, duration_seconds, last_heartbeat, is_legacy)
                    VALUES %s
                    """,
                    voice_sessions_to_insert,
                    page_size=5000
                )
                print(f"✅ {len(voice_sessions_to_insert):,} sessions vocales insérées.")

                print("📥 Insertion par lots dans 'message_events'...")
                cur.execute("DELETE FROM message_events WHERE is_legacy = TRUE")
                execute_values(
                    cur,
                    """
                    INSERT INTO message_events 
                    (user_id, server_id, channel_id, created_at, count, is_legacy)
                    VALUES %s
                    """,
                    message_events_to_insert,
                    page_size=5000
                )
                print(f"✅ {len(message_events_to_insert):,} lots de messages insérés.")

                conn.commit()
                print("🎉 MIGRATION TERMINÉE AVEC SUCCÈS ET VALIDÉE !")
            elif dry_run:
                print("ℹ️ Mode simulation terminé. Pour appliquer en BDD, lancez : python migrate_v3.py --execute")

    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migration des données Hourglass vers v3.0")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Simule la migration sans écriture")
    group.add_argument("--execute", action="store_true", help="Applique réellement la migration en BDD")

    args = parser.parse_args()
    run_migration(dry_run=args.dry_run)
