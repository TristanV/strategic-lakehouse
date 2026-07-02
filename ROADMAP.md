# 🗺️ ROADMAP — Strategic Lakehouse

> Projet Master 2 Data-IA — La Plateforme_ Marseille — 2026  
> Auteur : **Tristan Vanrullen**

---

## Statut global (2 juillet 2026)

| Couche / Composant | Statut | Tests | Notes |
|---|---|---|---|
| **Bronze** — Ingestion CSV → Parquet | ✅ Terminé | ✅ `test_bronze.py` (6 tests) | Métadonnées, idempotence, dtype str |
| **Silver** — Nettoyage, typage, PII | ✅ Terminé | ✅ `test_silver.py` (17 tests) | Typing, PII, dedup, intégrité réf., idempotence, total_amount > 0 |
| **Gold** — Agrégats KPI métier | ✅ Terminé | ✅ `test_gold.py` | KPI DuckDB → Parquet |
| **API FastAPI** — Exposition KPI | ✅ Terminé | ✅ `test_api.py` | Endpoints JSON, warm cache |
| **CI GitHub Actions** | ✅ Actif | — | lint + pytest + coverage |
| **Qualité Great Expectations** | 🟡 En cours | — | Sprint 3 — checkpoint Silver |
| **Qualité Soda** | 🔴 À faire | — | Sprint 3 — scan Bronze |
| **Data Lineage OpenLineage** | 🔴 À faire | — | Sprint 3 |
| **Orchestrateur pipeline** | 🔴 À faire | — | Sprint 3 — `src/pipeline.py` |
| **Présentation COMEX** | 🟡 Plan rédigé | — | Sprint 4 |

**Score tests :** 59 passed, 0 failed (2 juillet 2026 — 6 Bronze + 17 Silver + Gold + API)

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

- [x] `tests/test_silver.py` — **17 tests passés** (2 juillet 2026)
  - Typage colonnes (Int64 / float64 / datetime64)
  - Pseudonymisation PII (customer_name, email, phone)
  - Dédoublonnage (product_id, customer_id, sale_id)
  - Colonnes de linéage (_source_silo, _run_id, _silver_processed_at)
  - Intégrité référentielle fact_sales → dim_products / dim_customers
  - Idempotence (2 exécutions = même nb lignes)
  - Clés métier non-nulles
  - Règle métier : `total_amount > 0`
- [ ] **Great Expectations checkpoint Silver**
  - Expectation suite sur `g_fact_sales` : `total_amount > 0`, `quantity ≥ 1`, `customer_id` non-null
  - Expectation suite sur `g_dim_products` : `unit_price > 0`, `product_id` non-null, unicité
  - Rapport HTML GX généré dans `reports/gx/`
- [ ] **Soda scan Bronze**
  - Fichier `soda/bronze_checks.yml` : freshness, row count > 0, no-null sur clés
  - Exécution intégrée en CI avant la transformation Silver
- [ ] **OpenLineage — émission d’événements**
  - Décorateur `@emit_lineage` sur `ingest.py`, `transform.py`, `aggregate.py`
  - Transport : `FileTransport` (local) + optionnel `HttpTransport` vers Marquez
  - Validation : fichier NDJSON `lineage_events.jsonl` vérifié en test
- [ ] **`src/pipeline.py` — orchestrateur bout-en-bout**
  - Exécution séquentielle Bronze → Silver → Gold avec logs structurés
  - Argument CLI `--layer bronze|silver|gold|all`
  - `if __name__ == "__main__"` exécutable
  - Test d’intégration `tests/test_pipeline.py`

## Sprint 4 — Présentation COMEX + Soutenance (prochain)

- [ ] **Notebook de démonstration** `notebooks/demo_end_to_end.ipynb`
  - Cellules Bronze → Silver → Gold → appels API avec sorties visibles
  - Graphiques matplotlib/plotly des KPI Gold
- [ ] **Slides COMEX** (15–20 slides, plan rédigé dans `Strategic_Lakehouse_Plan_et_Veille.pdf`)
  - Contexte GlobalTrade (silos → lakehouse)
  - Architecture Medallion Bronze/Silver/Gold
  - Démo live API FastAPI
  - Résultats qualité (GX + Soda) et linéage (OpenLineage)
- [ ] **README final** — badge CI, instructions install/run, architecture diagram ASCII
- [ ] **Soutenance finale M2** — La Plateforme_, Marseille, 2026

---

## Architecture cible

```
CSV sources (ERP, CRM, Analytics)
        │
        ▼
  ┌─────────────┐
  │   BRONZE    │  ✅  src/bronze/ingest.py
  └──────┴──────┘      Parquet + métadonnées
         ▼
  ┌─────────────┐
  │   SILVER    │  ✅  src/silver/transform.py
  └──────┴──────┘      Nettoyage, typage, PII
         ▼
  ┌─────────────┐
  │    GOLD     │  ✅  src/gold/aggregate.py
  └──────┴──────┘      KPI métier DuckDB
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
