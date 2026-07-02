# 🗺️ ROADMAP — Strategic Lakehouse

> Projet Master 2 Data-IA — La Plateforme_ Marseille — 2026  
> Auteur : **Tristan Vanrullen**

---

## Statut global (2 juillet 2026)

| Couche / Composant | Statut | Tests | Notes |
|---|---|---|---|
| **Bronze** — Ingestion CSV → Parquet | ✅ Terminé | ✅ `test_bronze.py` (6 tests) | Métadonnées, idempotence, dtype str |
| **Silver** — Nettoyage, typage, PII | ✅ Terminé | ⚠️ Pas de tests Silver | `src/silver/transform.py` |
| **Gold** — Agrégats KPI métier | ✅ Terminé | ✅ `test_gold.py` | KPI DuckDB → Parquet |
| **API FastAPI** — Exposition KPI | ✅ Terminé | ✅ `test_api.py` | Endpoints JSON, warm cache |
| **CI GitHub Actions** | ✅ Actif | — | lint + pytest + coverage |
| **Qualité GX / Soda** | 🔴 À faire | — | Phase 3 |
| **Data Lineage OpenLineage** | 🔴 À faire | — | Phase 3 |
| **Présentation COMEX** | 🟡 Plan rédigé | — | 15–20 slides |

**Score tests :** 42 passed, 0 failed (2 juillet 2026)

---

## Sprint 1 — Bronze + Silver (terminé)

- [x] Ingestion CSV → Parquet avec métadonnées (`_ingested_at`, `_source_file`, `_source_silo`, `_run_id`)
- [x] Données CRM synthétiques (`generate_crm_interactions.py`)
- [x] Nettoyage Silver : typage, dédoublonnage, anonymisation PII
- [x] Profiling Bronze (`profiling.py`)
- [x] Tests Bronze (6 tests) — idempotence, dtype, métadonnées, row count

## Sprint 2 — Gold + API (terminé)

- [x] Agrégats KPI métier en DuckDB → Parquet Gold
- [x] API FastAPI : `GET /kpi`, `GET /kpi/{name}`, `GET /health`
- [x] Tests Gold (couverture agrégats, types, non-vide)
- [x] Tests API (status, schéma, pagination, perf < 500 ms warm)
- [x] Fix CI dtype `str` / `string[pyarrow]` (Pandas 2.x)

## Sprint 3 — Qualité + Lineage (à faire)

- [ ] `tests/test_silver.py` — typage colonnes, intégrité référentielle, no-dup
- [ ] Great Expectations checkpoint sur Silver (`g_fact_sales` : `sales > 0`, `quantity ≥ 1`, `customer_id` non-null)
- [ ] Soda scan sur Bronze → rapport qualité
- [ ] OpenLineage : émission d'events Bronze→Silver→Gold→API
- [ ] `src/pipeline.py` — orchestrateur bout-en-bout Bronze→Silver→Gold

## Sprint 4 — Présentation COMEX (à faire)

- [ ] Slides 15–20 pages : contexte GlobalTrade → architecture → démo live API
- [ ] Notebook de démonstration end-to-end
- [ ] Soutenance finale M2

---

## Architecture cible

```
CSV sources (ERP, CRM, Analytics)
        │
        ▼
  ┌─────────────┐
  │   BRONZE    │  ✅  src/bronze/ingest.py
  └──────┬──────┘      Parquet + métadonnées
         ▼
  ┌─────────────┐
  │   SILVER    │  ✅  src/silver/transform.py
  └──────┬──────┘      Nettoyage, typage, PII
         ▼
  ┌─────────────┐
  │    GOLD     │  ✅  src/gold/aggregate.py
  └──────┬──────┘      KPI métier DuckDB
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
