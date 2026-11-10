"""
Module : ingestion/raw.py
<<<<<<< HEAD
Rôle   : Lire tous les fichiers de journaux SSH (auth.log) du répertoire data/.
         Prend en charge les fichiers texte bruts (.log, .1, .2 …)
         et les fichiers compressés (.gz).
         Ignore automatiquement les fichiers non pertinents (.json, .py, etc.).
         Retourne une liste de lignes prêtes à être parsées.
=======
Rôle   : Lire tous les fichiers de logs du dossier data (fichiers bruts et .gz)
         Retourne la liste complète des lignes pour le parsing.
>>>>>>> 5e2f890a8d6fdd0cda6fc28e33fe12c4b6318d8f
"""
import gzip
import os
from pathlib import Path

from logger.app_logger import get_logger

_log = get_logger("ingestion.raw")

# Extensions ou suffixes de fichiers de log acceptés
_VALID_EXTENSIONS = (".log", ".gz")


def _is_log_file(filename: str) -> bool:
    """
    Vérifie si un fichier est bien un fichier de log SSH.
    Accepte auth.log, auth.log.1, auth.log.2, auth.log.3.gz, etc.
    Rejette geo_cache.json, scripts, caches et fichiers cachés.
    """
    if filename.startswith("."):
        return False
    if filename.endswith((".json", ".py", ".md", ".txt", ".png", ".html", ".lock", ".toml")):
        return False
    # auth.log ou auth.log.X ou extension .log/.gz
    lower = filename.lower()
    return "auth.log" in lower or lower.endswith(_VALID_EXTENSIONS)


def to_rows(path: str = "./data") -> list[str]:
    """
<<<<<<< HEAD
    Lit tous les fichiers de logs du répertoire 'path' et retourne leurs lignes.

    Paramètres
    ----------
    path : str
        Chemin vers le répertoire contenant les fichiers de logs.

    Retour
    ------
    list[str]
        Liste de toutes les lignes brutes lues.

    Erreurs possibles loggées
    -------------------------
    - Répertoire introuvable        → ERROR
    - Le chemin n'est pas un dossier→ ERROR
    - Permission refusée            → ERROR
    - Aucun fichier log valide      → WARNING
    - Fichier corrompu ou illisible → ERROR (on continue avec les autres)
=======
    Lit tous les fichiers d'un répertoire (texte brut et archives .gz).
    Retourne la liste complète des lignes.
>>>>>>> 5e2f890a8d6fdd0cda6fc28e33fe12c4b6318d8f
    """
    all_rows: list[str] = []

    if not path or not isinstance(path, (str, Path)):
        _log.error("Chemin invalide fourni : %r", path)
        return all_rows

    try:
        data_dir = Path(path)
    except Exception as exc:
        _log.error("Impossible de résoudre le chemin '%s' : %s", path, exc)
        return all_rows

<<<<<<< HEAD
    # --- Vérification de l'existence du répertoire ---
    if not data_dir.exists():
        _log.error("Répertoire de logs introuvable : %s", data_dir.resolve())
        return all_rows

    if not data_dir.is_dir():
        _log.error("Le chemin fourni n'est pas un répertoire : %s", data_dir.resolve())
=======
    if not data_dir.exists():
        _log.error("Dossier introuvable : %s", data_dir.resolve())
        return all_rows

    if not data_dir.is_dir():
        _log.error("Le chemin spécifié n'est pas un dossier : %s", data_dir.resolve())
>>>>>>> 5e2f890a8d6fdd0cda6fc28e33fe12c4b6318d8f
        return all_rows

    try:
        filenames = sorted(os.listdir(data_dir))
    except PermissionError as exc:
        _log.error("Permission refusée pour lister %s : %s", data_dir, exc)
        return all_rows
    except OSError as exc:
        _log.error("Erreur système lors du listage de %s : %s", data_dir, exc)
        return all_rows

<<<<<<< HEAD
    # Filtrer uniquement les fichiers de log pertinents
    log_files = [f for f in filenames if _is_log_file(f)]

    if not log_files:
        _log.warning("Aucun fichier de log valide trouvé dans : %s", data_dir.resolve())
        return all_rows

    _log.info(
        "Ingestion de %d fichier(s) de log dans %s : %s",
        len(log_files), data_dir.resolve(), ", ".join(log_files)
    )

    # --- Lecture sécurisée fichier par fichier ---
    for filename in log_files:
        file_path = data_dir / filename
        if not file_path.is_file():
            _log.debug("Ignoré (n'est pas un fichier standard) : %s", filename)
            continue

        try:
            if filename.endswith(".gz"):
                opener = gzip.open(file_path, mode="rt", encoding="utf-8", errors="replace")
            else:
                opener = open(file_path, mode="r", encoding="utf-8", errors="replace")
=======
    if not files:
        _log.warning("Aucun fichier trouvé dans %s", data_dir)
        return all_rows

    _log.info("Lecture de %d fichier(s) dans %s", len(files), data_dir)

    for filename in files:
        file_path = data_dir / filename
        if not file_path.is_file():
            continue

        try:
            # Opérateur ternaire conforme au cours pour gérer les fichiers .gz et texte
            opener = gzip.open(file_path, mode="rt", encoding="utf-8", errors="replace") if filename.endswith(".gz") else open(file_path, mode="r", encoding="utf-8", errors="replace")
>>>>>>> 5e2f890a8d6fdd0cda6fc28e33fe12c4b6318d8f

            with opener as f:
                lines = f.readlines()
                all_rows.extend(lines)
                _log.debug("Fichier '%s' chargé avec succès : %d lignes", filename, len(lines))

<<<<<<< HEAD
        except (gzip.BadGzipFile, OSError) as exc:
            _log.error("Impossible de lire le fichier '%s' : %s", filename, exc)
            continue
        except Exception as exc:
            _log.error("Erreur inattendue lors de la lecture de '%s' : %s", filename, exc)
            continue

    if not all_rows:
        _log.warning("Aucune ligne n'a pu être extraite des fichiers de logs.")
=======
        except (OSError, gzip.BadGzipFile) as exc:
            _log.error("Erreur lors de la lecture du fichier '%s' : %s", filename, exc)
            continue
        except Exception as exc:
            _log.error("Exception inattendue sur le fichier '%s' : %s", filename, exc)
            continue

    if not all_rows:
        _log.warning("Aucune ligne lue dans %s", data_dir)
>>>>>>> 5e2f890a8d6fdd0cda6fc28e33fe12c4b6318d8f
    else:
        _log.info("Ingestion terminée : total %d lignes lues.", len(all_rows))

    return all_rows


<<<<<<< HEAD
# ---------------------------------------------------------------------------
# Test direct du module
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    data = to_rows("./data")
    if data:
        print(f"Première ligne : {data[0].strip()}")
        print(f"Total lignes   : {len(data)}")
=======
if __name__ == "__main__":
    data = to_rows("./data")
    if data:
        print(f"Total : {len(data)} lignes lues.")
        print(f"Exemple : {data[0].strip()}")
>>>>>>> 5e2f890a8d6fdd0cda6fc28e33fe12c4b6318d8f
