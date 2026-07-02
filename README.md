# 💙 Strategic Lakehouse

> **Projet pédagogique : Strategic Lakehouse**  
> Transition d'un SI à l'ancienne vers une organisation et une architecture data-driven  
> Master 2 Data-IA — La Plateforme_ Marseille  
> Auteur : **Tristan Vanrullen** — 2026

[![CI](https://github.com/TristanV/strategic-lakehouse/actions/workflows/ci.yml/badge.svg)](https://github.com/TristanV/strategic-lakehouse/actions/workflows/ci.yml)

---

## 🎯 Contexte

Ce dépôt constitue des **éléments de correction et de référence** pour le projet Strategic Lakehouse, sujet du Master 2 Data-IA.  
Le cas d'étude fictif est **GlobalTrade Solutions**, entreprise dont le SI est fragmenté en trois silos (ERP on-premise, CRM SaaS, fichiers analytiques), et dont l'objectif est de devenir une organisation véritablement data-driven.

---

## 🚦 État d'avancement (2 juillet 2026)

| Couche | Statut | Tests |
|---|---|---|
| **Bronze** — Ingestion CSV → Parquet | ✅ Terminé | ✅ `test_bronze.py` (6 tests) |
| **Silver** — Nettoyage, typage, PII | ✅ Terminé | ⚠️ Pas de tests Silver |
| **Gold** — Agrégats KPI métier | ✅ Terminé | ✅ `test_gold.py` |
| **API FastAPI** — Exposition KPI JSON | ✅ Terminé | ✅ `test_api.py` |
| **CI GitHub Actions** | ✅ Actif | lint + pytest + coverage |
| **Qualité GX / Soda** | 🔴 À faire | — |
| **Data Lineage OpenLineage** | 🔴 À faire | — |
| **Présentation COMEX** | 🟡 Plan rédigé | — |

**Score tests :** 42 passed, 0 failed — voir la [ROADMAP.md](ROADMAP.md) pour le détail des sprints.

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

### Étape 2 — Créer l'environnement conda

```bash
conda create -n strategic-lakehouse python=3.11 -y
```

### Étape 3 — Activer l'environnement

```bash
conda activate strategic-lakehouse
```

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

### Étape 5 — Installer dbt (adapter DuckDB)

```bash
pip install dbt-core dbt-duckdb
dbt --version
```

### Étape 6 — Configurer nbstripout (hook git)

```bash
nbstripout --install
```

### Étape 7 — Vérifier l'installation

```bash
python -c "import pandas, duckdb, fastapi, great_expectations; print('✅ Environnement OK')"
dbt --version
```

---

### Lancer le pipeline Bronze → Silver

```bash
python src/bronze/ingest.py
python src/bronze/generate_crm_interactions.py
python src/silver/transform.py
```

### Lancer l'API FastAPI

```bash
uvicorn api.main:app --reload --port 8000
# Docs interactives : http://localhost:8000/docs
```

### Lancer les tests

```bash
pytest tests/ -v
ruff check src/ api/ tests/
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
| Bronze | `python src/bronze/ingest.py` |
| CRM synth. | `python src/bronze/generate_crm_interactions.py` |
| Silver | `python src/silver/transform.py` |
| API FastAPI | `uvicorn api.main:app --reload --port 8000` |
| Tests | `pytest tests/ -v` |
| Linting | `ruff check src/ api/ tests/` |
| Désactiver | `conda deactivate` |

---

## 📁 Structure du dépôt

```
strategic-lakehouse/
├── README.md                    ← Ce fichier
├── ROADMAP.md                   ← Historique des sprints + prochaines étapes
├── .gitignore
├── requirements.txt
├── .github/
│   └── workflows/
│       └── ci.yml               ← CI : lint (ruff) + tests (pytest + coverage)
├── cadrage/
│   ├── cdc_fonctionnel.md
│   └── glossaire_data.md
├── data/
│   ├── raw/                     ← CSV sources (ERP, CRM, analytics)
│   ├── bronze/                  ← Parquet bruts ingérés
│   ├── silver/                  ← Parquet nettoyés et typés
│   └── gold/                    ← Parquet agrégats KPI
├── src/
│   ├── bronze/
│   │   ├── ingest.py            ✅ CSV → Parquet + métadonnées
│   │   ├── generate_crm_interactions.py  ✅ CRM synthétique
│   │   └── profiling.py         ✅ Profil statistique Bronze
│   ├── silver/
│   │   └── transform.py         ✅ Nettoyage, typage, PII, jointures
│   └── gold/
│       └── aggregate.py         ✅ KPI métier DuckDB → Parquet
├── api/
│   └── main.py                  ✅ FastAPI — GET /kpi, GET /kpi/{name}, GET /health
└── tests/
    ├── conftest.py
    ├── test_bronze.py           ✅ 6 tests Bronze
    ├── test_gold.py             ✅ Tests Gold
    └── test_api.py              ✅ Tests API
```

---

## 🏗️ Architecture cible — Modèle Médaillon

```
Sources brutes (ERP on-premise, CRM SaaS, fichiers CSV)
        │
        ▼
  ┌─────────────┐
  │   BRONZE    │  ✅  Ingestion brute, format Parquet, traçabilité totale
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │   SILVER    │  ✅  Nettoyage, typage, dédoublonnage, PII
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │    GOLD     │  ✅  Agrégats métier, KPI DuckDB
  └──────┬──────┘
         ▼
   API FastAPI   ✅  GET /kpi — GET /kpi/{name} — GET /health
         ▼
   BI / Agents IA
```

---

## 🗺️ Phases du projet

| Phase | Intitulé | Statut |
|---|---|---|
| **1** | Bronze (ingestion) + Silver (transformation) | ✅ **Terminé** |
| **2** | Gold (KPI) + API FastAPI + CI | ✅ **Terminé** |
| **3** | Tests Silver + Qualité GX/Soda + Lineage | 🔴 **À faire** |
| **4** | Présentation COMEX + soutenance | 🟡 **Plan rédigé** |

---

## 🧰 Stack technique

| Domaine | Outils retenus |
|---|---|
| Ingestion / ELT | Python, DuckDB, Pandas, PyArrow |
| Transformation | dbt (Data Build Tool) |
| Format ouvert | Apache Parquet |
| Qualité | Great Expectations, Soda |
| Lineage | OpenLineage |
| Exposition | FastAPI + Uvicorn |
| Tests | pytest, ruff |
| CI/CD | GitHub Actions |

---

## 📊 Dataset de référence

Le projet s'appuie sur le dataset **Cleaned Retail Customer Dataset (SQL-based ETL)** disponible sur Kaggle : tables `g_dim_products`, `g_fact_sales`, `g_dim_customers` + rapports analytiques CSV.  
Les interactions CRM (`g_crm_interactions`, ~20 000 lignes) sont générées synthétiquement par `src/bronze/generate_crm_interactions.py`.

---

## 📚 Références clés

- [Databricks — Medallion Architecture](https://www.databricks.com/glossary/medallion-architecture)
- [OpenLineage](https://openlineage.io)
- [dbt Labs](https://docs.getdbt.com)
- [Great Expectations](https://greatexpectations.io)
- [Soda Core](https://www.soda.io/resources/soda-core)
- [AI Act EU](https://artificialintelligenceact.eu)

---

## 👤 Auteur

**Tristan Vanrullen** — Ingénieur IA · Data Scientist · Manager SI/Data  
[LinkedIn](https://www.linkedin.com/in/tristan-vanrullen/) · [GitHub](https://github.com/TristanV)  

*La Plateforme_ Marseille — 2026*
