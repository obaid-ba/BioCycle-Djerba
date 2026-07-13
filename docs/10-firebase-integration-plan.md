# Plan — Firebase Integration Layer (biodéchets par device)

> **Statut : PLANIFIÉ, non implémenté.** Ce document fige l'architecture cible.
> Aucun code Firebase n'existe encore. À implémenter contre un **stub** tant que
> le contrat de données du Raspberry Pi n'est pas figé.

## 1. Contexte & changement de modèle

Révision de la source de la quantité : elle **ne vient plus (uniquement) d'une
saisie manuelle**. Chaque hôtel dispose d'un **Raspberry Pi** qui pousse ses
mesures dans **Firebase**. À la création d'une Collection Request, le backend
doit récupérer **la dernière lecture Firebase** du device de l'hôtel et en faire
un **snapshot** dans PostgreSQL.

> ⚠️ Ce modèle réintroduit de l'IoT (Raspberry → Firebase), différent de l'IoT
> MQTT précédemment retiré. Firebase agit comme **buffer découplé** : le backend
> lit Firebase, il ne parle jamais directement au Raspberry.

## 2. Principe directeur : **lecture seule, jamais d'écriture**

La couche `integrations/firebase/` est **strictement read-only**. Le backend ne
crée, ne modifie et ne supprime **jamais** de données dans Firebase — c'est le
Raspberry Pi qui écrit. Toute écriture est un bug d'architecture. Le snapshot
vit uniquement dans PostgreSQL (source de vérité applicative).

```
  Raspberry Pi (hôtel)                Firebase (buffer)            Backend (nous)
  ───────────────────      push       ─────────────────   read-only   ───────────
  mesure poids/qualité  ───────────►  /devices/{id}/…   ◄───────────  snapshot → PG
                          (WRITE)                          (READ ONLY)
```

## 3. Structure de fichiers cible

```
backend/app/integrations/firebase/
├── __init__.py
├── client.py         # FirebaseReader (Protocol) + FirebaseRESTReader (vrai client, read-only)
├── stub.py           # StubFirebaseReader — lectures déterministes locales (dev/tests)
├── schemas.py        # DeviceReading (DTO normalisé de ce que le Raspberry écrit)
└── config.py         # settings Firebase (URL, credentials) — via env, jamais commit
```

Modèle : ajouter **`firebase_device_id`** (nullable, unique) sur `Hotel`
(migration dédiée). Mapping hôtel → device.

Snapshot : la Collection Request stocke déjà `declared_weight_kg`. On ajoutera
la provenance : `source` (`manual` | `firebase`), `firebase_reading_at`
(horodatage de la lecture d'origine), éventuellement `firebase_raw` (JSONB) pour
la traçabilité.

## 4. Interface (le point de couture)

Comme pour l'IA (`AIScorer`), on dépend d'une **interface**, pas de Firebase
directement — le service reste testable et le vrai client est branchable sans
toucher au métier.

```python
class FirebaseReader(Protocol):
    async def latest_reading(self, device_id: str) -> DeviceReading | None: ...

class DeviceReading(BaseSchema):
    device_id: str
    weight_kg: float
    recorded_at: datetime
    # champs additionnels selon le contrat Raspberry (humidité, etc.) — À FIGER
```

- **`StubFirebaseReader`** : renvoie une lecture déterministe (hash du device_id),
  comme le stub IA. Utilisé en dev/tests jusqu'à livraison du contrat.
- **`FirebaseRESTReader`** : lit `GET {FIREBASE_DB_URL}/devices/{device_id}/latest.json`
  (Realtime DB) ou un doc Firestore. **Aucune méthode d'écriture exposée.**

## 5. Flux à la création d'une Collection Request

```
Hotel crée une demande
        │
        ▼
  hotel.firebase_device_id renseigné ?
        │
   ┌────┴─────┐
   │ oui      │ non
   ▼          ▼
FirebaseReader     Fallback : saisie manuelle
.latest_reading()  (declared_weight_kg du body)
   │
   ├─ lecture trouvée → snapshot : declared_weight_kg = reading.weight_kg,
   │                    source="firebase", firebase_reading_at=reading.recorded_at
   │
   └─ rien / erreur  → selon politique (voir §6)
        │
        ▼
  suite normale : scoring IA, distance, file opérateur…
```

## 6. Décisions à figer avant implémentation

1. **Contrat de données Raspberry** : chemin exact + schéma du document Firebase
   (ex. `/devices/{id}/latest = {weight_kg, timestamp, humidity?, …}`). **Bloquant.**
2. **Firebase indisponible / device muet** : bloquer la création (erreur) OU
   retomber sur la saisie manuelle ? (recommandé : fallback manuel, non bloquant).
3. **Fraîcheur** : rejeter une lecture trop ancienne (seuil configurable) ?
4. **Auth Firebase** : clé de service (Firestore/Realtime DB REST) — stockée en
   env/secret, **jamais** commitée. Realtime DB vs Firestore ?
5. **Manuel vs Firebase** : le champ manuel disparaît-il du formulaire hôtel une
   fois Firebase en place, ou reste-t-il en fallback ? (impacte l'UI).

## 7. Tests prévus

- `StubFirebaseReader` déterministe (unitaire).
- Création avec device mappé → snapshot correct (weight, source, timestamp).
- Création sans device → fallback manuel inchangé.
- Lecture Firebase absente/en erreur → politique §6.2 respectée (pas de 500).
- **Garantie read-only** : le client n'expose aucune méthode d'écriture (test
  d'interface / revue).

## 8. Effort estimé

~1 à 1,5 jour une fois le contrat Firebase (§6.1) figé : migration
`firebase_device_id` + colonnes de provenance, interface + stub + client REST,
branchement dans `RequestService.create`, tests. Sans le contrat, on ne code que
l'interface + le stub (~2 h) pour débloquer le reste.
