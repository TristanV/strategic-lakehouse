# 🗺️ Roadmap — Strategic Lakehouse

> Auteur : Tristan Vanrullen — 2026  
> Projet : correction de référence — Master 2 Data-IA  
> Mis à jour : **2 juillet 2026**

---

## Objectif général

Faire évoluer GlobalTrade Solutions d'un SI fragmenté en trois silos vers une architecture data-driven de type Lakehouse, exposant des KPI fiables via API et ouvrant la voie aux usages IA (RAG, agents, analytique avancée).

---

## État d'avancement global

| Jalon | Statut | Dernière activité |
|---|---|---|
| Jalon 0 — Initialisation | ✅ **Terminé** | 2026-07-01 |
| Phase 1 — Bronze (ingestion) | ✅ **Terminé** | 2026-07-01 |
| Phase 1 — Silver (transformation) | ✅ **Terminé** | 2026-07-01 |
| Phase 2 — Gold (agrégats KPI) | 🔴 **À faire** | — |
| Phase 2 — API FastAPI | 🔴 **À faire** | — |
| Phase 3 — Qualité (GX / Soda) | 🔴 **À faire** | — |
| Phase 3 — Tests pytest | 🔴 **À faire** | — |
| Phase 3 — Lineage OpenLineage | 🔴 **À faire** | — |
| Phase 4 — dbt models | 🟡 **Optionnel / Phase 3** | — |
| Phase 4 — Présentation COMEX | 🟡 **En cours** (plan + veille ✅) | 2026-07-02 |

---

## Jalon 0 — Initialisation ✅

- [x] Prise en main du dataset Kaggle (`g_dim_products`, `g_dim_customers`, `g_fact_sales`, rapports analytiques)
- [x] Mise en place du dépôt Git (`main`, `.gitignore`, `requirements.txt`)
- [x] Environnement conda `strategic-lakehouse` (Python 3.11)
- [x] Structure des dossiers (`src/bronze/`, `src/silver/`, `data/bronze/`, `data/silver/`, `data/gold/`, `cadrage/`, `documents/`)
- [x] Cadrage fonctionnel (`cadrage/cdc_fonctionnel.md`, `cadrage/glossaire_data.md`)
- [x] Roadmap initiale

---

## Phase 1 — Bronze : ingestion brute ✅

Fichiers : `src/bronze/ingest.py`, `src/bronze/profiling.py`, `src/bronze/generate_crm_interactions.py`

- [x] Ingestion CSV → Parquet (format natif, aucune transformation métier)
- [x] Colonnes de traçabilité Bronze : `_ingested_at`, `_source_file`, `_source_silo`, `_run_id`
- [x] Détection automatique d'encodage (UTF-8 → Latin-1 fallback) pour `g_dim_customers`
- [x] Génération de données CRM synthétiques cohérentes (`g_crm_interactions`, ~20 000 lignes)
- [x] Profiling Bronze (`src/bronze/profiling.py`)
- [x] Données déposées dans `data/bronze/erp/`, `data/bronze/crm/`, `data/bronze/analytics/`

---

## Phase 1 — Silver : transformation et nettoyage ✅

Fichier : `src/silver/transform.py`

- [x] Nettoyage : suppression des doublons, gestion des valeurs nulles
- [x] Typage strict des colonnes (dates, numériques, catégorielles)
- [x] Dédoublonnage par clé métier
- [x] Pseudonymisation des données PII clients
- [x] Jointures préparatoires
- [x] Données déposées dans `data/silver/`

---

## Phase 2 — Gold + API FastAPI 🔴 Priorité 1

### Gold : agrégats KPI métier

Fichier à créer : `src/gold/aggregate.py`

- [ ] KPI 1 : chiffre d'affaires total et par période (`revenue_by_period`)
- [ ] KPI 2 : CA par région / segment client (`revenue_by_region`)
- [ ] KPI 3 : panier moyen et fréquence d'achat (`avg_basket_and_frequency`)
- [ ] KPI 4 : top produits par CA et par volume (`top_products`)
- [ ] KPI 5 : score d'engagement CRM par segment (`crm_engagement_by_segment`)
- [ ] Écriture des agrégats Gold en Parquet dans `data/gold/`

### API FastAPI

Fichiers à créer : `api/main.py`, `api/routers/kpi.py`

- [ ] Endpoint `GET /kpis/revenue` — CA total et par période
- [ ] Endpoint `GET /kpis/revenue/region` — CA par région
- [ ] Endpoint `GET /kpis/top-products` — top N produits
- [ ] Endpoint `GET /kpis/crm/engagement` — engagement CRM
- [ ] Endpoint `GET /health` — health check
- [ ] Documentation auto Swagger (`/docs`) et ReDoc (`/redoc`)
- [ ] Temps de réponse < 200 ms sur DuckDB Gold

---

## Phase 3 — Qualité, Tests, Lineage 🔴 Priorité 2

### Tests pytest

Fichiers à créer : `tests/test_bronze.py`, `tests/test_silver.py`, `tests/test_gold.py`, `tests/test_api.py`

- [ ] Tests unitaires Bronze (colonnes de métadonnées, types, non-vide)
- [ ] Tests unitaires Silver (complétude > 95 %, unicité des clés, types)
- [ ] Tests unitaires Gold (valeurs attendues des KPI, non-négatif, cohérence)
- [ ] Tests d'intégration API (codes HTTP, format JSON, latence)

### Qualité des données

- [ ] Suite Great Expectations ou Soda sur Silver
- [ ] Règles de qualité : complétude, unicité, plages de valeurs, formats
- [ ] Rapport de qualité exporté

### Data Lineage

- [ ] Instrumentation OpenLineage sur le pipeline (Bronze → Silver → Gold)
- [ ] Emission d'événements de run (`RunEvent`, `DatasetEvent`)

---

## Phase 3 (optionnelle) — dbt models 🟡

- [ ] Initialiser le projet dbt (`dbt init`, `dbt_project.yml`, `profiles.yml` DuckDB)
- [ ] Modèle `stg_erp_sales` (staging Silver)
- [ ] Modèle `mart_revenue_by_period` (Gold)
- [ ] Tests dbt (`not_null`, `unique`, `accepted_values`)
- [ ] Documentation dbt (`dbt docs generate`)

---

## Phase 4 — Présentation COMEX 🟡

- [x] Plan structuré de la présentation (30 slides, 4 chapitres + débat)
- [x] Bibliographie consolidée (85 sources vérifiées)
- [ ] Réalisation des slides (charte graphique, mascotte Octo, schémas)
- [ ] Démonstration live du POC (pipeline + API)
- [ ] Soutenance simulée (rôles CTO / CDO fictifs)
- [ ] Rapport final de projet

---

## Indicateurs de succès

| Indicateur | Cible | Statut |
|---|---|---|
| Pipeline reproductible en < 5 min | ✅ | 🟡 Bronze+Silver OK, Gold manquant |
| Qualité des données Silver > 95 % complétude | ✅ | 🟡 Transform OK, GX/Soda à valider |
| API Gold répond en < 200 ms sur un KPI | ✅ | 🔴 À implémenter |
| Catalogue documenté (description, owner, SLA) | ✅ | 🟡 cadrage/ présent, catalogue formel à faire |
| Tests CI passants sur main | ✅ | 🔴 Aucun test pytest pour l'instant |
| Présentation COMEX 15–20 slides | ✅ | 🟡 Plan fait, slides à produire |

---

## Prochaines étapes immédiates (Sprint 2 juillet)

1. **`src/gold/aggregate.py`** — calculer les 5 KPI métier depuis Silver via DuckDB, écrire en Parquet Gold
2. **`api/main.py` + `api/routers/kpi.py`** — API FastAPI exposant les KPI Gold en JSON
3. **`tests/`** — tests pytest Bronze + Silver + Gold + API
4. **Great Expectations ou Soda** — suite de qualité sur Silver
5. **OpenLineage** — instrumentation minimale du pipeline

---

*Tristan Vanrullen — La Plateforme_ Marseille — 2026*
