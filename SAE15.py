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
from folium.plugins import MarkerCluster, FeatureGroupSubGroup


# ---------------------------------------------------------------------------
# 1. Dossiers et lecture des fichiers
# ---------------------------------------------------------------------------

# Le script suppose que le dossier courant est la racine du projet.
DOSSIER_PROJET = Path.cwd()
DOSSIER_DATA = DOSSIER_PROJET / "data/data"
DOSSIER_REF = DOSSIER_PROJET / "ref/ref"

# Nombre d'exploitants dans le menu de la carte (les autres vont dans "Autres exploitants")
NB_EXPL = 8


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
# 7 bis. Graphique des exploitants qui ont le plus d'antennes
# ---------------------------------------------------------------------------

def graphique_gros_exploitants(nombre=3):
    """Fait un graphique avec les exploitants qui ont le plus d'antennes."""

    # Une antenne = une ligne (on enlève les doublons)
    antennes_uniques = antennes_analyse[["STA_NM_ANFR", "AER_ID", "ADM_LB_NOM"]].drop_duplicates()

    # On compte les antennes de chaque exploitant, du plus grand au plus petit
    comptes = (
        antennes_uniques.dropna(subset=["ADM_LB_NOM"])
        .groupby("ADM_LB_NOM")
        .size()
        .sort_values(ascending=False)
        .head(nombre)
    )

    # Le graphique est enregistré comme image
    plt.figure(figsize=(7, 4))
    plt.bar(comptes.index, comptes.values)
    plt.title(f"Les {nombre} exploitants avec le plus d'antennes")
    plt.ylabel("Nombre d'antennes")
    plt.tight_layout()
    plt.savefig(DOSSIER_PROJET / "graphique_gros_exploitants.png")
    plt.close()

    return comptes


# On crée le graphique des 3 plus gros exploitants
gros_exploitants = graphique_gros_exploitants(3)
print(gros_exploitants)

# On prépare une phrase pour le bilan avec les noms et les nombres d'antennes
phrase_gros_exploitants = ", ".join(
    f"{html.escape(str(nom))} ({nombre} antennes)"
    for nom, nombre in gros_exploitants.items()
)


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
# 9. Création de la carte Folium (avec choix des exploitants)
# ---------------------------------------------------------------------------

# On crée une carte, centrée sur la France
carte = folium.Map(
    location=[47, 1],        # Position de départ de la carte
    zoom_start=6,            # Zoom au départ
    tiles=None,              # Pas de fond par défaut
    min_zoom=4,              # Zoom minimum
)

# On ajoute les fonds de carte sans avoir besoin de compte ni de clé

# 1. Esri : les rues (fond par défaut)
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/"
          "World_Street_Map/MapServer/tile/{z}/{y}/{x}",
    attr="Tiles © Esri", name="Esri rues", no_wrap=False,
).add_to(carte)

# 2. Esri : la vue satellite
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/"
          "World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Tiles © Esri", name="Esri satellite", no_wrap=False, show=False,
).add_to(carte)

# 3. IGN : la carte officielle française
folium.TileLayer(
    tiles="https://data.geopf.fr/wmts?REQUEST=GetTile&SERVICE=WMTS&VERSION=1.0.0"
          "&STYLE=normal&TILEMATRIXSET=PM&FORMAT=image/png"
          "&LAYER=GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2"
          "&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}",
    attr="© IGN", name="IGN Plan", no_wrap=False, show=False,
).add_to(carte)

# 4. OpenTopoMap : le relief
folium.TileLayer(
    tiles="https://tile.opentopomap.org/{z}/{x}/{y}.png",
    attr="© OpenTopoMap, © OpenStreetMap", name="OpenTopoMap",
    no_wrap=False, show=False,
).add_to(carte)

# On affiche combien de supports sont sur la carte
print("Nombre de supports affichés :", len(donnees_carte))

if len(donnees_carte) > 0:

    # La liste : un support et un de ses exploitants par ligne
    liste = stations_supports[["SUP_ID", "ADM_LB_NOM"]].dropna().drop_duplicates()

    # Les exploitants qui ont le plus de supports (ceux du menu)
    top = liste["ADM_LB_NOM"].value_counts().head(NB_EXPL).index.tolist()

    # Fonction qui choisit le groupe d'un support (un seul groupe par support)
    def choisir_groupe(noms):
        noms = list(noms)

        # Plusieurs exploitants : le support va dans un groupe à part
        if len(noms) > 1:
            return "Plusieurs exploitants"

        # Un seul exploitant : son groupe, ou "Autres exploitants" s'il est petit
        return noms[0] if noms[0] in top else "Autres exploitants"

    # On calcule le groupe de chaque support
    groupes = (
        liste.groupby("SUP_ID")["ADM_LB_NOM"]
        .apply(choisir_groupe)
        .rename("groupe")
        .reset_index()
    )

    # On crée la fenêtre d'information de chaque support
    donnees_carte["fenetre"] = donnees_carte.apply(creer_fenetre, axis=1)

    # On ajoute le groupe à chaque support (1 ligne = 1 support = 1 marqueur)
    carte_df = pd.merge(donnees_carte, groupes, on="SUP_ID", how="left")

    # Les supports sans exploitant trouvé
    carte_df["groupe"] = carte_df["groupe"].fillna("Exploitant inconnu")

    # Un seul groupe de paquets pour toute la carte (pas de ligne dans le menu)
    paquets = MarkerCluster(control=False).add_to(carte)

    # L'ordre dans le menu
    ordre = top + ["Plusieurs exploitants", "Autres exploitants", "Exploitant inconnu"]

    # Pour chaque groupe, on crée une case à cocher dans le menu
    for nom in ordre:
        lignes = carte_df[carte_df["groupe"] == nom]
        if lignes.empty:
            continue

        # Les marqueurs de ce groupe restent regroupés dans les mêmes paquets
        sous_groupe = FeatureGroupSubGroup(paquets, name=f"{nom} ({len(lignes)})")
        sous_groupe.add_to(carte)

        # Un seul marqueur par support, tous avec le même style
        for ligne in lignes.itertuples():
            folium.CircleMarker(
                location=[ligne.lat, ligne.lon],
                radius=5,
                color="red",
                fill=True,
                fill_opacity=0.8,
                popup=folium.Popup(ligne.fenetre, max_width=350),
            ).add_to(sous_groupe)

    # Le zoom s'adapte aux limites géographiques des supports retenus.
    carte.fit_bounds([
        [donnees_carte["lat"].min(), donnees_carte["lon"].min()],
        [donnees_carte["lat"].max(), donnees_carte["lon"].max()],
    ])

# Le menu permet de changer de fond de carte et de choisir les exploitants
folium.LayerControl(collapsed=False).add_to(carte)
carte.save(DOSSIER_PROJET / "carte_code.html")


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
<iframe class="carte" src="carte_code.html" title="Carte interactive"></iframe>
"""

# Les chiffres utilisés dans la conclusion
def espaces(n):
    return f"{int(n):,}".replace(",", " ")      # 155061 devient 155 061

noms = [str(n).title() for n in gros_exploitants.index]   # "BOUYGUES TELECOM" devient "Bouygues Telecom"
nombres = [int(v) for v in gros_exploitants.values]
ecart = (nombres[0] / nombres[2] - 1) * 100               # écart entre le 1er et le 3e
nb_supports = espaces(len(donnees_carte))

# Le f devant les guillemets permet d'insérer les chiffres calculés
contenu_bilan = f"""
<div class="contenu">
  <h2>Introduction</h2>
  <p>L'Agence nationale des fréquences (ANFR) publie les données des installations
  radioélectriques présentes sur le territoire : les supports qui portent les antennes,
  les stations installées dessus, leurs antennes et leurs émetteurs. Ces informations
  sont aussi consultables sur le site Cartoradio.</p>
  <p>Dans le cadre de la SAÉ15, nous avons exploité ces fichiers avec Python pour deux
  objectifs : représenter les supports sur une carte interactive, où chaque marqueur
  donne les informations importantes du support, et analyser les exploitants à partir
  des antennes.</p>
  <p>Nous nous sommes posé deux questions : quels exploitants possèdent le plus
  d'antennes, et les azimuts sont-ils renseignés de la même façon pour le réseau privé
  et pour les autres exploitants ?</p>

  <h2>Méthode</h2>
  <p>Les fichiers ANFR sont lus avec Pandas. Les supports, stations, antennes,
  émetteurs et fichiers de référence sont reliés grâce à leurs identifiants.</p>

  <h2>Résultats</h2>
  <p>Le graphique compare les pourcentages d'azimuts manquants entre le réseau
  privé et les autres exploitants.</p>
  <img class="graphique" src="graphique_azimuts_exploitants.png"
       alt="Graphique des azimuts manquants par catégorie d'exploitant">
  <p>Le second graphique montre les trois exploitants qui possèdent le plus
  d'antennes : {phrase_gros_exploitants}.</p>
  <img class="graphique" src="graphique_gros_exploitants.png"
       alt="Graphique des trois exploitants avec le plus d'antennes">

  <h2>Conclusion</h2>
  <p>Cette étude montre que {noms[0]}, {noms[1]} et {noms[2]} sont les trois exploitants
  qui possèdent le plus d'antennes, avec respectivement {espaces(nombres[0])},
  {espaces(nombres[1])} et {espaces(nombres[2])} antennes. L'écart entre le premier et
  le troisième est d'environ {ecart:.0f} %, donc ces trois opérateurs ont des parcs
  d'antennes comparables. La carte interactive affiche {nb_supports} supports et permet
  de consulter, pour chacun, son adresse, sa hauteur, son propriétaire, ses exploitants,
  ses antennes et ses systèmes.</p>
  <p>Pour les azimuts, {taux_prive:.0f} % des antennes du réseau privé n'ont pas
  d'azimut renseigné, contre {taux_autres:.0f} % pour les autres exploitants. Ce résultat
  ne prouve pas à lui seul un défaut de déclaration : d'après la description des
  fichiers ANFR, l'azimut n'est donné que pour les antennes à rayonnement directif, et
  une antenne omnidirectionnelle n'en a pas. Il faudrait comparer avec le type de
  rayonnement des antennes pour le confirmer.</p>
  <p>Cette étude a plusieurs limites. Les graphiques portent sur toute la France, alors
  que la carte dépend du département choisi. Les données correspondent à un état à une
  date précise. Le réseau privé est repéré par l'identifiant d'exploitant 2, comme dans
  le script d'analyse fourni. Enfin, un support peut accueillir plusieurs exploitants, et
  on compte donc les antennes et non les supports pour comparer les exploitants.</p>
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

print("Terminé : index.html, bilan.html, carte_code.html et les graphiques ont été créés.")