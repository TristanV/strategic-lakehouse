# 🐙 Strategic Lakehouse

> **Projet pédagogique : Strategic Lakehouse**  
> Transition d'un SI à l'ancienne vers une organisation et une architecture data-driven  
> Master 2 Data-IA — La Plateforme_ Marseille  
> Auteur : **Tristan Vanrullen** — 2026

---

## 🎯 Contexte

Ce dépôt constitue des **éléments de correction et de référence** pour le projet Strategic Lakehouse, sujet du Master 2 Data-IA.  
Le cas d'étude fictif est **GlobalTrade Solutions**, entreprise dont le SI est fragmenté en trois silos (ERP on-premise, CRM SaaS, fichiers analytiques), et dont l'objectif est de devenir une organisation véritablement data-driven.

---

## ⚡ Installation — Environnement Conda `strategic-lakehouse`

### Prérequis

| Outil | Version minimale | Installation |
|---|---|---|
| [Miniconda](https://docs.conda.io/en/latest/miniconda.html) ou [Anaconda](https://www.anaconda.com/) | ≥ 23.x | [docs.conda.io](https://docs.conda.io/en/latest/miniconda.html) |
| Git | ≥ 2.40 | [git-scm.com](https://git-scm.com) |
| Python | **3.11** (géré par conda) | — |

> ⚠️ **Attention Windows** : utiliser **Anaconda Prompt** ou **Git Bash** pour toutes les commandes ci-dessous.

---

### Étape 1 — Cloner le dépôt

```bash
git clone https://github.com/TristanV/strategic-lakehouse.git
cd strategic-lakehouse
```

---

### Étape 2 — Créer l'environnement conda

```bash
conda create -n strategic-lakehouse python=3.11 -y
```

Cela crée un environnement isolé nommé `strategic-lakehouse` avec Python 3.11.  
Les environnements conda sont stockés dans `~/miniconda3/envs/` (ou `~/anaconda3/envs/`).

---

### Étape 3 — Activer l'environnement

```bash
conda activate strategic-lakehouse
```

Votre prompt doit afficher `(strategic-lakehouse)` en préfixe.

> ℹ️ Pour désactiver l'environnement en fin de session : `conda deactivate`

---

### Étape 4 — Mettre à jour pip et installer les dépendances

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Ce fichier installe toutes les bibliothèques du pipeline :
- **pandas, numpy, pyarrow, duckdb** — ingestion et transformation de données
- **fastapi, uvicorn, pydantic** — exposition des KPI via API REST
- **great-expectations, soda-core** — qualité et contrats de données
- **openlineage-python** — traçabilité du pipeline (data lineage)
- **jupyterlab, plotly, matplotlib, seaborn** — exploration et visualisation
- **pytest, ruff, mypy** — tests, linting, typage statique
- **nbstripout, python-dotenv, loguru** — utilitaires

> ⏱️ L'installation complète prend 3 à 8 minutes selon votre connexion.

---

### Étape 5 — Installer dbt (adapter DuckDB)

> `dbt-core` et `dbt-duckdb` sont installés **séparément** pour éviter les conflits de résolution de dépendances.

```bash
pip install dbt-core dbt-duckdb
```

Vérifier la version installée :

```bash
dbt --version
```

---

### Étape 6 — Configurer nbstripout (hook git)

`nbstripout` supprime automatiquement les outputs des notebooks Jupyter avant chaque commit, pour éviter de versionner des résultats d'exécution volumineux ou des données sensibles.

```bash
nbstripout --install
```

> Ce hook est local : il doit être réinstallé après chaque `git clone` ou `conda env create`.

---

### Étape 7 — Vérifier l'installation

```bash
python -c "import pandas, duckdb, fastapi, great_expectations; print('✅ Environnement OK')"
dbt --version
```

Résultat attendu :
```
✅ Environnement OK
Core:
  - installed: 1.x.x
  - latest:    1.x.x - Up to date!
```

---

### Étape 8 — Lancer JupyterLab (exploration)

```bash
jupyter lab
```

JupyterLab s'ouvre dans votre navigateur à `http://localhost:8888`.

---

### Étape 9 — Lancer l'API FastAPI (exposition des KPI Gold)

```bash
uvicorn api.main:app --reload --port 8000
```

L'API est accessible à `http://localhost:8000` — documentation interactive : `http://localhost:8000/docs`.

---

### 🔁 Gestion de l'environnement

#### Exporter l'environnement complet (reproductibilité)

```bash
conda env export > environment.yml
```

#### Recréer à partir de l'export

```bash
conda env create -f environment.yml
conda activate strategic-lakehouse
```

#### Réinitialiser l'environnement (repartir de zéro)

```bash
conda deactivate
conda env remove -n strategic-lakehouse
# puis reprendre à l'Étape 2
```

#### Mettre à jour toutes les dépendances

```bash
conda activate strategic-lakehouse
pip install --upgrade -r requirements.txt
```

---

### 📋 Résumé des commandes

| Étape | Commande |
|---|---|
| Cloner | `git clone https://github.com/TristanV/strategic-lakehouse.git` |
| Créer l'env | `conda create -n strategic-lakehouse python=3.11 -y` |
| Activer | `conda activate strategic-lakehouse` |
| Installer | `pip install --upgrade pip && pip install -r requirements.txt` |
| dbt | `pip install dbt-core dbt-duckdb` |
| Hook notebooks | `nbstripout --install` |
| Vérifier | `python -c "import pandas, duckdb, fastapi; print('OK')"` |
| JupyterLab | `jupyter lab` |
| API FastAPI | `uvicorn api.main:app --reload --port 8000` |
| Exporter env | `conda env export > environment.yml` |
| Désactiver | `conda deactivate` |
| Supprimer l'env | `conda env remove -n strategic-lakehouse` |

---

## 📁 Structure du dépôt

```
strategic-lakehouse/
├── README.md                    ← Ce fichier
├── .gitignore                   ← Fichiers ignorés par git
├── requirements.txt             ← Dépendances Python (pip)
├── environment.yml              ← Export conda (généré via conda env export)
├── documents/                   ← Roadmap, planification, livrables
│   └── roadmap.md
├── data/                        ← Jeux de données du projet
│   ├── raw/                     ← Données brutes (non versionnées)
│   ├── silver/                  ← Données nettoyées (non versionnées)
│   ├── gold/                    ← Agrégats métier (non versionnées)
│   └── README.md
├── cadrage/                     ← CDC fonctionnel, spécifications, cadrage
│   └── README.md
├── pipeline/                    ← Scripts Python Bronze → Silver → Gold
│   ├── bronze.py
│   ├── silver.py
│   └── gold.py
├── api/                         ← API FastAPI (exposition KPI Gold)
│   ├── main.py
│   └── routers/
├── tests/                       ← Pytest : pipeline, qualité, endpoints
│   └── test_pipeline.py
└── dbt/                         ← Transformations dbt (Phase 3)
    ├── dbt_project.yml
    └── models/
```

---

## 🗺️ Les 4 phases du projet

| Phase | Intitulé | Livrables principaux |
|---|---|---|
| **1** | Diagnostic SI + Benchmark archi | Cartographie, comparatif DWH/Lake/Lakehouse |
| **2** | Spécification technique | CDC MoSCoW, matrice risques, accessibilité |
| **3** | Conception + POC | Schémas C4/UML, pipeline Bronze→Silver→Gold→API |
| **4** | Présentation COMEX | 15-20 slides, soutenance CTO/CDO fictifs |

---

## 🏗️ Architecture cible — Modèle Médaille

```
Sources brutes (ERP on-premise, CRM SaaS, fichiers CSV)
        │
        ▼
  ┌─────────────┐
  │   BRONZE    │  Ingestion brute, format natif, traçabilité totale
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │   SILVER    │  Nettoyage, typage, dédoublonnage, jointures
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │    GOLD     │  Agrégats métier, KPI, exposition API / BI
  └──────┬──────┘
         ▼
   API Flask/FastAPI  ──▶  BI / Agents IA
```

---

## 🧰 Stack technique de référence

| Domaine | Outils retenus |
|---|---|
| Ingestion / ELT | Python, DuckDB, Pandas, Airbyte |
| Transformation | dbt (Data Build Tool) |
| Format ouvert | Apache Iceberg / Delta Lake / Parquet |
| Qualité | Great Expectations, Soda |
| Lineage | OpenLineage |
| Exposition | Flask / FastAPI |
| Orchestration | Apache Airflow |
| CI/CD | GitHub Actions |
| Observabilité | Grafana + Prometheus |

---

## 📊 Dataset de référence

Le projet s'appuie sur le dataset **Cleaned Retail Customer Dataset (SQL-based ETL)**  
disponible sur Kaggle : tables `g_dim_products`, `g_fact_sales`, `g_dim_customers` + CSV interactions.  

Voir [`data/README.md`](data/README.md) pour les détails de téléchargement et de structure.

---

## 📚 Références clés

- [DAMA-DMBOK](https://www.dama.org/cpages/body-of-knowledge) — Framework de gouvernance de la donnée
- [Databricks — Medallion Architecture](https://www.databricks.com/glossary/medallion-architecture) — Modèle Bronze/Silver/Gold
- [FranceNum — Piloter son entreprise par les données](https://www.francenum.gouv.fr) — Recommandations institutionnelles françaises
- [OpenLineage](https://openlineage.io) — Standard ouvert de data lineage
- [dbt Labs](https://docs.getdbt.com) — Transformation SQL versionnée et testée
- [Great Expectations](https://greatexpectations.io) — Tests qualité des données
- [Soda Core](https://www.soda.io/resources/soda-core) — Data contracts et règles de qualité
- [AI Act EU](https://artificialintelligenceact.eu) — Horizon réglementaire IA 2026

---

## 👤 Auteur

**Tristan Vanrullen** — Ingénieur IA · Data Scientist · Manager SI/Data  
[LinkedIn](https://www.linkedin.com/in/tristan-vanrullen/) · [GitHub](https://github.com/TristanV)  

*La Plateforme_ Marseille — 2026*
