# 🗺️ ROADMAP — Strategic Lakehouse

> Projet Master 2 Data-IA — La Plateforme_ Marseille — 2026  
> Auteur : **Tristan Vanrullen**

---

## Statut global (3 juillet 2026)

| Couche / Composant | Statut | Tests | Notes |
|---|---|---|---|
| **Bronze** — Ingestion CSV → Parquet | ✅ Terminé | ✅ `test_bronze.py` (6 tests) | 5 tables, 97 789 lignes, 1.49s total |
| **Silver** — Nettoyage, typage, PII | ✅ Terminé | ✅ `test_silver.py` (17 tests) | 4 tables, 99 177 lignes |
| **Gold** — Agrégats KPI métier | ✅ Terminé | ✅ `test_gold.py` | 5 KPI, 18 704 lignes |
| **API FastAPI** — Exposition KPI | ✅ Terminé | ✅ `test_api.py` | Endpoints JSON, warm cache |
| **CI GitHub Actions** | ✅ Actif | — | lint + pytest + coverage |
| **Pipeline orchestrateur** | ✅ Terminé | ✅ `test_pipeline.py` (6p/1s) | CLI `--layer`, 1.49s bout-en-bout |
| **Qualité Great Expectations** | ✅ Terminé | ✅ `test_gx_checkpoint.py` | GX Core v1.x + rapports HTML Silver |
| **Qualité Soda** | 🔴 À faire | — | Sprint 3 |
| **Data Lineage OpenLineage** | 🔴 À faire | — | Sprint 3 |
| **Présentation COMEX** | 🟡 Plan rédigé | — | Sprint 4 |

**Score tests :** 65 passed, 0 failed, 1 skipped (2 juillet 2026)

---

## Sprint 1 — Bronze + Silver (terminé)

- [x] Ingestion CSV → Parquet avec métadonnées (`_ingested_at`, `_source_file`, `_source_silo`, `_run_id`)
- [x] Données CRM synthétiques (`generate_crm_interactions.py`)
- [x] Nettoyage Silver : typage strict, dédoublonnage, anonymisation PII SHA-256
- [x] Profiling Bronze (`profiling.py`)
- [x] Tests Bronze (6 tests) — idempotence, dtype, métadonnées, row count

## Sprint 2 — Gold + API (terminé)

- [x] Agrégats KPI métier en DuckDB → Parquet Gold
- [x] API FastAPI : `GET /kpi`, `GET /kpi/{name}`, `GET /health`
- [x] Tests Gold (couverture agrégats, types, non-vide)
- [x] Tests API (status, schéma, pagination, perf < 500 ms warm)
- [x] Fix CI dtype `str` / `string[pyarrow]` (Pandas 2.x)

## Sprint 3 — Qualité + Linéage (en cours)

- [x] `tests/test_silver.py` — **17 tests passés**
- [x] `src/pipeline.py` — **orchestrateur CLI Bronze→Silver→Gold**
  - 5 tables Bronze (97 789 lignes) + 4 Silver (99 177) + 5 Gold KPI (18 704) en **1.49s**
  - `--layer bronze|silver|gold|all` + `--log-level`
  - 6 tests passés, 1 skipped (gold seul sans Silver amont)
- [x] **Great Expectations — checkpoint Silver** ✅
  - `src/quality/gx_checkpoint.py` : suite Silver sur `fact_sales` et `dim_products`
  - Migration vers **GX Core v1.x** : `context.data_sources.pandas_default.read_dataframe(df)`
  - Rapport HTML dans `reports/gx/`
  - Test `tests/test_gx_checkpoint.py`
- [ ] **Soda scan Bronze** ← prochaine étape
  - `soda/bronze_checks.yml` : freshness, row count > 0, no-null clés
  - Exécution CI avant transformation Silver
- [ ] **OpenLineage — émission d'événements**
  - Décorateur `@emit_lineage` sur `ingest.py`, `transform.py`, `aggregate.py`
  - Transport `FileTransport` → `lineage_events.jsonl`
  - Test NDJSON vérifié en pytest

## Sprint 4 — Présentation COMEX + Soutenance (prochain)

- [ ] **Notebook de démonstration** `notebooks/demo_end_to_end.ipynb`
- [ ] **Slides COMEX** (30 slides, plan dans `Strategic_Lakehouse_Plan_et_Veille.pdf`)
- [ ] **README final** — badge CI, instructions install/run, architecture diagram
- [ ] **Soutenance finale M2** — La Plateforme_, Marseille, 2026

---

## Résultats pipeline (run confirmé, 2 juillet 2026)

```
🐙  Strategic Lakehouse — Résumé pipeline
----------------------------------------------------
  BRONZE      5 tables     97 789 lignes
    └ g_dim_products                    295
    └ g_fact_sales                   60 398
    └ g_dim_customers                18 484
    └ Customer_report_cleaned_data   18 482
    └ Product_report_cleaned_data       130
  SILVER      4 tables     99 177 lignes
    └ dim_products                      295
    └ dim_customers                  18 484
    └ fact_sales                     60 398
    └ crm_interactions               20 000
  GOLD        5 tables     18 704 lignes
    └ kpi_revenue_by_period               38
    └ kpi_revenue_by_segment              17
    └ kpi_avg_basket                  18 484
    └ kpi_top_products                   130
    └ kpi_crm_engagement                  35
----------------------------------------------------
  Durée totale : 1.49s
```

---

## Architecture cible

```
CSV sources (ERP, CRM, Analytics)
        │
        ▼
  ┌─────────────┐
  │   BRONZE    │  ✅  src/bronze/ingest.py
  └─────┤──────┘      5 tables, 97 789 lignes
         ▼
  ┌─────────────┐
  │   SILVER    │  ✅  src/silver/transform.py
  └─────┤──────┘      4 tables, 99 177 lignes
         ▼
  ┌─────────────┐
  │    GOLD     │  ✅  src/gold/aggregate.py
  └─────┤──────┘      5 KPI, 18 704 lignes
         ▼
  ┌─────────────┐
  │   API REST  │  ✅  api/main.py (FastAPI)
  └─────────────┘
         ▼
   BI / Agents IA
```

---

## Décisions techniques

| Décision | Choix | Justification |
|---|---|---|
| Format stockage | Apache Parquet | Columnar, compressé, compatible DuckDB/Spark |
| Moteur SQL | DuckDB | In-process, zero-config, OLAP performant |
| API | FastAPI | Async, typage Pydantic, OpenAPI auto-généré |
| Tests | pytest + ruff | Standard Python, coverage intégré |
| CI | GitHub Actions | Natif GitHub, gratuit, cache pip |
| Dtype Bronze | `dtype=str` CSV read | Aucun cast métier en couche brute |
| Pseudonymisation PII | SHA-256 (irréversible) | RGPD — pas de déchiffrement possible |
| Qualité données | Great Expectations + Soda | GX pour assertions Python, Soda pour checks SQL/YAML |
| Linéage | OpenLineage | Standard ouvert LF AI & Data, compatible dbt/Airflow |
| Orchestrateur | `src/pipeline.py` | CLI argparse, importable, testable, idempotent |
