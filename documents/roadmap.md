# 🗺️ Roadmap — Strategic Lakehouse

> Auteur : Tristan Vanrullen — 2026  
> Projet : correction de référence — Master 2 Data-IA

---

## Objectif général

Faire évoluer GlobalTrade Solutions d'un SI fragmenté en trois silos vers une architecture data-driven de type Lakehouse, exposant des KPI fiables via API et ouvrant la voie aux usages IA (RAG, agents, analytique avancée).

---

## Jalon 0 — Initialisation (Semaine 1–2)

- [ ] Prise en main du dataset Kaggle et des sources simulées
- [ ] Mise en place du dépôt Git et des standards de contribution
- [ ] Réunion de lancement (kick-off) avec simulation des parties prenantes
- [ ] Atelier de cadrage : cartographie des silos, enjeux, ambition

---

## Phase 1 — Diagnostic (Semaine 3–5)

- [ ] Cartographie fonctionnelle et applicative du SI existant
- [ ] Analyse comparative : DWH vs Data Lake vs Lakehouse vs Data Mesh
- [ ] Qualification des problèmes : incohérences, qualité, traçabilité
- [ ] Identification des données critiques et des référentiels stratégiques
- [ ] **Livrable** : Rapport de diagnostic + recommandation 1 page

---

## Phase 2 — Spécification (Semaine 6–9)

- [ ] Rédaction du Cahier Des Charges fonctionnel (MoSCoW)
- [ ] Définition des critères de qualité et SLA par flux
- [ ] Matrice des risques (technique, organisationnel, réglementaire)
- [ ] Section accessibilité (RGAA / WCAG 2.1 AA)
- [ ] Conformité RGPD et AI Act : obligations applicables
- [ ] **Livrable** : CDC complet + matrice risques

---

## Phase 3 — Conception et POC (Semaine 10–16)

- [ ] Schémas d'architecture C4 (Context, Container, Component)
- [ ] Diagrammes UML : flux de données, séquences, composants
- [ ] Implémentation du pipeline Bronze → Silver → Gold
- [ ] Tests de qualité avec Great Expectations ou Soda
- [ ] Endpoint API Flask / FastAPI exposant un KPI Gold
- [ ] Interface HTML minimaliste accessible
- [ ] README reproductible + tests en CI (GitHub Actions)
- [ ] **Livrable** : POC fonctionnel + documentation technique

---

## Phase 4 — Présentation COMEX (Semaine 17–20)

- [ ] Construction de la présentation 15–20 slides
- [ ] Préparation de la démonstration live du POC
- [ ] Soutenance simulée (CTO / CDO fictifs)
- [ ] Rapport final de projet
- [ ] **Livrable** : Slides + soutenance + rapport

---

## Indicateurs de succès

| Indicateur | Cible |
|---|---|
| Pipeline reproductible en < 5 min | ✅ |
| Qualité des données Silver > 95 % complétude | ✅ |
| API Gold répond en < 200 ms sur un KPI | ✅ |
| Catalogue documenté (description, owner, SLA) | ✅ |
| Tests CI passants sur main | ✅ |
| Présentation COMEX 15–20 slides | ✅ |

---

*Tristan Vanrullen — 2026*
