"""
Module : serving/dashboard.py
Rôle   : Générer 3 graphiques PNG clairs depuis les données PostgreSQL.

Fichiers produits dans serving/ :
  - chart1_failed_by_country.png   (bar chart horizontal)
  - chart2_success_by_user.png     (bar chart vertical)
  - chart3_invalid_users.png       (bar chart horizontal)
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from logger.app_logger import get_logger

_log = get_logger("serving.dashboard")

OUTPUT_DIR = Path(__file__).resolve().parent

# Palette couleurs cohérente
_COLOR_FAILED  = "#c0392b"   # rouge foncé
_COLOR_SUCCESS = "#27ae60"   # vert
_COLOR_INVALID = "#e67e22"   # orange


# ---------------------------------------------------------------------------
# Utilitaire : sauvegarde propre d'une figure
# ---------------------------------------------------------------------------

def _save(fig, filepath: Path, label: str) -> bool:
    """
    Sauvegarde une figure matplotlib en PNG et ferme la figure.

    Paramètres
    ----------
    fig      : matplotlib.figure.Figure
    filepath : Path — chemin de sortie
    label    : str  — nom pour le log

    Retour
    ------
    bool : True si succès

    Erreurs possibles loggées
    -------------------------
    - Erreur écriture disque → ERROR
    - Exception inattendue   → ERROR
    """
    try:
        fig.savefig(filepath, dpi=130, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        _log.info("PNG sauvegardé : %s", filepath.name)
        return True
    except OSError as exc:
        _log.error("Impossible d'écrire %s : %s", filepath.name, exc)
        return False
    except Exception as exc:
        _log.error("Erreur inattendue sauvegarde %s : %s", filepath.name, exc)
        return False
    finally:
        plt.close(fig)


# ---------------------------------------------------------------------------
# Graphique 1 — Tentatives échouées par pays
# ---------------------------------------------------------------------------

def chart_failed_by_country(data: list) -> bool:
    """
    Bar chart horizontal : nombre de tentatives échouées par pays.

    Paramètres
    ----------
    data : list[tuple(country, nb_failed)]

    Retour
    ------
    bool

    Erreurs possibles loggées
    -------------------------
    - data vide             → WARNING
    - Exception matplotlib  → ERROR
    """
    if not data:
        _log.warning("chart1 : aucune donnée 'failed by country'")
        return False

    try:
        top    = data[:20]
        pays   = [str(r[0]) for r in top][::-1]
        counts = [int(r[1]) for r in top][::-1]

        height = max(5, len(pays) * 0.55)
        fig, ax = plt.subplots(figsize=(12, height))
        fig.patch.set_facecolor("#f9f9f9")
        ax.set_facecolor("#ffffff")

        bars = ax.barh(pays, counts, color=_COLOR_FAILED,
                       edgecolor="#f9f9f9", linewidth=0.6, height=0.65)

        # Étiquettes de valeur à droite de chaque barre
        for bar, val in zip(bars, counts):
            ax.text(bar.get_width() + max(counts) * 0.01, bar.get_y() + bar.get_height() / 2,
                    f"{val:,}", va="center", ha="left", fontsize=9, color="#2c3e50")

        ax.set_xlabel("Nombre de tentatives échouées", fontsize=11, labelpad=10)
        ax.set_title("Tentatives échouées par pays (Top 20)",
                     fontsize=14, fontweight="bold", pad=15, color="#2c3e50")
        ax.set_xlim(0, max(counts) * 1.15)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(left=False, labelsize=10)
        ax.xaxis.grid(True, linestyle="--", alpha=0.5)
        ax.set_axisbelow(True)

        fig.tight_layout(pad=1.5)
        _log.info("chart1 : %d pays tracés", len(pays))
        return _save(fig, OUTPUT_DIR / "chart1_failed_by_country.png", "chart1")

    except Exception as exc:
        _log.error("chart1 exception : %s", exc)
        plt.close("all")
        return False


# ---------------------------------------------------------------------------
# Graphique 2 — Connexions réussies par utilisateur
# ---------------------------------------------------------------------------

def chart_success_by_user(data: list) -> bool:
    """
    Bar chart vertical : connexions réussies par utilisateur.

    Paramètres
    ----------
    data : list[tuple(username, nb_success)]

    Retour
    ------
    bool

    Erreurs possibles loggées
    -------------------------
    - data vide             → WARNING
    - Exception matplotlib  → ERROR
    """
    if not data:
        _log.warning("chart2 : aucune donnée 'success by user'")
        return False

    try:
        top    = data[:15]
        users  = [str(r[0]) for r in top]
        counts = [int(r[1]) for r in top]

        fig, ax = plt.subplots(figsize=(max(8, len(users) * 0.9), 6))
        fig.patch.set_facecolor("#f9f9f9")
        ax.set_facecolor("#ffffff")

        bars = ax.bar(users, counts, color=_COLOR_SUCCESS,
                      edgecolor="#f9f9f9", linewidth=0.6, width=0.6)

        for bar, val in zip(bars, counts):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(counts) * 0.01,
                    f"{val:,}", ha="center", va="bottom", fontsize=9, color="#2c3e50")

        ax.set_ylabel("Nombre de connexions réussies", fontsize=11, labelpad=10)
        ax.set_title("Connexions réussies par utilisateur (Top 15)",
                     fontsize=14, fontweight="bold", pad=15, color="#2c3e50")
        ax.set_ylim(0, max(counts) * 1.15)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(axis="x", rotation=30, labelsize=10)
        ax.tick_params(axis="y", labelsize=10)
        ax.yaxis.grid(True, linestyle="--", alpha=0.5)
        ax.set_axisbelow(True)

        fig.tight_layout(pad=1.5)
        _log.info("chart2 : %d utilisateurs tracés", len(users))
        return _save(fig, OUTPUT_DIR / "chart2_success_by_user.png", "chart2")

    except Exception as exc:
        _log.error("chart2 exception : %s", exc)
        plt.close("all")
        return False


# ---------------------------------------------------------------------------
# Graphique 3 — Tentatives avec utilisateur invalide
# ---------------------------------------------------------------------------

def chart_invalid_users(data: list) -> bool:
    """
    Bar chart horizontal : tentatives avec utilisateur invalide (top 20).

    Paramètres
    ----------
    data : list[tuple(username, ip, country, nb_attempts)]

    Retour
    ------
    bool

    Erreurs possibles loggées
    -------------------------
    - data vide             → WARNING
    - Exception matplotlib  → ERROR
    """
    if not data:
        _log.warning("chart3 : aucune donnée 'invalid users'")
        return False

    try:
        top    = data[:20]
        labels = [f"{r[0]}  ({r[2]})" for r in top][::-1]
        counts = [int(r[3]) for r in top][::-1]

        height = max(5, len(labels) * 0.55)
        fig, ax = plt.subplots(figsize=(12, height))
        fig.patch.set_facecolor("#f9f9f9")
        ax.set_facecolor("#ffffff")

        bars = ax.barh(labels, counts, color=_COLOR_INVALID,
                       edgecolor="#f9f9f9", linewidth=0.6, height=0.65)

        for bar, val in zip(bars, counts):
            ax.text(bar.get_width() + max(counts) * 0.01, bar.get_y() + bar.get_height() / 2,
                    f"{val:,}", va="center", ha="left", fontsize=9, color="#2c3e50")

        ax.set_xlabel("Nombre de tentatives", fontsize=11, labelpad=10)
        ax.set_title("Tentatives avec utilisateur invalide (Top 20)",
                     fontsize=14, fontweight="bold", pad=15, color="#2c3e50")
        ax.set_xlim(0, max(counts) * 1.15)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(left=False, labelsize=10)
        ax.xaxis.grid(True, linestyle="--", alpha=0.5)
        ax.set_axisbelow(True)

        fig.tight_layout(pad=1.5)
        _log.info("chart3 : %d entrées tracées", len(labels))
        return _save(fig, OUTPUT_DIR / "chart3_invalid_users.png", "chart3")

    except Exception as exc:
        _log.error("chart3 exception : %s", exc)
        plt.close("all")
        return False


# ---------------------------------------------------------------------------
# Point d'entrée principal
# ---------------------------------------------------------------------------

def generate(conn) -> bool:
    """
    Lance la génération des 3 graphiques PNG.

    Paramètres
    ----------
    conn : psycopg2.connection

    Retour
    ------
    bool : True si au moins un graphique a été généré.

    Erreurs possibles loggées
    -------------------------
    - conn None                    → ERROR
    - Erreur requête DB            → ERROR (géré dans db.py)
    - Graphique individuel raté    → ERROR (les autres continuent)
    """
    if conn is None:
        _log.error("generate() : connexion None, dashboard non généré")
        return False

    _log.info("Génération des 3 graphiques PNG…")

    from storage.db import (
        query_failed_by_country,
        query_success_by_user,
        query_failed_invalid_users,
    )

    try:
        data_country = query_failed_by_country(conn)
        data_user    = query_success_by_user(conn)
        data_invalid = query_failed_invalid_users(conn)
    except Exception as exc:
        _log.error("Erreur récupération données dashboard : %s", exc)
        return False

    # KPI log
    _log.info(
        "KPI → Échecs: %d | Succès: %d | Invalides: %d | Pays: %d",
        sum(r[1] for r in data_country),
        sum(r[1] for r in data_user),
        sum(r[3] for r in data_invalid),
        len(data_country),
    )

    ok1 = chart_failed_by_country(data_country)
    ok2 = chart_success_by_user(data_user)
    ok3 = chart_invalid_users(data_invalid)

    nb_ok = sum([ok1, ok2, ok3])
    _log.info("%d/3 graphiques générés dans serving/", nb_ok)
    return nb_ok > 0


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from storage.db import get_connection
    conn = get_connection()
    if conn:
        generate(conn)
        conn.close()
