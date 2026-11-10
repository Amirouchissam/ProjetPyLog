"""
Module : ingestion/raw.py
Rôle   : Lire tous les fichiers de logs du dossier data (fichiers bruts et .gz)
         Retourne la liste complète des lignes pour le parsing.
"""
import gzip
import os
from pathlib import Path

from logger.app_logger import get_logger

_log = get_logger("ingestion.raw")


def to_rows(path: str = "./data") -> list[str]:
    """
    Lit tous les fichiers d'un répertoire (texte brut et archives .gz).
    Retourne la liste complète des lignes.
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

    if not data_dir.exists():
        _log.error("Dossier introuvable : %s", data_dir.resolve())
        return all_rows

    if not data_dir.is_dir():
        _log.error("Le chemin spécifié n'est pas un dossier : %s", data_dir.resolve())
        return all_rows

    try:
        files = sorted(os.listdir(data_dir))
    except PermissionError as exc:
        _log.error("Permission refusée pour lister %s : %s", data_dir, exc)
        return all_rows
    except OSError as exc:
        _log.error("Erreur système lors du listage de %s : %s", data_dir, exc)
        return all_rows

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

            with opener as f:
                lines = f.readlines()
                all_rows.extend(lines)
                _log.debug("Fichier '%s' lu : %d lignes", filename, len(lines))

        except (OSError, gzip.BadGzipFile) as exc:
            _log.error("Erreur lors de la lecture du fichier '%s' : %s", filename, exc)
            continue
        except Exception as exc:
            _log.error("Exception inattendue sur le fichier '%s' : %s", filename, exc)
            continue

    if not all_rows:
        _log.warning("Aucune ligne lue dans %s", data_dir)
    else:
        _log.info("Total lignes lues : %d", len(all_rows))

    return all_rows


if __name__ == "__main__":
    data = to_rows("./data")
    if data:
        print(f"Total : {len(data)} lignes lues.")
        print(f"Exemple : {data[0].strip()}")
