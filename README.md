# SAE 15 — Analyse des données ANFR

## Français

### Le projet

Ce projet a été réalisé pour la SAE 15 du BUT Réseaux et Télécommunications. Il utilise des fichiers de l’ANFR pour afficher des supports radio sur une carte et étudier les azimuts des antennes.

### Comment nous avons travaillé

J’ai d’abord préparé un algorithme pour organiser les étapes du programme. J’ai ensuite analysé les azimuts des antennes.

Après cette première partie, nous avons réuni les différents éléments du projet. Un camarade a réalisé la partie HTML, puis nous l’avons intégrée au programme. Le code Python lit les fichiers ANFR, prépare les informations et crée la carte et les pages du site.

### Ce que fait le programme

- Il lit les fichiers ANFR dans les dossiers `data/` et `ref/`.
- Il peut afficher les supports d’un département choisi.
- Il crée une carte interactive avec des marqueurs et des fenêtres d’information.
- Il crée les pages `index.html` et `bilan.html`.
- Il affiche un graphique sur les azimuts manquants dans la partie « Résultats » du bilan.

### Pour lancer le programme

Les dossiers `data/` et `ref/` doivent être à côté du fichier Python.

Installe les bibliothèques nécessaires :

```bash
pip install pandas folium matplotlib
```

Puis lance le programme depuis le dossier du projet :

```bash
python3 SAE15.py
```

Quand le programme demande un département, écris son numéro. Laisse la réponse vide pour afficher tous les départements.

---

## English

### The project

This project was made for the SAE 15 assignment in the Networks and Telecommunications BUT programme. It uses ANFR files to show radio sites on a map and study antenna azimuths.

### How we worked

I first planned an algorithm to organize the steps of the programme. Then I analysed the antenna azimuths.

After that, we brought the different parts of the project together. A classmate made the HTML part, and we added it to the programme. The Python code reads the ANFR files, prepares the information, and creates the map and website pages.

### What the programme does

- It reads ANFR files from the `data/` and `ref/` folders.
- It can show radio sites for a selected department.
- It creates an interactive map with markers and information windows.
- It creates the `index.html` and `bilan.html` pages.
- It shows a chart about missing azimuths in the Results section of the report.

### How to run the programme

The `data/` and `ref/` folders must be next to the Python file.

Install the required libraries:

```bash
pip install pandas folium matplotlib
```

Then run the programme from the project folder:

```bash
python3 SAE15.py
```

When asked for a department, enter its number. Leave the answer empty to show all departments.