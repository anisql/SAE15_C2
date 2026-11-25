"""SAE 15 : carte des supports radio et bilan des azimuts ANFR.

Arborescence attendue :
    projet/
    ├── SAE15_carte_bilan_graphique.py
    ├── data/  (sup_support.txt, sup_station.txt, sup_antenne.txt, sup_emetteur.txt)
    └── ref/   (fichiers de référence sup_*.txt)

Les fichiers ANFR sont lus avec un point-virgule comme séparateur.
"""

from pathlib import Path
import html
import webbrowser

import folium
import matplotlib.pyplot as plt
import pandas as pd
from folium.plugins import MarkerCluster


# ---------------------------------------------------------------------------
# 1. Dossiers et lecture des fichiers
# ---------------------------------------------------------------------------

# Le script suppose que le dossier courant est la racine du projet.
DOSSIER_PROJET = Path.cwd()
DOSSIER_DATA = DOSSIER_PROJET / "data"
DOSSIER_REF = DOSSIER_PROJET / "ref"


def lire_fichier(nom_fichier, dossier=DOSSIER_DATA, colonnes=None):
    """Lit un fichier ANFR et renvoie son contenu sous forme de tableau Pandas."""
    chemin = dossier / nom_fichier

    if not chemin.exists():
        raise FileNotFoundError(f"Fichier introuvable : {chemin}")

    # Les fichiers sont séparés par des points-virgules.
    # dtype=str garde les identifiants comme du texte.
    tableau = pd.read_csv(
        chemin,
        sep=";",
        dtype=str,
        encoding="utf-8-sig",
        usecols=colonnes,
    )

    # On retire les espaces des noms de colonnes et on les met en majuscules.
    tableau.columns = tableau.columns.str.strip().str.upper()
    return tableau


# ---------------------------------------------------------------------------
# 2. Lecture des fichiers qui servent à construire la carte
# ---------------------------------------------------------------------------

supports = lire_fichier("sup_support.txt")
stations = lire_fichier("sup_station.txt")
antennes = lire_fichier(
    "sup_antenne.txt",
    colonnes=["STA_NM_ANFR", "AER_ID", "TAE_ID", "SUP_ID"],
)
emetteurs = lire_fichier(
    "sup_emetteur.txt",
    colonnes=["STA_NM_ANFR", "AER_ID", "EMR_LB_SYSTEME"],
)

natures = lire_fichier("sup_nature.txt", DOSSIER_REF)
proprietaires = lire_fichier("sup_proprietaire.txt", DOSSIER_REF)
exploitants = lire_fichier("sup_exploitant.txt", DOSSIER_REF)
types_antennes = lire_fichier("sup_type_antenne.txt", DOSSIER_REF)


# ---------------------------------------------------------------------------
# 3. Préparation des supports et des coordonnées
# ---------------------------------------------------------------------------

# L'ANFR donne latitude et longitude en degrés, minutes et secondes.
colonnes_coordonnees = [
    "COR_NB_DG_LAT", "COR_NB_MN_LAT", "COR_NB_SC_LAT",
    "COR_NB_DG_LON", "COR_NB_MN_LON", "COR_NB_SC_LON",
]

for nom_colonne in colonnes_coordonnees:
    supports[nom_colonne] = pd.to_numeric(supports[nom_colonne], errors="coerce")

supports["lat"] = (
    supports["COR_NB_DG_LAT"]
    + supports["COR_NB_MN_LAT"] / 60
    + supports["COR_NB_SC_LAT"] / 3600
)
supports["lon"] = (
    supports["COR_NB_DG_LON"]
    + supports["COR_NB_MN_LON"] / 60
    + supports["COR_NB_SC_LON"] / 3600
)

# Les coordonnées sud et ouest sont négatives.
supports.loc[supports["COR_CD_NS_LAT"] == "S", "lat"] *= -1
supports.loc[supports["COR_CD_EW_LON"] == "W", "lon"] *= -1
supports = supports.dropna(subset=["lat", "lon"])

# Une réponse vide signifie que l'on garde toute la France.
departement = input("Département (vide = toute la France) : ").strip().upper()
if departement != "":
    departement = departement.zfill(2)
    supports = supports[supports["ADR_NM_CP"].str.startswith(departement, na=False)]

# Un support peut être lié à plusieurs stations : on garde ces liens avant
# de réduire le tableau à une ligne par support.
liens_support_stations = supports[["SUP_ID", "STA_NM_ANFR"]].drop_duplicates()
identifiants_supports = supports["SUP_ID"].drop_duplicates()
identifiants_stations = liens_support_stations["STA_NM_ANFR"].drop_duplicates()
supports = supports.drop_duplicates(subset="SUP_ID")


# ---------------------------------------------------------------------------
# 4. Ajout des informations de référence aux supports
# ---------------------------------------------------------------------------

supports = pd.merge(supports, natures, on="NAT_ID", how="left")
supports = pd.merge(supports, proprietaires, on="TPO_ID", how="left")


# ---------------------------------------------------------------------------
# 5. Informations sur les stations et leurs exploitants
# ---------------------------------------------------------------------------

# Cette copie complète sert au graphique, qui porte sur les antennes de tous
# les départements. Le tableau stations ci-dessous sert ensuite à la carte.
stations_toutes = stations.copy()
stations = stations[stations["STA_NM_ANFR"].isin(identifiants_stations)]
stations = pd.merge(stations, exploitants, on="ADM_ID", how="left")
stations["DATE"] = pd.to_datetime(
    stations["DTE_EN_SERVICE"], dayfirst=True, errors="coerce"
)

# On associe les stations à leurs supports, puis on garde les colonnes utiles.
stations_supports = pd.merge(
    liens_support_stations,
    stations[["STA_NM_ANFR", "ADM_LB_NOM", "DATE"]],
    on="STA_NM_ANFR",
    how="left",
)

# Une fonction simple transforme plusieurs valeurs en une seule chaîne.
def valeurs_reunies(serie):
    valeurs = serie.dropna().astype(str).drop_duplicates().sort_values()
    return ", ".join(valeurs)


infos_stations = stations_supports.groupby("SUP_ID").agg(
    exploitants=("ADM_LB_NOM", valeurs_reunies),
    mise_service=("DATE", "min"),
).reset_index()


# ---------------------------------------------------------------------------
# 6. Informations sur les antennes et les émetteurs
# ---------------------------------------------------------------------------

antennes = antennes[antennes["SUP_ID"].isin(identifiants_supports)]
antennes_types = pd.merge(antennes, types_antennes, on="TAE_ID", how="left")

infos_antennes = antennes_types.groupby("SUP_ID").agg(
    nombre_antennes=("AER_ID", "nunique"),
    types_antennes=("TAE_LB", valeurs_reunies),
).reset_index()

emetteurs = emetteurs[emetteurs["STA_NM_ANFR"].isin(identifiants_stations)]
emetteurs_antennes = pd.merge(
    emetteurs,
    antennes[["STA_NM_ANFR", "AER_ID", "SUP_ID"]],
    on=["STA_NM_ANFR", "AER_ID"],
    how="inner",
)

infos_emetteurs = emetteurs_antennes.groupby("SUP_ID").agg(
    systemes=("EMR_LB_SYSTEME", valeurs_reunies)
).reset_index()

# On rassemble toutes les informations dans un seul tableau.
donnees_carte = pd.merge(supports, infos_stations, on="SUP_ID", how="left")
donnees_carte = pd.merge(donnees_carte, infos_antennes, on="SUP_ID", how="left")
donnees_carte = pd.merge(donnees_carte, infos_emetteurs, on="SUP_ID", how="left")


# ---------------------------------------------------------------------------
# 7. Analyse simple des azimuts pour le bilan
# ---------------------------------------------------------------------------

# On relie chaque antenne à sa station et à l'exploitant de cette station.
stations_exploitants = pd.merge(
    stations_toutes[["STA_NM_ANFR", "ADM_ID"]],
    exploitants[["ADM_ID", "ADM_LB_NOM"]],
    on="ADM_ID",
    how="left",
)

# La valeur True signifie que l'azimut de l'antenne n'est pas renseigné.
antennes_analyse = lire_fichier(
    "sup_antenne.txt",
    colonnes=["AER_NB_AZIMUT", "AER_ID", "STA_NM_ANFR", "TAE_ID"],
)
antennes_analyse["AZIMUT_MANQUANT"] = antennes_analyse["AER_NB_AZIMUT"].isna()

# On ajoute à chaque antenne le nom de son exploitant.
antennes_analyse = pd.merge(
    antennes_analyse,
    stations_exploitants,
    on="STA_NM_ANFR",
    how="left",
)

# L'identifiant ADM_ID == "2" est utilisé ici pour le réseau privé,
# conformément au script d'analyse fourni.
antennes_privees = antennes_analyse[antennes_analyse["ADM_ID"] == "2"]
antennes_autres = antennes_analyse[antennes_analyse["ADM_ID"] != "2"]

if len(antennes_privees) > 0:
    taux_prive = antennes_privees["AZIMUT_MANQUANT"].mean() * 100
else:
    taux_prive = 0

if len(antennes_autres) > 0:
    taux_autres = antennes_autres["AZIMUT_MANQUANT"].mean() * 100
else:
    taux_autres = 0

# Le graphique est enregistré comme image puis affiché uniquement dans
# la section « Résultats » de bilan.html.
plt.figure(figsize=(7, 4))
plt.bar(["Réseau privé", "Autres exploitants"], [taux_prive, taux_autres])
plt.title("Pourcentage d’azimuts manquants")
plt.ylabel("Pourcentage (%)")
plt.ylim(0, 100)
plt.tight_layout()
plt.savefig(DOSSIER_PROJET / "graphique_azimuts_exploitants.png")
plt.close()


# ---------------------------------------------------------------------------
# 8. Création des fenêtres d'information des marqueurs
# ---------------------------------------------------------------------------

def texte_html(valeur, valeur_par_defaut="?"):
    """Renvoie une valeur lisible et sans code HTML dangereux."""
    if pd.isna(valeur) or str(valeur).strip() == "":
        return valeur_par_defaut
    return html.escape(str(valeur))


def creer_fenetre(informations):
    """Prépare le contenu affiché quand on clique sur un support."""
    adresse = informations.get("ADR_LB_LIEU")
    if pd.isna(adresse) or str(adresse).strip() == "":
        adresse = informations.get("ADR_LB_ADD1")

    date = informations.get("mise_service")
    if pd.notna(date):
        date = date.strftime("%d/%m/%Y")
    else:
        date = "?"

    contenu = (
        f"<b>{texte_html(adresse, 'Support')}</b><br>"
        f"{texte_html(informations.get('ADR_NM_CP'), '')}<hr>"
        f"<b>Nature :</b> {texte_html(informations.get('NAT_LB_NOM'))}<br>"
        f"<b>Hauteur :</b> {texte_html(informations.get('SUP_NM_HAUT'))} m<br>"
        f"<b>Propriétaire :</b> {texte_html(informations.get('TPO_LB'))}<br>"
        f"<b>Exploitant(s) :</b> {texte_html(informations.get('exploitants'))}<br>"
        f"<b>Mise en service :</b> {date}<br>"
        f"<b>Antennes :</b> {texte_html(informations.get('nombre_antennes'), '0')} "
        f"({texte_html(informations.get('types_antennes'))})<br>"
        f"<b>Systèmes :</b> {texte_html(informations.get('systemes'))}"
    )
    return contenu


# ---------------------------------------------------------------------------
# 9. Création de la carte Folium
# ---------------------------------------------------------------------------

carte = folium.Map(location=[47, 1], zoom_start=6, tiles=None)

# On ajoute des fonds de carte que l'utilisateur peut sélectionner.
folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(carte)
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Tiles © Esri",
    name="Satellite Esri",
).add_to(carte)
folium.TileLayer(
    tiles="https://data.geopf.fr/wmts?REQUEST=GetTile&SERVICE=WMTS&VERSION=1.0.0&STYLE=normal&TILEMATRIXSET=PM&FORMAT=image/png&LAYER=GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}",
    attr="© IGN",
    name="IGN Plan",
).add_to(carte)

print("Nombre de supports affichés :", len(donnees_carte))

if len(donnees_carte) > 0:
    groupe_marqueurs = MarkerCluster(name="Supports").add_to(carte)

    # Une boucle ajoute un marqueur pour chaque ligne du tableau.
    for numero_ligne in range(len(donnees_carte)):
        support = donnees_carte.iloc[numero_ligne]
        fenetre = creer_fenetre(support)

        folium.CircleMarker(
            location=[support["lat"], support["lon"]],
            radius=5,
            color="red",
            fill=True,
            fill_opacity=0.8,
            popup=folium.Popup(fenetre, max_width=350),
        ).add_to(groupe_marqueurs)

    # Le zoom s'adapte aux limites géographiques des supports retenus.
    carte.fit_bounds([
        [donnees_carte["lat"].min(), donnees_carte["lon"].min()],
        [donnees_carte["lat"].max(), donnees_carte["lon"].max()],
    ])

folium.LayerControl().add_to(carte)
carte.save(DOSSIER_PROJET / "carte_code05.html")


# ---------------------------------------------------------------------------
# 10. Création des pages index.html et bilan.html
# ---------------------------------------------------------------------------

style = """
body { font-family: Arial, sans-serif; margin: 0; background: #f4f6f8; color: #2c3e50; }
header, footer { background: #2c3e50; color: white; text-align: center; padding: 15px; }
nav { background: #34495e; text-align: center; padding: 12px; }
nav a { color: white; margin: 0 15px; }
main { padding: 20px; }
.carte { width: 100%; height: 75vh; border: 2px solid #2c3e50; }
.contenu { max-width: 900px; margin: auto; background: white; padding: 25px; line-height: 1.6; }
h2 { color: #c0392b; }
.graphique { display: block; max-width: 100%; height: auto; margin: 20px auto; }
"""

entete = """
<header><h1>SAE 15 – Groupe C2</h1></header>
<nav><a href="index.html">Carte</a><a href="bilan.html">Bilan d'étude</a></nav>
"""

contenu_carte = """
<iframe class="carte" src="carte_code05.html" title="Carte interactive"></iframe>
"""

contenu_bilan = """
<div class="contenu">
  <h2>Introduction</h2>
  <p>Présentez ici le sujet de votre étude et son contexte.</p>
  <h2>Méthode</h2>
  <p>Les fichiers ANFR sont lus avec Pandas. Les supports, stations, antennes,
  émetteurs et fichiers de référence sont reliés grâce à leurs identifiants.</p>
  <h2>Résultats</h2>
  <p>Le graphique compare les pourcentages d'azimuts manquants entre le réseau
  privé et les autres exploitants.</p>
  <img class="graphique" src="graphique_azimuts_exploitants.png"
       alt="Graphique des azimuts manquants par catégorie d'exploitant">
  <h2>Conclusion</h2>
  <p>Présentez ici les observations principales et les limites de l'étude.</p>
</div>
"""


def ecrire_page(nom_fichier, titre, contenu):
    """Crée une page HTML avec le même en-tête et la même feuille de style."""
    page = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{titre}</title>
  <style>{style}</style>
</head>
<body>
{entete}
<main>{contenu}</main>
<footer>SAE 15 – Groupe C2</footer>
</body>
</html>"""

    chemin = DOSSIER_PROJET / nom_fichier
    chemin.write_text(page, encoding="utf-8")


ecrire_page("index.html", "SAE 15 - Carte", contenu_carte)
ecrire_page("bilan.html", "SAE 15 - Bilan d'étude", contenu_bilan)

# Ouvre la page d'accueil dans le navigateur par défaut.
webbrowser.open((DOSSIER_PROJET / "index.html").as_uri())

print("Terminé : index.html, bilan.html, carte_code05.html et le graphique ont été créés.")
