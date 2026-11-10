"""
Module : logger/app_logger.py
<<<<<<< HEAD
Rôle   : Fournir un logger centralisé pour chaque module de l'application.
         Utilise RotatingFileHandler (vu en cours) pour limiter la taille
         du fichier de log avec sauvegarde automatique.
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ------------------------------------------------------------------
# Répertoire de logs
# ------------------------------------------------------------------
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"

# Format identique au cours : date|level|name|message
_FORMATTER = logging.Formatter(
    fmt="%(asctime)s|%(levelname)s|%(name)s|%(message)s",
    datefmt="%d-%m-%Y %H:%M:%S",
)
=======
Rôle   : Configuration du logger de l'application selon les notions vues en cours.
         Utilise RotatingFileHandler et Formatter (format : date|niveau|nom|message).
"""
import logging
import os
from logging.handlers import RotatingFileHandler

# Format standard vu en cours (log_courses/lesson.py)
FORMAT: str = "%(asctime)s|%(levelname)s|%(name)s|%(message)s"
DATE_FORMAT: str = "%d-%m-%Y %H:%M:%S"

LOG_DIR: str = "logs"
LOG_FILE: str = os.path.join(LOG_DIR, "app.log")
>>>>>>> 5e2f890a8d6fdd0cda6fc28e33fe12c4b6318d8f


def get_logger(module_name: str) -> logging.Logger:
    """
<<<<<<< HEAD
    Retourne un logger configuré pour le module donné.

    - Handler fichier rotatif : logs/app.log
        maxBytes=500 000 (≈500 Ko), backupCount=5
    - Handler console : stdout (level INFO)

    Paramètres
    ----------
    module_name : str
        Nom du module appelant (ex: 'ingestion.raw').

    Retour
    ------
    logging.Logger
    """
    logger = logging.getLogger(module_name)

    # Éviter l'ajout multiple de handlers
=======
    Retourne un logger configuré avec sortie console et fichier tournant.
    """
    logger = logging.getLogger(module_name)
>>>>>>> 5e2f890a8d6fdd0cda6fc28e33fe12c4b6318d8f
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(fmt=FORMAT, datefmt=DATE_FORMAT)

<<<<<<< HEAD
    # --- Handler fichier rotatif (vu en cours : RotatingFileHandler) ---
    try:
        file_handler = RotatingFileHandler(
            filename=LOG_FILE,
            maxBytes=500_000,   # 500 Ko max par fichier
            backupCount=5,      # 5 fichiers de sauvegarde
            encoding="utf-8",
=======
    # Création du dossier logs si nécessaire
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
    except OSError as exc:
        print(f"Erreur création dossier logs : {exc}")

    # Handler fichier tournant (RotatingFileHandler vu en cours)
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=500_000,
            backupCount=3,
            encoding="utf-8"
>>>>>>> 5e2f890a8d6fdd0cda6fc28e33fe12c4b6318d8f
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError as exc:
<<<<<<< HEAD
        import sys
        print(f"[app_logger] Impossible de créer le fichier de log : {exc}", file=sys.stderr)
=======
        print(f"Erreur création fichier log : {exc}")
>>>>>>> 5e2f890a8d6fdd0cda6fc28e33fe12c4b6318d8f

    # Handler console (StreamHandler)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.propagate = False
    return logger
