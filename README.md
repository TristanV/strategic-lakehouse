# 🐙 Strategic Lakehouse

> **Projet pédagogique : Strategic Lakehouse**  
> Transition d'un SI à l'ancienne vers une organisation et une architecture data-driven  
> Master 2 Data-IA — La Plateforme_ Marseille  
> Auteur : **Tristan Vanrullen** — 2026

---

## 🎯 Contexte

Ce dépôt constitue des **éléments de correction et de référence** pour le projet Strategic Lakehouse, sujet du Master 2 Data-IA).  
Le cas d'étude fictif est **GlobalTrade Solutions**, entreprise dont le SI est fragmenté en trois silos (ERP on-premise, CRM SaaS, fichiers analytiques), et dont l'objectif est de devenir une organisation véritablement data-driven.

---

## 📁 Structure du dépôt

```
strategic-lakehouse/
├── README.md                    ← Ce fichier
├── documents/                   ← Roadmap, planification, livrables
│   └── roadmap.md
├── data/                        ← Jeux de données du projet
│   └── README.md
└── cadrage/                     ← CDC fonctionnel, spécifications, cadrage
    └── README.md
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

## 🏗️ Architecture cible

L'architecture cible est un **Strategic Lakehouse** fondé sur le modèle médaille :

```
Sources brutes (ERP, CRM, CSV)
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
available on Kaggle : tables `g_dim_products`, `g_fact_sales`, `g_dim_customers` + CSV interactions.  

Voir [`data/README.md`](data/README.md) pour les détails.

---

## 📚 Références clés

- [DAMA-DMBOK](https://www.dama.org/cpages/body-of-knowledge) — Framework de gouvernance de la donnée
- [Databricks — Medallion Architecture](https://www.databricks.com/glossary/medallion-architecture) — Modèle Bronze/Silver/Gold
- [FranceNum — Piloter son entreprise par les données](https://www.francenum.gouv.fr) — Recommandations institutionnelles françaises
- [OpenLineage](https://openlineage.io) — Standard ouvert de data lineage
- [dbt Labs](https://docs.getdbt.com) — Transformation SQL versionnée
- [AI Act EU](https://artificialintelligenceact.eu) — Horizon réglementaire IA
- [Great Expectations](https://greatexpectations.io) — Tests qualité des données

---

## 👤 Auteur

**Tristan Vanrullen** — Ingénieur IA · Data Scientist · Manager SI/Data  
[LinkedIn](https://www.linkedin.com/in/tristan-vanrullen/) · [GitHub](https://github.com/TristanV)  

*La Plateforme_ Marseille — 2026*
