"""
Module : serving/dashboard.py
Rôle   : Générer un dashboard HTML interactif à partir des données PostgreSQL.
         Utilise uniquement matplotlib (stdlib + matplotlib) pour les graphiques
         exportés en PNG embarqués en base64 dans le HTML.

Dashboard produit (fichier : serving/dashboard.html) :
  1. Nombre de tentatives échouées par pays (bar chart horizontal)
  2. Nombre de tentatives réussies par utilisateur (bar chart)
  3. Tentatives échouées avec utilisateurs invalides (table HTML)
"""
import base64
import io
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")          # Backend non-interactif (pas d'écran requis)
import matplotlib.pyplot as plt

from logger.app_logger import get_logger

_log = get_logger("serving.dashboard")

OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = OUTPUT_DIR / "dashboard.html"


# ---------------------------------------------------------------------------
# Utilitaires graphiques
# ---------------------------------------------------------------------------

def _fig_to_base64(fig) -> str:
    """
    Convertit une figure matplotlib en chaîne base64 PNG.

    Paramètres
    ----------
    fig : matplotlib.figure.Figure

    Retour
    ------
    str : données base64 de l'image PNG.

    Erreurs possibles loggées
    -------------------------
    - Erreur lors de la conversion → ERROR
    """
    try:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=120)
        buf.seek(0)
        encoded = base64.b64encode(buf.read()).decode("utf-8")
        plt.close(fig)
        return encoded
    except Exception as exc:
        _log.error("Erreur conversion figure en base64 : %s", exc)
        plt.close(fig)
        return ""


def _chart_failed_by_country(data: list) -> str:
    """
    Graphique : tentatives échouées par pays.

    Paramètres
    ----------
    data : list[tuple(country, nb_failed)]

    Retour
    ------
    str : image PNG encodée en base64.
    """
    if not data:
        _log.warning("Aucune donnée pour le graphique 'failed by country'")
        return ""

    countries = [row[0] for row in data[:20]]   # top 20
    counts    = [row[1] for row in data[:20]]

    fig, ax = plt.subplots(figsize=(10, max(4, len(countries) * 0.4)))
    bars = ax.barh(countries[::-1], counts[::-1], color="#e74c3c")
    ax.set_xlabel("Nombre de tentatives échouées", fontsize=11)
    ax.set_title("Tentatives échouées par pays (Top 20)", fontsize=13, fontweight="bold")
    ax.bar_label(bars, padding=3, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()

    _log.info("Graphique 'failed_by_country' généré (%d pays)", len(countries))
    return _fig_to_base64(fig)


def _chart_success_by_user(data: list) -> str:
    """
    Graphique : connexions réussies par utilisateur.

    Paramètres
    ----------
    data : list[tuple(username, nb_success)]

    Retour
    ------
    str : image PNG encodée en base64.
    """
    if not data:
        _log.warning("Aucune donnée pour le graphique 'success by user'")
        return ""

    users  = [row[0] for row in data[:15]]
    counts = [row[1] for row in data[:15]]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(users, counts, color="#2ecc71")
    ax.set_ylabel("Nombre de connexions réussies", fontsize=11)
    ax.set_title("Connexions réussies par utilisateur (Top 15)", fontsize=13, fontweight="bold")
    ax.bar_label(bars, padding=3, fontsize=9)
    plt.xticks(rotation=30, ha="right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()

    _log.info("Graphique 'success_by_user' généré (%d utilisateurs)", len(users))
    return _fig_to_base64(fig)


def _table_invalid_users(data: list) -> str:
    """
    Génère un tableau HTML pour les tentatives avec utilisateurs invalides.

    Paramètres
    ----------
    data : list[tuple(username, ip, country, nb_attempts)]

    Retour
    ------
    str : fragment HTML du tableau.
    """
    if not data:
        _log.warning("Aucune donnée pour la table 'invalid users'")
        return "<p style='color:#999'>Aucune donnée disponible.</p>"

    rows_html = ""
    for username, ip, country, nb in data:
        rows_html += f"""
        <tr>
          <td>{username}</td>
          <td>{ip}</td>
          <td>{country}</td>
          <td style="text-align:center;font-weight:bold;color:#e74c3c">{nb}</td>
        </tr>"""

    _log.info("Table 'invalid_users' générée (%d lignes)", len(data))
    return f"""
    <table>
      <thead>
        <tr>
          <th>Utilisateur</th>
          <th>Adresse IP</th>
          <th>Pays</th>
          <th>Tentatives</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>"""


# ---------------------------------------------------------------------------
# Génération du HTML complet
# ---------------------------------------------------------------------------

def _build_html(
    chart_country: str,
    chart_user: str,
    table_invalid: str,
    stats: dict,
) -> str:
    """
    Assemble le HTML final du dashboard.

    Paramètres
    ----------
    chart_country  : str — base64 PNG tentatives par pays
    chart_user     : str — base64 PNG succès par utilisateur
    table_invalid  : str — HTML table utilisateurs invalides
    stats          : dict — compteurs globaux

    Retour
    ------
    str : document HTML complet.
    """
    img_country = (
        f'<img src="data:image/png;base64,{chart_country}" alt="Failed by country">'
        if chart_country else "<p>Graphique indisponible</p>"
    )
    img_user = (
        f'<img src="data:image/png;base64,{chart_user}" alt="Success by user">'
        if chart_user else "<p>Graphique indisponible</p>"
    )

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Log Analysis Dashboard</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Segoe UI', Arial, sans-serif;
      background: #f0f2f5;
      color: #333;
      padding: 24px;
    }}
    h1 {{
      text-align: center;
      color: #2c3e50;
      margin-bottom: 8px;
      font-size: 2rem;
    }}
    .subtitle {{
      text-align: center;
      color: #7f8c8d;
      margin-bottom: 32px;
      font-size: 0.95rem;
    }}
    .kpi-row {{
      display: flex;
      gap: 16px;
      justify-content: center;
      flex-wrap: wrap;
      margin-bottom: 32px;
    }}
    .kpi {{
      background: white;
      border-radius: 12px;
      padding: 20px 32px;
      text-align: center;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
      min-width: 160px;
    }}
    .kpi .value {{
      font-size: 2.2rem;
      font-weight: bold;
    }}
    .kpi .label {{
      font-size: 0.85rem;
      color: #7f8c8d;
      margin-top: 4px;
    }}
    .kpi.red   .value {{ color: #e74c3c; }}
    .kpi.green .value {{ color: #2ecc71; }}
    .kpi.orange .value {{ color: #e67e22; }}
    .card {{
      background: white;
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 24px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }}
    .card h2 {{
      color: #2c3e50;
      margin-bottom: 16px;
      font-size: 1.1rem;
      border-left: 4px solid #3498db;
      padding-left: 10px;
    }}
    .card img {{
      max-width: 100%;
      display: block;
      margin: 0 auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
    }}
    thead tr {{
      background: #2c3e50;
      color: white;
    }}
    th, td {{
      padding: 10px 14px;
      text-align: left;
    }}
    tbody tr:nth-child(even) {{ background: #f8f9fa; }}
    tbody tr:hover {{ background: #eaf4fb; }}
    .footer {{
      text-align: center;
      color: #bdc3c7;
      font-size: 0.8rem;
      margin-top: 32px;
    }}
  </style>
</head>
<body>
  <h1>🔐 SSH Log Analysis Dashboard</h1>
  <p class="subtitle">Analyse des journaux d'authentification SSH — Pipeline Python + PostgreSQL</p>

  <!-- KPI -->
  <div class="kpi-row">
    <div class="kpi red">
      <div class="value">{stats.get('total_failed', 0)}</div>
      <div class="label">Tentatives échouées</div>
    </div>
    <div class="kpi green">
      <div class="value">{stats.get('total_success', 0)}</div>
      <div class="label">Connexions réussies</div>
    </div>
    <div class="kpi orange">
      <div class="value">{stats.get('total_invalid', 0)}</div>
      <div class="label">Utilisateurs invalides</div>
    </div>
    <div class="kpi">
      <div class="value">{stats.get('total_countries', 0)}</div>
      <div class="label">Pays distincts</div>
    </div>
  </div>

  <!-- Graphique 1 : Tentatives échouées par pays -->
  <div class="card">
    <h2>🌍 Tentatives échouées par pays</h2>
    {img_country}
  </div>

  <!-- Graphique 2 : Connexions réussies par utilisateur -->
  <div class="card">
    <h2>✅ Connexions réussies par utilisateur</h2>
    {img_user}
  </div>

  <!-- Table 3 : Utilisateurs invalides -->
  <div class="card">
    <h2>🚫 Tentatives avec utilisateurs invalides (Top 50)</h2>
    {table_invalid}
  </div>

  <div class="footer">
    Généré automatiquement par log_analysis · Python + PostgreSQL (port 4001)
  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Point d'entrée principal
# ---------------------------------------------------------------------------

def generate(conn) -> bool:
    """
    Génère le fichier dashboard.html à partir des données PostgreSQL.

    Paramètres
    ----------
    conn : psycopg2.connection

    Retour
    ------
    bool : True si le fichier a été créé avec succès.

    Erreurs possibles loggées
    -------------------------
    - Connexion None             → ERROR
    - Données vides pour un KPI  → WARNING
    - Erreur écriture du fichier → ERROR
    """
    if conn is None:
        _log.error("generate() : connexion PostgreSQL None, dashboard non généré")
        return False

    _log.info("Début de la génération du dashboard…")

    # --- Import ici pour éviter la circularité ---
    from storage.db import (
        query_failed_by_country,
        query_success_by_user,
        query_failed_invalid_users,
    )

    data_country = query_failed_by_country(conn)
    data_user    = query_success_by_user(conn)
    data_invalid = query_failed_invalid_users(conn)

    # --- KPI globaux ---
    stats = {
        "total_failed":    sum(r[1] for r in data_country),
        "total_success":   sum(r[1] for r in data_user),
        "total_invalid":   sum(r[3] for r in data_invalid),
        "total_countries": len(data_country),
    }
    _log.info("KPI globaux : %s", stats)

    # --- Graphiques ---
    chart_country = _chart_failed_by_country(data_country)
    chart_user    = _chart_success_by_user(data_user)
    table_invalid = _table_invalid_users(data_invalid)

    # --- Écriture HTML ---
    html_content = _build_html(chart_country, chart_user, table_invalid, stats)

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
            fh.write(html_content)
        _log.info("Dashboard généré : %s", OUTPUT_FILE)
        return True
    except OSError as exc:
        _log.error("Impossible d'écrire le dashboard : %s", exc)
        return False


# ---------------------------------------------------------------------------
# Test rapide si exécuté directement
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from storage.db import get_connection
    conn = get_connection()
    if conn:
        ok = generate(conn)
        conn.close()
        if ok:
            print(f"Dashboard généré : {OUTPUT_FILE}")
    else:
        print("Connexion PostgreSQL impossible.")
