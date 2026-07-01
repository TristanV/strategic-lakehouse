# Glossaire Data — Strategic Lakehouse

> Auteur : Tristan Vanrullen — 2026

| Terme | Définition | Exemple |
|---|---|---|
| Donnée brute | Donnée ingérée sans modification depuis la source | CSV ERP exporté à J-1 |
| Donnée Silver | Donnée nettoyée, normalisée, validée | Client dédoublonné, typé, pseudonymisé |
| Donnée Gold | Agrégat métier calculé, exposable à la BI | Chiffre d'affaires par région par mois |
| Data lineage | Traçabilité source → transformation → consommation | Champ `created_at` lié à pipeline `ingest_erp` |
| Data steward | Gardien métier de la qualité d'un périmètre | Responsable des données clients |
| Data owner | Propriétaire métier d'un domaine de données | Directeur commercial |
| Data contract | Contrat explicite entre producteur et consommateur | Schéma, SLA, règles d'évolution |
| Catalogue | Inventaire des actifs data avec métadonnées | DataHub, Atlan |
| MDM | Master Data Management — référentiel maître | Référentiel client unique |
| KPI | Key Performance Indicator | Taux de rétention client |
| ETL | Extract-Transform-Load | Talend, Informatica |
| ELT | Extract-Load-Transform | dbt + Airbyte |
| Data observability | Surveillance de la santé des données | Monte Carlo, Soda |
| Time travel | Capacité à interroger un état passé des données | Delta Lake, Iceberg |
| ACID | Atomicité, Cohérence, Isolation, Durabilité | Garanties transactionnelles |
| SLA | Service Level Agreement | Fraîcheur < 24h, disponibilité 99,5% |
| RGPD | Règlement Général sur la Protection des Données | Droits d'accès, de rectification, d'effacement |
| Privacy by design | Intégration de la protection des données dès la conception | Pseudonymisation native en Silver |

---

*Tristan Vanrullen — 2026*
