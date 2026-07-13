# BioCycle Djerba — Dossier d'Ingénierie

> Cahier des charges industriel de la plateforme intelligente d'optimisation de
> l'alimentation de l'unité de biométhanisation de Djerba.

**Version du dossier :** 1.0 (draft en cours de rédaction)
**Date :** 2026-07-08
**Cabinet d'ingénierie :** Architecture logicielle · IA · IoT · Smart City · Méthanisation · DevOps · Cybersécurité · UX/UI
**Statut :** 🚧 En cours — aucun développement au-delà du prototype existant ne doit débuter avant validation de l'ensemble des livrables ci-dessous.

---

## Objet du dossier

Ce dossier constitue le **référentiel contractuel** à partir duquel une équipe de
développement doit pouvoir implémenter la plateforme BioCycle Djerba **sans laisser
d'hypothèse au développeur**. Chaque module y est spécifié fonctionnellement et
techniquement. Le dossier couvre à la fois :

- l'**existant** déjà construit (backend FastAPI, frontend React, socle IoT MQTT + WebSocket) ;
- la **cible industrielle** à atteindre (moteur IA de scoring, routage dynamique du camion, applications mobiles, modules Centre / Municipalité / Citoyen / Collecteur, prototype matériel).

## Livrables

| # | Document | Fichier | Statut |
|---|----------|---------|--------|
| 1 | Vision Produit | [01-vision-produit.md](01-vision-produit.md) | ✅ Rédigé |
| 2 | Cahier des charges fonctionnel | [02-cahier-fonctionnel.md](02-cahier-fonctionnel.md) | ⬜ À venir |
| 3 | Cahier des charges technique | [03-cahier-technique.md](03-cahier-technique.md) | ⬜ À venir |
| 4 | Étude d'architecture | [04-architecture.md](04-architecture.md) | ⬜ À venir |
| 5 | UML complet | [05-uml.md](05-uml.md) | ⬜ À venir |
| 6 | Base de données | [06-base-de-donnees.md](06-base-de-donnees.md) | ⬜ À venir |
| 7 | API Contract | [07-api-contract.md](07-api-contract.md) | ⬜ À venir |
| 8 | Architecture des microservices | [08-microservices.md](08-microservices.md) | ⬜ À venir |
| 9 | Plan de développement Sprint par Sprint | [09-roadmap-sprints.md](09-roadmap-sprints.md) | ⬜ À venir |

## Conventions du dossier

- **Langue :** français professionnel.
- **Identifiants d'exigence :** `EF-XXX` (exigence fonctionnelle), `ET-XXX` (exigence technique), `RG-XXX` (règle de gestion), `US-XXX` (user story).
- **Priorisation :** MoSCoW — `M` (Must), `S` (Should), `C` (Could), `W` (Won't-this-time).
- **Acteurs :** Hôtel, Restaurant, Grande surface, Citoyen, Collecteur indépendant, Chauffeur, Centre de méthanisation, Municipalité, Administrateur, Moteur IA (acteur système).
- **Unités :** masses en kg/tonnes, distances en km, temps en minutes, énergie en kWh, biogaz/méthane en m³, CO₂ en kg.

## Chiffres directeurs du projet

| Paramètre | Valeur | Source |
|-----------|--------|--------|
| Besoin quotidien de l'unité | **16,4 tonnes/jour** de biodéchets | Cahier des charges métier |
| Capacité utile du camion | **3,5 tonnes/rotation** | Spécification véhicule |
| Rotations théoriques/jour | ⌈16,4 / 3,5⌉ = **5 rotations** | Calcul dérivé |
| Fonctionnement | **24h/24 en 3 shifts** | Contrainte d'exploitation |
| Territoire | Île de Djerba (Tunisie) | Périmètre géographique |
