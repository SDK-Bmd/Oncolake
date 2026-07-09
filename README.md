# OncoLake

OncoLake ingère des données biomédicales depuis deux sources publiques, les fait
transiter par trois zones (*raw → staging → curated*), et entraîne un modèle Random Forest 
pour répondre à une question de biologie structurale  
orchestrée par un pipeline reproductible (DVC) et exposé via une API (FastAPI).

---

## La question que l'on se pose : 

> **La forme 3D d'une protéine contient-elle des indices révélant si c'est une
> protéine liée au cancer ? Peut-on distinguer un oncogène d'un suppresseur de
> tumeur rien qu'en regardant sa structure ?**

Deux familles de gènes contrôlent la division cellulaire : les **oncogènes** (les
*accélérateurs*) et les **suppresseurs de tumeur** (les *freins*). 
Un cancer, c'est en grande partie un accélérateur coincé ou un frein
cassé au niveau moléculaire, donc une question de protéines, donc de formes 3D.

**Intuition biologique exploitée :** les protéines du cancer présentent souvent
beaucoup de **régions désordonnées**, impliquées dans
la signalisation et le contrôle de la division. AlphaFold les repère via son score de
confiance **pLDDT** (faible confiance ≈ région probablement désordonnée), ce qui en
fait une feature de choix.

---

## Sources de données (dataset fichier + API)

Le sujet demande **deux sources : un dataset fichier et une source issue d'une API**.
OncoLake les combine ainsi :

| Source | Type | Rôle |
|---|---|---|
| **AlphaFold DB** | **Fichiers** (`.cif`) téléchargés et stockés bruts dans la zone raw | structures 3D pré-calculées + scores pLDDT |
| **UniProt** | **API REST** | séquences + labels (oncogène / suppresseur) + accessions |

**Le pont gène  <-> protéine.** Les listes de gènes du cancer parlent en *noms de gènes*
(`TP53`), AlphaFold est indexé par *accession UniProt* (`P04637`). UniProt fait le
pont : une requête par mot-clé renvoie accession + gène + séquence + label. On
**consomme** les structures déjà calculées d'AlphaFold DB. L'URL des fichiers est résolue via l'**API** AlphaFold
(`/api/prediction/{accession}`) et non codée en dur, pour rester robuste aux
changements de version de la base.

> Mots-clés UniProt utilisés : `KW-0656` (Proto-oncogene) et `KW-0043` (Tumor
> suppressor), filtrés humain (`organism_id:9606`) + *reviewed*.

---

## Installation

**Prérequis :** Python 3.12, [uv](https://docs.astral.sh/uv/), Docker.

```bash
git clone git@github.com:SDK-Bmd/Oncolake.git Oncolake && cd Oncolake

uv venv --python 3.12
source .venv/bin/activate          # Windows : .venv\Scripts\Activate.ps1
uv pip install -e ".[all]"         


docker compose up -d minio minio-setup
# Vérification 
python scripts/check_minio.py 
```

---

## Utilisation

### Option A — le pipeline complet via DVC 
```bash
docker compose up -d minio minio-setup
dvc repro            # exécute ingest → features → curate → train
dvc dag              
dvc metrics show     
```

### Option B — Par script CLI 

```bash
python scripts/ingest.py --limit 20     
python scripts/ingest.py               
python scripts/build_features.py        
python -m oncolake.ml.train     
```

### API Gateway

```bash
python -m uvicorn oncolake.api.main:app --reload   # http://localhost:8000/docs
```

| Endpoint | Méthode | Description |
|---|---|---|
| `/health` | GET | état de la connexion MinIO |
| `/stats` | GET | nombre d'objets par zone |
| `/raw` `/staging` `/curated` | GET | exploration du contenu de chaque zone |
| `/ingest` | POST | ingestion d'un batch de séquences (version naïve, séquentielle, chronométrée) |
| `/ingest_fast` | POST | version optimisée (objectif : battre `/ingest` d'au moins 30 %) |

Exemple de corps pour `/ingest` :

```json
{
  "items": [
    {"accession": "P04637", "sequence": "MEEPQSDPSV..."},
    {"accession": "P01116", "sequence": "MTEYKLVVVG..."}
  ]
}
```

---

## Pipeline DVC (reproductibilité)

Le pipeline (`dvc.yaml`) enchaîne quatre stages, chacun étant un mince adaptateur
(`pipelines/stage_*.py`) qui appelle la logique du package `oncolake` et matérialise
un artefact local suivi par DVC :

| Stage | Entrée | Sortie suivie |
|---|---|---|
| `ingest` | params UniProt/AlphaFold | `data/raw/manifest.json` |
| `features` | manifeste + `.cif` | `data/staging/features.parquet` |
| `curate` | Parquet staging | `data/curated.duckdb` |
| `train` | table curated | `metrics.json` + `data/model.joblib` |

Les artefacts locaux servent à DVC pour
détecter les changements et garantir la reproductibilité.

---

## État des données (après ingestion complète)

| Classe | Protéines (humain, reviewed) |
|---|---|
| Oncogènes (`KW-0656`) | 231 |
| Suppresseurs (`KW-0043`) | 187 |
| **Total ingéré** | **418** |

- **414** protéines disposent d'une structure AlphaFold, **4** non.
- Les 4 sans structure — **KMT2A, APC, ATM, BRCA2** — sont des protéines *géantes*
  (> 2700 résidus), au-delà de la couverture pleine chaîne d'AlphaFold DB. Absence
  légitime, pas un échec de l'ingestion.
- **~5 protéines portent les deux labels** (rôle double). Elles violent l'unicité de
  l'accession attendue en staging ; elles sont arbitrées à l'étape features via une
  politique configurable (`--dual-label drop | oncogene | suppressor | both`,
  défaut `drop`).
- Après arbitrage double-label + retrait des sans-structure : **404 protéines**
  exploitables pour le ML (**225 oncogènes / 179 suppresseurs**).

---

## Résultats du modèle

Modèle : Random Forest (300 arbres), split stratifié 75/25, validation croisée 5 plis.

| Métrique | Valeur |
|---|---|
| Exactitude (test) | 0.50 |
| Exactitude (validation croisée 5 plis) | 0.52 ± 0.04 |
| Baseline (classe majoritaire) | 0.56 |

**Lecture honnête du résultat.** À partir de ces features de **forme globale**
(désordre, compacité, longueur, composition), le modèle **ne bat pas** une baseline
naïve. L'importance des features est quasi uniforme, pas même
le pourcentage de désordre qu'on pensait discriminant. La matrice de confusion montre
que le modèle se rabat sur la classe majoritaire et échoue sur la plupart des
suppresseurs.

**Interprétation biologique.** 
 Oncogènes et suppresseurs sont tous deux des protéines du cancer, aux propriétés
structurales globales proches. Leur différence se joue probablement à une
mutation ponctuelle, partenaires d'interaction qui sont **invisibles pour la silhouette 3D**.
Le pipeline rend ce constat explicite.

---

## Niveau avancé — `/ingest` vs `/ingest_fast`

L'endpoint `/ingest_fast` doit traiter un batch de séquences **au moins 30 % plus
vite** que la version naïve. Leviers : ThreadPoolExecutor / async (httpx) pour
paralléliser les téléchargements AFDB (I/O-bound), Numba sur les calculs de
coordonnées (CPU-bound), vectorisation NumPy pour la composition en acides aminés.


### Benchmarks

Deux mesures complémentaires.

**1. Endpoints API `/ingest` vs `/ingest_fast`** : Reproductible via `scripts/bench_api.py` (API lancée) :

| Batch | `/ingest` (s) | `/ingest_fast` (s) | Gain |
|---|---|---|---|
| 1 élément | 0,26 | 0,10 | 63 % |
| 100 éléments | 11,01 | 1,22 | **89 %** |

**2. Ingestion complète en zone raw** : `scripts/ingest.py` vs
`scripts/ingest_fast.py`, résultats dans `logs/comparison.md` :

| Variante | Temps (s) | Protéines | Débit (prot/s) | Workers |
|---|---|---|---|---|
| `ingest` (naïf, séquentiel) | 53,8 | 418 | 7,8 | 1 |
| `ingest_fast` (ThreadPool) | 11,6 | 418 | 36,2 | 16 |

→ accélération **×4,7**, gain **78,5 %**.

Dans les deux cas, le gain vient de la **parallélisation des téléchargements AlphaFold**
(étape I/O-bound). 