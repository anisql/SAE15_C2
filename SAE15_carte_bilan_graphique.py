"""SAE 15 : carte des supports radio et bilan des azimuts ANFR."""

from pathlib import Path
import html
import webbrowser

import folium
import matplotlib.pyplot as plt
import pandas as pd
from folium.plugins import MarkerCluster, FeatureGroupSubGroup


# ---------------------------------------------------------------------------
# 1. DOSSIER DU PROJET
# ---------------------------------------------------------------------------

# Chemin absolu du dossier du projet.
DOSSIER_PROJET = Path.cwd()
DOSSIER_DATA = DOSSIER_PROJET / "data/data"
DOSSIER_REF = DOSSIER_PROJET / "ref/ref"


# ---------------------------------------------------------------------------
# 2. LECTURE DES FICHIERS
# ---------------------------------------------------------------------------

def lire_fichier(chemin):
    """Ouvre un fichier ANFR séparé par des points-virgules."""
    if not chemin.exists():
        print("Fichier introuvable :", chemin)
        raise FileNotFoundError(chemin)

    tableau = pd.read_csv(chemin, sep=";", dtype=str, encoding="utf-8-sig")

    # Les noms de colonnes sont nettoyés pour éviter les espaces inattendus.
    nouveaux_noms = []
    for nom in tableau.columns:
        nouveaux_noms.append(nom.strip().upper())
    tableau.columns = nouveaux_noms
    return tableau


def valeurs_texte(liste):
    """Retire les doublons d'une liste et les assemble dans une phrase."""
    liste_sans_doublons = []
    for valeur in liste:
        if valeur is not None and valeur != "" and valeur not in liste_sans_doublons:
            liste_sans_doublons.append(str(valeur))
    liste_sans_doublons.sort()
    return ", ".join(liste_sans_doublons)


def texte_html(valeur, remplacement="?"):
    """Prépare une valeur pour l'afficher sans risque dans une fenêtre HTML."""
    if pd.isna(valeur) or str(valeur).strip() == "":
        return remplacement
    return html.escape(str(valeur))


def creer_fenetre(support):
    """Construit le texte visible lorsque l'on clique sur un marqueur."""
    adresse = support.get("ADR_LB_LIEU")
    if pd.isna(adresse) or str(adresse).strip() == "":
        adresse = support.get("ADR_LB_ADD1")

    date = support.get("mise_service")
    if pd.notna(date):
        date = date.strftime("%d/%m/%Y")
    else:
        date = "?"

    texte = (
        "<b>" + texte_html(adresse, "Support") + "</b><br>"
        + texte_html(support.get("ADR_NM_CP"), "") + "<hr>"
        + "<b>Nature :</b> " + texte_html(support.get("NAT_LB_NOM")) + "<br>"
        + "<b>Hauteur :</b> " + texte_html(support.get("SUP_NM_HAUT")) + " m<br>"
        + "<b>Propriétaire :</b> " + texte_html(support.get("TPO_LB")) + "<br>"
        + "<b>Exploitant(s) :</b> " + texte_html(support.get("exploitants")) + "<br>"
        + "<b>Mise en service :</b> " + date + "<br>"
        + "<b>Antennes :</b> " + texte_html(support.get("nombre_antennes"), "0")
        + " (" + texte_html(support.get("types_antennes")) + ")<br>"
        + "<b>Systèmes :</b> " + texte_html(support.get("systemes"))
    )
    return texte


# Les fichiers sont cherchés dans les dossiers data/ et ref/ à côté du projet.
supports = lire_fichier(DOSSIER_DATA / "sup_support.txt")
stations = lire_fichier(DOSSIER_DATA / "sup_station.txt")
antennes = lire_fichier(DOSSIER_DATA / "sup_antenne.txt")
emetteurs = lire_fichier(DOSSIER_DATA / "sup_emetteur.txt")

natures = lire_fichier(DOSSIER_REF / "sup_nature.txt")
proprietaires = lire_fichier(DOSSIER_REF / "sup_proprietaire.txt")
exploitants = lire_fichier(DOSSIER_REF / "sup_exploitant.txt")
types_antennes = lire_fichier(DOSSIER_REF / "sup_type_antenne.txt")


# ---------------------------------------------------------------------------
# 3. COORDONNÉES ET CHOIX DU DÉPARTEMENT
# ---------------------------------------------------------------------------

# L'ANFR donne les coordonnées en degrés, minutes et secondes.
colonnes_coordonnees = [
    "COR_NB_DG_LAT", "COR_NB_MN_LAT", "COR_NB_SC_LAT",
    "COR_NB_DG_LON", "COR_NB_MN_LON", "COR_NB_SC_LON",
]
for nom in colonnes_coordonnees:
    supports[nom] = pd.to_numeric(supports[nom], errors="coerce")

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

# Les coordonnées situées au sud ou à l'ouest sont négatives.
for numero in range(len(supports)):
    if supports.iloc[numero]["COR_CD_NS_LAT"] == "S":
        supports.iloc[numero, supports.columns.get_loc("lat")] *= -1
    if supports.iloc[numero]["COR_CD_EW_LON"] == "W":
        supports.iloc[numero, supports.columns.get_loc("lon")] *= -1

supports = supports.dropna(subset=["lat", "lon"])

departement = input("Choisissez un département (laisser vide pour toute la France) : ")
departement = departement.strip().upper()
if departement != "":
    departement = departement.zfill(2)
    supports = supports[supports["ADR_NM_CP"].str.startswith(departement, na=False)]

# On mémorise les liens avant de ne garder qu'une ligne par support.
liens_support_stations = supports[["SUP_ID", "STA_NM_ANFR"]].drop_duplicates()
identifiants_supports = supports["SUP_ID"].drop_duplicates()
identifiants_stations = liens_support_stations["STA_NM_ANFR"].drop_duplicates()
supports = supports.drop_duplicates(subset="SUP_ID")


# ---------------------------------------------------------------------------
# 4. INFORMATIONS DES FICHIERS DE RÉFÉRENCE
# ---------------------------------------------------------------------------

supports = pd.merge(supports, natures, on="NAT_ID", how="left")
supports = pd.merge(supports, proprietaires, on="TPO_ID", how="left")

stations_toutes = stations.copy()
stations = stations[stations["STA_NM_ANFR"].isin(identifiants_stations)]
stations = pd.merge(stations, exploitants, on="ADM_ID", how="left")
stations["DATE"] = pd.to_datetime(
    stations["DTE_EN_SERVICE"], dayfirst=True, errors="coerce"
)

# Prépare un dictionnaire : pour chaque station, on garde son exploitant
# et sa date de mise en service.
infos_station = {}
for numero in range(len(stations)):
    station = stations.iloc[numero]
    nom_station = station["STA_NM_ANFR"]
    infos_station[nom_station] = {
        "exploitant": station.get("ADM_LB_NOM"),
        "date": station["DATE"],
    }

# Pour chaque support, rassemble les exploitants et prend la date la plus
# ancienne parmi les stations reliées à ce support.
infos_support_stations = {}
for numero in range(len(liens_support_stations)):
    lien = liens_support_stations.iloc[numero]
    id_support = lien["SUP_ID"]
    id_station = lien["STA_NM_ANFR"]

    if id_support not in infos_support_stations:
        infos_support_stations[id_support] = {"exploitants": [], "dates": []}

    if id_station in infos_station:
        exploitant = infos_station[id_station]["exploitant"]
        date = infos_station[id_station]["date"]
        if pd.notna(exploitant):
            infos_support_stations[id_support]["exploitants"].append(exploitant)
        if pd.notna(date):
            infos_support_stations[id_support]["dates"].append(date)


# ---------------------------------------------------------------------------
# 5. INFORMATIONS DES ANTENNES ET DES ÉMETTEURS
# ---------------------------------------------------------------------------

antennes = antennes[antennes["SUP_ID"].isin(identifiants_supports)]
infos_support_antennes = {}
# Ce dictionnaire permet de retrouver le nom d'un type sans reparcourir
# tout le fichier de référence pour chaque antenne.
noms_types_antennes = {}
for numero in range(len(types_antennes)):
    type_antenne = types_antennes.iloc[numero]
    noms_types_antennes[type_antenne["TAE_ID"]] = type_antenne.get("TAE_LB")

# On mémorise aussi le support de chaque antenne pour retrouver rapidement
# les antennes associées à un émetteur.
supports_par_antenne = {}
for numero in range(len(antennes)):
    antenne = antennes.iloc[numero]
    id_support = antenne["SUP_ID"]
    if id_support not in infos_support_antennes:
        infos_support_antennes[id_support] = {"ids": [], "types": []}

    id_antenne = antenne["AER_ID"]
    if id_antenne not in infos_support_antennes[id_support]["ids"]:
        infos_support_antennes[id_support]["ids"].append(id_antenne)

    cle_antenne = (antenne["STA_NM_ANFR"], antenne["AER_ID"])
    supports_par_antenne[cle_antenne] = id_support

    nom_type = noms_types_antennes.get(antenne["TAE_ID"])
    if pd.notna(nom_type):
        infos_support_antennes[id_support]["types"].append(nom_type)

infos_support_emetteurs = {}
for numero in range(len(emetteurs)):
    emetteur = emetteurs.iloc[numero]
    cle_antenne = (emetteur["STA_NM_ANFR"], emetteur["AER_ID"])
    if cle_antenne in supports_par_antenne:
        id_support = supports_par_antenne[cle_antenne]
        if id_support not in infos_support_emetteurs:
            infos_support_emetteurs[id_support] = []
        infos_support_emetteurs[id_support].append(emetteur.get("EMR_LB_SYSTEME"))

# Ajoute les informations préparées aux lignes des supports.
donnees_carte = []
for numero in range(len(supports)):
    support = supports.iloc[numero].copy()
    id_support = support["SUP_ID"]

    support["exploitants"] = "?"
    support["mise_service"] = pd.NaT
    support["nombre_antennes"] = 0
    support["types_antennes"] = "?"
    support["systemes"] = "?"

    if id_support in infos_support_stations:
        infos = infos_support_stations[id_support]
        support["exploitants"] = valeurs_texte(infos["exploitants"])
        if len(infos["dates"]) > 0:
            support["mise_service"] = min(infos["dates"])

    if id_support in infos_support_antennes:
        infos = infos_support_antennes[id_support]
        support["nombre_antennes"] = len(infos["ids"])
        support["types_antennes"] = valeurs_texte(infos["types"])

    if id_support in infos_support_emetteurs:
        support["systemes"] = valeurs_texte(infos_support_emetteurs[id_support])

    donnees_carte.append(support)


# ---------------------------------------------------------------------------
# 6. BILAN DES AZIMUTS MANQUANTS ET GRAPHIQUE
# ---------------------------------------------------------------------------

stations_exploitants = pd.merge(
    stations_toutes[["STA_NM_ANFR", "ADM_ID"]],
    exploitants[["ADM_ID", "ADM_LB_NOM"]],
    on="ADM_ID",
    how="left",
)

# Relie chaque support aux noms de ses exploitants pour créer les filtres de la carte.
stations_supports = pd.merge(
    liens_support_stations[["SUP_ID", "STA_NM_ANFR"]],
    stations_exploitants[["STA_NM_ANFR", "ADM_LB_NOM"]],
    on="STA_NM_ANFR",
    how="left",
)

# Le fichier des antennes contient les valeurs d'azimut utilisées au bilan.
# On le relit en entier : le graphique porte sur tous les départements,
# même si un département a été choisi pour afficher la carte.
antennes_analyse = lire_fichier(DOSSIER_DATA / "sup_antenne.txt")
antennes_analyse["AZIMUT_MANQUANT"] = antennes_analyse["AER_NB_AZIMUT"].isna()
antennes_analyse = pd.merge(
    antennes_analyse,
    stations_exploitants[["STA_NM_ANFR", "ADM_ID", "ADM_LB_NOM"]],
    on="STA_NM_ANFR",
    how="left",
)

# Dans le script fourni, ADM_ID égal à "2" désigne le réseau privé.
nombre_prive = 0
azimuts_prives_manquants = 0
nombre_autres = 0
azimuts_autres_manquants = 0

for numero in range(len(antennes_analyse)):
    antenne = antennes_analyse.iloc[numero]
    if antenne["ADM_ID"] == "2":
        nombre_prive += 1
        if antenne["AZIMUT_MANQUANT"]:
            azimuts_prives_manquants += 1
    else:
        nombre_autres += 1
        if antenne["AZIMUT_MANQUANT"]:
            azimuts_autres_manquants += 1

taux_prive = 0
if nombre_prive > 0:
    taux_prive = azimuts_prives_manquants / nombre_prive * 100

taux_autres = 0
if nombre_autres > 0:
    taux_autres = azimuts_autres_manquants / nombre_autres * 100

plt.figure(figsize=(7, 4))
plt.bar(["Réseau privé", "Autres exploitants"], [taux_prive, taux_autres])
plt.title("Pourcentage d'azimuts manquants")
plt.ylabel("Pourcentage (%)")
plt.ylim(0, 100)
plt.tight_layout()
plt.savefig(DOSSIER_PROJET / "graphique_azimuts_exploitants.png")
plt.close()


# ---------------------------------------------------------------------------
# 7. Graphique des exploitants qui ont le plus d'antennes
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
# 8. CRÉATION DE LA CARTE FOLIUM
# ---------------------------------------------------------------------------

carte = folium.Map(location=[47, 1], zoom_start=6, tiles=None)

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
# Nombre d'exploitants principaux affichés séparément dans le menu.
NB_EXPL = 5

print("Nombre de supports affichés :", len(donnees_carte))

if len(donnees_carte) > 0:
    # Prépare les données de la carte.
    donnees_carte = pd.DataFrame(donnees_carte)

    # Trouve les principaux exploitants en fonction du nombre de supports.
    liste = stations_supports[["SUP_ID", "ADM_LB_NOM"]].dropna().drop_duplicates()
    top = liste["ADM_LB_NOM"].value_counts().head(NB_EXPL).index.tolist()

    # Attribue un seul groupe à chaque support.
    groupes = liste.groupby("SUP_ID")["ADM_LB_NOM"].apply(
        lambda noms: "Plusieurs exploitants" if len(noms) > 1
        else noms.iloc[0] if noms.iloc[0] in top
        else "Autres exploitants"
    )

    donnees_carte["groupe"] = donnees_carte["SUP_ID"].map(groupes).fillna("Exploitant inconnu")
    donnees_carte["fenetre"] = donnees_carte.apply(creer_fenetre, axis=1)

    # Regroupe les marqueurs et ajoute une case à cocher par catégorie.
    paquets = MarkerCluster(control=False).add_to(carte)

    for nom in top + ["Plusieurs exploitants", "Autres exploitants", "Exploitant inconnu"]:
        lignes = donnees_carte[donnees_carte["groupe"] == nom]

        if not lignes.empty:
            groupe = FeatureGroupSubGroup(paquets, name=f"{nom} ({len(lignes)})")
            groupe.add_to(carte)

            for ligne in lignes.itertuples():
                folium.Marker(
                    [ligne.lat, ligne.lon],
                    popup=folium.Popup(ligne.fenetre, max_width=350),
                ).add_to(groupe)

    # Ajuste automatiquement le zoom aux supports affichés.
    carte.fit_bounds([
        [donnees_carte["lat"].min(), donnees_carte["lon"].min()],
        [donnees_carte["lat"].max(), donnees_carte["lon"].max()],
    ])

folium.LayerControl().add_to(carte)
carte.save(DOSSIER_PROJET / "carte_code.html")


# ---------------------------------------------------------------------------
# 9. PAGES HTML : LA CARTE ET LE BILAN
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

# La page d'accueil affiche la carte enregistrée sous carte_code.html.
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
    """Enregistre une page HTML dans le dossier du projet."""
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

# Ouvre le site local dans le navigateur par défaut.
webbrowser.open((DOSSIER_PROJET / "index.html").as_uri())
print("Terminé : ouvrez index.html pour voir la carte et le bilan.")