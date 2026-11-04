# Audit OSM des cheminements piétons — Nancy

`audit-osm-pietons-nancy.pdf` : rapport de 2 pages, PDF balisé (structure, titres, tableaux avec en-têtes,
texte alternatif des cartes, langue fr-FR, métadonnées).

Chaîne de génération :

```bash
bash dl.sh data                                   # tuiles OSM via l'API 0.6 (+ data/boundary.json, relation 52399)
python3 analyse.py data res.pkl                   # trottoirs, passages, bordures, feux, zones
python3 contrib.py data contrib.pkl               # auteurs des dernières modifications des trottoirs
python3 zone_kerb.py data res.pkl zk.pkl          # trottoirs sans info bordure / podotactile
python3 report_html.py res.pkl out 2026-11-04 fonts contrib.pkl zk.pkl   # cartes + HTML sémantique
node render_pdf.js out/audit.html out/tagged.pdf  # Chromium : PDF balisé
python3 metadata.py out/tagged.pdf audit-osm-pietons-nancy.pdf          # contenu décoratif en Artifact + métadonnées
python3 a11y_check.py audit-osm-pietons-nancy.pdf   # contrôles PDF/UA principaux + ordre de lecture des balises
```

`fonts/` doit contenir les TTF Inter (https://github.com/rsms/inter, dossier `extras/ttf`).

`controle-accessibilite.txt` : résultat du contrôle (critères + ordre de lecture tel qu'un lecteur d'écran le suit).
