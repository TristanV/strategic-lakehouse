# 📦 Données du projet — Strategic Lakehouse

> Auteur : Tristan Vanrullen — 2026

---

## Dataset source

Le projet s'appuie sur le dataset public **Cleaned Retail Customer Dataset (SQL-based ETL)**, disponible sur Kaggle.  
Il simule l'environnement de données de **GlobalTrade Solutions** avec trois silos :

| Silo | Table / fichier | Contenu |
|---|---|---|
| ERP on-premise | `g_dim_products.csv` | Référentiel produits |
| ERP on-premise | `g_fact_sales.csv` | Transactions de ventes |
| CRM SaaS | `g_dim_customers.csv` | Référentiel clients |
| CRM SaaS | `g_crm_interactions.csv` | Historique interactions |
| Analytique | `g_sales_aggregated.csv` | Exports CSV agrégés |

---

## Structure attendue du dossier `data/`

```
data/
├── README.md                   ← Ce fichier
├── raw/                        ← Couche Bronze : données brutes non modifiées
│   ├── erp/
│   │   ├── g_dim_products.csv
│   │   └── g_fact_sales.csv
│   ├── crm/
│   │   ├── g_dim_customers.csv
│   │   └── g_crm_interactions.csv
│   └── analytics/
│       └── g_sales_aggregated.csv
├── silver/                     ← Couche Silver : données nettoyées et normalisées
│   ├── dim_products.parquet
│   ├── dim_customers.parquet
│   └── fact_sales.parquet
└── gold/                       ← Couche Gold : agrégats métier exposables
    ├── kpi_sales_by_region.parquet
    ├── kpi_top_customers.parquet
    └── kpi_product_performance.parquet
```

---

## Règles de gestion des données

- **Bronze** : aucune modification, ingestion verbatim avec timestamp d'ingestion
- **Silver** : typage strict, dédoublonnage, jointure référentiel, règles de qualité documentées
- **Gold** : agrégats métier calculés, conformes aux définitions du glossaire
- Les fichiers `.parquet` utilisent un schéma versionné (cf. `cadrage/`)
- Les données sensibles (PII) sont pseudonymisées dès la couche Silver

---

## Téléchargement du dataset

Dataset Kaggle : [Cleaned Retail Customer Dataset](https://www.kaggle.com/datasets)  
Télécharger et placer les fichiers dans `data/raw/` selon la structure ci-dessus.

---

*Tristan Vanrullen — 2026*
