"""
main.py — Orchestrateur du pipeline Log Analysis
=================================================
Enchaîne les étapes dans l'ordre :
  1. Ingestion   : lecture des fichiers de logs
  2. Processing  : parsing des événements SSH
  3. Géolocation : enrichissement des IP
  4. Storage     : insertion dans PostgreSQL (port 4001)
  5. Serving     : génération du dashboard HTML

Usage :
  python main.py [--data-dir ./data]
"""
import sys
import argparse
import time

from logger.app_logger import get_logger
from ingestion import raw
from processing import extract_transforme, geo_location
from storage import db
from serving import dashboard

_log = get_logger("main")


def parse_args():
    parser = argparse.ArgumentParser(description="SSH Log Analysis Pipeline")
    parser.add_argument(
        "--data-dir",
        default="./data",
        help="Répertoire contenant les fichiers de logs (défaut: ./data)",
    )
    parser.add_argument(
        "--skip-geo",
        action="store_true",
        help="Désactiver la géolocalisation (utile hors ligne)",
    )
    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Désactiver l'insertion en base (dry-run)",
    )
    return parser.parse_args()


def run_pipeline(data_dir: str, skip_geo: bool = False, skip_db: bool = False) -> bool:
    """
    Exécute le pipeline complet.

    Retour
    ------
    bool : True si toutes les étapes critiques ont réussi.

    Erreurs possibles loggées
    -------------------------
    - Ingestion vide              → ERROR  (arrêt)
    - Parsing 0 événements        → ERROR  (arrêt)
    - Connexion DB impossible     → ERROR  (arrêt si skip_db=False)
    - Dashboard non généré        → WARNING
    - Exception non prévue        → CRITICAL
    """
    start = time.time()
    _log.info("=" * 60)
    _log.info("DÉMARRAGE DU PIPELINE LOG ANALYSIS")
    _log.info("=" * 60)

    # ------------------------------------------------------------------ #
    # ÉTAPE 1 — Ingestion                                                 #
    # ------------------------------------------------------------------ #
    _log.info("[1/5] Ingestion des fichiers depuis '%s'…", data_dir)
    try:
        rows = raw.to_rows(data_dir)
    except Exception as exc:
        _log.critical("Erreur critique lors de l'ingestion : %s", exc)
        return False

    if not rows:
        _log.error("Aucune ligne lue. Pipeline interrompu.")
        return False
    _log.info("[1/5] ✓ %d lignes lues", len(rows))

    # ------------------------------------------------------------------ #
    # ÉTAPE 2 — Parsing / extraction                                      #
    # ------------------------------------------------------------------ #
    _log.info("[2/5] Parsing et extraction des événements SSH…")
    try:
        events = extract_transforme.extract_all(rows)
    except Exception as exc:
        _log.critical("Erreur critique lors du parsing : %s", exc)
        return False

    if not events:
        _log.error("Aucun événement SSH extrait. Pipeline interrompu.")
        return False
    _log.info("[2/5] ✓ %d événements extraits", len(events))

    # ------------------------------------------------------------------ #
    # ÉTAPE 3 — Géolocalisation                                           #
    # ------------------------------------------------------------------ #
    if skip_geo:
        _log.info("[3/5] ⚠ Géolocalisation désactivée (--skip-geo)")
        # On ajoute quand même des valeurs par défaut
        events = [{**ev, "country": "Unknown", "city": "Unknown", "org": "Unknown"}
                  for ev in events]
    else:
        _log.info("[3/5] Géolocalisation des IPs (peut prendre du temps)…")
        try:
            events = geo_location.enrich_events(events)
        except Exception as exc:
            _log.error("Erreur lors de la géolocalisation (non bloquant) : %s", exc)
            events = [{**ev, "country": "Unknown", "city": "Unknown", "org": "Unknown"}
                      for ev in events]
    _log.info("[3/5] ✓ %d événements enrichis", len(events))

    # ------------------------------------------------------------------ #
    # ÉTAPE 4 — Stockage PostgreSQL                                       #
    # ------------------------------------------------------------------ #
    conn = None
    if skip_db:
        _log.info("[4/5] ⚠ Base de données désactivée (--skip-db)")
    else:
        _log.info("[4/5] Connexion à PostgreSQL (port 4001)…")
        try:
            conn = db.get_connection()
        except Exception as exc:
            _log.error("Erreur inattendue lors de la connexion DB : %s", exc)
            conn = None

        if conn is None:
            _log.error("Connexion PostgreSQL impossible. Pipeline interrompu.")
            return False

        # Initialisation du schéma
        if not db.init_schema(conn):
            _log.error("Schéma non initialisé. Pipeline interrompu.")
            conn.close()
            return False

        # Insertion des événements
        try:
            inserted = db.insert_events(conn, events)
            _log.info("[4/5] ✓ %d événements insérés en base", inserted)
        except Exception as exc:
            _log.error("Erreur lors de l'insertion en base : %s", exc)

    # ------------------------------------------------------------------ #
    # ÉTAPE 5 — Dashboard                                                 #
    # ------------------------------------------------------------------ #
    _log.info("[5/5] Génération du dashboard HTML…")
    if skip_db or conn is None:
        _log.warning("[5/5] ⚠ Dashboard ignoré (pas de connexion DB)")
    else:
        try:
            ok = dashboard.generate(conn)
            if ok:
                _log.info("[5/5] ✓ Dashboard PNG généré : serving/dashboard.png")
            else:
                _log.warning("[5/5] ⚠ Dashboard PNG non généré (voir les logs)")
        except Exception as exc:
            _log.error("Erreur lors de la génération du dashboard : %s", exc)
        finally:
            conn.close()
            _log.info("Connexion PostgreSQL fermée")

    elapsed = time.time() - start
    _log.info("=" * 60)
    _log.info("PIPELINE TERMINÉ en %.2f secondes", elapsed)
    _log.info("Dashboard → serving/dashboard.png")
    _log.info("=" * 60)
    return True


if __name__ == "__main__":
    args = parse_args()
    success = run_pipeline(
        data_dir=args.data_dir,
        skip_geo=args.skip_geo,
        skip_db=args.skip_db,
    )
    sys.exit(0 if success else 1)
