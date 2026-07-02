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

## 🚦 État d'avancement (2 juillet 2026)

| Couche | Statut | Fichiers |
|---|---|---|
| **Bronze** — Ingestion CSV → Parquet | ✅ Terminé | `src/bronze/ingest.py`, `src/bronze/generate_crm_interactions.py` |
| **Silver** — Nettoyage, typage, PII | ✅ Terminé | `src/silver/transform.py` |
| **Gold** — Agrégats KPI métier | 🔴 À faire | `src/gold/aggregate.py` (à créer) |
| **API** — FastAPI exposition KPI | 🔴 À faire | `api/main.py` (à créer) |
| **Tests pytest** | 🔴 À faire | `tests/` (à compléter) |
| **Qualité GX / Soda** | 🔴 À faire | — |
| **Lineage OpenLineage** | 🔴 À faire | — |
| **Présentation COMEX** | 🟡 Plan fait | `documents/roadmap.md` |

> 📋 Voir la [Roadmap complète](documents/roadmap.md) pour le détail des prochaines étapes.

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

---

### Étape 3 — Activer l'environnement

```bash
conda activate strategic-lakehouse
```

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

---

### Étape 5 — Installer dbt (adapter DuckDB)

```bash
pip install dbt-core dbt-duckdb
dbt --version
```

---

### Étape 6 — Configurer nbstripout (hook git)

```bash
nbstripout --install
```

---

### Étape 7 — Vérifier l'installation

```bash
python -c "import pandas, duckdb, fastapi, great_expectations; print('✅ Environnement OK')"
dbt --version
```

---

### Étape 8 — Lancer le pipeline Bronze → Silver

```bash
# 1. Générer les données Bronze (CSV → Parquet)
python src/bronze/ingest.py

# 2. Générer les interactions CRM synthétiques
python src/bronze/generate_crm_interactions.py

# 3. Transformer Bronze → Silver
python src/silver/transform.py
```

---

### Étape 9 — Lancer l'API FastAPI (exposition des KPI Gold)

> ⚠️ La couche Gold et l'API sont en cours d'implémentation.

```bash
uvicorn api.main:app --reload --port 8000
```

L'API sera accessible à `http://localhost:8000` — documentation interactive : `http://localhost:8000/docs`.

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
├── .gitignore
├── requirements.txt             ← Dépendances Python (pip)
├── cadrage/                     ← CDC fonctionnel, glossaire, cadrage
│   ├── README.md
│   ├── cdc_fonctionnel.md
│   └── glossaire_data.md
├── data/                        ← Jeux de données (non versionnés sauf .gitkeep)
│   ├── raw/                     ← CSV sources (ERP, CRM, analytics)
│   ├── bronze/                  ← Parquet bruts ingérés
│   │   ├── erp/
│   │   ├── crm/
│   │   └── analytics/
│   ├── silver/                  ← Parquet nettoyés et typés
│   └── gold/                    ← Parquet agrégats KPI (à créer)
├── documents/
│   └── roadmap.md               ← Roadmap et suivi d'avancement
├── src/
│   ├── __init__.py
│   ├── bronze/
│   │   ├── __init__.py
│   │   ├── ingest.py            ✅ CSV → Parquet avec métadonnées
│   │   ├── generate_crm_interactions.py  ✅ Données CRM synthétiques
│   │   └── profiling.py         ✅ Profil statistique Bronze
│   └── silver/
│       ├── __init__.py
│       └── transform.py         ✅ Nettoyage, typage, PII, jointures
├── src/gold/                    🔴 À créer
│   └── aggregate.py             ← KPI métier → data/gold/
├── api/                         🔴 À créer
│   ├── main.py                  ← Application FastAPI
│   └── routers/
│       └── kpi.py               ← Endpoints KPI
├── tests/                       🔴 À compléter
│   └── test_pipeline.py
└── dbt/                         🟡 Phase 3 optionnelle
    ├── dbt_project.yml
    └── models/
```

---

## 🏗️ Architecture cible — Modèle Médaille

```
Sources brutes (ERP on-premise, CRM SaaS, fichiers CSV)
        │
        ▼
  ┌─────────────┐
  │   BRONZE    │  ✅  Ingestion brute, format Parquet, traçabilité totale
  └──────┬──────┘      src/bronze/ingest.py + generate_crm_interactions.py
         ▼
  ┌─────────────┐
  │   SILVER    │  ✅  Nettoyage, typage, dédoublonnage, PII
  └──────┬──────┘      src/silver/transform.py
         ▼
  ┌─────────────┐
  │    GOLD     │  🔴  Agrégats métier, KPI → À implémenter
  └──────┬──────┘      src/gold/aggregate.py
         ▼
   API FastAPI   🔴  À implémenter → api/main.py
         ▼
   BI / Agents IA
```

---

## 🗺️ Les 4 phases du projet

| Phase | Intitulé | Statut |
|---|---|---|
| **1** | Bronze (ingestion) + Silver (transformation) | ✅ **Terminé** |
| **2** | Gold (KPI) + API FastAPI | 🔴 **À faire — priorité 1** |
| **3** | Tests pytest + Qualité GX/Soda + Lineage | 🔴 **À faire — priorité 2** |
| **4** | Présentation COMEX 15–20 slides + soutenance | 🟡 **Plan rédigé** |

---

## 🧰 Stack technique de référence

| Domaine | Outils retenus |
|---|---|
| Ingestion / ELT | Python, DuckDB, Pandas, PyArrow |
| Transformation | dbt (Data Build Tool) |
| Format ouvert | Apache Parquet / Iceberg |
| Qualité | Great Expectations, Soda |
| Lineage | OpenLineage |
| Exposition | FastAPI + Uvicorn |
| Tests | pytest, ruff |
| Orchestration | Apache Airflow |
| CI/CD | GitHub Actions |

---

## 📊 Dataset de référence

Le projet s'appuie sur le dataset **Cleaned Retail Customer Dataset (SQL-based ETL)**  
disponible sur Kaggle : tables `g_dim_products`, `g_fact_sales`, `g_dim_customers` + rapports analytiques CSV.  
Les interactions CRM (`g_crm_interactions`, ~20 000 lignes) sont générées synthétiquement par `src/bronze/generate_crm_interactions.py`.

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
