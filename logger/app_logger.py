"""
Module : logger/app_logger.py
Rôle   : Fournir un logger centralisé pour chaque module de l'application.
         Chaque module obtient son propre logger nommé, avec sortie
         simultanée vers la console et vers le fichier logs/app.log.
"""
import logging
import os
import sys
from pathlib import Path

# ------------------------------------------------------------------
# Répertoire de logs : on le crée s'il n'existe pas
# ------------------------------------------------------------------
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except (OSError, PermissionError) as exc:
    print(f"[app_logger] Impossible de créer le répertoire de logs : {exc}", file=sys.stderr)

LOG_FILE = LOG_DIR / "app.log"

# Format unique pour tous les loggers
_FORMATTER = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_logger(module_name: str) -> logging.Logger:
    """
    Retourne un logger configuré pour le module donné.

    - Handler fichier  : logs/app.log (level DEBUG, rotation manuelle)
    - Handler console  : stdout      (level INFO)

    Paramètres
    ----------
    module_name : str
        Nom du module appelant (ex: 'ingestion.raw', 'processing.extract').

    Retour
    ------
    logging.Logger
        Logger prêt à l'emploi.
    """
    logger = logging.getLogger(module_name)

    # Éviter d'ajouter plusieurs handlers si get_logger est appelé plusieurs fois
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # --- Handler fichier (DEBUG et au-dessus) ---
    try:
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(_FORMATTER)
        logger.addHandler(file_handler)
    except OSError as exc:
        # Si on ne peut pas écrire dans le fichier, on le signale sur stderr
        import sys
        print(f"[app_logger] Impossible de créer le fichier de log : {exc}", file=sys.stderr)

    # --- Handler console (INFO et au-dessus) ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(_FORMATTER)
    logger.addHandler(console_handler)

    # Ne pas propager vers le root logger (évite les doublons)
    logger.propagate = False

    return logger
