# Lille Ciné

Les séances des 17 cinémas de la métropole lilloise sur une seule page (sur le modèle de paris-cine.info).

- `scrape.py` récupère 7 jours de séances sur AlloCiné et écrit `data.json` et `posters/`.
- `index.html` est le site (statique, sans dépendance).

## En local

    python scrape.py
    python -m http.server 8000   # puis http://localhost:8000

## En ligne, mis à jour tous les jours

Le site est publié par GitHub Pages (source : GitHub Actions).
Le workflow `.github/workflows/update.yml` relance la collecte chaque matin et republie le site.

Pour ajouter un cinéma, ajoutez son code AlloCiné dans `CINEMAS` (`scrape.py`).
