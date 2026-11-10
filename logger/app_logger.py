"""
Module : logger/app_logger.py
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


def get_logger(module_name: str) -> logging.Logger:
    """
    Retourne un logger configuré avec sortie console et fichier tournant.
    """
    logger = logging.getLogger(module_name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(fmt=FORMAT, datefmt=DATE_FORMAT)

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
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError as exc:
        print(f"Erreur création fichier log : {exc}")

    # Handler console (StreamHandler)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.propagate = False
    return logger
