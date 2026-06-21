# OncoLake

> Data lake de bout en bout pour la classification de protéines liées au cancer.
> Projet final — **Data Lakes & Data Integration**, EFREI 2025-2026.

OncoLake ingère des données biomédicales depuis deux APIs publiques, les fait
transiter par trois zones (*raw → staging → curated*), et entraîne un modèle de
Machine Learning pour répondre à une question de biologie structurale — le tout
orchestré par un pipeline reproductible et exposé via une API.

---

## Question scientifique

> **La forme 3D d'une protéine contient-elle des indices révélant si c'est une
> protéine liée au cancer ? Peut-on distinguer un oncogène d'un suppresseur de
> tumeur rien qu'en regardant sa structure ?**

Deux familles de gènes contrôlent la division cellulaire : les **oncogènes** (les
*accélérateurs* — « multiplie-toi ») et les **suppresseurs de tumeur** (les *freins*
— « stop »). Un cancer, c'est en grande partie un accélérateur coincé ou un frein
cassé au niveau moléculaire, donc une question de protéines, donc de formes 3D.

**Intuition biologique exploitée :** les protéines du cancer présentent souvent
beaucoup de **régions désordonnées** (zones mobiles, non repliées en forme rigide),
impliquées dans la signalisation et le contrôle de la division. AlphaFold les repère
via son score de confiance **pLDDT** (faible confiance ≈ région probablement
désordonnée), ce qui en fait une feature de choix.

---

## Vue d'ensemble

```
       ┌────────────────────┐      ┌──────────────────────────┐
       │   API UniProt       │      │   API AlphaFold (AFDB)    │
       │   gène, séquence,   │      │   structure 3D (.cif)     │
       │   accession, label  │      │   + pLDDT, via accession  │
       └─────────┬───────────┘      └────────────┬─────────────┘
                 │                                │
                 ▼                                ▼
   ┌─────────────────────────────────────────────────────────────┐
   │  DATA LAKE                                                    │
   │   raw (MinIO)      JSON UniProt brut + .cif + manifest.json   │
   │       │                                                       │
   │       ▼                                                       │
   │   staging (Parquet)   features : pLDDT, % désordre, Rg,       │
   │       │               longueur, composition en acides aminés │
   │       ▼                                                       │
   │   curated (DuckDB)    vecteurs propres + label, prêts ML      │
   └───────────────────────────────┬─────────────────────────────┘
                                    ▼
                        ┌──────────────────────────┐
                        │   Random Forest           │
                        │   oncogène vs suppresseur │
                        │   + matrice de confusion  │
                        └──────────────────────────┘

   Transverses :
   • Pipeline DVC : ingest → features → curate → train (reproductible)
   • API FastAPI  : /raw /staging /curated /health /stats /ingest /ingest_fast
```

---

## Sources de données

| Source | Rôle | Accès |
|---|---|---|
| **UniProt** | séquences + labels (oncogène / suppresseur) + accessions | API REST, mots-clés `KW-0656` (Proto-oncogene) et `KW-0043` (Tumor suppressor), filtrés humain + *reviewed* |
| **AlphaFold DB** | structures 3D pré-calculées (`.cif`) + scores pLDDT | API publique `alphafold.ebi.ac.uk` |

**Le pont gène ↔ protéine.** Les listes de gènes du cancer parlent en *noms de gènes*
(`TP53`), AlphaFold est indexé par *accession UniProt* (`P04637`). UniProt fait le
pont : interroger par mot-clé renvoie en une seule requête accession + gène +
séquence + label. On ne fait **pas** tourner AlphaFold soi-même (trop lourd) — on
consomme les structures déjà calculées de l'AlphaFold Protein Structure Database.

> ⚠️ L'URL des fichiers est résolue via l'**API** AlphaFold (`/api/prediction/{accession}`)
> et non codée en dur (`…-model_v4.cif`), pour rester robuste aux changements de
> version de la base (actuellement **v6**).

---

## Architecture — les trois zones

| Zone | Techno | Contenu |
|---|---|---|
| **raw** | MinIO (objet, compatible S3) | JSON UniProt brut, fichiers `.cif` AlphaFold non transformés, `manifest.json` |
| **staging** | Parquet (sur MinIO), traité en pandas | features extraites : pLDDT moyen, % de résidus faible confiance (proxy désordre), longueur de séquence, composition en acides aminés, rayon de giration (compacité) |
| **curated** | DuckDB | vecteurs de features nettoyés + label oncogène/suppresseur, prêts pour le ML |

Le **manifeste** (`raw/manifest.json`) joue le rôle de table d'index entre les zones :
il liste chaque protéine avec son label, sa séquence, et un drapeau `has_structure`.

---

## Stack technique

| Composant | Outil | Justification |
|---|---|---|
| Stockage zone raw | **MinIO** | object store S3-compatible, vraie console + persistance (remplace LocalStack) |
| Parsing structures | **gemmi** | lecture mmCIF rapide ; pLDDT lu directement dans le champ B-factor |
| Manipulation données | **pandas** | tables de features de la zone staging |
| Base curated | **DuckDB** | SQL analytique en process, lit le Parquet directement depuis MinIO (`httpfs`) |
| Orchestration | **DVC** | pipeline reproductible et versionné (`ingest → features → curate → train`) |
| Contrats de schéma | **Pydantic** | validation des données aux frontières de zones + I/O de l'API |
| API Gateway | **FastAPI** | exposition des zones + endpoints d'ingestion |
| HTTP async | **httpx** | appels concurrents pour le endpoint optimisé |
| Calcul optimisé | **Numba** | JIT sur les calculs de coordonnées atomiques (niveau avancé) |
| Modèle ML | **scikit-learn** (Random Forest) | interprétable → quelles features comptent |

Runtime : **Python 3.12**, dépendances gérées avec **uv**, conteneurs via Docker
Compose.

---

## Installation

**Prérequis :** Python 3.12, [uv](https://docs.astral.sh/uv/), Docker.

```bash
# 1. Environnement virtuel + dépendances
uv venv --python 3.12
source .venv/bin/activate          # Windows : .venv\Scripts\Activate.ps1
uv pip install -e ".[dev]"

# 2. Configuration (les valeurs par défaut pointent sur le MinIO local)
cp .env.example .env

# 3. Démarrer MinIO + créer les buckets raw / staging / curated
docker compose up -d minio minio-setup

# 4. Vérifier que le stockage répond
python scripts/check_minio.py      # attendu : "Tout est operationnel."
```

Groupes d'extras optionnels : `.[ml]` (entraînement), `.[perf]` (Numba), `.[dev]`
(tests + lint), `.[all]`.

---

## Utilisation

### Ingestion vers la zone raw

```bash
python scripts/ingest.py --limit 20    # test rapide (20 protéines par classe)
python scripts/ingest.py               # ingestion complète
```

Pour chaque classe, le script interroge UniProt, dépose le JSON brut dans
`raw/uniprot/{label}.json`, télécharge chaque structure dans
`raw/alphafold/{accession}.cif`, et écrit le manifeste. Les protéines sans structure
AlphaFold sont loguées et écartées proprement.

### API Gateway

```bash
uvicorn oncolake.api.main:app --reload     # http://localhost:8000/docs
```

| Endpoint | Description |
|---|---|
| `GET /health` | état de la connexion MinIO |
| `GET /stats` | nombre d'objets par zone |
| `GET /raw` `/staging` `/curated` | exploration de chaque zone |
| `POST /ingest` | ingestion d'un batch de séquences (version naïve, séquentielle) |
| `POST /ingest_fast` | version optimisée (objectif : battre `/ingest` d'au moins 30 %) |

---

## État des données (après ingestion complète)

| Classe | Protéines (humain, reviewed) |
|---|---|
| Oncogènes (`KW-0656`) | 231 |
| Suppresseurs (`KW-0043`) | 187 |
| **Total** | **418** |

- **414** protéines disposent d'une structure AlphaFold, **4** non.
- Les 4 sans structure — **KMT2A, APC, ATM, BRCA2** — sont des protéines *géantes*
  (toutes > 2700 résidus), au-delà de la couverture en modèle pleine chaîne
  d'AlphaFold DB. Absence légitime, et non un échec de l'ingestion.
- **~5 protéines portent les deux labels** (rôle double oncogène *et* suppresseur).
  Elles apparaissent dans les deux requêtes → deux entrées de manifeste mais un seul
  `.cif`. Ce conflit d'étiquette sera arbitré en zone curated (écarter / prioriser /
  classe « both ») avant l'entraînement.

> Ce dernier point illustre l'honnêteté scientifique attendue : la vérité terrain
> n'est pas toujours binaire, et le pipeline le rend explicite plutôt que de le
> masquer.

---

## Structure du dépôt

```
oncolake/
├── docker-compose.yml          # MinIO + buckets + API
├── Dockerfile                  # image de l'API (uv, Python 3.12)
├── pyproject.toml              # dépendances + extras [ml] [perf] [dev]
├── dvc.yaml / params.yaml      # pipeline reproductible + paramètres
├── scripts/
│   ├── check_minio.py          # vérification du stockage
│   └── ingest.py               # étape 1 : ingestion → raw
├── src/oncolake/
│   ├── config/settings.py      # configuration (pydantic-settings)
│   ├── schemas.py              # contrats Pydantic des données
│   ├── lake/
│   │   ├── storage.py          # accès objets MinIO (boto3)
│   │   └── warehouse.py        # connexion DuckDB ↔ MinIO
│   ├── ingest/                 # connecteurs UniProt + AlphaFold
│   ├── features/extract.py     # extraction de features (gemmi)
│   ├── curate/build.py         # staging → table DuckDB
│   ├── ml/train.py             # Random Forest
│   └── api/main.py             # API FastAPI
├── notebooks/feasibility.ipynb # preuve de faisabilité (TP53 / KRAS / RB1)
└── tests/
```

---

## Niveau avancé — `/ingest` vs `/ingest_fast`

L'endpoint `/ingest_fast` doit traiter un batch de séquences **au moins 30 % plus
vite** que la version naïve. Leviers prévus :

- **ThreadPoolExecutor / async (httpx)** pour paralléliser les téléchargements AFDB
  (charge I/O-bound — le levier le plus rentable) ;
- **Numba** pour les calculs numériques sur coordonnées atomiques (rayon de giration,
  distances — CPU-bound) ;
- **vectorisation NumPy** pour la composition en acides aminés.

Chronométrages sur batch de 1 et de 100 à documenter ici. *(À venir — étape 7.)*

---

## Feuille de route

- [x] **Étape 1** — preuve de faisabilité (pont UniProt → AlphaFold validé)
- [x] **Étape 2** — squelette du dépôt (3 zones, stack, Docker)
- [x] **Étape 3** — ingestion → zone raw (`scripts/ingest.py`)
- [ ] **Étape 4** — extraction de features → zone staging
- [ ] **Étape 5** — zone curated (DuckDB) + Random Forest + matrice de confusion
- [ ] **Étape 6** — endpoints FastAPI complets + `/ingest` naïf
- [ ] **Étape 7** — `/ingest_fast` optimisé (+30 %) + benchmarks

---

## Résultats du modèle

*À venir (étapes 5 et 7) : matrice de confusion, importance des features, et
comparaison de performance `/ingest` vs `/ingest_fast`.*

Une note d'honnêteté est attendue ici : si le modèle sépare bien « cancer vs normal »
mais peine sur « oncogène vs suppresseur », **ce n'est pas un échec, c'est un
résultat** — à présenter comme tel.