import pandas as pd

# 1. Chemins des fichiers ANFR


fichier_station = "data/sup_station.txt"
fichier_antenne = "data/sup_antenne.txt"
fichier_support = "data/sup_support.txt"
fichier_emetteur = "data/sup_emetteur.txt"
fichier_bande = "data/sup_bande.txt"


# 2. Chargement des données

stations = pd.read_csv(
    fichier_station, sep=";", encoding="utf-8", dtype=str
)

antennes = pd.read_csv(
    fichier_antenne, sep=";", encoding="utf-8", dtype=str
)

supports = pd.read_csv(
    fichier_support, sep=";", encoding="utf-8", dtype=str
)

emetteurs = pd.read_csv(
    fichier_emetteur, sep=";", encoding="utf-8", dtype=str
)

bandes = pd.read_csv(
    fichier_bande, sep=";", encoding="utf-8", dtype=str
)

# 3. Vérification des données


print("===== DONNEES ANFR =====")

print("Nombre de stations :", len(stations))
print("Nombre d'antennes :", len(antennes))
print("Nombre de supports :", len(supports))
print("Nombre d'émetteurs :", len(emetteurs))
print("Nombre de bandes :", len(bandes))

# 4. Affichage des premières lignes

print("\n===== APERCU DES STATIONS =====")
print(stations.head())

print("\n===== COLONNES DES STATIONS =====")
print(stations.columns)

print(supports.dtypes)

# Vérification des valeurs manquantes

print("Valeurs manquantes dans les stations :")
print(stations.isnull().sum())

print("Valeurs manquantes dans les supports :")
print(supports.isnull().sum())


print("Valeurs manquantes dans les antennes :")
print(antennes.isnull().sum())

print("Valeurs manquantes dans les emetteurs :")
print(emetteurs.isnull().sum())

print("Valeurs manquantes dans les bandes")
print (bandes.isnull().sum())

# Tableau récapitulatif des valeurs manquantes

bilan = pd.DataFrame({
    "Fichier": ["Stations", "Antennes", "Supports", "Emetteurs", "Bandes"],
    "Valeurs manquantes": [
        stations.isnull().sum().sum(),
        antennes.isnull().sum().sum(),
        supports.isnull().sum().sum(),
        emetteurs.isnull().sum().sum(),
        bandes.isnull().sum().sum()
    ]
})

print("BILAN DES VALEURS MANQUANTES")
print(bilan)

#- isnull() détecte les valeurs manquantes.
# Le premier sum() les compte par colonne.
#- Le deuxième sum() additionne les résultats pour obtenir le total du fichier.
#- DataFrame() construit un tableau récapitulatif.

#possible que l'azimut est beaoup plus de trous (valeurs manquantes) car possiblement amateur avec raddio ne savent as comment le remplir 